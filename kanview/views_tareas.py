"""Pantalla de Tareas y Actividades: tablero kanban agrupado por ESTADO real.

El diseño original agrupaba por departamento (Costura / Tapicería / Carpintería)
con prioridad y responsable, datos que no existen en el modelo. Aquí se reagrupa
por el estado real de `TareasPedido` / `Actividades` (pendiente / en progreso /
completado) reutilizando el mismo layout de columnas y tarjetas.
"""

from django.contrib.auth.decorators import login_required

from .models import ESTADOS_KANBAN, Actividades, TareasPedido
from .views_site import _render

# Columnas del tablero, en el orden real de ESTADOS_KANBAN (3 columnas del diseño).
COLUMNAS = tuple(estado for estado, _etiqueta in ESTADOS_KANBAN)


def _agrupar(queryset):
    """Reparte un queryset de tareas/actividades en listas por estado."""
    grupos = {estado: [] for estado in COLUMNAS}
    for obj in queryset:
        grupos[obj.estado].append(obj)
    return grupos


@login_required
def tareas(request):
    """Tablero de tareas de pedido y actividades agrupadas por estado."""
    grupos_tareas = _agrupar(
        TareasPedido.objects.select_related("id_pedido", "id_pedido__id_empleado")
        .prefetch_related("actividades_set")
        .order_by("fecha_fin", "nombre")
    )
    grupos_actividades = _agrupar(
        Actividades.objects.select_related("id_tarea", "id_tarea__id_pedido").order_by(
            "fecha_fin", "nombre"
        )
    )

    return _render(
        request,
        "kanview/tareas.html",
        "Tasks",
        pendientes=grupos_tareas["pendiente"],
        en_progreso=grupos_tareas["en progreso"],
        completadas=grupos_tareas["completado"],
        actividades_pendientes=grupos_actividades["pendiente"],
        actividades_en_progreso=grupos_actividades["en progreso"],
        actividades_completadas=grupos_actividades["completado"],
        total_tareas=TareasPedido.objects.count(),
        total_actividades=Actividades.objects.count(),
    )
