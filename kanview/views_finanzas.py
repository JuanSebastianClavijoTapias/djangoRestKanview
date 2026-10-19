from decimal import Decimal

from django.db.models import F, Sum

from . import busqueda
from .models import AnalisisFinanciero
from .permisos import seccion_requerida
from .views_site import _render


@seccion_requerida("finanzas")
def finanzas(request):
    """Pantalla de Finanzas con KPIs, gráfica y tabla alimentados con datos reales.

    Todos los agregados se derivan exclusivamente de los campos existentes del
    modelo AnalisisFinanciero (gastos, fuentes_ingresos, productos_vendidos).
    """
    # El buscador del header filtra con `?q=` por administrador (nombre o
    # documento). La lista y los KPIs salen del mismo conjunto filtrado.
    q = busqueda.texto(request)
    vigentes = busqueda.filtrar(
        AnalisisFinanciero.objects.filter(activo=True),
        q,
        ("id_administrador__nombre", "id_administrador__documento"),
    )

    # Lista de registros con la relación ya cargada y el balance por fila
    # anotado en la query (no se toca el modelo).
    registros = list(
        vigentes
        .select_related("id_administrador")
        .annotate(balance=F("fuentes_ingresos") - F("gastos"))
        .order_by("-id")
    )

    # Agregados reales (solo registros vigentes).
    agregados = vigentes.aggregate(
        total_gastos=Sum("gastos"),
        total_ingresos=Sum("fuentes_ingresos"),
        total_productos_vendidos=Sum("productos_vendidos"),
    )
    total_gastos = agregados["total_gastos"] or Decimal("0")
    total_ingresos = agregados["total_ingresos"] or Decimal("0")
    total_productos_vendidos = agregados["total_productos_vendidos"] or 0
    balance = total_ingresos - total_gastos
    total_registros = len(registros)

    # KPI derivado: margen neto (%) a partir del balance y los ingresos.
    margen = (balance / total_ingresos * 100) if total_ingresos else Decimal("0")

    # Serie real para la gráfica: un punto por registro de análisis.
    grafica_registros = [
        {
            "label": f"#{r.pk} · {r.id_administrador.nombre}",
            "ingresos": float(r.fuentes_ingresos),
            "gastos": float(r.gastos),
        }
        for r in registros
    ]

    return _render(
        request,
        "kanview/finanzas.html",
        "Finanzas",
        registros=registros,
        total_registros=total_registros,
        total_gastos=total_gastos,
        total_ingresos=total_ingresos,
        balance=balance,
        total_productos_vendidos=total_productos_vendidos,
        margen=margen,
        grafica_registros=grafica_registros,
        **busqueda.contexto(request, "Buscar movimientos...", "finanzas"),
    )
