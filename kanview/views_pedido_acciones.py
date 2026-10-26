"""Acciones del pedido: aprobación, solicitudes, multimedia y factura."""

import mimetypes
import os

from django.contrib import messages
from django.core import signing
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import historial
from .auditoria import registrar as registrar_auditoria
from .facturacion import crear_factura, enviar_factura, generar_pdf
from .models import Empleado, EvidenciaPedido, Pedido, SolicitudModificacionPedido
from .notificaciones import notificar_cliente, notificar_staff
from .permisos import SECCION_ESCRITURA, es_administracion, es_administrador, es_solo_cliente, puede, seccion_requerida
from .views_pedidos import _pedidos_queryset
from .views_site import _nav

SAL_MEDIA = "kanview.evidencia"


def _pedido_visible(request, pk):
    return get_object_or_404(_pedidos_queryset(request), pk=pk)


def _puede_gestionar_pedido(request, pedido):
    return puede(request.user, "gestion-pedidos")


def _puede_ver_evidencia(request, evidencia):
    pedido = evidencia.pedido
    if es_solo_cliente(request.user):
        return (pedido.id_cliente.correo or "").lower() == (request.user.email or "").lower()
    return _puede_gestionar_pedido(request, pedido)


# ---- Aprobación / rechazo -------------------------------------------------

