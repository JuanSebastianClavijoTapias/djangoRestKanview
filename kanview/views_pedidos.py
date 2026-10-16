"""Vistas de Pedidos (FBV) conectadas a datos reales del modelo Pedido.

Convención del proyecto: funciones (no clases), decoradas con @login_required
y renderizadas con el helper _render de views_site.

Columnas del tablero kanban derivadas SOLO de campos reales del modelo Pedido
(el modelo únicamente tiene 2 estados: "activo" / "inactivo"):

    - "Pendiente"  -> estado == "activo" y sin evidencias adjuntas.
    - "En proceso" -> estado == "activo" y con evidencias adjuntas.
    - "Hecho"      -> estado == "inactivo".

No se inventan campos: el criterio usa ``estado`` + ``evidencias``.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Pedido
from .views_site import _render


# ---- Helpers (funciones, no clases) --------------------------------------

def _pedidos_queryset():
    """Pedido con sus relaciones resueltas de una sola consulta."""
    return Pedido.objects.select_related(
        "id_cliente",
        "id_empleado",
        "id_producto",
    ).order_by("-id")


def _sin_evidencias():
    """Filtro: pedidos sin evidencias adjuntas (campo real ``evidencias``)."""
    return Q(evidencias="") | Q(evidencias__isnull=True)


# ---- Vistas ---------------------------------------------------------------

@login_required
def pedidos_tablero(request):
    """Tablero kanban de pedidos (active="Orders")."""
    pedidos = _pedidos_queryset()
    pedidos_activos = pedidos.filter(estado="activo")

    pedidos_pendientes = pedidos_activos.filter(_sin_evidencias())
    pedidos_en_proceso = pedidos_activos.exclude(_sin_evidencias())
    pedidos_hechos = pedidos.filter(estado="inactivo")

    return _render(
        request,
        "kanview/pedidos_tablero.html",
        "Orders",
        pedidos=pedidos,
        pedidos_pendientes=pedidos_pendientes,
        pedidos_en_proceso=pedidos_en_proceso,
        pedidos_hechos=pedidos_hechos,
        total_pedidos=pedidos.count(),
    )


@login_required
def pedido_detalle(request, pk):
    """Detalle de un pedido (active="Orders")."""
    pedido = get_object_or_404(_pedidos_queryset(), pk=pk)

    return _render(
        request,
        "kanview/pedidos_detalle.html",
        "Orders",
        pedido=pedido,
    )
