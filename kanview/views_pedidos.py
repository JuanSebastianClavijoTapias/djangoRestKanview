"""Tablero único de procesos (FBV) conectado a datos reales de ``Pedido``.

Convención del proyecto: funciones (no clases), decoradas con
``@seccion_requerida`` y renderizadas con el helper ``_render`` de views_site.

Un solo kanban para todo el taller:

- Las **columnas** son el estado del pedido, calculado de sus actividades con
  la función pura ``estado_del_pedido`` (no se inventa ningún campo de etapa).
- Cada **tarjeta** es un pedido: código, producto, cliente, fecha límite,
  avance (actividades completadas / total) y las actividades **agrupadas por
  trabajador**.
- Cada actividad abre el **modal de detalle** y desde ahí se cambia su estado
  (POST a ``kanview:actividad-estado``).

Reglas que aplican aquí:

- Solo se muestran pedidos ``activo=True``: desactivar un pedido lo saca del
  tablero.
- Los pedidos de clientes desactivados tampoco se muestran: al desactivar un
  cliente, sus pedidos anteriores desaparecen de tableros y listados.
- El rol Cliente solo ve SUS pedidos (por el correo de su cuenta); si intenta
  abrir el detalle de un pedido ajeno recibe 404.
- Las tarjetas las mueve el Administrador (todas) y el Trabajador (solo las de
  sus procesos).
- Un pedido solo pasa a «Completado» si ya se realizaron sus tareas: al
  finalizar se genera su factura, su pago se refleja en Finanzas y el pedido
  queda en el histórico.
- Las tareas y sus actividades se gestionan en el módulo «Tareas».
"""

import json

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import busqueda, historial
from .auditoria import registrar as registrar_auditoria
from .facturacion import crear_factura
from .formato import moneda_cop
from .models import ESTADOS_KANBAN, ESTADOS_PEDIDO_KANBAN, Actividades, Administrador, AnalisisFinanciero, Empleado, Pedido
from .notificaciones import notificar_cliente, notificar_staff
from .permisos import (
    SECCION_ESCRITURA,
    es_administracion,
    es_administrador,
    es_solo_cliente,
    es_trabajador,
    puede,
    seccion_requerida,
)
from .views_site import _render

#: Columnas del tablero de pedidos, en orden.
COLUMNAS = ESTADOS_PEDIDO_KANBAN

#: Texto del modal cuando un campo viene vacío.
SIN_DATO = "Sin dato"


# ---- Cálculo del estado (función pura, testeable) -------------------------

def _actividades_de(pedido):
    """Todas las actividades de las tareas de un pedido (sin tocar la BD de más)."""
    actividades = []
    for tarea in pedido.tareaspedido_set.all():
        actividades.extend(tarea.actividades_set.all())
    return actividades


def estado_del_pedido(pedido):
    """Estado del pedido derivado de sus actividades.

    - Sin actividades                         -> ``pendiente``
    - Todas completadas                       -> ``completado``
    - Alguna que no está pendiente            -> ``en proceso``
    - Resto (todas pendientes)                -> ``pendiente``
    """
    actividades = _actividades_de(pedido)
    total = len(actividades)
    if total == 0:
        return "pendiente"
    if all(actividad.estado == "completado" for actividad in actividades):
        return "completado"
    if any(actividad.estado != "pendiente" for actividad in actividades):
        return "en proceso"
    return "pendiente"


def etiqueta_estado(estado):
    """Nombre visible de un estado calculado."""
    return dict(COLUMNAS).get(estado, estado.title())


def estado_visible(pedido):
    """Estado del tablero: el manual si existe; si no, el derivado de actividades."""
    return pedido.estado_kanban or estado_del_pedido(pedido)


# ---- Reglas de movimiento y finalización ---------------------------------


def _empleado_de(usuario):
    """Registro de Empleado vinculado a la cuenta (o ``None``)."""
    return getattr(usuario, "empleado_kanview", None)


