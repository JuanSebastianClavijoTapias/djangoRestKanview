"""Pantalla de Catálogo de productos (solo lectura, datos reales).

FBV `catalogo` que alimenta `kanview/catalogo.html`: lista de productos con sus
tarjetas, chips de categoría, ficha lateral (detalle) e historial de pedidos
por mes derivado de `Pedido`.

No crea ni modifica modelos: solo consulta `Producto`, `Catalogo`,
`Inventario` y `Pedido`.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.urls import reverse
from django.utils import timezone

from .models import Catalogo, Inventario, Pedido, Producto
from .views_site import _render

#: Un producto con esta cantidad o menos se muestra como "Bajo stock".
STOCK_BAJO = 5

#: Meses que muestra el gráfico de historial de la ficha lateral.
MESES_VENTANA = 6

MESES_CORTOS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


# ---- Helpers (funciones, no clases) ---------------------------------------

def _moneda_cop(valor):
    """Formatea un número como pesos colombianos: 4500000 -> '4.500.000'."""
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return valor


def _meses_ventana(hoy, cantidad=MESES_VENTANA):
    """[(anio, mes), ...] de los últimos `cantidad` meses (más antiguo primero)."""
    anio, mes = hoy.year, hoy.month
    ventana = []
    for _ in range(cantidad):
        ventana.append((anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(ventana))


def _pedidos_por_mes(producto_id, ventana):
    """Pedidos del producto alineados con la ventana de meses recibida."""
    filas = (
        Pedido.objects.filter(id_producto_id=producto_id)
        .values("fecha_creacion__year", "fecha_creacion__month")
        .annotate(total=Count("pk"))
    )
    por_mes = {
        (fila["fecha_creacion__year"], fila["fecha_creacion__month"]): fila["total"]
        for fila in filas
    }
    return [por_mes.get(clave, 0) for clave in ventana]


def _datos_ficha(producto, ventana, inventario_por_producto, categoria_catalogo):
    """Datos que la ficha lateral (JS) pinta para un producto."""
    totales = _pedidos_por_mes(producto.pk, ventana)
    maximo = max(totales, default=0)
    stock_bajo = producto.cantidad <= STOCK_BAJO
    return {
        "id": producto.pk,
        "codigo": producto.codigo_producto,
        "nombre": producto.nombre,
        "categoria": categoria_catalogo or producto.categoria,
        "descripcion": producto.descripcion,
        "cantidad": producto.cantidad,
        "inventario": inventario_por_producto.get(producto.pk, producto.cantidad),
        "estado": "Bajo stock" if stock_bajo else "En stock",
        "stock_bajo": stock_bajo,
        "precio": _moneda_cop(producto.precio),
        "editar_url": reverse("kanview:producto-editar", args=[producto.pk]),
        "ventas_total": sum(totales),
        "ventas_max": maximo,
        "serie": [
            {
                "label": MESES_CORTOS[mes - 1],
                "total": total,
                "pct": round(total * 100 / maximo) if maximo else 0,
            }
            for (_anio, mes), total in zip(ventana, totales)
        ],
    }


# ---- Vista -----------------------------------------------------------------

@login_required
def catalogo(request):
    """Catálogo de productos con filtro por categoría (query `?categoria=`)."""
    filtro = (request.GET.get("categoria") or "").strip()

    consulta = Producto.objects.all()
    if filtro:
        consulta = consulta.filter(categoria__iexact=filtro)
    productos = list(consulta.order_by("-cantidad", "nombre"))

    categorias = list(
        Producto.objects.exclude(categoria="")
        .values_list("categoria", flat=True)
        .order_by("categoria")
        .distinct()
    )

    destacado = productos[0] if productos else None
    restantes = productos[1:]

    # Categoría del catálogo (modelo Catalogo) del producto destacado, si existe.
    catalogo_destacado = None
    if destacado is not None:
        catalogo_destacado = (
            Catalogo.objects.filter(id_producto=destacado).select_related("id_inventario").first()
        )

    categoria_catalogo = {
        fila["id_producto"]: fila["categorias"]
        for fila in Catalogo.objects.values("id_producto", "categorias")
    }
    inventario_por_producto = {
        fila["id_producto"]: fila["total"]
        for fila in Inventario.objects.values("id_producto").annotate(total=Sum("cantidad"))
    }

    ventana = _meses_ventana(timezone.localdate())
    datos_ficha = {
        str(producto.pk): _datos_ficha(
            producto,
            ventana,
            inventario_por_producto,
            categoria_catalogo.get(producto.pk),
        )
        for producto in productos
    }

    agregados = Producto.objects.aggregate(
        unidades=Sum("cantidad"),
        valor=Sum(F("precio") * F("cantidad")),
    )

    return _render(
        request,
        "kanview/catalogo.html",
        "Catálogo",
        productos=productos,
        producto_destacado=destacado,
        productos_restantes=restantes,
        categorias=categorias,
        categoria_activa=filtro,
        catalogo_destacado=catalogo_destacado,
        datos_ficha=datos_ficha,
        umbral_stock_bajo=STOCK_BAJO,
        total_productos=len(productos),
        unidades_totales=agregados["unidades"] or 0,
        valor_inventario=_moneda_cop(agregados["valor"] or 0),
    )
