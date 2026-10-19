"""Formato y normalización de los campos de dinero (precios, salarios, gastos).

Un solo sitio para las dos caras del dinero en Kanview:

- ``moneda_cop``: cómo se imprime (``250000`` -> ``"250.000"``, puntos cada tres
  dígitos).
- ``normalizar_monto`` / ``normalizar_montos``: cómo se lee lo que escribe la
  persona antes de validar (``250.000`` -> ``"250000"``, ``250,50`` ->
  ``"250.50"``, ``1.250.000`` -> ``"1250000"``). La normalización va en las
  VISTAS: ``kanview/forms.py`` no se toca.

Lo usan las vistas y el filtro de plantilla ``moneda_cop`` de
``kanview/templatetags/kanview_extras.py``, así el criterio no queda duplicado.
"""

import re

#: Campos de dinero del sistema: se tratan igual en formularios y en listados.
CAMPOS_MONEDA = ("precio", "salario", "gastos", "fuentes_ingresos")

#: Etiqueta de cada campo para los avisos en español.
ETIQUETAS_MONEDA = {
    "precio": "El precio",
    "salario": "El salario",
    "gastos": "El valor de los gastos",
    "fuentes_ingresos": "El valor de las fuentes de ingresos",
}

#: Agrupación de miles con puntos o con comas: 250.000, 1.250.000, 1,250,000.
_MILES = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")

#: Número ya normalizado (sin separadores de miles, punto decimal).
_NUMERO = re.compile(r"^\d+(?:\.\d+)?$")

#: Ruido que se ignora al leer un monto: espacios, signos de pesos, letras.
_RUIDO = re.compile(r"[^\d.,\-]")


def moneda_cop(valor):
    """Imprime un monto como pesos colombianos: ``4500000`` -> ``'4.500.000'``."""
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return valor


def normalizar_monto(texto):
    """Devuelve el monto como número limpio (``"250.000"`` -> ``"250000"``).

    Acepta lo que la gente escribe a mano y lo que envía el navegador: puntos de
    miles (``1.250.000``), comas de miles (``1,250,000``), coma decimal
    (``250,50``) y las dos cosas (``1.234,56``). Un texto vacío se deja vacío (el
    formulario decide si el campo es obligatorio). Si no se puede leer como
    número lanza ``ValueError`` para que la vista avise en español.
    """
    crudo = str(texto if texto is not None else "").strip()
    if not crudo:
        return ""
    limpio = _RUIDO.sub("", crudo)
    if not limpio:
        raise ValueError(f"«{texto}» no es un número válido.")

    signo = "-" if limpio.startswith("-") else ""
    limpio = limpio[1:] if signo else limpio

    if "," in limpio and "." in limpio:
        # El último separador es el decimal; el otro separa los miles.
        corte = max(limpio.rfind(","), limpio.rfind("."))
        enteros = re.sub(r"[.,]", "", limpio[:corte])
        decimales = re.sub(r"[.,]", "", limpio[corte + 1:])
        limpio = f"{enteros}.{decimales}"
    elif _MILES.match(limpio):
        # Todo el número va agrupado de tres en tres: son separadores de miles.
        limpio = re.sub(r"[.,]", "", limpio)
    elif "," in limpio:
        # Coma decimal suelta: 250,50 -> 250.50
        limpio = limpio.replace(".", "").replace(",", ".")

    if not _NUMERO.match(limpio):
        raise ValueError(f"«{texto}» no es un número válido.")
    return signo + limpio


def normalizar_montos(post):
    """Copia del ``request.POST`` con los campos de dinero ya normalizados.

    Devuelve ``(datos, errores)``: ``datos`` es un ``QueryDict`` mutable que se le
    pasa al formulario y ``errores`` es ``{campo: mensaje en español}`` con los
    valores que no se pudieron leer como número.
    """
    datos = post.copy()
    errores = {}
    for campo in CAMPOS_MONEDA:
        if campo not in datos:
            continue
        try:
            datos[campo] = normalizar_monto(datos.get(campo))
        except ValueError:
            errores[campo] = (
                f"{ETIQUETAS_MONEDA[campo]} no es un número válido: "
                "separa los miles con puntos (por ejemplo 1.250.000)."
            )
    return datos, errores
