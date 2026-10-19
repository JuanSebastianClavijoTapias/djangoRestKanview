"""Prueba E2E con Playwright del ojito de la contraseña en el login de Kanview.

Requisitos:
- Servidor corriendo: `python manage.py runserver` (default http://127.0.0.1:8000)
- `pip install playwright`
- Navegador: usa el Chrome del sistema (channel="chrome"), no requiere `playwright install`.

Uso:
    python e2e/test_login_ui.py
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
from playwright.sync_api import sync_playwright  # noqa: E402

BASE_URL = os.environ.get("KANVIEW_BASE_URL", "http://127.0.0.1:8000")
USERNAME = "e2e@kanview.com"
PASSWORD = "E2ePass123!"

failures = []


def check(cond, msg):
    print(("  PASS: " if cond else "  FAIL: ") + msg)
    if not cond:
        failures.append(msg)


def seed():
    user, _ = User.objects.get_or_create(
        username=USERNAME, defaults={"is_staff": True, "is_superuser": True}
    )
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        user.save()
    return user


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

        errores_js = []
        page.on("pageerror", lambda exc: errores_js.append(str(exc)))

        page.goto(f"{BASE_URL}/login/")
        page.wait_for_load_state("domcontentloaded")

        password_input = page.locator("#id_password")
        toggle = page.locator("#toggle-password")

        check(toggle.count() == 1, "el botón del ojito existe en el login")
        page.fill("#id_username", USERNAME)
        password_input.fill(PASSWORD)
        check(password_input.get_attribute("type") == "password", "la contraseña inicia oculta")

        toggle.click()
        check(password_input.get_attribute("type") == "text", "primer clic muestra la contraseña")
        check(
            toggle.locator(".material-symbols-outlined").inner_text().strip() == "visibility",
            "el ícono cambia a 'visibility' al mostrarla",
        )
        check(toggle.get_attribute("aria-pressed") == "true", "aria-pressed pasa a true")
        check(
            password_input.input_value() == PASSWORD,
            "el valor escrito se conserva al mostrarla",
        )
        check(password_input.get_attribute("type") == "text", "la contraseña sigue visible tras escribir")

        toggle.click()
        check(password_input.get_attribute("type") == "password", "segundo clic vuelve a ocultarla")
        check(
            toggle.locator(".material-symbols-outlined").inner_text().strip() == "visibility_off",
            "el ícono vuelve a 'visibility_off'",
        )
        check(toggle.get_attribute("aria-pressed") == "false", "aria-pressed vuelve a false")

        # El botón no debe enviar el formulario: seguimos en el login
        check(page.url.rstrip("/").endswith("/login"), "el clic en el ojito no envía el formulario")

        # Con la contraseña visible el envío debe funcionar igual
        toggle.click()
        check(password_input.get_attribute("type") == "text", "contraseña visible antes de enviar")
        with page.expect_navigation(timeout=15000):
            page.get_by_role("button", name="Iniciar sesión").click()
        check(page.url.rstrip("/") == BASE_URL, "login exitoso con la contraseña visible")

        # El CDN de Tailwind se bloquea a propósito en esta prueba, así que su error no cuenta.
        errores_reales = [e for e in errores_js if "tailwind" not in e.lower()]
        check(not errores_reales, f"sin errores de JavaScript de la página ({errores_reales})")

        browser.close()

    print()
    if failures:
        print(f"{len(failures)} chequeo(s) fallaron:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("Todos los chequeos E2E del ojito de la contraseña pasaron.")


if __name__ == "__main__":
    main()
