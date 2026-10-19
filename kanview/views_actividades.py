"""Pantalla de Actividades: tablero kanban agrupado por ESTADO real.

Misma lógica que ``views_tareas`` pero mostrando únicamente las actividades
(``Actividades``), agrupadas por estado (pendiente / en progreso / completado)
y con el pedido y el empleado responsable de cada una.
"""

from django.contrib.auth.decorators import login_required

from .models import ESTADOS_KANBAN, Actividades
from .views_site import _render

# Columnas del tablero, en el orden real de ESTADOS_KANBAN.
COLUMNAS = tuple(estado for estado, _etiqueta in ESTADOS_KANBAN)


def _agrupar(queryset):
    """Reparte un queryset de actividades en listas por estado.

    Las actividades con un estado fuera de ESTADOS_KANBAN no rompen la
    pantalla: quedan en la lista `otras`.
    """
    grupos = {estado: [] for estado in COLUMNAS}
    otras = []
    for obj in queryset:
        if obj.estado in grupos:
            grupos[obj.estado].append(obj)
        else:
            otras.append(obj)
    return grupos, otras


@login_required
def actividades(request):
    """Tablero de actividades agrupadas por estado."""
    actividades_qs = (
        Actividades.objects.select_related(
            "id_tarea", "id_tarea__id_pedido", "id_tarea__id_pedido__id_empleado"
        )
        .order_by("fecha_fin", "nombre")
    )
    grupos, otras = _agrupar(actividades_qs)

    return _render(
        request,
        "kanview/actividades.html",
        "Actividades",
        pendientes=grupos["pendiente"],
        en_progreso=grupos["en progreso"],
        completadas=grupos["completado"],
        otras=otras,
        total_actividades=Actividades.objects.count(),
    )
