"""Pantalla de existencias: lee el stock directamente de ``Producto``.

Convención del proyecto: vistas como funciones (FBV), nunca clases. El
helper `_render` de `views_site` inyecta `nav_items` y `active` para el
sidebar compartido, así que aquí solo se pasan los datos de la pantalla.

``Producto`` es la única fuente de verdad: ``cantidad`` es el stock y
``categoria`` la categoría. Esta pantalla ya no es un módulo del menú (el
stock se gestiona desde «Productos»), pero la ruta se conserva para no romper
enlaces y para ver el panorama de existencias de un vistazo.

Campos del diseño que no existen en los modelos (ubicación/bodega,
proveedor) se descartaron; el estado de stock se deriva de `cantidad`.
"""

from django.urls import reverse

from . import busqueda
from .models import Producto
from .notificaciones import UMBRAL_STOCK_BAJO
from .permisos import seccion_requerida
from .views_site import _render


def _estado(cantidad):
    """Deriva (texto, clases de la píldora, agotado) a partir de la cantidad."""
    if cantidad <= 0:
        return "Agotado", "bg-error/10 text-error", True
    if cantidad <= UMBRAL_STOCK_BAJO:
        return "Stock Bajo", "bg-tertiary-container/20 text-tertiary", False
    return "En Stock", "bg-primary/10 text-primary", False


def _fila(producto):
    """Aplana un Producto para la tabla de existencias."""
    cantidad = producto.cantidad or 0
    estado, estado_clase, agotado = _estado(cantidad)
    return {
        "id": producto.pk,
        "codigo": producto.codigo_producto,
        "nombre": producto.nombre,
        "categoria": producto.get_categoria_display(),
        "cantidad": cantidad,
        "precio": producto.precio,
        "estado": estado,
        "estado_clase": estado_clase,
        "agotado": agotado,
        "activo": bool(producto.activo),
        # Acciones de la fila: editar y desactivar/reactivar el PRODUCTO.
        "editar_url": reverse("kanview:producto-editar", args=[producto.pk]),
        "desactivar_url": reverse("kanview:producto-eliminar", args=[producto.pk]),
        "reactivar_url": reverse("kanview:producto-reactivar", args=[producto.pk]),
        "acciones": {
            "editar": reverse("kanview:producto-editar", args=[producto.pk]),
            "desactivar": reverse("kanview:producto-eliminar", args=[producto.pk]),
            "reactivar": reverse("kanview:producto-reactivar", args=[producto.pk]),
        },
    }


# ---- Vistas ---------------------------------------------------------------

@seccion_requerida("inventario")
def inventario(request):
    """Lista las existencias vigentes por producto.

    El buscador del header filtra en el servidor con ``?q=`` por nombre,
    código o categoría del producto.
    """
    q = busqueda.texto(request)
    productos = busqueda.filtrar(
        Producto.objects.filter(activo=True),
        q,
        ("nombre", "codigo_producto", "categoria"),
    ).order_by("nombre", "pk")
    filas = [_fila(producto) for producto in productos]
    return _render(
        request,
        "kanview/inventario.html",
        "Inventario",
        filas=filas,
        categorias=sorted({fila["categoria"] for fila in filas if fila["categoria"]}),
        total_lineas=len(filas),
        total_stock=sum(fila["cantidad"] for fila in filas),
        total_agotados=sum(1 for fila in filas if fila["agotado"]),
        total_stock_bajo=sum(1 for fila in filas if fila["estado"] == "Stock Bajo"),
        **busqueda.contexto(request, "Buscar en inventario...", "inventario"),
    )
