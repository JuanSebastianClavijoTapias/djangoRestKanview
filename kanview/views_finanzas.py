"""Pantalla de Finanzas con KPIs, flujo de caja y fuentes de ingresos reales."""

from collections import OrderedDict
from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone

from . import busqueda
from .models import AnalisisFinanciero
from .permisos import seccion_requerida
from .views_site import _render

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
PERIODOS = (3, 6, 12)
COLORES_FUENTES = ("#006565", "#76d6d5", "#8b4823", "#5d5f5f", "#bdc9c8")


def _meses_anteriores(hoy, cantidad):
    """Lista de ``(año, mes)`` desde el más antiguo hasta el mes actual."""
    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1
    return list(reversed(meses))


def _periodo(request):
    try:
        periodo = int(request.GET.get("periodo", 6))
    except (TypeError, ValueError):
        periodo = 6
    return periodo if periodo in PERIODOS else 6


def _flujo_caja(registros, hoy, cantidad):
    """Ingresos y gastos agrupados por mes para el período elegido."""
    meses = {clave: {"ingresos": Decimal("0"), "gastos": Decimal("0")} for clave in _meses_anteriores(hoy, cantidad)}
    for registro in registros:
        fecha = registro.fecha or hoy
        clave = (fecha.year, fecha.month)
        if clave not in meses:
            continue
        meses[clave]["ingresos"] += registro.fuentes_ingresos
        meses[clave]["gastos"] += registro.gastos
    return [
        {
            "label": f"{MESES[mes - 1]} {anio}",
            "ingresos": float(valores["ingresos"]),
            "gastos": float(valores["gastos"]),
        }
        for (anio, mes), valores in meses.items()
    ]


def _fuentes_ingreso(registros):
    """Participación real de cada fuente de ingreso registrada."""
    etiquetas = dict(AnalisisFinanciero.FUENTES_INGRESO)
    totales = OrderedDict()
    for registro in registros:
        fuente = registro.fuente_ingreso or "otro"
        totales[fuente] = totales.get(fuente, Decimal("0")) + registro.fuentes_ingresos
    total = sum(totales.values(), Decimal("0"))
    datos = []
    for indice, (fuente, valor) in enumerate(totales.items()):
        datos.append(
            {
                "clave": fuente,
                "label": etiquetas.get(fuente, fuente.title()),
                "valor": float(valor),
                "porcentaje": float(valor / total * 100) if total else 0,
                "color": COLORES_FUENTES[indice % len(COLORES_FUENTES)],
            }
        )
    return datos


@seccion_requerida("finanzas")
def finanzas(request):
    """KPIs, flujo de caja y distribución por fuente de ingreso.

    Los datos salen de ``AnalisisFinanciero`` (fecha, gastos, fuentes_ingresos,
    fuente_ingreso y productos vendidos). El buscador filtra por administrador
    y la tabla de transacciones se retiró de esta pantalla.
    """
    q = busqueda.texto(request)
    vigentes = busqueda.filtrar(
        AnalisisFinanciero.objects.filter(activo=True),
        q,
        ("id_administrador__nombre", "id_administrador__documento", "fuente_ingreso", "id_pedido__codigo_pedido"),
    )
    registros = list(
        vigentes.select_related("id_administrador")
        .annotate(balance=F("fuentes_ingresos") - F("gastos"))
        .order_by("-fecha", "-id")
    )

    # Pagos amarrados a un pedido: al finalizar un pedido se genera su factura
    # y su ingreso queda vinculado aquí (campo «Pedido pagado»).
    pagos = []
    for registro in vigentes.filter(id_pedido__isnull=False).select_related(
        "id_pedido", "id_pedido__id_cliente", "id_pedido__id_producto"
    ).order_by("-fecha", "-id"):
        try:
            numero_factura = registro.id_pedido.factura.numero
        except Exception:
            numero_factura = ""
        pagos.append({
            "fecha": registro.fecha,
            "pedido": registro.id_pedido,
            "cliente": registro.id_pedido.id_cliente.nombre,
            "productos_vendidos": registro.productos_vendidos,
            "ingreso": registro.fuentes_ingresos,
            "factura": numero_factura,
        })

    agregados = vigentes.aggregate(
        total_gastos=Sum("gastos"),
        total_ingresos=Sum("fuentes_ingresos"),
        total_productos_vendidos=Sum("productos_vendidos"),
    )
    total_gastos = agregados["total_gastos"] or Decimal("0")
    total_ingresos = agregados["total_ingresos"] or Decimal("0")
    total_productos_vendidos = agregados["total_productos_vendidos"] or 0
    balance = total_ingresos - total_gastos
    margen = (balance / total_ingresos * 100) if total_ingresos else Decimal("0")
    periodo = _periodo(request)
    hoy = timezone.localdate()

    return _render(
        request,
        "kanview/finanzas.html",
        "Finanzas",
        total_registros=len(registros),
        total_gastos=total_gastos,
        total_ingresos=total_ingresos,
        balance=balance,
        total_productos_vendidos=total_productos_vendidos,
        margen=margen,
        flujo_caja=_flujo_caja(registros, hoy, periodo),
        fuentes_ingresos_datos=_fuentes_ingreso(registros),
        pagos=pagos,
        total_pagos=sum((pago["ingreso"] for pago in pagos), Decimal("0")),
        periodos=PERIODOS,
        periodo_activo=periodo,
        **busqueda.contexto(request, "Buscar movimientos...", "finanzas"),
    )