@seccion_requerida(SECCION_ESCRITURA["pedidos"])
@require_POST
def pedido_aprobar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    # El trabajador se asigna al aprobar: los pedidos creados por el cliente
    # nacen «Sin asignar» y el taller elige quién los atiende en este paso.
    empleado_id = (request.POST.get("empleado") or "").strip()
    empleado = Empleado.objects.filter(pk=empleado_id, activo=True).first() if empleado_id.isdigit() else None
    if empleado_id and empleado is None:
        messages.error(request, "Selecciona un trabajador válido para asignar al pedido.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    if empleado is not None:
        pedido.id_empleado = empleado
    if pedido.id_empleado_id is None:
        messages.error(request, "Asigna un trabajador al pedido antes de aprobarlo.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    pedido.estado_aprobacion = "aprobado"
    pedido.motivo_rechazo = ""
    pedido.aprobado_por = request.user
    pedido.fecha_aprobacion = timezone.now()
    pedido.save(update_fields=[
        "estado_aprobacion", "motivo_rechazo", "aprobado_por", "fecha_aprobacion", "id_empleado",
    ])
    asignado = f" Trabajador asignado: {pedido.id_empleado.nombre}." if empleado else ""
    historial.registrar(
        pedido, "pedido_aprobado",
        f"Pedido aprobado por {request.user.get_full_name() or request.user.get_username()}.{asignado}",
        request.user,
    )
    registrar_auditoria(request, "aprobar", "Pedido", pedido, f"Pedido {pedido.codigo_pedido} aprobado")
    notificar_cliente(
        pedido.id_cliente,
        "aprobacion",
        f"Tu pedido {pedido.codigo_pedido} fue aprobado. Producto: {pedido.id_producto.nombre}.",
        reverse("kanview:pedido-detalle", args=[pedido.pk]),
        asunto="Kanview · Pedido aprobado",
    )
    messages.success(request, f"Pedido {pedido.codigo_pedido} aprobado.")
    return redirect("kanview:pedido-detalle", pk=pedido.pk)


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
@require_POST
def pedido_rechazar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    motivo = (request.POST.get("motivo") or "").strip()
    if not motivo:
        messages.error(request, "Indica el motivo del rechazo.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    pedido.estado_aprobacion = "rechazado"
    pedido.motivo_rechazo = motivo
    pedido.aprobado_por = request.user
    pedido.fecha_aprobacion = timezone.now()
    pedido.save(update_fields=["estado_aprobacion", "motivo_rechazo", "aprobado_por", "fecha_aprobacion"])
    historial.registrar(pedido, "pedido_rechazado", f"Pedido rechazado: {motivo}", request.user)
    registrar_auditoria(
        request, "rechazar", "Pedido", pedido,
        f"Pedido {pedido.codigo_pedido} rechazado", {"motivo": motivo},
    )
    notificar_cliente(
        pedido.id_cliente,
        "rechazo",
        f"Tu pedido {pedido.codigo_pedido} fue rechazado. Motivo: {motivo}",
        reverse("kanview:pedido-detalle", args=[pedido.pk]),
        asunto="Kanview · Pedido rechazado",
    )
    messages.success(request, f"Pedido {pedido.codigo_pedido} rechazado.")
    return redirect("kanview:pedido-detalle", pk=pedido.pk)


# ---- Solicitudes de modificación -----------------------------------------

def _puede_editar_solicitud(request, solicitud):
    if not solicitud.activo or solicitud.estado != "pendiente":
        return False
    pedido = solicitud.pedido
    return (
        es_solo_cliente(request.user)
        and (pedido.id_cliente.correo or "").lower() == (request.user.email or "").lower()
    )


def _solicitud_contexto(request, pedido, solicitud=None):
    return {
        "pedido": pedido,
        "solicitud": solicitud,
        "titulo": "Editar solicitud" if solicitud else "Nueva solicitud de modificación",
        "cancel_url": reverse("kanview:pedido-detalle", args=[pedido.pk]),
        **_nav("Procesos", request),
    }


@seccion_requerida("pedidos")
def solicitud_crear(request, pk):
    pedido = _pedido_visible(request, pk)
    if not es_solo_cliente(request.user):
        messages.error(request, "Solo el cliente puede solicitar cambios en su pedido.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    if request.method == "POST":
        descripcion = (request.POST.get("descripcion") or "").strip()
        if not descripcion:
            messages.error(request, "Describe el cambio que necesitas.")
        else:
            solicitud = SolicitudModificacionPedido.objects.create(
                pedido=pedido,
                solicitado_por=request.user,
                descripcion=descripcion,
            )
            historial.registrar(
                pedido, "solicitud_modificacion",
                f"Solicitud de modificación #{solicitud.pk}: {descripcion}",
                request.user,
            )
            registrar_auditoria(
                request, "crear", "SolicitudModificacion", solicitud,
                f"Solicitud de modificación del pedido {pedido.codigo_pedido}",
            )
            notificar_staff(
                "pedido",
                f"Nueva solicitud de modificación del pedido {pedido.codigo_pedido}.",
                reverse("kanview:pedido-detalle", args=[pedido.pk]),
            )
            messages.success(request, "Solicitud registrada.")
            return redirect("kanview:pedido-detalle", pk=pedido.pk)
    return render(request, "kanview/solicitud_form.html", _solicitud_contexto(request, pedido))


@seccion_requerida("pedidos")
def solicitud_editar(request, pk):
    solicitud = get_object_or_404(
        SolicitudModificacionPedido.objects.select_related("pedido"), pk=pk
    )
    pedido = solicitud.pedido
    if not _puede_editar_solicitud(request, solicitud):
        messages.error(request, "Esta solicitud ya no se puede editar.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    if request.method == "POST":
        descripcion = (request.POST.get("descripcion") or "").strip()
        if not descripcion:
            messages.error(request, "Describe el cambio que necesitas.")
        else:
            solicitud.descripcion = descripcion
            solicitud.save(update_fields=["descripcion", "fecha_actualizacion"])
            historial.registrar(
                pedido, "solicitud_actualizada",
                f"Solicitud #{solicitud.pk} actualizada.", request.user,
            )
            registrar_auditoria(
                request, "editar", "SolicitudModificacion", solicitud,
                f"Solicitud #{solicitud.pk} actualizada",
            )
            messages.success(request, "Solicitud actualizada.")
            return redirect("kanview:pedido-detalle", pk=pedido.pk)
    return render(
        request, "kanview/solicitud_form.html",
        _solicitud_contexto(request, pedido, solicitud),
    )


@seccion_requerida("pedidos")
@require_POST
def solicitud_eliminar(request, pk):
    solicitud = get_object_or_404(SolicitudModificacionPedido, pk=pk)
    if not _puede_editar_solicitud(request, solicitud):
        messages.error(request, "Esta solicitud ya no se puede eliminar.")
        return redirect("kanview:pedido-detalle", pk=solicitud.pedido_id)
    solicitud.activo = False
    solicitud.save(update_fields=["activo", "fecha_actualizacion"])
    historial.registrar(
        solicitud.pedido, "solicitud_eliminada",
        f"Solicitud #{solicitud.pk} eliminada.", request.user,
    )
    registrar_auditoria(
        request, "eliminar", "SolicitudModificacion", solicitud,
        f"Solicitud #{solicitud.pk} eliminada",
    )
    messages.success(request, "Solicitud eliminada.")
    return redirect("kanview:pedido-detalle", pk=solicitud.pedido_id)


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
@require_POST
def solicitud_revisar(request, pk):
    solicitud = get_object_or_404(SolicitudModificacionPedido, pk=pk)
    if not es_administracion(request.user):
        messages.error(request, "Solo Administración o Secretaría pueden revisar solicitudes.")
        return redirect("kanview:pedido-detalle", pk=solicitud.pedido_id)
    estado = (request.POST.get("estado") or "").strip()
    respuesta = (request.POST.get("respuesta") or "").strip()
    if estado not in ("aceptada", "rechazada"):
        messages.error(request, "Estado de revisión no válido.")
    else:
        solicitud.estado = estado
        solicitud.respuesta = respuesta
        solicitud.revisado_por = request.user
        solicitud.save(update_fields=["estado", "respuesta", "revisado_por", "fecha_actualizacion"])
        historial.registrar(
            solicitud.pedido, f"solicitud_{estado}",
            f"Solicitud #{solicitud.pk} {estado}: {respuesta}", request.user,
        )
        registrar_auditoria(
            request, estado, "SolicitudModificacion", solicitud,
            f"Solicitud #{solicitud.pk} {estado}", {"respuesta": respuesta},
        )
        notificar_cliente(
            solicitud.pedido.id_cliente,
            "pedido",
            f"Tu solicitud de modificación del pedido "
            f"{solicitud.pedido.codigo_pedido} fue {estado}.",
            reverse("kanview:pedido-detalle", args=[solicitud.pedido_id]),
            asunto="Kanview · Solicitud de modificación",
        )
        messages.success(request, f"Solicitud {estado}.")
    return redirect("kanview:pedido-detalle", pk=solicitud.pedido_id)


# ---- Multimedia -----------------------------------------------------------

@seccion_requerida(SECCION_ESCRITURA["pedidos"])
def evidencia_editar(request, pk):
    from django.conf import settings
    from PIL import Image

    evidencia = get_object_or_404(EvidenciaPedido, pk=pk)
    if request.method == "POST":
        descripcion = (request.POST.get("descripcion") or "").strip()[:255]
        archivo = request.FILES.get("archivo")
        if archivo:
            extension = os.path.splitext(archivo.name or "")[1].lower()
            tipo = (archivo.content_type or "").lower()
            if extension in {".jpg", ".jpeg", ".png", ".webp"} and tipo.startswith("image/"):
                if archivo.size > 5 * 1024 * 1024:
                    messages.error(request, "La imagen supera los 5 MB.")
                    return redirect("kanview:evidencia-editar", pk=evidencia.pk)
                try:
                    Image.open(archivo).verify()
                    archivo.seek(0)
                except Exception:
                    messages.error(request, "La imagen no es válida o está dañada.")
                    return redirect("kanview:evidencia-editar", pk=evidencia.pk)
                evidencia.tipo = "imagen"
            elif extension in {".mp4", ".webm", ".mov", ".m4v"} and tipo.startswith("video/"):
                if archivo.size > settings.MAX_VIDEO_BYTES:
                    messages.error(request, "El video supera el tamaño permitido.")
                    return redirect("kanview:evidencia-editar", pk=evidencia.pk)
                evidencia.tipo = "video"
            else:
                messages.error(request, "El archivo debe ser una imagen o un video permitido.")
                return redirect("kanview:evidencia-editar", pk=evidencia.pk)
            anterior = evidencia.archivo
            evidencia.archivo = archivo
            evidencia.save(update_fields=["archivo", "tipo", "descripcion"])
            if anterior and anterior.name != evidencia.archivo.name:
                anterior.delete(save=False)
        else:
            evidencia.descripcion = descripcion
            evidencia.save(update_fields=["descripcion"])
        registrar_auditoria(
            request, "editar", "Evidencia", evidencia,
            f"Evidencia #{evidencia.pk} actualizada",
        )
        messages.success(request, "Evidencia actualizada.")
        return redirect("kanview:pedido-detalle", pk=evidencia.pedido_id)
    return render(request, "kanview/evidencia_form.html", {
        "evidencia": evidencia,
        "pedido": evidencia.pedido,
        **_nav("Procesos", request),
    })


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
@require_POST
def evidencia_eliminar(request, pk):
    evidencia = get_object_or_404(EvidenciaPedido, pk=pk)
    pedido = evidencia.pedido
    archivo = evidencia.archivo
    historial.registrar(
        pedido, "evidencia_eliminada",
        f"Archivo eliminado: {evidencia.descripcion or archivo.name}", request.user,
    )
    evidencia.delete()
    if archivo:
        archivo.delete(save=False)
    registrar_auditoria(
        request, "eliminar", "Evidencia", objeto_id=pk,
        descripcion=f"Archivo de evidencia #{pk} eliminado",
    )
    messages.success(request, "Archivo eliminado.")
    return redirect("kanview:pedido-detalle", pk=pedido.pk)


def _token_evidencia(evidencia):
    return signing.dumps({"evidencia": evidencia.pk}, salt=SAL_MEDIA)


def evidencia_publica(request, pk, token):
    """Archivo de evidencia con enlace firmado y caducidad (para correos)."""
    evidencia = get_object_or_404(EvidenciaPedido, pk=pk)
    try:
        datos = signing.loads(token, salt=SAL_MEDIA, max_age=7 * 24 * 3600)
    except signing.BadSignature:
        raise Http404("Enlace de evidencia no válido o vencido.")
    if datos.get("evidencia") != evidencia.pk:
        raise Http404("Enlace de evidencia no válido.")
    return _respuesta_archivo(evidencia)


def evidencia_archivo(request, pk):
    evidencia = get_object_or_404(EvidenciaPedido, pk=pk)
    if not _puede_ver_evidencia(request, evidencia):
        raise Http404
    return _respuesta_archivo(evidencia)


def _respuesta_archivo(evidencia):
    archivo = evidencia.archivo
    if not archivo or not archivo.storage.exists(archivo.name):
        raise Http404("El archivo ya no existe.")
    tipo = mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"
    return FileResponse(archivo.open("rb"), content_type=tipo, filename=archivo.name.split("/")[-1])


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
@require_POST
def pedido_compartir_multimedia(request, pk):
    pedido = get_object_or_404(Pedido.objects.prefetch_related("galeria"), pk=pk)
    if not pedido.id_cliente.correo:
        messages.error(request, "El cliente no tiene correo registrado.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    enlaces = []
    for evidencia in pedido.galeria.all():
        token = _token_evidencia(evidencia)
        url = request.build_absolute_uri(
            reverse("kanview:evidencia-publica", args=[evidencia.pk, token])
        )
        enlaces.append(f"- {evidencia.descripcion or evidencia.archivo.name.split('/')[-1]}: {url}")
    if not enlaces:
        messages.error(request, "El pedido no tiene archivos para compartir.")
        return redirect("kanview:pedido-detalle", pk=pedido.pk)
    from .correo import enviar_correo

    enviado = enviar_correo(
        f"Kanview · Archivos del pedido {pedido.codigo_pedido}",
        "Hola,\n\nEstos son los archivos de tu pedido:\n\n"
        + "\n".join(enlaces)
        + "\n\nLos enlaces vencen en 7 días.\n\nKanview",
        [pedido.id_cliente.correo],
    )
    if enviado:
        historial.registrar(
            pedido, "multimedia_compartida",
            f"Archivos compartidos con {pedido.id_cliente.correo}.", request.user,
        )
        registrar_auditoria(
            request, "compartir", "Pedido", pedido,
            f"Archivos del pedido {pedido.codigo_pedido} compartidos",
        )
        messages.success(request, "Archivos enviados al cliente.")
    else:
        registrar_auditoria(
            request, "envio_fallido", "Pedido", pedido,
            f"No se pudieron enviar los archivos del pedido {pedido.codigo_pedido}",
        )
        messages.warning(request, "No se pudo enviar el correo; revisa la configuración SMTP.")
    return redirect("kanview:pedido-detalle", pk=pedido.pk)


# ---- Factura --------------------------------------------------------------

def _factura_visible(request, pedido):
    # El Cliente no consulta facturas desde el portal; el personal sí.
    return not es_solo_cliente(request.user)


@seccion_requerida("pedidos")
def factura_ver(request, pk):
    pedido = _pedido_visible(request, pk)
    if not _factura_visible(request, pedido):
        raise Http404
    factura, creada = crear_factura(pedido, request.user)
    if creada:
        registrar_auditoria(
            request, "crear", "Factura", factura,
            f"Factura {factura.numero} generada para {pedido.codigo_pedido}",
        )
        historial.registrar(pedido, "factura_generada", f"Factura {factura.numero} generada.", request.user)
    pdf = generar_pdf(factura)
    return FileResponse(
        pdf,
        content_type="application/pdf",
        filename=f"factura-{factura.numero}.pdf",
    )


@seccion_requerida("pedidos")
def factura_descargar(request, pk):
    pedido = _pedido_visible(request, pk)
    if not _factura_visible(request, pedido):
        raise Http404
    factura, creada = crear_factura(pedido, request.user)
    if creada:
        registrar_auditoria(
            request, "crear", "Factura", factura,
            f"Factura {factura.numero} generada para {pedido.codigo_pedido}",
        )
        historial.registrar(pedido, "factura_generada", f"Factura {factura.numero} generada.", request.user)
    pdf = generar_pdf(factura)
    respuesta = FileResponse(pdf, content_type="application/pdf")
    respuesta["Content-Disposition"] = f'attachment; filename="factura-{factura.numero}.pdf"'
    return respuesta


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
@require_POST
def factura_enviar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    factura, creada = crear_factura(pedido, request.user)
    if creada:
        registrar_auditoria(
            request, "crear", "Factura", factura,
            f"Factura {factura.numero} generada para {pedido.codigo_pedido}",
        )
        historial.registrar(pedido, "factura_generada", f"Factura {factura.numero} generada.", request.user)
    enviado = enviar_factura(factura)
    if enviado:
        registrar_auditoria(
            request, "enviar", "Factura", factura,
            f"Factura {factura.numero} enviada al cliente",
        )
        historial.registrar(
            pedido, "factura_enviada",
            f"Factura {factura.numero} enviada a {factura.cliente_correo}.", request.user,
        )
        messages.success(request, "Factura enviada por correo.")
    else:
        registrar_auditoria(
            request, "envio_fallido", "Factura", factura,
            f"No se pudo enviar la factura {factura.numero}",
        )
        messages.warning(request, "No se pudo enviar la factura; revisa el correo del cliente o el SMTP.")
    return redirect("kanview:pedido-detalle", pk=pedido.pk)
