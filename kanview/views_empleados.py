"""Pantalla de Empleados: conecta el diseño de Stitch con datos reales.

Convención del proyecto: vistas como funciones (FBV), nunca clases. El helper
`_render` de `views_site` inyecta `nav_items` y `active` para el sidebar
compartido, así que aquí solo se pasan los datos de la pantalla.

Campos del diseño que no existen en el modelo (foto, email, turno) se
omitieron; en su lugar la plantilla muestra datos reales (cargo, salario,
tareas realizadas) sin alterar la estructura Tailwind/Stitch.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Sum

from .models import Empleado
from .views_site import _render

# Etiquetas en plural para las píldoras de conteo por cargo del encabezado.
PLURALES_CARGO = {
    "costr": "Costureros",
    "tapcr": "Tapiceros",
    "gerente": "Gerentes",
    "secre": "Secretarios",
}


def _resumen_cargos(conteos):
    """Lista [{codigo, etiqueta, total}] por cargo con al menos un empleado.

    La etiqueta va en singular cuando el cargo tiene un solo empleado.
    """
    return [
        {
            "codigo": codigo,
            "etiqueta": etiqueta if conteos[codigo] == 1 else PLURALES_CARGO[codigo],
            "total": conteos[codigo],
        }
        for codigo, etiqueta in Empleado.CARGOS
        if conteos.get(codigo)
    ]


@login_required
def empleados(request):
    """Lista los empleados reales y los indicadores del encabezado.

    Indicadores: total de empleados, suma de tareas realizadas y la
    productividad promedio, entendida como el promedio de tareas por empleado
    medido contra el mejor del equipo (el que más tareas realizó equivale al
    100%).
    """
    empleados = Empleado.objects.all()

    metricas = Empleado.objects.aggregate(
        total=Count("id"),
        tareas=Sum("tareas_realizadas"),
        maximo=Max("tareas_realizadas"),
    )
    total_empleados = metricas["total"] or 0
    total_tareas = metricas["tareas"] or 0
    max_tareas = metricas["maximo"] or 0
    promedio_tareas = round(total_tareas / total_empleados) if total_empleados else 0
    productividad = round(promedio_tareas / max_tareas * 100) if max_tareas else 0

    conteos = dict(
        Empleado.objects.values("cargo")
        .annotate(n=Count("id"))
        .values_list("cargo", "n")
    )

    return _render(
        request,
        "kanview/empleados.html",
        None,
        empleados=empleados,
        resumen_cargos=_resumen_cargos(conteos),
        total_empleados=total_empleados,
        total_tareas=total_tareas,
        promedio_tareas=promedio_tareas,
        max_tareas=max_tareas,
        productividad=productividad,
    )