def _proceso_del_trabajador(empleado, pedido):
    """True si el trabajador participa del pedido (asignado o con trabajo en él)."""
    if empleado is None:
        return False
    if pedido.id_empleado_id == empleado.pk:
        return True
    return pedido.tareaspedido_set.filter(
        Q(id_empleado=empleado) | Q(actividades__id_empleado=empleado)
    ).exists()


def _puede_mover_tarjeta(usuario, pedido):
    """El Administrador mueve cualquier tarjeta; el Trabajador solo las suyas."""
    if es_administrador(usuario):
        return True
    if not es_trabajador(usuario):
        return False
    return _proceso_del_trabajador(_empleado_de(usuario), pedido)


def error_de_finalizacion(pedido):
    """Mensaje si el pedido aún no puede marcarse como completado.

    Un proceso solo se marca completado si ya se realizaron sus tareas (y las
    actividades de cada tarea).
    """
    tareas = pedido.tareaspedido_set.filter(activo=True)
    if not tareas.exists():
        return (
            "El pedido no tiene tareas registradas: registra y completa sus "
            "tareas antes de marcarlo como completado."
        )
    pendientes = tareas.exclude(estado="completado").count()
    if pendientes:
        return (
            f"El pedido tiene {pendientes} tarea(s) sin completar. "
            "Completa y confirma cada tarea antes de marcarlo como completado."
        )
    actividades = Actividades.objects.filter(id_tarea__in=tareas, activo=True).exclude(estado="completado").count()
    if actividades:
        return (
            f"El pedido tiene {actividades} actividad(es) sin completar. "
            "Completa cada actividad antes de marcarlo como completado."
        )
    return ""


def _registrar_finalizacion(request, pedido):
    """Al finalizar un pedido: factura, pago reflejado en Finanzas e histórico.

    Cada vez que una tarjeta pasa a «Completado» se genera su factura y un
    ingreso amarrado al pedido en el módulo Finanzas, y el pedido queda en el
    histórico de usuarios.
    """
    factura, _creada = crear_factura(pedido, request.user)
    if not pedido.registros_financieros.filter(activo=True).exists():
        AnalisisFinanciero.objects.create(
            fecha=timezone.localdate(),
            gastos=0,
            fuentes_ingresos=factura.total,
            fuente_ingreso="directa",
            productos_vendidos=pedido.cantidad or 1,
            id_pedido=pedido,
            id_administrador=Administrador.objects.filter(usuario=request.user).first(),
        )
    historial.registrar(
        pedido,
        "pedido_completado",
        f"Pedido {pedido.codigo_pedido} finalizado: todas sus tareas fueron realizadas. "
        f"Factura {factura.numero} generada por {moneda_cop(factura.total)}.",
        request.user,
    )
    registrar_auditoria(
        request, "finalizar", "Pedido", pedido,
        f"Pedido {pedido.codigo_pedido} finalizado y facturado ({factura.numero}).",
    )
    return factura


# ---- Helpers (funciones, no clases) --------------------------------------

def _pedidos_queryset(request=None):
    """Pedidos vigentes con sus relaciones, tareas y actividades precargadas."""
    consulta = (
        Pedido.objects.filter(activo=True, id_cliente__activo=True)
        .select_related("id_cliente", "id_empleado", "id_producto")
        .prefetch_related(
            "galeria",
            "solicitudes_modificacion",
            "historial__usuario",
            "tareaspedido_set__actividades_set__id_empleado",
        )
        .order_by("-id")
    )
    if request is not None and es_solo_cliente(request.user):
        consulta = consulta.filter(id_cliente__correo__iexact=request.user.email)
    return consulta


#: Vistas de la pantalla de procesos: el tablero y la tabla usan el MISMO queryset.
VISTAS = ("kanban", "lista")


