"""Pantalla de Actividades: tablero kanban agrupado por ESTADO real.

Misma lógica que ``views_tareas`` pero mostrando únicamente las actividades
(``Actividades``), agrupadas por estado (pendiente / en progreso / completado)
y con el pedido y el empleado responsable de cada una.

El rol Trabajador solo ve SUS actividades (las que tiene asignadas): no puede
ver las tareas de sus compañeros.
"""

from . import busqueda
from django.db.models import Q

from .models import ESTADOS_KANBAN, Actividades, Empleado
from .permisos import es_trabajador, puede, seccion_requerida
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
    cargo = (request.GET.get("cargo") or "").strip()
    trabajador = (request.GET.get("trabajador") or "").strip()
    actividades_qs = busqueda.filtrar(
        Actividades.objects.select_related(
            "id_tarea", "id_tarea__id_pedido", "id_tarea__id_pedido__id_empleado",
            "id_empleado",
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
    if cargo:
        actividades_qs = actividades_qs.filter(id_empleado__cargo=cargo)
    # El trabajador solo ve SUS actividades asignadas: no las de sus compañeros.
    empleado = getattr(request.user, "empleado_kanview", None)
    if es_trabajador(request.user) and empleado is not None:
        actividades_qs = actividades_qs.filter(id_empleado=empleado)
    if trabajador.isdigit():
        actividades_qs = actividades_qs.filter(
            Q(id_empleado_id=int(trabajador))
            | Q(id_tarea__id_empleado_id=int(trabajador))
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
        puede_mover=puede(request.user, "tareas"),
        cargos=Empleado.CARGOS,
        cargo_activo=cargo,
        # El trabajador solo se filtra a sí mismo: no ve a sus compañeros.
        trabajadores=(
            Empleado.objects.filter(pk=empleado.pk)
            if es_trabajador(request.user) and empleado is not None
            else Empleado.objects.filter(activo=True).order_by("nombre")
        ),
        trabajador_activo=trabajador,
    )
