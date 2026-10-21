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
- El rol Cliente solo ve SUS pedidos (por el correo de su cuenta); si intenta
  abrir el detalle de un pedido ajeno recibe 404.
- ``/tareas/`` ya no es un tablero: redirige aquí (se conserva el nombre de la
  ruta para no romper enlaces viejos).
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from . import busqueda
from .models import ESTADOS_KANBAN, Pedido
from .permisos import es_solo_cliente, puede, seccion_requerida
from .views_site import _render

#: Columnas del tablero (estado calculado del pedido), en orden.
COLUMNAS = (
    ("pendiente", "Pendiente"),
    ("en proceso", "En proceso"),
    ("completado", "Completado"),
)

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


# ---- Helpers (funciones, no clases) --------------------------------------

def _pedidos_queryset(request=None):
    """Pedidos vigentes con sus relaciones, tareas y actividades precargadas."""
    consulta = (
        Pedido.objects.filter(activo=True)
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


def _tarjeta(pedido):
    """Datos de la tarjeta del pedido para el tablero."""
    actividades = _actividades_de(pedido)
    total = len(actividades)
    completadas = sum(1 for actividad in actividades if actividad.estado == "completado")
    estado = estado_del_pedido(pedido)
    vencida = bool(pedido.fecha_limite and pedido.fecha_limite < _hoy())
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
        "url_detalle": reverse("kanview:pedido-detalle", args=[pedido.pk]),
        "url_actividades": f"{reverse('kanview:tarea-crear')}?pedido={pedido.pk}",
        "tareas": [
            {
                "pk": tarea.pk,
                "nombre": tarea.nombre,
                "estado": tarea.get_estado_display(),
                "url": reverse("kanview:tarea-detalle", args=[tarea.pk]),
            }
            for tarea in pedido.tareaspedido_set.all()
        ],
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
    estado = estado_del_pedido(pedido)
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
        estados_kanban=ESTADOS_KANBAN,
        **busqueda.contexto(request, "Buscar procesos, clientes o trabajadores...", "procesos"),
    )


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
        # Un detalle no tiene lista que filtrar: el header muestra su título.
        cabecera_titulo=f"Pedido {pedido.codigo_pedido}",
        mostrar_buscador=False,
    )


@seccion_requerida("pedidos")
def redirigir_a_procesos(request):
    """``/tareas/`` ya no es un tablero: lleva al único kanban («Procesos»)."""
    return redirect("kanview:pedidos-tablero")