def pedidos_filtrados(request, q=None):
    """Queryset único de la pantalla: vigentes, búsqueda del header y rol.

    La búsqueda cubre código y descripción del pedido, cliente, producto y los
    trabajadores (de la tarea y de la actividad).
    """
    if q is None:
        q = busqueda.texto(request)
    consulta = _pedidos_queryset(request)
    if not q:
        return consulta
    consulta = consulta.filter(
        Q(codigo_pedido__icontains=q)
        | Q(descripcion__icontains=q)
        | Q(id_cliente__nombre__icontains=q)
        | Q(id_producto__nombre__icontains=q)
        | Q(id_empleado__nombre__icontains=q)
        | Q(tareaspedido__id_empleado__nombre__icontains=q)
        | Q(tareaspedido__actividades__id_empleado__nombre__icontains=q)
    )
    return consulta.distinct()


def _vista(request):
    """``kanban`` | ``lista`` según ``?vista=`` (por defecto, el tablero)."""
    elegida = (request.GET.get("vista") or "").strip().lower()
    return elegida if elegida in VISTAS else "kanban"


def url_vista(request, vista):
    """Enlace GET a la otra vista conservando el resto de la query (q, filtros)."""
    parametros = request.GET.copy()
    parametros["vista"] = vista
    return f"?{parametros.urlencode()}"


def _texto(valor, vacio=SIN_DATO):
    """Texto limpio para el modal (nada de campos vacíos ni None)."""
    limpio = (valor or "").strip() if isinstance(valor, str) else valor
    return limpio if limpio else vacio


def _fecha(valor):
    """Fecha corta para el modal, o el texto de 'sin dato'."""
    return valor.strftime("%d/%m/%Y") if valor else SIN_DATO


def _detalle_actividad(actividad):
    """Detalle que el modal pinta para una actividad del tablero."""
    tarea = actividad.id_tarea
    pedido = tarea.id_pedido if tarea else None
    trabajador = actividad.id_empleado or (tarea.id_empleado if tarea else None)
    return {
        "tipo": "Actividad",
        "nombre": _texto(actividad.nombre),
        "descripcion": _texto(actividad.descripcion, "Sin descripción"),
        "estado": _texto(actividad.get_estado_display(), "Sin estado"),
        "codigo": actividad.estado,
        "url_estado": reverse("kanview:actividad-estado", args=[actividad.pk]),
        "fecha_inicio": _fecha(actividad.fecha_inicio),
        "fecha_fin": _fecha(actividad.fecha_fin),
        "pedido": _texto(pedido.codigo_pedido) if pedido else SIN_DATO,
        "cliente": _texto(pedido.id_cliente.nombre) if pedido else SIN_DATO,
        "empleado": _texto(trabajador.nombre) if trabajador else "Sin asignar",
        "tarea": _texto(tarea.nombre) if tarea else "",
    }


def _actividad_tarjeta(actividad):
    """Actividad ya lista para pintar dentro de la tarjeta del pedido."""
    return {
        "pk": actividad.pk,
        "nombre": actividad.nombre,
        "estado": actividad.get_estado_display(),
        "codigo": actividad.estado,
        "detalle_id": f"actividad-{actividad.pk}",
    }


def _grupos_por_trabajador(actividades):
    """Agrupa las actividades por trabajador, conservando el orden de nombre."""
    grupos = {}
    for actividad in actividades:
        trabajador = actividad.id_empleado
        clave = trabajador.pk if trabajador else 0
        grupo = grupos.setdefault(clave, {
            "trabajador": trabajador.nombre if trabajador else "Sin asignar",
            "cargo": trabajador.get_cargo_display() if trabajador else "Sin trabajador asignado",
            "iniciales": (trabajador.nombre[:2].upper() if trabajador else "?"),
            "actividades": [],
        })
        grupo["actividades"].append(_actividad_tarjeta(actividad))
    return sorted(grupos.values(), key=lambda grupo: grupo["trabajador"].lower())


