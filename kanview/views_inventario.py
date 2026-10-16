"""Pantalla de Inventario: conecta el diseño de Stitch con datos reales.

Convención del proyecto: vistas como funciones (FBV), nunca clases. El
helper `_render` de `views_site` inyecta `nav_items` y `active` para el
sidebar compartido, así que aquí solo se pasan los datos de la pantalla.

Campos del diseño que no existen en los modelos (ubicación/bodega,
proveedor) se descartaron; el estado de stock se deriva de `cantidad`.
"""

from django.contrib.auth.decorators import login_required

from .models import Inventario
from .views_site import _render

# A partir de esta cantidad (inclusive) la línea se marca como "Stock Bajo".
UMBRAL_STOCK_BAJO = 10


def _estado(cantidad):
    """Deriva (texto, clases de la píldora, agotado) a partir de la cantidad."""
    if cantidad <= 0:
        return "Agotado", "bg-error/10 text-error", True
    if cantidad <= UMBRAL_STOCK_BAJO:
        return "Stock Bajo", "bg-tertiary-container/20 text-tertiary", False
    return "En Stock", "bg-primary/10 text-primary", False


def _fila(linea):
    """Aplana una línea de Inventario junto con su Producto para el template."""
    producto = linea.id_producto
    cantidad = linea.cantidad or 0
    estado, estado_clase, agotado = _estado(cantidad)
    return {
        "id": linea.pk,
        "codigo": producto.codigo_producto,
        "nombre": producto.nombre,
        "categoria": producto.categoria,
        "cantidad": cantidad,
        "precio": producto.precio,
        "estado": estado,
        "estado_clase": estado_clase,
        "agotado": agotado,
    }


# ---- Vistas ---------------------------------------------------------------

@login_required
def inventario(request):
    """Lista el inventario real cruzando cada línea con su producto."""
    lineas = list(
        Inventario.objects.select_related("id_producto").order_by("id_producto__nombre", "id")
    )
    filas = [_fila(linea) for linea in lineas]
    return _render(
        request,
        "kanview/inventario.html",
        "Inventory",
        inventario_items=lineas,
        filas=filas,
        categorias=sorted({fila["categoria"] for fila in filas if fila["categoria"]}),
        total_lineas=len(filas),
        total_stock=sum(fila["cantidad"] for fila in filas),
        total_agotados=sum(1 for fila in filas if fila["agotado"]),
        total_stock_bajo=sum(1 for fila in filas if fila["estado"] == "Stock Bajo"),
    )
