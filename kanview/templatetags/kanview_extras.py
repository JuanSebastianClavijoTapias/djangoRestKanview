from django import template

register = template.Library()


@register.filter(name="getattr")
def getattr_filter(obj, attr_name):
    value = getattr(obj, attr_name, "")
    display_method = getattr(obj, f"get_{attr_name}_display", None)
    if callable(display_method):
        return display_method()
    return value


@register.filter(name="moneda_cop")
def moneda_cop(valor):
    """Formatea un número como pesos colombianos: 4500000 -> '4.500.000'."""
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return valor
