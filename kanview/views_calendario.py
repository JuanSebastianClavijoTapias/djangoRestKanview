"""Pantalla de Calendario conectada a datos reales.

Convención del proyecto: cada vista es una función con ``@seccion_requerida`` y usa el
helper ``_render`` de ``views_site`` (que inyecta ``nav_items`` y ``active``).

Fuente de los eventos (nunca datos inventados):
1. Tabla ``Calendario`` del mes (``select_related`` al pedido y su producto).
2. Si la tabla no tiene filas para ese mes, se usan los pedidos creados en el mes
   (``Pedido.fecha_creacion``).
"""
import calendar
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.formats import date_format

from . import busqueda
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Calendario, Pedido, Recordatorio
from .permisos import seccion_requerida
from .views_crud import _validar_horas_calendario
from .views_site import _render

# El diseño de Stitch empieza la semana en domingo (SUN..SAT).
PRIMER_DIA_SEMANA = 6
ANIO_MINIMO = 1900

#: Texto que se muestra cuando el pedido no tiene fecha límite de entrega.
SIN_FECHA_LIMITE = "Sin fecha límite"


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
    """Filas vigentes de ``Calendario`` del mes, con el pedido ya precargado."""
    return list(
        Calendario.objects.filter(activo=True)
        .select_related("id_pedido", "id_pedido__id_producto", "id_pedido__id_cliente")
        .filter(Q(fecha__year=anio, fecha__month=mes) | Q(anio=anio, mes=mes))
        .order_by("fecha", "id")
    )


def _pedidos_del_mes(anio, mes):
    """Pedidos vigentes creados en el mes (fuente alterna si ``Calendario`` está vacío)."""
    return list(
        Pedido.objects.filter(activo=True)
        .select_related("id_producto", "id_cliente")
        .filter(fecha_creacion__year=anio, fecha_creacion__month=mes)
        .order_by("fecha_creacion", "codigo_pedido")
    )


def _evento(fecha, pedido, nombre_dia="", nombre_mes="", registro=None):
    """Evento listo para el template (equivale a una 'tarea' de una celda).

    Cada evento trae dos fechas distintas y bien separadas:

    - ``fecha``: la del registro de calendario (el día en el que se pinta).
    - ``fecha_limite`` / ``entrega``: la fecha límite de entrega del pedido
      (``Pedido.fecha_limite``), o «Sin fecha límite» si el pedido no la tiene.

    Si ``registro`` es un evento personal (sin pedido), se usan sus propios
    campos de título, descripción y horarios.
    """
    limite = getattr(pedido, "fecha_limite", None) if pedido is not None else None
    es_personal = registro is not None and registro.id_pedido is None
    return {
        "id": registro.pk if registro is not None else None,
        "registro": registro,
        "fecha": fecha,
        "fecha_texto": fecha.strftime("%d/%m/%Y") if fecha else "",
        "dia": fecha.day,
        "nombre_dia": nombre_dia or date_format(fecha, "l").capitalize(),
        "nombre_mes": nombre_mes or date_format(fecha, "F").capitalize(),
        "pedido": pedido,
        "codigo": pedido.codigo_pedido if pedido else "",
        "descripcion": pedido.descripcion if pedido else "",
        "producto": pedido.id_producto.nombre if pedido else "",
        "estado": pedido.estado if pedido else "",
        "estado_display": pedido.get_estado_display() if pedido else "",
        "activo": bool(pedido and pedido.estado == "activo") if not es_personal else True,
        "fecha_limite": limite,
        "entrega": limite.strftime("%d/%m/%Y") if limite else SIN_FECHA_LIMITE,
        "cliente": pedido.id_cliente.nombre if pedido else "",
        "es_personal": es_personal,
        "titulo": registro.titulo if es_personal else "",
        "descripcion_personal": registro.descripcion if es_personal else "",
        "hora_inicio": registro.hora_inicio if es_personal else None,
        "hora_limite": registro.hora_limite if es_personal else None,
        "recordatorio": registro.recordatorio if es_personal else False,
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

@seccion_requerida("calendario")
def calendario(request):
    """Calendario de producción con los eventos reales del mes solicitado.

    El mes se pide con ``?mes=`` y el buscador del header filtra además con
    ``?q=`` por código de pedido, descripción, cliente o producto.
    """
    anio, mes = _mes_solicitado(request)
    hoy = timezone.localdate()
    q = busqueda.texto(request)

    eventos, origen = _eventos_del_mes(anio, mes)
    eventos = [
        evento for evento in eventos
        if busqueda.coincide(
            q,
            evento["codigo"],
            evento["descripcion"],
            evento["cliente"],
            evento["producto"],
        )
    ]
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
        **busqueda.contexto(request, "Buscar en el calendario...", "calendario"),
    )


