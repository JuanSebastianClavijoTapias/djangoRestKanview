"""Registro central de auditoría."""

import logging

from django.utils import timezone

from .models import RegistroAuditoria

logger = logging.getLogger(__name__)


def _ip(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None


def registrar(request, accion, entidad, objeto=None, descripcion="", datos=None, objeto_id="", usuario=None):
    """Guarda una acción relevante sin interrumpir la operación original.

    Nunca se deben pasar contraseñas, tokens ni secretos en ``datos``.
    """
    if usuario is None:
        usuario = getattr(request, "user", None)
    if usuario is not None and not getattr(usuario, "is_authenticated", False):
        usuario = None
    if objeto is not None and not objeto_id:
        objeto_id = str(getattr(objeto, "pk", "") or "")
    try:
        RegistroAuditoria.objects.create(
            usuario=usuario,
            accion=accion[:60],
            entidad=entidad[:60],
            objeto_id=str(objeto_id or "")[:40],
            descripcion=descripcion[:255],
            ip=_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255] if request else "",
            datos=datos or {},
        )
    except Exception:
        logger.exception("No se pudo registrar la auditoría de %s/%s", entidad, accion)
    return timezone.now()
