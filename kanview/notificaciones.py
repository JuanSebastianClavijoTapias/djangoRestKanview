"""Avisos reales del taller para la campana del header.

Un único helper (`notificaciones`) calcula el contador y la lista del panel a
partir de datos que ya existen; no hay tabla de notificaciones ni nada
inventado. Se expone a todas las plantillas con el context processor
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

from .models import Pedido, Producto, TareasPedido
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
            "inventory_2",
            f"Stock bajo: {producto.nombre} "
            f"({producto.cantidad} unidad(es) disponibles).",
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
    return {
        **datos,
        "avisos_total": datos["total"],
        "avisos_restantes": max(0, datos["total"] - len(datos["avisos"])),
        "usuario_nombre": nombre,
        "usuario_correo": usuario.email or usuario.get_username(),
        "rol_usuario": _rol(usuario),
        "puede_configuracion": puede(usuario, "configuracion"),
    }


def _rol(usuario):
    """Rol real del usuario (`rol_principal` de permisos.py), tolerante a fallos."""
    from .permisos import rol_principal

    return rol_principal(usuario)