@seccion_requerida("calendario")
@require_POST
def calendario_evento_crear(request):
    """Crea un evento del calendario o asigna una fecha límite a un pedido.

    Se invoca desde el modal del calendario. Soporta dos tipos:

    - ``pedido``: vincula un pedido existente a una fecha del calendario.
    - ``evento``: crea un evento personal con título, horarios y recordatorio.
    """
    tipo = (request.POST.get("tipo") or "").strip()
    fecha_raw = (request.POST.get("fecha") or "").strip()

    try:
        fecha = date.fromisoformat(fecha_raw)
    except ValueError:
        return HttpResponseBadRequest("Fecha inválida.")

    if fecha < timezone.localdate():
        return HttpResponseBadRequest("No se pueden crear eventos en fechas pasadas.")

    nombre_dia = date_format(fecha, "l").capitalize()
    nombre_mes = date_format(fecha, "F").capitalize()

    if tipo == "pedido":
        pedido_id = request.POST.get("id_pedido")
        pedido = Pedido.objects.filter(pk=pedido_id, activo=True).first()
        if pedido is None:
            return HttpResponseBadRequest("Pedido no encontrado.")
        Calendario.objects.create(
            fecha=fecha,
            anio=fecha.year,
            mes=fecha.month,
            nombre_mes=nombre_mes,
            dia=fecha.day,
            nombre_dia=nombre_dia,
            id_pedido=pedido,
            usuario=request.user,
        )

    elif tipo == "evento":
        titulo = (request.POST.get("titulo") or "").strip()
        if not titulo:
            return HttpResponseBadRequest("El nombre del evento es obligatorio.")

        descripcion = (request.POST.get("descripcion") or "").strip()
        hora_inicio_raw = (request.POST.get("hora_inicio") or "").strip()
        hora_limite_raw = (request.POST.get("hora_limite") or "").strip()
        hora_inicio = datetime.strptime(hora_inicio_raw, "%H:%M").time() if hora_inicio_raw else None
        hora_limite = datetime.strptime(hora_limite_raw, "%H:%M").time() if hora_limite_raw else None
        recordatorio = request.POST.get("recordatorio") == "1"
        minutos_raw = (request.POST.get("minutos_recordatorio") or "").strip()
        minutos_recordatorio = int(minutos_raw) if minutos_raw.isdigit() else None

        error = _validar_horas_calendario(fecha, hora_inicio, hora_limite)
        if error:
            return HttpResponseBadRequest(error)

        try:
            evento = Calendario(
                fecha=fecha,
                anio=fecha.year,
                mes=fecha.month,
                nombre_mes=nombre_mes,
                dia=fecha.day,
                nombre_dia=nombre_dia,
                titulo=titulo,
                descripcion=descripcion,
                hora_inicio=hora_inicio,
                hora_limite=hora_limite,
                recordatorio=recordatorio,
                minutos_recordatorio=minutos_recordatorio,
                usuario=request.user,
            )
            evento.full_clean()
            evento.save()
        except ValidationError as exc:
            return HttpResponseBadRequest(" ".join(exc.messages))

        if recordatorio and hora_inicio and minutos_recordatorio is not None:
            inicio = datetime.combine(fecha, evento.hora_inicio)
            inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
            Recordatorio.objects.create(
                calendario=evento,
                fecha_hora=inicio - timedelta(minutes=minutos_recordatorio),
            )
    else:
        return HttpResponseBadRequest("Tipo de evento no válido.")

    return redirect(f"{reverse('kanview:calendario')}?mes={fecha.year}-{fecha.month:02d}")