def _tareas_del_pedido(pedido):
    """Tareas visibles en la tarjeta y datos para su modal de actividades."""
    tarjetas = []
    modales = {}
    for tarea in pedido.tareaspedido_set.all():
        if not tarea.activo:
            continue
        actividades = [a for a in tarea.actividades_set.all() if a.activo]
        total = len(actividades)
        completadas = sum(1 for a in actividades if a.estado == "completado")
        responsable = tarea.id_empleado
        if responsable is None:
            responsable = next((a.id_empleado for a in actividades if a.id_empleado), None)
        cargo = responsable.get_cargo_display() if responsable else "Sin trabajador asignado"
        iniciales = responsable.nombre[:2].upper() if responsable else "?"
        titulos_grupo = {
            "pendiente": "Pendientes",
            "en progreso": "En progreso",
            "completado": "Completadas",
        }
        grupos = [
            {
                "clave": clave,
                "titulo": titulos_grupo[clave],
                "actividades": [
                    {
                        "pk": actividad.pk,
                        "nombre": actividad.nombre,
                        "descripcion": actividad.descripcion,
                        "estado": actividad.get_estado_display(),
                        "empleado": (
                            actividad.id_empleado.nombre
                            if actividad.id_empleado
                            else "Sin asignar"
                        ),
                        "cargo": (
                            actividad.id_empleado.get_cargo_display()
                            if actividad.id_empleado
                            else "Sin trabajador asignado"
                        ),
                        "detalle_id": f"actividad-{actividad.pk}",
                    }
                    for actividad in actividades
                    if actividad.estado == clave
                ],
            }
            for clave, titulo in ESTADOS_KANBAN
        ]
        tarjetas.append({
            "pk": tarea.pk,
            "nombre": tarea.nombre,
            "descripcion": tarea.descripcion,
            "estado": tarea.estado,
            "estado_etiqueta": tarea.get_estado_display(),
            "responsable": responsable.nombre if responsable else "Sin asignar",
            "cargo": cargo,
            "iniciales": iniciales,
            "total": total,
            "completadas": completadas,
            "avance": round(completadas * 100 / total) if total else 0,
            "detalle_id": f"tarea-{tarea.pk}",
            "url": reverse("kanview:tarea-detalle", args=[tarea.pk]),
        })
        modales[f"tarea-{tarea.pk}"] = {
            "nombre": tarea.nombre,
            "descripcion": tarea.descripcion,
            "estado": tarea.get_estado_display(),
            "responsable": responsable.nombre if responsable else "Sin asignar",
            "cargo": cargo,
            "fecha_inicio": _fecha(tarea.fecha_inicio),
            "fecha_fin": _fecha(tarea.fecha_fin),
            "grupos": grupos,
        }
    return tarjetas, modales


def _tarjeta(pedido):
    """Datos de la tarjeta del pedido para el tablero."""
    actividades = _actividades_de(pedido)
    total = len(actividades)
    completadas = sum(1 for actividad in actividades if actividad.estado == "completado")
    estado = estado_visible(pedido)
    vencida = bool(pedido.fecha_limite and pedido.fecha_limite < _hoy())
    tareas, tareas_modal = _tareas_del_pedido(pedido)
    return {
        "pk": pedido.pk,
        "codigo": pedido.codigo_pedido,
        "producto": pedido.id_producto.nombre,
        "cliente": pedido.id_cliente.nombre,
        "fecha_limite": pedido.fecha_limite.strftime("%d/%m/%Y") if pedido.fecha_limite else "Sin fecha límite",
        "vencida": vencida,
        "estado": estado,
        "estado_etiqueta": etiqueta_estado(estado),
        "estado_aprobacion": pedido.estado_aprobacion,
        "estado_aprobacion_etiqueta": pedido.get_estado_aprobacion_display(),
        "total": total,
        "completadas": completadas,
        "avance": round(completadas * 100 / total) if total else 0,
        "grupos": _grupos_por_trabajador(actividades),
        "sin_actividades": total == 0,
        "sin_tareas": not tareas,
        "tareas_total": len(tareas),
        "tareas_completadas": sum(1 for tarea in tareas if tarea["estado"] == "completado"),
        "tareas_pendientes": sum(1 for tarea in tareas if tarea["estado"] != "completado"),
        "url_detalle": reverse("kanview:pedido-detalle", args=[pedido.pk]),
        "url_estado": reverse("kanview:pedido-estado", args=[pedido.pk]),
        "url_actividades": f"{reverse('kanview:tarea-crear')}?pedido={pedido.pk}",
        "tareas": tareas,
        "tareas_modal": tareas_modal,
    }


