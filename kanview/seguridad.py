"""Seguridad de las cuentas: perfil, 2FA y aceptación de términos."""

import base64
import io
import secrets
from urllib.parse import quote

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect
from django.utils import timezone

from .models import PerfilUsuario

#: Cantidad de códigos de respaldo que se entregan al activar 2FA.
CODIGOS_RESPALDO = 8


def perfil_de(usuario):
    """Devuelve el perfil del usuario, creándolo si aún no existe."""
    if usuario is None or not getattr(usuario, "pk", None):
        return None
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    return perfil


def terminos_aceptados(usuario):
    """True si el usuario aceptó la versión vigente de los términos."""
    perfil = perfil_de(usuario)
    return bool(perfil and perfil.terminos_version == settings.TERMINOS_VERSION)


def aceptar_terminos(usuario):
    perfil = perfil_de(usuario)
    perfil.terminos_version = settings.TERMINOS_VERSION
    perfil.terminos_aceptados_en = timezone.now()
    perfil.save(update_fields=["terminos_version", "terminos_aceptados_en"])
    return perfil


def nuevo_secreto():
    return pyotp.random_base32()


def uri_totp(usuario, secreto):
    nombre = usuario.get_full_name() or usuario.get_username()
    etiqueta = quote(f"Kanview:{nombre}")
    emisor = quote(getattr(settings, "EMPRESA_NOMBRE", "Kanview"))
    return f"otpauth://totp/{etiqueta}?secret={secreto}&issuer={emisor}&digits=6&period=30"


def qr_data_uri(uri):
    """Genera un PNG del código QR como data URI (sin archivos temporales)."""
    imagen = qrcode.make(uri)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def verificar_totp(secreto, codigo):
    if not secreto or not codigo:
        return False
    return pyotp.TOTP(secreto).verify(str(codigo).strip(), valid_window=1)


def generar_codigos_respaldo():
    """Ocho códigos de un solo uso, en claro, para mostrar una única vez."""
    return [f"{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}" for _ in range(CODIGOS_RESPALDO)]


def guardar_codigos_respaldo(perfil, codigos):
    """Guarda solo hashes; los códigos en claro no se vuelven a mostrar."""
    perfil.codigos_respaldo = [make_password(codigo) for codigo in codigos]
    perfil.save(update_fields=["codigos_respaldo"])


def consumir_codigo_respaldo(perfil, codigo):
    """Valida y consume un código de respaldo. Devuelve True si era válido."""
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return False
    restantes = []
    usado = False
    for hash_guardado in perfil.codigos_respaldo or []:
        if not usado and check_password(codigo, hash_guardado):
            usado = True
        else:
            restantes.append(hash_guardado)
    if usado:
        perfil.codigos_respaldo = restantes
        perfil.save(update_fields=["codigos_respaldo"])
    return usado


def activar_2fa(usuario):
    """Genera secreto y códigos nuevos; devuelve (secreto, codigos, qr)."""
    perfil = perfil_de(usuario)
    secreto = nuevo_secreto()
    codigos = generar_codigos_respaldo()
    perfil.totp_secret = secreto
    perfil.totp_habilitado = False
    perfil.save(update_fields=["totp_secret", "totp_habilitado"])
    return secreto, codigos, qr_data_uri(uri_totp(usuario, secreto))


def confirmar_2fa(usuario, codigo):
    """Activa 2FA únicamente si el primer código TOTP es correcto."""
    perfil = perfil_de(usuario)
    if not verificar_totp(perfil.totp_secret, codigo):
        return False
    perfil.totp_habilitado = True
    perfil.save(update_fields=["totp_habilitado"])
    return True


def desactivar_2fa(usuario, clave):
    """Desactiva 2FA comprobando la contraseña actual."""
    if not usuario.check_password(clave or ""):
        return False
    perfil = perfil_de(usuario)
    perfil.totp_habilitado = False
    perfil.totp_secret = ""
    perfil.codigos_respaldo = []
    perfil.save(update_fields=["totp_habilitado", "totp_secret", "codigos_respaldo"])
    return True


class TerminosMiddleware:
    """Obliga a aceptar la versión vigente de los términos antes de usar la app."""

    EXENTAS = (
        "/login/",
        "/logout/",
        "/terminos/",
        "/recuperar/",
        "/recuperar/verificar/",
        "/admin/",
        "/api/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings as django_settings

        if getattr(django_settings, "TESTING", False) and not getattr(
            django_settings, "TERMINOS_EN_PRUEBAS", False
        ):
            return self.get_response(request)
        usuario = getattr(request, "user", None)
        ruta = request.path_info
        if (
            usuario is not None
            and usuario.is_authenticated
            and not usuario.is_superuser
            and not any(ruta.startswith(exenta) for exenta in self.EXENTAS)
            and not terminos_aceptados(usuario)
        ):
            request.session["terminos_next"] = request.get_full_path()
            return redirect("kanview:terminos")
        return self.get_response(request)
