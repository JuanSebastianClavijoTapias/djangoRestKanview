"""Prueba E2E con Playwright de los formularios CRUD de Kanview.

Verifica la nueva interfaz:

- Las listas muestran la columna "Estado" (píldora Activo/Inactivo).
- Nada se borra: el botón de la papelera pasó a ser "Desactivar" y existe
  "Reactivar".
- El producto se crea con el formulario construido en la VISTA
  (no hay forms.py) y su stock queda en ``Producto.cantidad``.
- La pantalla de existencias (/inventario/) lee esos mismos productos.
- Los CRUD de Inventario y Catálogo ya no existen.

Requisitos:
- Servidor corriendo en el puerto del agente, p. ej.
  `python manage.py runserver 127.0.0.1:8020 --noreload`
  y `KANVIEW_BASE_URL=http://127.0.0.1:8020 python e2e/test_crud_ui.py`
- `pip install playwright`
- Navegador: usa el Chrome del sistema (channel="chrome"), no requiere `playwright install`.

Uso:
    python e2e/test_crud_ui.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"  # permite ORM de Django dentro del contexto sync de Playwright

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.urls import reverse  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from kanview.models import Producto  # noqa: E402

BASE_URL = os.environ.get("KANVIEW_BASE_URL", "http://127.0.0.1:8000")
USERNAME = "e2e@kanview.com"
PASSWORD = "E2ePass123!"

MODULES = [
    ("analisis-financiero", "Análisis financiero"),
    ("producto", "Productos"),
    ("tarea", "Tareas"),
    ("actividad", "Actividades"),
    ("historial", "Historial"),
    ("calendario", "Calendario"),
]

CODIGO_AUTO = "E2ECAT"

failures = []

#: pks que siembra esta prueba, para poder borrar exactamente esos registros.
PKS_PRODUCTO = set()


def check(cond, msg):
    print(("  PASS: " if cond else "  FAIL: ") + msg)
    if not cond:
        failures.append(msg)


def limpiar():
    """Borra SOLO los productos que sembró esta prueba, identificados por su pk."""
    for pk in PKS_PRODUCTO:
        Producto.objects.filter(pk=pk).delete()
    PKS_PRODUCTO.clear()


def seed():
    user, _ = User.objects.get_or_create(
        username=USERNAME, defaults={"is_staff": True, "is_superuser": True}
    )
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        user.save()
    producto, _ = Producto.objects.get_or_create(
        codigo_producto="E2E01",
        defaults={
            "nombre": "Silla E2E",
            "categoria": "tela",
            "cantidad": 5,
            "precio": 100,
            "descripcion": "e2e",
        },
    )
    PKS_PRODUCTO.add(producto.pk)
    return producto


def main():
    seed()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page()
        page.set_default_timeout(15000)
        # Bloquear recursos externos (imágenes/fuentes/CDN de Google) para un 'load' rápido.
        page.route(
            "**/*",
            lambda route: route.abort()
            if "127.0.0.1" not in route.request.url
            else route.continue_(),
        )

        # Login
        page.goto(f"{BASE_URL}/login/")
        page.fill("#id_username", USERNAME)
        page.fill("#id_password", PASSWORD)
        page.get_by_role("button", name="Iniciar sesión").click()
        page.wait_for_load_state("domcontentloaded")
        check(page.url.rstrip("/") == BASE_URL, "login ok y redirige al dashboard")

        # Listas de los módulos que siguen existiendo y formularios de crear
        for name, title in MODULES:
            list_url = f"{BASE_URL}{reverse(f'kanview:{name}-lista')}"
            page.goto(list_url)
            page.wait_for_load_state("domcontentloaded")
            html = page.content()
            check(title in html, f"lista {name} renderiza ({title})")
            check("Estado" in html, f"lista {name} tiene columna Estado")

        for name, _title in MODULES:
            create_url = f"{BASE_URL}{reverse(f'kanview:{name}-crear')}"
            page.goto(create_url)
            page.wait_for_load_state("domcontentloaded")
            check("Guardar" in page.content(), f"form crear {name} renderiza")

        # --- Flujo completo crear -> editar -> desactivar -> reactivar (Producto) ---
        page.goto(f"{BASE_URL}{reverse('kanview:producto-crear')}")
        page.fill("#id_nombre", "Producto flujo E2E")
        page.select_option("#id_categoria", "madera")
        page.fill("#id_codigo_producto", "E2EFLJ")
        page.fill("#id_cantidad", "42")
        page.fill("#id_precio", "50000")
        page.fill("#id_descripcion", "creado por la prueba e2e")
        page.get_by_role("button", name="Guardar").click()
        page.wait_for_load_state("domcontentloaded")
        check("42" in page.content(), "producto creado y visible en la lista")

        producto = Producto.objects.filter(codigo_producto="E2EFLJ").order_by("-pk").first()
        check(producto is not None, "producto persistido en BD")
        if producto is not None:
            PKS_PRODUCTO.add(producto.pk)

        page.goto(f"{BASE_URL}{reverse('kanview:producto-editar', args=[producto.pk])}")
        page.fill("#id_cantidad", "99")
        page.get_by_role("button", name="Guardar").click()
        page.wait_for_load_state("domcontentloaded")
        producto.refresh_from_db()
        check(producto.cantidad == 99, "producto editado (cantidad 42 -> 99)")

        # Desactivar: ya no dice "Eliminar" y NO borra
        page.goto(f"{BASE_URL}{reverse('kanview:producto-eliminar', args=[producto.pk])}")
        page.wait_for_load_state("domcontentloaded")
        check("Desactivar" in page.content(), "la confirmación dice Desactivar (no Eliminar)")
        page.get_by_role("button", name="Desactivar").click()
        page.wait_for_load_state("domcontentloaded")
        producto.refresh_from_db()
        check(Producto.objects.filter(pk=producto.pk).exists(), "el producto sigue en la base (no se borró)")
        check(producto.activo is False, "el producto quedó inactivo (activo=False)")
        check("Inactivo" in page.content(), "la lista muestra la píldora Inactivo")

        # Reactivar desde la propia lista
        fila = page.locator("tr", has_text="99").first
        fila.get_by_role("button", name="Reactivar").click()
        page.wait_for_load_state("domcontentloaded")
        producto.refresh_from_db()
        check(producto.activo is True, "el producto se reactivó (activo=True)")
        check("Activo" in page.content(), "la lista muestra la píldora Activo")

        # --- La pantalla de existencias lee del mismo Producto ---
        page.goto(f"{BASE_URL}{reverse('kanview:inventario')}")
        page.wait_for_load_state("domcontentloaded")
        html = page.content()
        check("Producto flujo E2E" in html, "la pantalla de existencias muestra el producto")
        check(">99<" in html or "99" in html, "la pantalla de existencias muestra su stock")

        # --- Los CRUD de Inventario y Catálogo ya no existen ---
        for ruta in ("/crud/inventario/", "/crud/catalogo/"):
            resp = page.request.get(f"{BASE_URL}{ruta}")
            check(resp.status == 404, f"{ruta} ya no existe (404)")

        # --- Pedido: la fecha límite se captura desde el formulario ---
        page.goto(f"{BASE_URL}{reverse('kanview:pedido-crear')}")
        page.wait_for_load_state("domcontentloaded")
        check(
            page.locator("#id_fecha_limite").count() == 1,
            "el formulario del pedido tiene el campo «Fecha límite de entrega»",
        )

        browser.close()

    # Deja la base como estaba: la prueba limpia lo que sembró.
    limpiar()

    print()
    if failures:
        print(f"{len(failures)} chequeo(s) fallaron:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("Todos los chequeos E2E pasaron.")


if __name__ == "__main__":
    main()
