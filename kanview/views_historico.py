"""Histórico: log de los pedidos completados (los suyos, para el cliente).

Cuando un proceso se marca como completado queda registrado en el histórico de
usuarios. Aquí el cliente encuentra sus pedidos finalizados y la bitácora de
cada uno (creación, aprobación, tareas y finalización con su factura); el
personal del taller ve el histórico completo.
"""

from .models import Factura
from .permisos import es_solo_cliente, seccion_requerida
from .views_pedidos import _pedidos_queryset, estado_visible
from .views_site import _render


def _entradas_de(pedido):
    """Bitácora del pedido, del registro más reciente al más antiguo."""
    entradas = []
    for entrada in pedido.historial.all():
        entradas.append({
            "fecha": entrada.fecha_creacion.strftime("%d/%m/%Y"),
            "hora": entrada.hora_creacion.strftime("%H:%M") if entrada.hora_creacion else "",
            "usuario": (
                entrada.usuario.get_full_name() or entrada.usuario.get_username()
            ) if entrada.usuario else "Sistema",
            "accion": entrada.get_accion_display() if hasattr(entrada, "get_accion_display") else entrada.accion.replace("_", " ").capitalize(),
            "detalle": entrada.detalle,
        })
    return entradas


def _registro(pedido):
    """Datos del pedido completado ya listos para la plantilla."""
    try:
        factura = pedido.factura
    except Factura.DoesNotExist:
        factura = None
    return {
        "pedido": pedido,
        "factura_numero": factura.numero if factura else "",
        "total": factura.total if factura else pedido.subtotal,
        "entradas": _entradas_de(pedido),
    }


@seccion_requerida("pedidos")
def historico(request):
    """Log de pedidos completados: los del cliente o todos los del taller."""
    registros = [
        _registro(pedido)
        for pedido in _pedidos_queryset(request)
        if estado_visible(pedido) == "completado"
    ]
    return _render(
        request,
        "kanview/historico.html",
        "Histórico",
        registros=registros,
        total=len(registros),
        es_cliente=es_solo_cliente(request.user),
        mostrar_buscador=False,
    )
