"""Enlaza las cuentas que ya existían con su Cliente / Empleado.

Antes el vínculo no existía en la base de datos: se adivinaba por el correo del
cliente o por una marca guardada en ``User.last_name`` (``kanview:trabajador:<pk>``).
Esta migración de datos deja ese enlace escrito en los campos nuevos
``Cliente.usuario`` y ``Empleado.usuario``, y limpia la marca de ``last_name``.

Es idempotente: si se vuelve a ejecutar (o si algo ya está enlazado) no rompe.
"""

from django.db import migrations

PREFIJO_MARCA = "kanview:trabajador:"


def enlazar(apps, schema_editor):
    # El modelo histórico: asignar un ``User`` real (importado de
    # ``django.contrib.auth.models``) a un campo de un modelo histórico lanza
    # ``ValueError: ... must be a "User" instance``, porque son clases distintas.
    User = apps.get_model("auth", "User")
    Cliente = apps.get_model("kanview", "Cliente")
    Empleado = apps.get_model("kanview", "Empleado")

    usados = set()

    # --- Clientes: el correo del cliente identifica su cuenta -----------------
    for cliente in Cliente.objects.filter(usuario__isnull=True).exclude(correo=""):
        user = (
            User.objects.filter(username__iexact=cliente.correo).first()
            or User.objects.filter(email__iexact=cliente.correo).first()
        )
        if user is None or user.pk in usados:
            continue
        cliente.usuario = user
        cliente.save(update_fields=["usuario"])
        usados.add(user.pk)
    usados |= set(
        Cliente.objects.filter(usuario__isnull=False).values_list("usuario_id", flat=True)
    )

    # --- Trabajadores: la marca decía cuál era su cuenta ---------------------
    for empleado in Empleado.objects.all():
        marca = f"{PREFIJO_MARCA}{empleado.pk}"
        user = User.objects.filter(last_name=marca).first()

        if empleado.usuario_id is None and user is not None and user.pk not in usados:
            empleado.usuario = user
            if not empleado.correo:
                empleado.correo = (user.email or user.username or "").lower()
            empleado.save(update_fields=["usuario", "correo"])
            usados.add(user.pk)

        # La marca ya no hace falta: el enlace vive en la base de datos.
        if user is not None and user.last_name == marca:
            user.last_name = ""
            user.save(update_fields=["last_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("kanview", "0006_cliente_usuario_empleado_correo_empleado_usuario"),
    ]

    operations = [
        migrations.RunPython(enlazar, migrations.RunPython.noop),
    ]
