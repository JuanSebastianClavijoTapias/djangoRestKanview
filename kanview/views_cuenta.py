"""Perfil, 2FA, términos y notificaciones del usuario."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .auditoria import registrar as registrar_auditoria
from .models import Cliente, Empleado, Notificacion
from .seguridad import (
    aceptar_terminos,
    activar_2fa,
    confirmar_2fa,
    desactivar_2fa,
    guardar_codigos_respaldo,
    perfil_de,
    qr_data_uri,
    terminos_aceptados,
    uri_totp,
)
from .views_site import _nav


@login_required
def perfil(request):
    perfil_usuario = perfil_de(request.user)
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        correo = (request.POST.get("correo") or "").strip().lower()
        if not nombre or not correo or "@" not in correo:
            messages.error(request, "Nombre y correo válido son obligatorios.")
        elif (
            request.user.__class__.objects.filter(email__iexact=correo)
            .exclude(pk=request.user.pk)
            .exists()
        ):
            messages.error(request, "Ese correo ya está en uso por otra cuenta.")
        elif (
            Cliente.objects.filter(correo__iexact=correo).exclude(usuario=request.user).exists()
            or Empleado.objects.filter(correo__iexact=correo).exclude(usuario=request.user).exists()
        ):
            messages.error(request, "Ese correo ya está registrado para otra persona.")
        else:
            anterior = request.user.email
            request.user.first_name = nombre[:150]
            request.user.email = correo
            if request.user.username == anterior:
                request.user.username = correo
            request.user.save(update_fields=["first_name", "email", "username"])
            with transaction.atomic():
                Cliente.objects.filter(usuario=request.user).update(correo=correo)
                Empleado.objects.filter(usuario=request.user).update(correo=correo)
            registrar_auditoria(
                request, "editar", "Perfil", request.user,
                f"Perfil de {request.user} actualizado",
            )
            messages.success(request, "Perfil actualizado.")
            return redirect("kanview:perfil")

    return render(
        request,
        "kanview/perfil.html",
        {
            "perfil": perfil_usuario,
            "terminos_aceptados": terminos_aceptados(request.user),
            **_nav(None, request),
        },
    )


@login_required
def perfil_password(request):
    if request.method == "POST":
        actual = request.POST.get("actual") or ""
        nueva = request.POST.get("nueva") or ""
        repetida = request.POST.get("repetida") or ""
        if not request.user.check_password(actual):
            messages.error(request, "La contraseña actual no es correcta.")
        elif len(nueva) < 8:
            messages.error(request, "La nueva contraseña debe tener al menos 8 caracteres.")
        elif nueva != repetida:
            messages.error(request, "Las contraseñas nuevas no coinciden.")
        else:
            request.user.set_password(nueva)
            request.user.save(update_fields=["password"])
            update_session_auth_hash(request, request.user)
            registrar_auditoria(
                request, "cambiar_password", "Usuario", request.user,
                f"Contraseña cambiada por {request.user}",
            )
            messages.success(request, "Contraseña actualizada.")
            return redirect("kanview:perfil")
    return render(request, "kanview/perfil_password.html", {**_nav(None, request)})


@login_required
def perfil_2fa(request):
    perfil_usuario = perfil_de(request.user)
    if request.method == "POST":
        accion = request.POST.get("accion") or ""
        if accion == "generar":
            secreto, codigos, qr = activar_2fa(request.user)
            request.session["2fa_codigos_temporales"] = codigos
            return render(
                request,
                "kanview/perfil_2fa.html",
                {
                    "perfil": perfil_usuario,
                    "qr": qr,
                    "secreto": secreto,
                    "codigos": codigos,
                    "confirmar": True,
                    "uri": uri_totp(request.user, secreto),
                    **_nav(None, request),
                },
            )
        if accion == "confirmar":
            if confirmar_2fa(request.user, request.POST.get("codigo")):
                codigos = request.session.pop("2fa_codigos_temporales", [])
                guardar_codigos_respaldo(perfil_usuario, codigos)
                registrar_auditoria(
                    request, "activar_2fa", "Usuario", request.user,
                    f"2FA activado por {request.user}",
                )
                messages.success(request, "2FA activado correctamente. Guarda tus códigos de respaldo.")
                return render(
                    request,
                    "kanview/perfil_2fa.html",
                    {
                        "perfil": perfil_usuario,
                        "codigos_nuevos": codigos,
                        **_nav(None, request),
                    },
                )
            messages.error(request, "El código no es válido. Intenta de nuevo.")
        if accion == "desactivar":
            if desactivar_2fa(request.user, request.POST.get("clave")):
                registrar_auditoria(
                    request, "desactivar_2fa", "Usuario", request.user,
                    f"2FA desactivado por {request.user}",
                )
                messages.success(request, "2FA desactivado.")
                return redirect("kanview:perfil-2fa")
            messages.error(request, "La contraseña no es correcta.")
    if request.method == "POST" and accion == "confirmar":
        secreto = perfil_usuario.totp_secret
        return render(
            request,
            "kanview/perfil_2fa.html",
            {
                "perfil": perfil_usuario,
                "confirmar": True,
                "secreto": secreto,
                "qr": qr_data_uri(uri_totp(request.user, secreto)) if secreto else "",
                "codigos": request.session.get("2fa_codigos_temporales", []),
                **_nav(None, request),
            },
        )
    return render(
        request,
        "kanview/perfil_2fa.html",
        {"perfil": perfil_usuario, **_nav(None, request)},
    )


def terminos(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.info(request, "Inicia sesión para aceptar los términos.")
            return redirect("kanview:login")
        aceptar_terminos(request.user)
        registrar_auditoria(
            request, "aceptar_terminos", "Usuario", request.user,
            f"Términos aceptados por {request.user}",
        )
        messages.success(request, "Términos y condiciones aceptados.")
        siguiente = request.session.pop("terminos_next", "")
        return redirect(siguiente or "kanview:dashboard")
    return render(request, "kanview/terminos.html", {"version": settings.TERMINOS_VERSION, **_nav(None, request)})


@login_required
@require_POST
def notificaciones_leer(request):
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    siguiente = request.META.get("HTTP_REFERER") or ""
    if not url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        siguiente = reverse("kanview:dashboard")
    return redirect(siguiente)
