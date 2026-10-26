"""Roles y control de acceso de Kanview.

Un rol = un grupo de Django. El administrador crea las cuentas desde el módulo
Usuarios (`/usuarios/`) y les asigna un rol; nadie se registra por su cuenta.

Reglas acordadas:

    Administrador -> todo
    Secretaria    -> todo, incluidos usuarios
    Trabajador    -> todo menos finanzas, auditoría y gestión de usuarios
    Cliente       -> solo su panel y sus pedidos
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.models import Group
from django.shortcuts import redirect

ROL_ADMINISTRADOR = "Administrador"
ROL_SECRETARIA = "Secretaria"
ROL_TRABAJADOR = "Trabajador"
ROL_CLIENTE = "Cliente"

ROLES = (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR, ROL_CLIENTE)

#: Qué roles pueden ver cada sección del sistema.
#: Las secciones `gestion-*` separan la ESCRITURA de la LECTURA: el rol Cliente
#: solo tiene lectura de `pedidos` y `catalogo` (los suyos), nunca escritura.
SECCIONES = {
    "panel": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "pedidos": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR, ROL_CLIENTE),
    "gestion-pedidos": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "catalogo": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "gestion-catalogo": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "inventario": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "tareas": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "calendario": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR),
    "auditoria": (ROL_ADMINISTRADOR, ROL_SECRETARIA),
    "mensajeria": (ROL_ADMINISTRADOR, ROL_SECRETARIA, ROL_TRABAJADOR, ROL_CLIENTE),
    "finanzas": (ROL_ADMINISTRADOR, ROL_SECRETARIA),
    "usuarios": (ROL_ADMINISTRADOR, ROL_SECRETARIA),
    "configuracion": (ROL_ADMINISTRADOR, ROL_SECRETARIA),
}

#: Secciones de escritura y la sección de lectura que les corresponde.
SECCION_ESCRITURA = {
    "pedidos": "gestion-pedidos",
    "catalogo": "gestion-catalogo",
}


def roles_de(usuario):
    """Conjunto de roles (nombres de grupo) que tiene el usuario."""
    if not usuario or not usuario.is_authenticated:
        return set()
    return set(usuario.groups.values_list("name", flat=True))


def es_administrador(usuario):
    """True para superusuarios o para quien tenga el rol Administrador."""
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.is_superuser or ROL_ADMINISTRADOR in roles_de(usuario)


def es_administracion(usuario):
    """True para Administración o Secretaría (revisión de solicitudes)."""
    if not usuario or not usuario.is_authenticated:
        return False
    return es_administrador(usuario) or ROL_SECRETARIA in roles_de(usuario)


def es_solo_cliente(usuario):
    """True para el rol Cliente: solo ve su panel y sus propios pedidos."""
    if not usuario or not usuario.is_authenticated:
        return False
    return not es_administrador(usuario) and rol_principal(usuario) == ROL_CLIENTE


def puede(usuario, seccion):
    """¿El usuario puede ver esta sección?"""
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    return bool(roles_de(usuario) & set(SECCIONES.get(seccion, ())))


def secciones_visibles(usuario):
    """Secciones que le corresponden al usuario (para filtrar el sidebar)."""
    return [seccion for seccion in SECCIONES if puede(usuario, seccion)]


def asignar_rol(usuario, rol):
    """Deja al usuario únicamente con el rol indicado."""
    usuario.groups.clear()
    if rol in ROLES:
        grupo, _ = Group.objects.get_or_create(name=rol)
        usuario.groups.add(grupo)
    return usuario


def rol_principal(usuario):
    """Nombre del rol del usuario, o cadena vacía si no tiene ninguno."""
    if es_administrador(usuario):
        return ROL_ADMINISTRADOR
    roles = roles_de(usuario)
    for rol in ROLES:
        if rol in roles:
            return rol
    return ""


def seccion_requerida(seccion):
    """Decorador de vista: exige sesión iniciada y permiso sobre la sección."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/login/?next={request.path}")
            if not puede(request.user, seccion):
                messages.error(request, "No tienes permiso para entrar a esa sección.")
                return redirect("kanview:dashboard")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
