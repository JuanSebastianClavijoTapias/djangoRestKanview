"""Pantalla de Calendario conectada a datos reales.

Convención del proyecto: cada vista es una función con ``@login_required`` y usa el
helper ``_render`` de ``views_site`` (que inyecta ``nav_items`` y ``active``).

Fuente de los eventos (nunca datos inventados):
1. Tabla ``Calendario`` del mes (``select_related`` al pedido y su producto).
2. Si la tabla no tiene filas para ese mes, se usan los pedidos creados en el mes
   (``Pedido.fecha_creacion``).
"""
import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.utils.formats import date_format

from .models import Calendario, Pedido
from .views_site import _render

# El diseño de Stitch empieza la semana en domingo (SUN..SAT).
PRIMER_DIA_SEMANA = 6
ANIO_MINIMO = 1900


# ---- Helpers ---------------------------------------------------------------

def _mes_solicitado(request):
    """Devuelve ``(anio, mes)`` a partir del parámetro ``?mes=``.

    Acepta ``?mes=2026-10`` y ``?mes=10&anio=2026``. Sin parámetro válido usa el
    mes actual.
    """
    hoy = timezone.localdate()
    anio, mes = hoy.year, hoy.month

    crudo = (request.GET.get("mes") or "").strip()
    anio_param = (request.GET.get("anio") or "").strip()

    if crudo:
        partes = crudo.split("-")
        try:
            if len(partes) >= 2:
                anio, mes = int(partes[0]), int(partes[1])
            else:
                mes = int(partes[0])
                anio = int(anio_param) if anio_param else anio
        except ValueError:
            return hoy.year, hoy.month
    elif anio_param:
        try:
            anio = int(anio_param)
        except ValueError:
            return hoy.year, hoy.month

    if 1 <= mes <= 12 and ANIO_MINIMO <= anio <= 9999:
        return anio, mes
    return hoy.year, hoy.month


def _mes_vecino(anio, mes, salto):
    """Mes anterior (``salto=-1``) o siguiente (``salto=1``)."""
    indice = (anio * 12 + mes - 1) + salto
    return {"anio": indice // 12, "mes": indice % 12 + 1}


def _registros_calendario(anio, mes):
    """Filas de ``Calendario`` del mes, con el pedido ya precargado."""
    return list(
        Calendario.objects.select_related("id_pedido", "id_pedido__id_producto")
        .filter(Q(fecha__year=anio, fecha__month=mes) | Q(anio=anio, mes=mes))
        .order_by("fecha", "id")
    )


def _pedidos_del_mes(anio, mes):
    """Pedidos creados en el mes (fuente alterna cuando ``Calendario`` está vacío)."""
    return list(
        Pedido.objects.select_related("id_producto")
        .filter(fecha_creacion__year=anio, fecha_creacion__month=mes)
        .order_by("fecha_creacion", "codigo_pedido")
    )


def _evento(fecha, pedido, nombre_dia="", nombre_mes="", registro=None):
    """Evento listo para el template (equivale a una 'tarea' de una celda)."""
    return {
        "id": registro.pk if registro is not None else None,
        "registro": registro,
        "fecha": fecha,
        "dia": fecha.day,
        "nombre_dia": nombre_dia or date_format(fecha, "l").capitalize(),
        "nombre_mes": nombre_mes or date_format(fecha, "F").capitalize(),
        "pedido": pedido,
        "codigo": pedido.codigo_pedido if pedido else "",
        "descripcion": pedido.descripcion if pedido else "",
        "producto": pedido.id_producto.nombre if pedido else "",
        "estado": pedido.estado if pedido else "",
        "estado_display": pedido.get_estado_display() if pedido else "",
        "activo": bool(pedido and pedido.estado == "activo"),
    }


def _eventos_del_mes(anio, mes):
    """``(eventos, origen)`` del mes: tabla ``Calendario`` y, si está vacía,
    los pedidos creados en el mes."""
    registros = _registros_calendario(anio, mes)
    if registros:
        eventos = [
            _evento(r.fecha, r.id_pedido, r.nombre_dia, r.nombre_mes, registro=r)
            for r in registros
        ]
        return eventos, "calendario"

    pedidos = _pedidos_del_mes(anio, mes)
    eventos = [_evento(p.fecha_creacion, p) for p in pedidos]
    return eventos, ("pedidos" if pedidos else "vacio")


def _grilla(anio, mes, eventos, hoy):
    """``(dias, semanas)``: días del mes más los de los meses vecinos que completan
    la semana, cada uno con sus eventos."""
    por_fecha = {}
    for evento in eventos:
        por_fecha.setdefault(evento["fecha"], []).append(evento)

    dias = []
    for fecha in calendar.Calendar(firstweekday=PRIMER_DIA_SEMANA).itermonthdates(anio, mes):
        dias.append(
            {
                "fecha": fecha,
                "dia": fecha.day,
                "del_mes": fecha.year == anio and fecha.month == mes,
                "hoy": fecha == hoy,
                "eventos": por_fecha.get(fecha, []),
            }
        )

    semanas = [dias[i:i + 7] for i in range(0, len(dias), 7)]
    return dias, semanas


# ---- Vista -----------------------------------------------------------------

@login_required
def calendario(request):
    """Calendario de producción con los eventos reales del mes solicitado."""
    anio, mes = _mes_solicitado(request)
    hoy = timezone.localdate()

    eventos, origen = _eventos_del_mes(anio, mes)
    eventos.sort(key=lambda e: (e["fecha"], e["codigo"]))
    dias, semanas = _grilla(anio, mes, eventos, hoy)

    pedidos_mes = []
    vistos = set()
    for evento in eventos:
        pedido = evento["pedido"]
        if pedido is not None and pedido.pk not in vistos:
            vistos.add(pedido.pk)
            pedidos_mes.append(pedido)

    nombre_mes = next(
        (e["nombre_mes"] for e in eventos if e["nombre_mes"]),
        date_format(date(anio, mes, 1), "F").capitalize(),
    )

    return _render(
        request,
        "kanview/calendario.html",
        "Calendario",
        anio=anio,
        mes=mes,
        nombre_mes=nombre_mes,
        mes_titulo=f"{nombre_mes} {anio}",
        hoy=hoy,
        dias=dias,
        semanas=semanas,
        eventos=eventos,
        total_eventos=len(eventos),
        dias_con_eventos=sum(1 for dia in dias if dia["eventos"]),
        pedidos_mes=pedidos_mes,
        origen=origen,
        mes_anterior=_mes_vecino(anio, mes, -1),
        mes_siguiente=_mes_vecino(anio, mes, 1),
    )
