"""Pantalla de Actividades: tablero kanban agrupado por ESTADO real.

Misma lógica que ``views_tareas`` pero mostrando únicamente las actividades
(``Actividades``), agrupadas por estado (pendiente / en progreso / completado)
y con el pedido y el empleado responsable de cada una.
"""

from . import busqueda
from .models import ESTADOS_KANBAN, Actividades
from .permisos import seccion_requerida
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


@seccion_requerida("tareas")
def actividades(request):
    """Tablero de actividades agrupadas por estado (con buscador del header)."""
    q = busqueda.texto(request)
    actividades_qs = busqueda.filtrar(
        Actividades.objects.select_related(
            "id_tarea", "id_tarea__id_pedido", "id_tarea__id_pedido__id_empleado"
        ).order_by("fecha_fin", "nombre"),
        q,
        [
            "nombre",
            "descripcion",
            "estado",
            "id_tarea__nombre",
            "id_tarea__id_pedido__codigo_pedido",
            "id_empleado__nombre",
        ],
    )
    grupos, otras = _agrupar(actividades_qs)

    return _render(
        request,
        "kanview/actividades.html",
        "Actividades",
        cabecera_titulo="Actividades",
        **busqueda.contexto(request, "Buscar actividades...", "actividades"),
        pendientes=grupos["pendiente"],
        en_progreso=grupos["en progreso"],
        completadas=grupos["completado"],
        otras=otras,
        total_actividades=actividades_qs.count(),
    )
