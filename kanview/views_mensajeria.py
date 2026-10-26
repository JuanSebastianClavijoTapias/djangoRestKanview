"""Vistas HTTP de la mensajería interna."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .mensajeria import (
    contactos,
    conversacion_visible,
    conversaciones_de,
    crear_mensaje,
    datos_mensaje,
    marcar_leidos,
    no_leidos,
    obtener_conversacion,
    puede_hablar_con,
)
from .permisos import seccion_requerida
from .views_site import _nav

User = get_user_model()


def _rol_de(usuario):
    empleado = getattr(usuario, "empleado_kanview", None)
    if empleado is not None:
        return empleado.get_cargo_display()
    if getattr(usuario, "cliente_kanview", None) is not None:
        return "Cliente"
    if usuario.groups.filter(name="Administrador").exists() or usuario.is_superuser:
        return "Administración"
    if usuario.groups.filter(name="Secretaria").exists():
        return "Secretaría"
    return "Usuario"


def _persona(usuario):
    nombre = usuario.get_full_name() or usuario.get_username()
    return {
        "usuario": usuario,
        "nombre": nombre,
        "rol": _rol_de(usuario),
        "iniciales": (nombre[:2] or "?").upper(),
    }


def _conversaciones(usuario, activa_id=None):
    items = []
    for conversacion in conversaciones_de(usuario):
        otro = conversacion.otro(usuario)
        mensajes = list(conversacion.mensajes.all())
        ultimo = mensajes[-1] if mensajes else None
        no_leidos_conv = sum(
            1 for mensaje in mensajes
            if not mensaje.leido and mensaje.autor_id != usuario.pk
        )
        items.append({
            "conversacion": conversacion,
            "otro": _persona(otro),
            "ultimo": ultimo,
            "no_leidos": no_leidos_conv,
            "activa": conversacion.pk == activa_id,
        })
    return items


def _contactos_nuevos(usuario, conversaciones):
    ya = {item["otro"]["usuario"].pk for item in conversaciones}
    return [
        _persona(contacto)
        for contacto in contactos(usuario)
        if contacto.pk not in ya
    ]


@seccion_requerida("mensajeria")
def mensajeria(request):
    lista = _conversaciones(request.user)
    return render(
        request,
        "kanview/mensajeria.html",
        {
            "conversaciones": lista,
            "contactos": _contactos_nuevos(request.user, lista),
            "conversacion": None,
            "mensajes": [],
            "total_no_leidos": no_leidos(request.user),
            "cabecera_titulo": "Mensajería",
            **_nav("Mensajería", request),
        },
    )


@seccion_requerida("mensajeria")
def conversacion(request, pk):
    actual = conversacion_visible(request.user, pk)
    if actual is None:
        raise Http404("Conversación no encontrada.")
    marcar_leidos(actual, request.user)
    mensajes = list(
        actual.mensajes.select_related("autor").order_by("creado", "id")
    )
    lista = _conversaciones(request.user, activa_id=actual.pk)
    otro = actual.otro(request.user)
    return render(
        request,
        "kanview/mensajeria.html",
        {
            "conversaciones": lista,
            "contactos": _contactos_nuevos(request.user, lista),
            "conversacion": actual,
            "otro": _persona(otro),
            "mensajes": mensajes,
            "total_no_leidos": no_leidos(request.user),
            "cabecera_titulo": f"Chat con {otro.get_full_name() or otro.get_username()}",
            **_nav("Mensajería", request),
        },
    )


@seccion_requerida("mensajeria")
@require_POST
def iniciar(request, pk):
    otro = get_object_or_404(User, pk=pk, is_active=True)
    if not puede_hablar_con(request.user, otro):
        messages.error(request, "No puedes iniciar una conversación con ese usuario.")
        return redirect("kanview:mensajeria")
    actual = obtener_conversacion(request.user, otro)
    if actual is None:
        messages.error(request, "No puedes iniciar una conversación contigo mismo.")
        return redirect("kanview:mensajeria")
    return redirect("kanview:mensajeria-conversacion", pk=actual.pk)


@seccion_requerida("mensajeria")
@require_POST
def enviar(request, pk):
    actual = conversacion_visible(request.user, pk)
    if actual is None:
        raise Http404("Conversación no encontrada.")
    mensaje = crear_mensaje(actual, request.user, request.POST.get("texto"))
    if mensaje is None:
        messages.error(request, "Escribe un mensaje antes de enviar.")
    else:
        capa = get_channel_layer()
        if capa is not None:
            async_to_sync(capa.group_send)(
                f"chat_{actual.pk}",
                {"type": "chat.message", "mensaje": datos_mensaje(mensaje)},
            )
    return redirect("kanview:mensajeria-conversacion", pk=actual.pk)
