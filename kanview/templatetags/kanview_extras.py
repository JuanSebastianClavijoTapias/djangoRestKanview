from django import template

from ..formato import moneda_cop

register = template.Library()


@register.filter(name="getattr")
def getattr_filter(obj, attr_name):
    value = getattr(obj, attr_name, "")
    display_method = getattr(obj, f"get_{attr_name}_display", None)
    if callable(display_method):
        return display_method()
    return value


# El criterio del dinero vive en `kanview/formato.py` (lo comparten las vistas y
# las plantillas): aquí solo se registra como filtro, sin duplicar la lógica.
register.filter("moneda_cop", moneda_cop)
