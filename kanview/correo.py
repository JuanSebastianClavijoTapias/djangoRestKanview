"""Envío de correos con manejo controlado de fallos."""

import logging

from django.conf import settings
from django.core.mail import EmailMessage, send_mail

logger = logging.getLogger(__name__)


def enviar_correo(asunto, mensaje, destinatarios, adjuntos=None):
    """Envía un correo y devuelve True/False sin romper la operación principal.

    ``adjuntos`` es una lista de tuplas ``(nombre, contenido_bytes, mime)``.
    Si el SMTP no está configurado o falla, se registra el error y se devuelve
    False para que la vista pueda avisar al usuario.
    """
    destinatarios = [correo for correo in dict.fromkeys(destinatarios or []) if correo]
    if not destinatarios:
        return False
    if settings.EMAIL_BACKEND.endswith("smtp.EmailBackend") and not (
        settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD
    ):
        logger.warning(
            "Falta EMAIL_HOST_USER/EMAIL_HOST_PASSWORD en el .env: no se pudo enviar el correo %s",
            asunto,
        )
        return False
    try:
        if adjuntos:
            correo = EmailMessage(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                destinatarios,
            )
            for nombre, contenido, mime in adjuntos:
                correo.attach(nombre, contenido, mime)
            correo.send(fail_silently=False)
        else:
            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                destinatarios,
                fail_silently=False,
            )
        return True
    except Exception as error:
        logger.warning("No se pudo enviar el correo %s: %s", asunto, error)
        return False
