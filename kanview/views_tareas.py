"""Cambio de estado de tareas y actividades desde el tablero de procesos.

El tablero (`/pedidos/`, «Procesos») pinta las actividades de cada pedido y su
modal permite cambiar el estado. Estas dos FBV son el único punto de escritura:
validan el estado contra ``ESTADOS_KANBAN`` y vuelven al tablero conservando la
búsqueda. No hay pantalla propia de tareas: ``/tareas/`` redirige a
``/pedidos/``.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import ESTADOS_KANBAN, Actividades, TareasPedido
from .permisos import seccion_requerida


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

    objeto.estado = estado
    objeto.save(update_fields=["estado"])
    messages.success(
        request,
        f"{etiqueta} pasó a «{objeto.get_estado_display()}».",
    )
    return redirect(_volver_al_tablero(request))


@seccion_requerida("tareas")
@require_POST
def tarea_estado(request, pk):
    """POST: cambia el estado de una tarea desde el tablero."""
    tarea = get_object_or_404(TareasPedido, pk=pk)
    return _cambiar_estado(request, tarea, f"La tarea «{tarea.nombre}»")


@seccion_requerida("tareas")
@require_POST
def actividad_estado(request, pk):
    """POST: cambia el estado de una actividad desde su modal del tablero."""
    actividad = get_object_or_404(Actividades, pk=pk)
    return _cambiar_estado(request, actividad, f"La actividad «{actividad.nombre}»")
