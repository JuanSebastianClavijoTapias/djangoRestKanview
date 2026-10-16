"""Prueba E2E con Playwright de los formularios CRUD de Kanview.

Requisitos:
- Servidor corriendo: `python manage.py runserver` (default http://127.0.0.1:8000)
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

from kanview.models import Inventario, Producto  # noqa: E402

BASE_URL = os.environ.get("KANVIEW_BASE_URL", "http://127.0.0.1:8000")
USERNAME = "e2e@kanview.com"
PASSWORD = "E2ePass123!"

MODULES = [
    ("analisis-financiero", "Análisis financiero"),
    ("inventario", "Inventario"),
    ("catalogo", "Catálogo"),
    ("tarea", "Tareas"),
    ("actividad", "Actividades"),
    ("historial", "Historial"),
    ("calendario", "Calendario"),
]

failures = []


def check(cond, msg):
    print(("  PASS: " if cond else "  FAIL: ") + msg)
    if not cond:
        failures.append(msg)


def seed():
    # Limpiar residuos de corridas anteriores de esta prueba.
    Inventario.objects.filter(cantidad__in=[42, 99]).delete()
    user, created = User.objects.get_or_create(
        username=USERNAME, defaults={"is_staff": True, "is_superuser": True}
    )
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        user.save()
    producto, _ = Producto.objects.get_or_create(
        codigo_producto="E2E01",
        defaults={
            "nombre": "Silla E2E",
            "categoria": "Muebles",
            "cantidad": 5,
            "precio": 100,
            "descripcion": "e2e",
        },
    )
    return producto


def main():
    producto = seed()
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

        # Listas y formularios de crear renderizan
        for name, title in MODULES:
            list_url = f"{BASE_URL}{reverse(f'kanview:{name}-lista')}"
            page.goto(list_url)
            page.wait_for_load_state("domcontentloaded")
            check(title in page.content(), f"lista {name} renderiza ({title})")

            create_url = f"{BASE_URL}{reverse(f'kanview:{name}-crear')}"
            page.goto(create_url)
            page.wait_for_load_state("domcontentloaded")
            check("Guardar" in page.content(), f"form crear {name} renderiza")

        # Flujo completo crear -> editar -> eliminar sobre Inventario
        page.goto(f"{BASE_URL}{reverse('kanview:inventario-crear')}")
        page.fill("#id_cantidad", "42")
        page.select_option("#id_id_producto", str(producto.pk))
        page.get_by_role("button", name="Guardar").click()
        page.wait_for_load_state("domcontentloaded")
        check("42" in page.content(), "inventario creado y visible en lista")

        obj = Inventario.objects.filter(cantidad=42).order_by("-pk").first()
        check(obj is not None, "inventario persistido en BD")

        page.goto(f"{BASE_URL}{reverse('kanview:inventario-editar', args=[obj.pk])}")
        page.fill("#id_cantidad", "99")
        page.get_by_role("button", name="Guardar").click()
        page.wait_for_load_state("domcontentloaded")
        obj.refresh_from_db()
        check(obj.cantidad == 99, "inventario editado (cantidad 42 -> 99)")

        page.goto(f"{BASE_URL}{reverse('kanview:inventario-eliminar', args=[obj.pk])}")
        page.get_by_role("button", name="Eliminar").click()
        page.wait_for_load_state("domcontentloaded")
        check(not Inventario.objects.filter(pk=obj.pk).exists(), "inventario eliminado")

        browser.close()

    print()
    if failures:
        print(f"{len(failures)} chequeo(s) fallaron:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("Todos los chequeos E2E pasaron.")


if __name__ == "__main__":
    main()
