from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum

from .models import AnalisisFinanciero
from .views_site import _render


@login_required
def finanzas(request):
    """Pantalla de Finanzas con KPIs, gráfica y tabla alimentados con datos reales.

    Todos los agregados se derivan exclusivamente de los campos existentes del
    modelo AnalisisFinanciero (gastos, fuentes_ingresos, productos_vendidos).
    """
    # Lista de registros con la relación ya cargada y el balance por fila
    # anotado en la query (no se toca el modelo).
    registros = list(
        AnalisisFinanciero.objects.select_related("id_administrador")
        .annotate(balance=F("fuentes_ingresos") - F("gastos"))
        .order_by("-id")
    )

    # Agregados reales.
    agregados = AnalisisFinanciero.objects.aggregate(
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
    )
