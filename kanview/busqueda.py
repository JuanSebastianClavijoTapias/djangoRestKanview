"""Búsqueda compartida del header (`?q=`) para las pantallas de Kanview.

El header es uno solo para todas las pantallas, pero cada vista filtra *lo suyo*:
tareas por nombre/descripción/código de pedido, inventario por producto/código,
clientes por nombre/documento/celular, etc. Aquí viven las dos piezas comunes:

- ``texto(request)``: el término ya limpio (sin espacios sobrantes y acotado).
- ``filtrar(queryset, q, campos)``: un ``OR`` de ``icontains`` sobre los campos
  que la vista indique. Sin ``q`` devuelve el queryset intacto.

El servidor manda: el filtro funciona sin JavaScript y al pulsar Enter, porque
el input vive dentro de un ``<form method="get">``.
"""

from django.db.models import Q

#: Largo máximo aceptado para el término (evita URLs y consultas absurdas).
MAX_LARGO = 80


def texto(request):
    """Término de búsqueda normalizado (cadena vacía si no hay `?q=`)."""
    return (request.GET.get("q") or "").strip()[:MAX_LARGO]


def filtrar(queryset, q, campos):
    """Filtra ``queryset`` por ``q`` en cualquiera de ``campos`` (OR, sin distinguir mayúsculas)."""
    if not q:
        return queryset
    condicion = Q()
    for campo in campos:
        condicion |= Q(**{f"{campo}__icontains": q})
    return queryset.filter(condicion)


def coincide(q, *textos):
    """¿Alguno de ``textos`` contiene ``q``? (mismo criterio, para listas en memoria)."""
    if not q:
        return True
    aguja = q.lower()
    return any(aguja in (texto or "").lower() for texto in textos)


def contexto(request, placeholder, alcance):
    """Contexto que el header necesita para pintar el buscador de esta pantalla.

    ``placeholder`` y ``alcance`` los define cada vista: el header es el mismo,
    pero el texto y el chip («Buscando en tareas: …») cambian por pantalla.
    """
    q = texto(request)
    return {
        "q": q,
        "buscar_placeholder": placeholder,
        "buscar_alcance": alcance,
        "mostrar_buscador": True,
    }
