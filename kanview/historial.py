"""Registro automático del historial de pedidos."""

from django.utils import timezone

from .models import Historial


def registrar(pedido, accion, detalle="", usuario=None):
    """Añade una entrada al historial del pedido con los datos congelados."""
    if pedido is None:
        return None
    ahora = timezone.localtime()
    return Historial.objects.create(
        hora_creacion=ahora.time().replace(microsecond=0),
        fecha_creacion=ahora.date(),
        id_cliente=pedido.id_cliente,
        id_empleado=pedido.id_empleado,
        id_producto=pedido.id_producto,
        id_pedido=pedido,
        accion=accion[:60],
        detalle=detalle,
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
    )
