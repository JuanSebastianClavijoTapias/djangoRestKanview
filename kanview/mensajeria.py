"""Reglas de acceso y utilidades del chat interno."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.urls import reverse

from .models import Cliente, Conversacion, Empleado, Mensaje
from .permisos import ROL_CLIENTE, ROL_TRABAJADOR, es_administracion, roles_de

User = get_user_model()


def es_staff_chat(usuario):
    """Administración y Secretaría pueden iniciar chats con todo el taller."""
    return es_administracion(usuario)


def _cliente_de(usuario):
    cliente = getattr(usuario, "cliente_kanview", None)
    if cliente is not None:
        return cliente
    correo = (getattr(usuario, "email", "") or "").strip()
    return Cliente.objects.filter(correo__iexact=correo).first() if correo else None


def _empleado_de(usuario):
    return getattr(usuario, "empleado_kanview", None)


def _ids_contactos(usuario):
    """IDs de usuarios con los que el rol puede iniciar una conversación."""
    if es_staff_chat(usuario):
        return list(
            User.objects.filter(
                is_active=True,
                groups__name__in=(ROL_CLIENTE, ROL_TRABAJADOR),
            )
            .exclude(pk=usuario.pk)
            .values_list("pk", flat=True)
            .distinct()
        )

    ids = set()

    if ROL_CLIENTE in roles_de(usuario):
        cliente = _cliente_de(usuario)
        if cliente is not None:
            empleados = Empleado.objects.filter(
                activo=True,
                usuario__isnull=False,
            ).filter(
                Q(pedido__id_cliente=cliente)
                | Q(tareas_asignadas__id_pedido__id_cliente=cliente)
                | Q(actividades__id_tarea__id_pedido__id_cliente=cliente)
            ).distinct()
            ids.update(empleados.values_list("usuario_id", flat=True))

    if ROL_TRABAJADOR in roles_de(usuario):
        empleado = _empleado_de(usuario)
        if empleado is not None:
            clientes = Cliente.objects.filter(
                usuario__isnull=False,
            ).filter(
                Q(pedido__id_empleado=empleado)
                | Q(pedido__tareaspedido__id_empleado=empleado)
                | Q(pedido__tareaspedido__actividades__id_empleado=empleado)
            ).distinct()
            ids.update(clientes.values_list("usuario_id", flat=True))

    # Una conversación ya iniciada (por ejemplo, por Administración) permite
    # responder aunque el otro usuario no esté en el listado habitual.
    pares = Conversacion.objects.filter(Q(usuario_a=usuario) | Q(usuario_b=usuario))
    ids.update(pares.values_list("usuario_a_id", flat=True))
    ids.update(pares.values_list("usuario_b_id", flat=True))
    ids.discard(usuario.pk)
    return list(ids)


def contactos(usuario):
    """Usuarios visibles en el selector de conversaciones."""
    if not usuario or not usuario.is_authenticated:
        return User.objects.none()
    return (
        User.objects.filter(pk__in=_ids_contactos(usuario), is_active=True)
        .select_related("empleado_kanview", "cliente_kanview")
        .order_by("first_name", "username")
        .distinct()
    )


def puede_hablar_con(usuario, otro):
    if not usuario or not usuario.is_authenticated or otro is None or usuario.pk == otro.pk:
        return False
    if Conversacion.objects.filter(
        Q(usuario_a=usuario, usuario_b=otro) | Q(usuario_a=otro, usuario_b=usuario)
    ).exists():
        return True
    return otro.pk in set(_ids_contactos(usuario))


def obtener_conversacion(usuario, otro):
    """Devuelve o crea la conversación directa ordenando los IDs."""
    if usuario.pk == otro.pk:
        return None
    a, b = sorted((usuario, otro), key=lambda u: u.pk)
    conversacion, _ = Conversacion.objects.get_or_create(usuario_a=a, usuario_b=b)
    return conversacion


def conversacion_visible(usuario, pk):
    return (
        Conversacion.objects.select_related("usuario_a", "usuario_b")
        .filter(Q(usuario_a=usuario) | Q(usuario_b=usuario), pk=pk)
        .first()
    )


def conversaciones_de(usuario):
    return (
        Conversacion.objects.filter(Q(usuario_a=usuario) | Q(usuario_b=usuario))
        .select_related("usuario_a", "usuario_b")
        .prefetch_related("mensajes__autor")
        .order_by("-actualizada")
    )


def marcar_leidos(conversacion, usuario):
    return (
        Mensaje.objects.filter(conversacion=conversacion, leido=False)
        .exclude(autor=usuario)
        .update(leido=True)
    )


def no_leidos(usuario):
    return Mensaje.objects.filter(
        Q(conversacion__usuario_a=usuario) | Q(conversacion__usuario_b=usuario),
        leido=False,
    ).exclude(autor=usuario).count()


def crear_mensaje(conversacion, autor, texto):
    texto = (texto or "").strip()
    if not texto:
        return None
    if len(texto) > 2000:
        texto = texto[:2000]
    with transaction.atomic():
        mensaje = Mensaje.objects.create(
            conversacion=conversacion,
            autor=autor,
            texto=texto,
        )
        conversacion.save(update_fields=["actualizada"])
    return mensaje


def datos_mensaje(mensaje):
    return {
        "id": mensaje.pk,
        "autor_id": mensaje.autor_id,
        "autor": mensaje.autor.get_full_name() or mensaje.autor.get_username(),
        "texto": mensaje.texto,
        "creado": mensaje.creado.isoformat(),
        "leido": mensaje.leido,
    }


def url_conversacion(conversacion):
    return reverse("kanview:mensajeria-conversacion", args=[conversacion.pk])
