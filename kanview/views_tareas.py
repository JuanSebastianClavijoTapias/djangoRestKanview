"""Tareas y actividades: cambio de estado, confirmación y detalle.

El tablero de Procesos sigue siendo el centro operativo, pero las tareas tienen
una vista propia para revisar sus actividades y confirmar su finalización por
área. El cierre exige que todas las actividades estén completadas.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auditoria import registrar as registrar_auditoria
from .historial import registrar as registrar_historial
from .models import ESTADOS_KANBAN, Actividades, TareasPedido
from .notificaciones import notificar_area, notificar_cliente, notificar_staff
from .permisos import es_administrador, seccion_requerida
from .views_site import _nav


def _volver_al_tablero(request):
    """Vuelve a /pedidos/ conservando la query del tablero (q, vista, etc.)."""
    url = reverse("kanview:pedidos-tablero")
    query = request.GET.urlencode()
    return f"{url}?{query}" if query else url


def _cambiar_estado(request, objeto, etiqueta):
    """Valida el estado contra ESTADOS_KANBAN, lo guarda y avisa en español."""
    estado = (request.POST.get("estado") or "").strip()
    validos = dict(ESTADOS_KANBAN)
    if estado not in validos:
        messages.error(
            request,
            f"El estado «{estado}» no es válido: {etiqueta.lower()} no cambió.",
        )
        return redirect(_volver_al_tablero(request))

    if isinstance(objeto, TareasPedido) and estado == "completado":
        estado_anterior = objeto.estado
        pendientes = objeto.actividades_set.filter(activo=True).exclude(estado="completado").count()
        if pendientes:
            messages.error(
                request,
                f"La tarea «{objeto.nombre}» tiene {pendientes} actividad(es) sin completar. "
                "Confirma primero cada actividad.",
            )
            return redirect(_volver_al_tablero(request))
        objeto.estado = estado
        objeto.confirmado_por = request.user
        objeto.fecha_confirmacion = timezone.now()
        objeto.save(update_fields=["estado", "confirmado_por", "fecha_confirmacion"])
        if estado_anterior != "completado" and objeto.id_empleado_id:
            objeto.id_empleado.tareas_realizadas += 1
            objeto.id_empleado.save(update_fields=["tareas_realizadas"])
        registrar_auditoria(
            request, "confirmar", "Tarea", objeto,
            f"Tarea «{objeto.nombre}» confirmada como completada.",
        )
    else:
        objeto.estado = estado
        objeto.save(update_fields=["estado"])
        registrar_auditoria(
            request, "cambiar_estado", type(objeto).__name__, objeto,
            f"{etiqueta} pasó a «{objeto.get_estado_display()}».",
        )

    if isinstance(objeto, TareasPedido):
        registrar_historial(
            objeto.id_pedido,
            "tarea_actualizada",
            f"Tarea «{objeto.nombre}»: {objeto.get_estado_display()}.",
            request.user,
        )
        if estado == "completado":
            notificar_staff(
                "tarea",
                f"La tarea «{objeto.nombre}» fue confirmada como completada.",
                reverse("kanview:tarea-detalle", args=[objeto.pk]),
            )
        from .views_pedidos import estado_del_pedido

        if objeto.id_pedido.id_cliente:
            notificar_cliente(
                objeto.id_pedido.id_cliente,
                "pedido",
                f"Tu pedido {objeto.id_pedido.codigo_pedido} está en estado "
                f"«{estado_del_pedido(objeto.id_pedido)}».",
                reverse("kanview:pedido-detalle", args=[objeto.id_pedido.pk]),
                asunto="Kanview · Estado de tu pedido",
            )
    else:
        tarea = objeto.id_tarea
        if estado == "completado":
            notificar_area(
                getattr(objeto.id_empleado, "cargo", ""),
                "actividad",
                f"Actividad finalizada: «{objeto.nombre}» del pedido "
                f"{tarea.id_pedido.codigo_pedido}.",
                reverse("kanview:actividades"),
            )
            notificar_staff(
                "actividad",
                f"Actividad completada: «{objeto.nombre}» "
                f"({tarea.id_pedido.codigo_pedido}).",
                reverse("kanview:actividades"),
            )
        registrar_historial(
            tarea.id_pedido,
            "actividad_actualizada",
            f"Actividad «{objeto.nombre}»: {objeto.get_estado_display()}.",
            request.user,
        )
        from .views_pedidos import estado_del_pedido

        estado_pedido = estado_del_pedido(tarea.id_pedido)
        if tarea.id_pedido.id_cliente:
            notificar_cliente(
                tarea.id_pedido.id_cliente,
                "pedido",
                f"Tu pedido {tarea.id_pedido.codigo_pedido} está en estado «{estado_pedido}».",
                reverse("kanview:pedido-detalle", args=[tarea.id_pedido.pk]),
                asunto="Kanview · Estado de tu pedido",
            )

    messages.success(
        request,
        f"{etiqueta} pasó a «{objeto.get_estado_display()}».",
    )
    return redirect(_volver_al_tablero(request))


def _puede_confirmar(usuario, tarea):
    """El responsable, su área o Administración pueden confirmar la tarea."""
    if es_administrador(usuario):
        return True
    empleados = set(tarea.actividades_set.exclude(id_empleado=None).values_list("id_empleado_id", flat=True))
    if tarea.id_empleado_id:
        empleados.add(tarea.id_empleado_id)
    empleado = getattr(usuario, "empleado_kanview", None)
    if empleado is None:
        return False
    if empleado.pk in empleados:
        return True
    cargos = set(tarea.actividades_set.exclude(id_empleado=None).values_list("id_empleado__cargo", flat=True))
    if tarea.id_empleado_id:
        cargos.add(tarea.id_empleado.cargo)
    return empleado.cargo in cargos


@seccion_requerida("tareas")
def tarea_detalle(request, pk):
    """Detalle de una tarea con sus actividades y el botón de confirmación."""
    tarea = get_object_or_404(
        TareasPedido.objects.select_related("id_pedido", "id_empleado").prefetch_related(
            "actividades_set__id_empleado"
        ),
        pk=pk,
    )
    actividades = tarea.actividades_set.filter(activo=True).select_related("id_empleado")
    pendientes = actividades.exclude(estado="completado").count()
    return render(
        request,
        "kanview/tarea_detalle.html",
        {
            "tarea": tarea,
            "actividades": actividades,
            "pendientes": pendientes,
            "puede_confirmar": _puede_confirmar(request.user, tarea),
            "estados": ESTADOS_KANBAN,
            **_nav("Actividades", request),
        },
    )


@seccion_requerida("tareas")
@require_POST
def tarea_confirmar(request, pk):
    """Confirma la finalización de una tarea; exige actividades completadas."""
    tarea = get_object_or_404(TareasPedido, pk=pk)
    if not _puede_confirmar(request.user, tarea):
        messages.error(request, "No tienes permiso para confirmar esta tarea.")
        return redirect("kanview:tarea-detalle", pk=tarea.pk)
    pendientes = tarea.actividades_set.filter(activo=True).exclude(estado="completado").count()
    if pendientes:
        messages.error(
            request,
            f"Faltan {pendientes} actividad(es) por completar antes de cerrar la tarea.",
        )
        return redirect("kanview:tarea-detalle", pk=tarea.pk)

    estado_anterior = tarea.estado
    tarea.estado = "completado"
    tarea.confirmado_por = request.user
    tarea.fecha_confirmacion = timezone.now()
    tarea.save(update_fields=["estado", "confirmado_por", "fecha_confirmacion"])
    if estado_anterior != "completado" and tarea.id_empleado_id:
        tarea.id_empleado.tareas_realizadas += 1
        tarea.id_empleado.save(update_fields=["tareas_realizadas"])
    registrar_historial(
        tarea.id_pedido,
        "tarea_confirmada",
        f"Tarea «{tarea.nombre}» confirmada por {request.user}.",
        request.user,
    )
    registrar_auditoria(
        request, "confirmar", "Tarea", tarea,
        f"Tarea «{tarea.nombre}» confirmada.",
    )
    notificar_staff(
        "tarea",
        f"La tarea «{tarea.nombre}» fue confirmada como completada.",
        reverse("kanview:tarea-detalle", args=[tarea.pk]),
    )
    if tarea.id_pedido.id_cliente:
        notificar_cliente(
            tarea.id_pedido.id_cliente,
            "tarea",
            f"La tarea «{tarea.nombre}» de tu pedido {tarea.id_pedido.codigo_pedido} fue completada.",
            reverse("kanview:pedido-detalle", args=[tarea.id_pedido.pk]),
        )
    messages.success(request, "Tarea confirmada como completada.")
    return redirect("kanview:tarea-detalle", pk=tarea.pk)


@seccion_requerida("tareas")
@require_POST
def tarea_estado(request, pk):
    """POST: cambia el estado de una tarea desde el tablero."""
    tarea = get_object_or_404(TareasPedido, pk=pk)
    estado = (request.POST.get("estado") or "").strip()
    if estado == "completado" and not _puede_confirmar(request.user, tarea):
        messages.error(request, "No tienes permiso para confirmar esta tarea.")
        return redirect(_volver_al_tablero(request))
    return _cambiar_estado(request, tarea, f"La tarea «{tarea.nombre}»")


@seccion_requerida("tareas")
@require_POST
def actividad_estado(request, pk):
    """POST: cambia el estado de una actividad desde su modal del tablero."""
    actividad = get_object_or_404(Actividades, pk=pk)
    estado = (request.POST.get("estado") or "").strip()
    if estado == "completado" and not es_administrador(request.user):
        empleado = getattr(request.user, "empleado_kanview", None)
        if empleado is None or actividad.id_empleado_id != empleado.pk:
            messages.error(request, "Solo el trabajador asignado o Administración pueden completar esta actividad.")
            return redirect(_volver_al_tablero(request))
    return _cambiar_estado(request, actividad, f"La actividad «{actividad.nombre}»")
