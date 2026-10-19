"""Crea los grupos (roles) del sistema y da rol Administrador a los usuarios existentes.

Nadie se registra por su cuenta: el administrador crea las cuentas desde el
módulo Usuarios y les asigna uno de estos roles.
"""

from django.db import migrations

ROLES = ("Administrador", "Secretaria", "Trabajador", "Cliente")


def crear_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")

    grupos = {nombre: Group.objects.get_or_create(name=nombre)[0] for nombre in ROLES}

    # Los usuarios que ya existían (staff/superusuarios) quedan como Administrador.
    for usuario in User.objects.filter(is_staff=True):
        usuario.groups.add(grupos["Administrador"])


def borrar_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("kanview", "0004_alter_actividades_options_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(crear_roles, borrar_roles),
    ]