def _hoy():
    """Fecha de hoy (se aísla para poder probar la marca de «vencida»)."""
    from django.utils import timezone

    return timezone.localdate()


def _fila_lista(pedido):
    """Una fila de la tabla: los datos del pedido ya listos para el template."""
    actividades = _actividades_de(pedido)
    total = len(actividades)
    completadas = sum(1 for actividad in actividades if actividad.estado == "completado")
    estado = estado_visible(pedido)
    return {
        "pk": pedido.pk,
        "codigo": pedido.codigo_pedido,
        "cliente": pedido.id_cliente.nombre,
        "producto": pedido.id_producto.nombre,
        "estado": etiqueta_estado(estado),
        "fecha_limite": pedido.fecha_limite.strftime("%d/%m/%Y") if pedido.fecha_limite else "Sin fecha límite",
        "avance": f"{completadas}/{total} actividades" if total else "Sin actividades cargadas",
        "aprobacion": pedido.get_estado_aprobacion_display(),
        "url": reverse("kanview:pedido-detalle", args=[pedido.pk]),
    }


# ---- Vistas ---------------------------------------------------------------

@seccion_requerida("pedidos")
def pedidos_tablero(request):
    """Tablero único de procesos, con las actividades agrupadas por trabajador.

    El buscador del header filtra en el servidor con ``?q=`` por código del
    pedido, cliente, producto o trabajador.
    """
    q = busqueda.texto(request)
    pedidos = list(pedidos_filtrados(request, q))
    vista = _vista(request)

    tarjetas = [_tarjeta(pedido) for pedido in pedidos]
    tareas_modales = {}
    for tarjeta, pedido in zip(tarjetas, pedidos):
        # Solo el administrador mueve todas; el trabajador, las de SUS procesos.
        tarjeta["puede_mover"] = _puede_mover_tarjeta(request.user, pedido)
        tareas_modales.update(tarjeta.pop("tareas_modal", {}))
    columnas = [
        {
            "clave": clave,
            "titulo": titulo,
            "pedidos": [tarjeta for tarjeta in tarjetas if tarjeta["estado"] == clave],
        }
        for clave, titulo in COLUMNAS
    ]

    detalles = {}
    for pedido in pedidos:
        for tarea in pedido.tareaspedido_set.all():
            for actividad in tarea.actividades_set.all():
                detalles[f"actividad-{actividad.pk}"] = _detalle_actividad(actividad)

    return _render(
        request,
        "kanview/pedidos_tablero.html",
        "Procesos",
        pedidos=pedidos,
        columnas=columnas,
        tarjetas=tarjetas,
        total_pedidos=len(pedidos),
        # Conmutador Kanban / Lista: enlaces GET, sin JavaScript.
        vista=vista,
        url_kanban=url_vista(request, "kanban"),
        url_lista=url_vista(request, "lista"),
        filas_pedidos=[_fila_lista(pedido) for pedido in pedidos] if vista == "lista" else [],
        detalle_modales=detalles,
        tareas_modales=tareas_modales,
        puede_gestionar=puede(request.user, SECCION_ESCRITURA["pedidos"]),
        puede_mover=es_administrador(request.user) or es_trabajador(request.user),
        es_trabajador=es_trabajador(request.user),
        es_cliente=es_solo_cliente(request.user),
        estados_kanban=ESTADOS_KANBAN,
        **busqueda.contexto(request, "Buscar procesos, clientes o trabajadores...", "procesos"),
    )


