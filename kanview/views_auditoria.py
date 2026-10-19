"""Vistas de Auditoría (FBV), conectadas a datos reales de ``Historial``."""

from django.core.paginator import Paginator
from django.utils import timezone

from . import busqueda
from .models import Empleado, Historial
from .permisos import seccion_requerida
from .views_site import _render

REGISTROS_POR_PAGINA = 10


def _clientes_del_historial():
    """Nombres de cliente que aparecen en el historial vigente (para el filtro)."""
    return (
        Historial.objects.filter(activo=True)
        .values_list("id_cliente__nombre", flat=True)
        .distinct()
        .order_by("id_cliente__nombre")
    )


@seccion_requerida("auditoria")
def auditoria(request):
    """Pantalla de auditoría: registros vigentes de Historial con cliente/empleado/producto.

    El buscador del header filtra en el servidor con ``?q=`` por nombre de
    cliente, empleado o producto (y código del producto).
    """
    q = busqueda.texto(request)
    registros = busqueda.filtrar(
        Historial.objects.filter(activo=True),
        q,
        (
            "id_cliente__nombre",
            "id_empleado__nombre",
            "id_producto__nombre",
            "id_producto__codigo_producto",
        ),
    ).select_related(
        "id_cliente", "id_empleado", "id_producto"
    ).order_by("-fecha_creacion", "-hora_creacion")

    paginator = Paginator(registros, REGISTROS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get("page"))

    return _render(
        request,
        "kanview/auditoria.html",
        "Auditoría",
        historial=page_obj.object_list,
        page_obj=page_obj,
        paginator=paginator,
        is_paginated=page_obj.has_other_pages(),
        total_historial=paginator.count,
        registros_hoy=registros.filter(fecha_creacion=timezone.localdate()).count(),
        ultimo_registro=registros.first(),
        cargos=Empleado.CARGOS,
        clientes=_clientes_del_historial(),
        **busqueda.contexto(request, "Buscar en la auditoría...", "auditoría"),
    )
