"""Comprobaciones de configuración que se ejecutan al arrancar."""

from django.conf import settings
from django.core import checks


@checks.register()
def correo_smtp_configurado(app_configs, **kwargs):
    """Avisa si el backend SMTP no tiene credenciales.

    Es un aviso (no un error) para no bloquear arranques legítimos (por
    ejemplo con el backend de consola). El síntoma típico es editar el .env
    con el servidor ya en marcha: Django solo lee el .env al arrancar, así
    que hay que reiniciarlo para que los cambios surtan efecto.
    """
    if not settings.EMAIL_BACKEND.endswith("smtp.EmailBackend"):
        return []
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        return []
    return [
        checks.Warning(
            "El envío de correos está configurado con SMTP pero faltan "
            "EMAIL_HOST_USER y/o EMAIL_HOST_PASSWORD en el .env: los correos "
            "no se enviarán.",
            hint=(
                "Añade las credenciales al .env y REINICIA el servidor "
                "(Django solo lee el .env al arrancar)."
            ),
            id="kanview.W001",
        )
    ]
