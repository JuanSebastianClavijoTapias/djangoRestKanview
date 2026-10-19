"""Prueba E2E con Playwright: verifica que cada pantalla de diseño (Stitch)
muestra datos REALES de la base de datos (no la maqueta fija).

Requisitos: servidor corriendo (`python manage.py runserver`), `pip install playwright`.
Uso: python e2e/test_pantallas_ui.py
"""
import os
import sys
from datetime import date, time, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.urls import reverse  # noqa: E402
from django.utils import timezone  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from kanview.models import (  # noqa: E402
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Cliente,
    Empleado,
    Historial,
    Pedido,
    Producto,
    TareasPedido,
)

BASE_URL = os.environ.get("KANVIEW_BASE_URL", "http://127.0.0.1:8000")
USERNAME = "e2e@kanview.com"
PASSWORD = "E2ePass123!"

MARK = "ZETA-E2E"  # marcador distintivo para reconocer los datos sembrados

failures = []


def check(cond, msg):
    print(("  PASS: " if cond else "  FAIL: ") + msg)
    if not cond:
        failures.append(msg)


def limpiar():
    Calendario.objects.filter(nombre_mes=MARK).delete()
    Historial.objects.filter(id_producto__codigo_producto="ZZE2E1").delete()
    Actividades.objects.filter(nombre__startswith=MARK).delete()
    TareasPedido.objects.filter(nombre__startswith=MARK).delete()
    AnalisisFinanciero.objects.filter(id_administrador__documento="ZZE2E").delete()
    Pedido.objects.filter(codigo_pedido="E2EZET").delete()
    Producto.objects.filter(codigo_producto="ZZE2E1").delete()
    Cliente.objects.filter(documento="ZZE2E").delete()
    Empleado.objects.filter(documento="ZZE2E").delete()
    Administrador.objects.filter(documento="ZZE2E").delete()


def sembrar():
    limpiar()
    hoy = timezone.localdate()

    user, _ = User.objects.get_or_create(
        username=USERNAME, defaults={"is_staff": True, "is_superuser": True}
    )
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        user.save()

    admin = Administrador.objects.create(nombre=f"Admin {MARK}", celular="3000000000", documento="ZZE2E")
    cliente = Cliente.objects.create(
        nombre=f"Cliente {MARK}", fecha_nacimiento=date(1990, 1, 1), documento="ZZE2E",
        celular="3001111111", direccion="Calle Zeta", edad=35,
    )
    empleado = Empleado.objects.create(
        documento="ZZE2E", nombre=f"Empleado {MARK}", cargo="tapcr", celular="3002222222",
        direccion="Calle Zeta", salario=2500000, edad=40, fecha_nacimiento=date(1985, 5, 5),
        tareas_realizadas=7,
    )
    producto = Producto.objects.create(
        nombre=f"Producto {MARK}", categoria="Muebles", cantidad=9, precio=1234500,
        descripcion="e2e", codigo_producto="ZZE2E1",
    )
    pedido = Pedido.objects.create(
        codigo_pedido="E2EZET", fecha_creacion=hoy, hora_creacion=timezone.now(),
        estado="activo", evidencias="foto.jpg", descripcion=f"Pedido {MARK}",
        id_cliente=cliente, id_empleado=empleado, id_producto=producto,
    )
    tarea = TareasPedido.objects.create(
        nombre=f"{MARK} Tarea", descripcion="d", fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=2),
        estado="pendiente", id_pedido=pedido, id_empleado=empleado,
    )
    Actividades.objects.create(
        nombre=f"{MARK} Actividad", descripcion="d", fecha_inicio=hoy, fecha_fin=hoy,
        estado="en progreso", id_tarea=tarea, id_empleado=empleado,
    )
    AnalisisFinanciero.objects.create(
        gastos=350000, fuentes_ingresos=550000, productos_vendidos=15, id_administrador=admin
    )
    Historial.objects.create(
        hora_creacion=time(14, 30), fecha_creacion=hoy,
        id_cliente=cliente, id_empleado=empleado, id_producto=producto,
    )
    mes = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
           "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    d = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    Calendario.objects.create(
        fecha=hoy, anio=hoy.year, mes=hoy.month, nombre_mes=MARK,
        dia=hoy.day, nombre_dia=d[hoy.isoweekday()], id_pedido=pedido,
    )
    return pedido


# (nombre_url, texto_esperado) — el texto prueba que se ven datos reales de la BD
PAGINAS = [
    ("clientes", f"Cliente {MARK}"),
    ("empleados", f"Empleado {MARK}"),
    ("catalogo", f"Producto {MARK}"),
    ("inventario", f"Producto {MARK}"),
    ("pedidos-tablero", "E2EZET"),
    ("finanzas", f"Admin {MARK}"),
    ("auditoria", f"Cliente {MARK}"),
    ("calendario", "E2EZET"),
]


def main():
    pedido = sembrar()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page()
        page.set_default_timeout(15000)
        page.route(
            "**/*",
            lambda r: r.abort() if "127.0.0.1" not in r.request.url else r.continue_(),
        )

        page.goto(f"{BASE_URL}/login/")
        page.fill("#id_username", USERNAME)
        page.fill("#id_password", PASSWORD)
        page.get_by_role("button", name="Iniciar sesión").click()
        page.wait_for_load_state("domcontentloaded")
        check(page.url.rstrip("/") == BASE_URL, "login ok")

        for name, esperado in PAGINAS:
            url = f"{BASE_URL}{reverse('kanview:' + name)}"
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            html = page.content()
            check(esperado in html, f"/{name}/ muestra datos reales ('{esperado}')")

        detalle = f"{BASE_URL}{reverse('kanview:pedido-detalle', args=[pedido.pk])}"
        page.goto(detalle)
        page.wait_for_load_state("domcontentloaded")
        check("E2EZET" in page.content(), "detalle de pedido muestra el pedido real")

        browser.close()

    limpiar()

    print()
    if failures:
        print(f"{len(failures)} chequeo(s) fallaron:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("Todas las pantallas muestran datos reales.")


if __name__ == "__main__":
    main()
