"""Avisos reales del taller para la campana del header.

Un helper (`notificaciones`) calcula avisos a partir de datos que ya existen y
otro (`contexto_header`) suma las notificaciones persistentes de la tabla
`Notificacion`. Se expone a todas las plantillas con el context processor
`kanview.notificaciones.contexto_header` (ver `config/settings.py`), así que
ninguna vista repite estas consultas.

Avisos que se generan:

- Tareas vigentes vencidas (fecha fin pasada y estado distinto de completado).
- Pedidos activos con fecha límite vencida o que vence en los próximos
  `DIAS_AVISO_ENTREGA` días.
- Pedidos activos sin evidencias cargadas.
- Productos por debajo del umbral de stock bajo (``Producto.cantidad``).

El rol Cliente no ve los avisos internos del taller: solo los de sus pedidos
(lo que sí puede abrir).
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .correo import enviar_correo
from .models import Empleado, Notificacion, Pedido, Producto, TareasPedido
from .permisos import es_solo_cliente, puede

#: Mismo umbral que usa la pantalla de existencias para «Stock Bajo».
UMBRAL_STOCK_BAJO = 10

#: Un pedido cuya fecha límite cae dentro de estos días avisa en la campana.
DIAS_AVISO_ENTREGA = 3

#: Avisos por tipo que se listan en el panel (el contador cuenta todos).
MAX_POR_TIPO = 6


# ---- Constructores de cada aviso ------------------------------------------

def _aviso(tipo, icono, texto, url):
    """Aviso listo para la plantilla (tipo, icono Material, texto y enlace)."""
    return {"tipo": tipo, "icono": icono, "texto": texto, "url": url}


def _tareas_vencidas(hoy):
    """Tareas vigentes con la fecha fin pasada y que no están completadas."""
    consulta = (
        TareasPedido.objects.filter(activo=True, fecha_fin__lt=hoy, id_pedido__activo=True)
        .exclude(estado="completado")
        .select_related("id_pedido")
        .order_by("fecha_fin", "nombre")
    )
    url = reverse("kanview:tareas")
    avisos = [
        _aviso(
            "tarea",
            "assignment_late",
            f"La tarea «{tarea.nombre}» venció el {tarea.fecha_fin:%d/%m/%Y} "
            f"(pedido {tarea.id_pedido.codigo_pedido}).",
            url,
        )
        for tarea in consulta[:MAX_POR_TIPO]
    ]
    return consulta.count(), avisos


def _pedidos_por_vencer(pedidos, hoy):
    """Pedidos activos con fecha límite vencida o a punto de vencer."""
    limite = hoy + timedelta(days=DIAS_AVISO_ENTREGA)
    consulta = (
        pedidos.filter(fecha_limite__isnull=False, fecha_limite__lte=limite)
        .select_related("id_cliente")
        .order_by("fecha_limite", "codigo_pedido")
    )
    avisos = []
    for pedido in consulta[:MAX_POR_TIPO]:
        dias = (pedido.fecha_limite - hoy).days
        if dias < 0:
            texto = (
                f"El pedido {pedido.codigo_pedido} pasó su fecha límite "
                f"({pedido.fecha_limite:%d/%m/%Y}) hace {-dias} día(s)."
            )
            icono = "event_busy"
        elif dias == 0:
            texto = f"El pedido {pedido.codigo_pedido} vence hoy ({pedido.fecha_limite:%d/%m/%Y})."
            icono = "event_upcoming"
        else:
            texto = (
                f"El pedido {pedido.codigo_pedido} vence en {dias} día(s) "
                f"({pedido.fecha_limite:%d/%m/%Y})."
            )
            icono = "event_upcoming"
        avisos.append(
            _aviso(
                "pedido",
                icono,
                texto,
                reverse("kanview:pedido-detalle", args=[pedido.pk]),
            )
        )
    return consulta.count(), avisos


def _pedidos_sin_evidencias(pedidos):
    """Pedidos activos que todavía no tienen ninguna imagen en su galería."""
    consulta = pedidos.filter(galeria__isnull=True).distinct().order_by("id")
    url = reverse("kanview:pedidos-tablero")
    avisos = [
        _aviso(
            "evidencia",
            "photo_library",
            f"El pedido {pedido.codigo_pedido} no tiene evidencias cargadas.",
            url,
        )
        for pedido in consulta[:MAX_POR_TIPO]
    ]
    return consulta.count(), avisos


def _stock_bajo():
    """Productos vigentes en el umbral de stock bajo (stock = ``Producto.cantidad``)."""
    consulta = (
        Producto.objects.filter(activo=True, cantidad__lte=UMBRAL_STOCK_BAJO)
        .order_by("cantidad", "nombre")
    )
    url = reverse("kanview:inventario")
    avisos = [
        _aviso(
            "inventario",
            "production_quantity_limits" if producto.cantidad <= 0 else "inventory_2",
            (
                f"Producto agotado: {producto.nombre} (0 unidades disponibles)."
                if producto.cantidad <= 0
                else f"Stock bajo: {producto.nombre} "
                f"({producto.cantidad} unidad(es) disponibles)."
            ),
            url,
        )
        for producto in consulta[:MAX_POR_TIPO]
    ]
    return consulta.count(), avisos


# ---- API pública -----------------------------------------------------------

def notificaciones(usuario):
    """``{"total": n, "avisos": [...]}`` con los avisos reales de ``usuario``.

    ``total`` cuenta todos los avisos (el número de la campana) y ``avisos``
    trae como mucho ``MAX_POR_TIPO`` por tipo para el panel. Sin avisos,
    ``total`` es 0 y la plantilla no pinta el contador.
    """
    if not usuario or not usuario.is_authenticated:
        return {"total": 0, "avisos": []}

    hoy = timezone.localdate()
    solo_cliente = es_solo_cliente(usuario)

    pedidos = Pedido.objects.filter(activo=True, estado="activo")
    if solo_cliente:
        pedidos = pedidos.filter(id_cliente__correo__iexact=usuario.email)

    generadores = []
    # El Cliente no entra a tareas ni a inventario: no se le avisa de eso.
    if not solo_cliente:
        generadores.append(lambda: _tareas_vencidas(hoy))
    generadores.append(lambda: _pedidos_por_vencer(pedidos, hoy))
    generadores.append(lambda: _pedidos_sin_evidencias(pedidos))
    if not solo_cliente:
        generadores.append(_stock_bajo)

    total = 0
    avisos = []
    for generar in generadores:
        cuantos, lista = generar()
        total += cuantos
        avisos.extend(lista)

    return {"total": total, "avisos": avisos}


def contexto_header(request):
    """Context processor: deja los avisos y los datos de cuenta en el header.

    Se registra en ``config/settings.py`` para que TODAS las pantallas (también
    las del CRUD, que heredan de ``crud_base.html``) pinten la misma campana sin
    que cada vista tenga que pasar nada.
    """
    usuario = getattr(request, "user", None)
    datos = notificaciones(usuario)
    if not usuario or not usuario.is_authenticated:
        return datos

    nombre = usuario.get_full_name() or usuario.get_username()
    persistentes = list(
        Notificacion.objects.filter(usuario=usuario, leida=False)
        .order_by("-fecha_creacion", "-id")[:MAX_POR_TIPO]
    )
    avisos_persistentes = [
        {
            "id": aviso.pk,
            "tipo": aviso.tipo,
            "icono": ICONOS_NOTIFICACION.get(aviso.tipo, "notifications"),
            "texto": aviso.mensaje,
            "url": aviso.url,
            "persistente": True,
        }
        for aviso in persistentes
    ]
    total = datos["total"] + Notificacion.objects.filter(usuario=usuario, leida=False).count()
    avisos = avisos_persistentes + datos["avisos"]
    return {
        **datos,
        "avisos": avisos,
        "avisos_total": total,
        "avisos_restantes": max(0, total - len(avisos)),
        "notificaciones_persistentes": len(persistentes),
        "url_marcar_notificaciones": reverse("kanview:notificaciones-leer"),
        "usuario_nombre": nombre,
        "usuario_correo": usuario.email or usuario.get_username(),
        "rol_usuario": _rol(usuario),
        "puede_configuracion": puede(usuario, "configuracion"),
    }


def _rol(usuario):
    """Rol real del usuario (`rol_principal` de permisos.py), tolerante a fallos."""
    from .permisos import rol_principal

    return rol_principal(usuario)


#: Icono Material asociado a cada tipo de notificación persistente.
ICONOS_NOTIFICACION = {
    "pedido": "shopping_bag",
    "aprobacion": "verified",
    "rechazo": "cancel",
    "tarea": "assignment",
    "actividad": "task_alt",
    "multimedia": "perm_media",
    "factura": "receipt_long",
    "sistema": "info",
    "seguridad": "shield",
}


def crear_notificacion(usuario, tipo, mensaje, url=""):
    """Crea una notificación para una cuenta activa."""
    if usuario is None or not getattr(usuario, "is_active", False):
        return None
    return Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo[:40],
        mensaje=mensaje[:255],
        url=(url or "")[:500],
    )


def _usuarios_staff():
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(
        is_active=True,
        groups__name__in=("Administrador", "Secretaria"),
    ).distinct()


def notificar_staff(tipo, mensaje, url=""):
    """Notifica en la campana a Administración y Secretaría."""
    return [crear_notificacion(usuario, tipo, mensaje, url) for usuario in _usuarios_staff()]


def notificar_cliente(cliente, tipo, mensaje, url="", asunto=None, enviar_email=True):
    """Notifica al cliente por campana si tiene cuenta y por correo si se pide."""
    creada = crear_notificacion(getattr(cliente, "usuario", None), tipo, mensaje, url)
    correo = (getattr(cliente, "correo", "") or "").strip()
    enviado = False
    if correo and enviar_email:
        enviado = enviar_correo(
            asunto or "Kanview · Actualización de tu pedido",
            mensaje,
            [correo],
        )
    return creada, enviado


def notificar_empleado(empleado, tipo, mensaje, url="", asunto=None):
    """Notifica al trabajador; si no tiene cuenta, usa su correo o avisa al staff."""
    if empleado is None:
        return notificar_staff(tipo, mensaje, url)
    creada = crear_notificacion(getattr(empleado, "usuario", None), tipo, mensaje, url)
    correo = (getattr(empleado, "correo", "") or "").strip()
    enviado = False
    if getattr(empleado, "usuario", None) is None and correo:
        enviado = enviar_correo(
            asunto or "Kanview · Actividad asignada",
            mensaje,
            [correo],
        )
    if getattr(empleado, "usuario", None) is None and not correo:
        notificar_staff(tipo, mensaje, url)
    return creada, enviado


def notificar_area(cargo, tipo, mensaje, url="", excepto=None):
    """Notifica a todos los trabajadores activos de un área (cargo)."""
    empleados = Empleado.objects.filter(activo=True, cargo=cargo)
    if excepto is not None:
        empleados = empleados.exclude(pk=excepto)
    for empleado in empleados:
        notificar_empleado(empleado, tipo, mensaje, url)
