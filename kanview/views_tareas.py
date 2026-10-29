"""Tareas y actividades: tableros Kanban, cambio de estado y confirmación.

Las tareas y actividades comparten los mismos estados (`ESTADOS_KANBAN`) y
endpoints de cambio de estado. Los tableros envían POST con `Accept:
application/json`; el resto de pantallas sigue usando redirecciones normales.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import busqueda
from .auditoria import registrar as registrar_auditoria
from .historial import registrar as registrar_historial
from .models import ESTADOS_KANBAN, Actividades, Empleado, TareasPedido
from .notificaciones import notificar_area, notificar_cliente, notificar_staff
from .permisos import es_administrador, es_solo_cliente, es_trabajador, puede, seccion_requerida
from .views_site import _nav


def _volver_al_tablero(request):
    """Vuelve a /pedidos/ conservando la query del tablero (q, vista, etc.)."""
    url = reverse("kanview:pedidos-tablero")
    query = request.GET.urlencode()
    return f"{url}?{query}" if query else url


def _json_solicitado(request):
    return "application/json" in (request.headers.get("Accept") or "") or (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _cambiar_estado(request, objeto, etiqueta, responder_json=False):
    """Valida el estado contra ESTADOS_KANBAN, lo guarda y responde."""
    estado = (request.POST.get("estado") or "").strip()
    if estado not in dict(ESTADOS_KANBAN):
        mensaje = f"El estado «{estado}» no es válido: {etiqueta.lower()} no cambió."
        if responder_json:
            return JsonResponse({"error": mensaje}, status=400)
        messages.error(request, mensaje)
        return redirect(_volver_al_tablero(request))

    if isinstance(objeto, TareasPedido) and estado == "completado":
        estado_anterior = objeto.estado
        pendientes = objeto.actividades_set.filter(activo=True).exclude(estado="completado").count()
        if pendientes:
            mensaje = (
                f"La tarea «{objeto.nombre}» tiene {pendientes} actividad(es) sin completar. "
                "Confirma primero cada actividad."
            )
            if responder_json:
                return JsonResponse({"error": mensaje}, status=400)
            messages.error(request, mensaje)
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
        from .views_pedidos import estado_visible

        if objeto.id_pedido.id_cliente:
            notificar_cliente(
                objeto.id_pedido.id_cliente,
                "pedido",
                f"Tu pedido {objeto.id_pedido.codigo_pedido} está en estado "
                f"«{estado_visible(objeto.id_pedido)}».",
                reverse("kanview:pedido-detalle", args=[objeto.id_pedido.pk]),
                asunto="Kanview · Estado de tu pedido",
                enviar_email=False,
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
        from .views_pedidos import estado_visible

        estado_pedido = estado_visible(tarea.id_pedido)
        if tarea.id_pedido.id_cliente:
            notificar_cliente(
                tarea.id_pedido.id_cliente,
                "pedido",
                f"Tu pedido {tarea.id_pedido.codigo_pedido} está en estado «{estado_pedido}».",
                reverse("kanview:pedido-detalle", args=[tarea.id_pedido.pk]),
                asunto="Kanview · Estado de tu pedido",
                enviar_email=False,
            )

    if responder_json:
        return JsonResponse({
            "ok": True,
            "pk": objeto.pk,
            "estado": objeto.estado,
            "etiqueta": objeto.get_estado_display(),
        })
    messages.success(request, f"{etiqueta} pasó a «{objeto.get_estado_display()}».")
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
def tareas_tablero(request):
    """Tablero Kanban de tareas agrupadas por estado."""
    q = busqueda.texto(request)
    trabajador = (request.GET.get("trabajador") or "").strip()
    consulta = TareasPedido.objects.filter(activo=True).select_related(
        "id_pedido", "id_empleado"
    ).prefetch_related("actividades_set__id_empleado").order_by("fecha_fin", "nombre")
    consulta = busqueda.filtrar(
        consulta,
        q,
        [
            "nombre", "descripcion", "id_pedido__codigo_pedido",
            "id_empleado__nombre", "actividades__nombre",
        ],
    )
    if trabajador.isdigit():
        consulta = consulta.filter(
            Q(id_empleado_id=int(trabajador))
            | Q(actividades__id_empleado_id=int(trabajador))
        )
    tareas = list(consulta.distinct())
    for tarea in tareas:
        actividades = [actividad for actividad in tarea.actividades_set.all() if actividad.activo]
        total = len(actividades)
        completadas = sum(1 for actividad in actividades if actividad.estado == "completado")
        tarea.total_actividades = total
        tarea.actividades_completadas = completadas
        tarea.avance = round(completadas * 100 / total) if total else 0
    columnas = [
        {
            "clave": clave,
            "titulo": titulo,
            "tareas": [tarea for tarea in tareas if tarea.estado == clave],
        }
        for clave, titulo in ESTADOS_KANBAN
    ]
    return render(request, "kanview/tareas_tablero.html", {
        "columnas": columnas,
        "total_tareas": len(tareas),
        "trabajadores": Empleado.objects.filter(activo=True).order_by("nombre"),
        "trabajador_activo": trabajador,
        "puede_mover": puede(request.user, "tareas"),
        "cabecera_titulo": "Tareas",
        **_nav("Tareas", request),
        **busqueda.contexto(request, "Buscar tareas...", "tareas"),
    })


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
            **_nav("Tareas", request),
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
        mensaje = "No tienes permiso para confirmar esta tarea."
        if _json_solicitado(request):
            return JsonResponse({"error": mensaje}, status=403)
        messages.error(request, mensaje)
        return redirect(_volver_al_tablero(request))
    return _cambiar_estado(
        request, tarea, f"La tarea «{tarea.nombre}»", responder_json=_json_solicitado(request)
    )


@login_required
@require_POST
def actividad_estado(request, pk):
    """POST: cambia el estado de una actividad desde su modal o tablero.

    El Cliente puede cambiar las actividades de sus propios pedidos. El personal
    conserva las reglas de permisos por área para completar actividades.
    """
    actividad = get_object_or_404(Actividades, pk=pk)
    pedido = actividad.id_tarea.id_pedido
    es_cliente = es_solo_cliente(request.user)
    if es_cliente:
        if (pedido.id_cliente.correo or "").lower() != (request.user.email or "").lower():
            mensaje = "No puedes modificar una actividad de otro pedido."
            if _json_solicitado(request):
                return JsonResponse({"error": mensaje}, status=403)
            messages.error(request, mensaje)
            return redirect("kanview:pedidos-tablero")
    elif not puede(request.user, "tareas"):
        mensaje = "No tienes permiso para cambiar actividades."
        if _json_solicitado(request):
            return JsonResponse({"error": mensaje}, status=403)
        messages.error(request, mensaje)
        return redirect("kanview:pedidos-tablero")
    elif es_trabajador(request.user):
        # El trabajador solo manipula SUS actividades: no las de sus compañeros.
        empleado = getattr(request.user, "empleado_kanview", None)
        if empleado is None or actividad.id_empleado_id != empleado.pk:
            mensaje = "Solo puedes cambiar el estado de tus propias actividades asignadas."
            if _json_solicitado(request):
                return JsonResponse({"error": mensaje}, status=403)
            messages.error(request, mensaje)
            return redirect("kanview:actividades")
    estado = (request.POST.get("estado") or "").strip()
    if not es_cliente and estado == "completado" and not es_administrador(request.user):
        empleado = getattr(request.user, "empleado_kanview", None)
        if empleado is None or actividad.id_empleado_id != empleado.pk:
            mensaje = "Solo el trabajador asignado o Administración pueden completar esta actividad."
            if _json_solicitado(request):
                return JsonResponse({"error": mensaje}, status=403)
            messages.error(request, mensaje)
            return redirect(_volver_al_tablero(request))
    return _cambiar_estado(
        request, actividad, f"La actividad «{actividad.nombre}»", responder_json=_json_solicitado(request)
    )