@seccion_requerida("pedidos")
@require_POST
def pedido_estado(request, pk):
    """Cambia el estado manual del pedido desde el tablero (drag & drop).

    El Administrador mueve cualquier tarjeta y el Trabajador solo las de SUS
    procesos; el resto de roles (incluido el Cliente) ven el tablero sin
    arrastre. Pasar a «Completado» exige que las tareas del pedido ya se hayan
    realizado: al finalizar se factura el pedido, su pago se refleja en
    Finanzas y queda registrado en el histórico.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if not _puede_mover_tarjeta(request.user, pedido):
        return JsonResponse(
            {"error": "Solo el administrador y el trabajador asignado pueden mover esta tarjeta."},
            status=403,
        )
    try:
        cuerpo = json.loads(request.body or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        cuerpo = {}
    estado = (cuerpo.get("estado") or request.POST.get("estado") or "").strip()
    validos = dict(ESTADOS_PEDIDO_KANBAN)
    if estado not in validos:
        return JsonResponse({"error": "Estado no válido."}, status=400)
    if estado == "completado":
        error = error_de_finalizacion(pedido)
        if error:
            return JsonResponse({"error": error}, status=400)
    ya_finalizado = pedido.historial.filter(accion="pedido_completado").exists()
    anterior = estado_visible(pedido)
    pedido.estado_kanban = estado
    pedido.save(update_fields=["estado_kanban"])
    if anterior != estado:
        historial.registrar(
            pedido, "estado_tablero",
            f"Pedido movido de «{etiqueta_estado(anterior)}» a «{etiqueta_estado(estado)}».",
            request.user,
        )
        registrar_auditoria(
            request, "mover", "Pedido", pedido,
            f"Pedido {pedido.codigo_pedido}: {etiqueta_estado(anterior)} → {etiqueta_estado(estado)}",
        )
        notificar_cliente(
            pedido.id_cliente,
            "pedido",
            f"Tu pedido {pedido.codigo_pedido} pasó a «{etiqueta_estado(estado)}».",
            reverse("kanview:pedido-detalle", args=[pedido.pk]),
            asunto="Kanview · Estado de tu pedido",
            enviar_email=False,
        )
        notificar_staff(
            "pedido",
            f"Pedido {pedido.codigo_pedido}: {etiqueta_estado(estado)}.",
            reverse("kanview:pedido-detalle", args=[pedido.pk]),
        )
    # Al pasar a «Completado» se factura el pedido, su pago se refleja en
    # Finanzas y el pedido queda en el histórico (una sola vez).
    if estado == "completado" and not ya_finalizado:
        _registrar_finalizacion(request, pedido)
    return JsonResponse({
        "ok": True,
        "pedido": pedido.pk,
        "estado": estado,
        "etiqueta": etiqueta_estado(estado),
    })


@seccion_requerida("pedidos")
def pedido_detalle(request, pk):
    """Detalle de un pedido (active="Procesos"). Un pedido ajeno da 404."""
    pedido = get_object_or_404(_pedidos_queryset(request), pk=pk)

    return _render(
        request,
        "kanview/pedidos_detalle.html",
        "Procesos",
        pedido=pedido,
        puede_gestionar=puede(request.user, "gestion-pedidos"),
        es_cliente=es_solo_cliente(request.user),
        puede_revisar_solicitudes=es_administracion(request.user),
        # Trabajadores que se pueden asignar al aprobar el pedido.
        empleados=Empleado.objects.filter(activo=True).order_by("nombre"),
        # Un detalle no tiene lista que filtrar: el header muestra su título.
        cabecera_titulo=(
            f"Mi pedido {pedido.codigo_pedido}"
            if es_solo_cliente(request.user)
            else f"Pedido {pedido.codigo_pedido}"
        ),
        mostrar_buscador=False,
    )
