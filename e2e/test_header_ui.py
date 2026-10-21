"""Prueba E2E del header funcional, del menú móvil y del tablero «Procesos».

Cubre, con el navegador de verdad:

- A. Buscador de `/pedidos/`: escribir un término filtra el tablero en el
  servidor (cliente, producto o trabajador) y «Quitar filtro» lo devuelve.
- B. Campana: el panel se abre, muestra al menos un aviso real y se cierra con
  `Esc`.
- C. Cuenta: el menú muestra nombre y rol real, y «Cerrar sesión» (POST) vuelve
  al login.
- D. Menú móvil: a 375 px la hamburguesa abre el sidebar y se cierra con `Esc`.
- E. Conmutador Kanban / Lista de `/pedidos/`: la tabla muestra el pedido, el
  botón queda marcado y se vuelve al tablero.
- F. Cambio de estado desde el modal de una actividad: el pedido se mueve a la
  columna «Completado».
- G. El sidebar dice «Procesos», «Productos» y «Catálogo», y no «Tareas» ni
  «Inventario»; `/tareas/` acaba en `/pedidos/`.

Requisitos:
- Servidor en 8020:
  ``python manage.py runserver 127.0.0.1:8020 --noreload``
  y ``KANVIEW_BASE_URL=http://127.0.0.1:8020 python e2e/test_header_ui.py``
- Navegador: Chrome del sistema (``channel="chrome"``).

Uso:
    python e2e/test_header_ui.py
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.utils import timezone  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from kanview.models import (  # noqa: E402
    Actividades,
    Cliente,
    Empleado,
    Pedido,
    Producto,
    TareasPedido,
)

BASE_URL = os.environ.get("KANVIEW_BASE_URL", "http://127.0.0.1:8000")
USERNAME = "e2e@kanview.com"
PASSWORD = "E2ePass123!"

MARK = "HDR-E2E"
ANCHO_MOVIL = {"width": 375, "height": 800}
ANCHO_ESCRITORIO = {"width": 1440, "height": 900}

failures = []


def check(cond, msg):
    print(("  PASS: " if cond else "  FAIL: ") + msg)
    if not cond:
        failures.append(msg)


# ---- Datos de la prueba ------------------------------------------------------


def limpiar():
    """Borra solo lo que sembró esta prueba (las FK están en PROTECT)."""
    tareas = TareasPedido.objects.filter(nombre__startswith=MARK)
    Actividades.objects.filter(id_tarea__in=tareas).delete()
    tareas.delete()
    Pedido.objects.filter(codigo_pedido__startswith=MARK).delete()
    Producto.objects.filter(codigo_producto__startswith=MARK).delete()
    Cliente.objects.filter(documento__startswith=MARK).delete()
    Empleado.objects.filter(documento__startswith=MARK).delete()


def sembrar():
    """Dos procesos con clientes, productos y trabajadores distintos."""
    limpiar()
    hoy = timezone.localdate()

    user, _ = User.objects.get_or_create(
        username=USERNAME, defaults={"is_staff": True, "is_superuser": True}
    )
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        user.save()

    alfa, beta = [], []
    for sufijo, cargo, tela in (("Alfa", "costr", "tela"), ("Beta", "tapcr", "madera")):
        cliente = Cliente.objects.create(
            nombre=f"Cliente {MARK} {sufijo}", documento=f"{MARK}-{sufijo}",
            fecha_nacimiento=date(1990, 1, 1),
        )
        empleado = Empleado.objects.create(
            documento=f"{MARK}-{sufijo}", nombre=f"Empleado {MARK} {sufijo}",
            cargo=cargo, celular="300", direccion="Calle", salario=1000,
            fecha_nacimiento=date(1990, 1, 1),
        )
        producto = Producto.objects.create(
            nombre=f"Producto {MARK} {sufijo}", categoria=tela, cantidad=40,
            precio=1000, descripcion="prueba del header",
            codigo_producto=f"{MARK}-{sufijo}",
        )
        pedido = Pedido.objects.create(
            codigo_pedido=f"{MARK}-P{sufijo}", fecha_creacion=hoy,
            hora_creacion=timezone.now(), estado="activo", evidencias="",
            descripcion=f"Pedido {MARK} {sufijo}",
            fecha_limite=hoy + timedelta(days=30),
            id_cliente=cliente, id_empleado=empleado, id_producto=producto,
        )
        tarea = TareasPedido.objects.create(
            nombre=f"{MARK} {sufijo} Tarea", descripcion=f"Cortar {tela}",
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=2),
            estado="pendiente", id_pedido=pedido, id_empleado=empleado,
        )
        actividad = Actividades.objects.create(
            nombre=f"{MARK} {sufijo} Actividad", descripcion="Medir el asiento",
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=1),
            estado="en progreso", id_tarea=tarea, id_empleado=empleado,
        )
        (alfa if sufijo == "Alfa" else beta).extend([pedido, actividad])

    return alfa[0], alfa[1], beta[0], beta[1]


# ---- Utilidades --------------------------------------------------------------


def ir(page, ruta):
    """Navega sin esperar al evento `load` (los CDN de fuentes pueden colgarse)."""
    page.goto(f"{BASE_URL}{ruta}", wait_until="domcontentloaded")


def entrar(page):
    ir(page, "/login/")
    page.fill("#id_username", USERNAME)
    page.fill("#id_password", PASSWORD)
    page.get_by_role("button", name="Iniciar sesión").click()
    page.wait_for_load_state("domcontentloaded")
    return page.url.rstrip("/") == BASE_URL


def pulsar(page, selector):
    """Clic real sobre el elemento, sin depender de la fuente de iconos.

    Los iconos son texto de Material Symbols: si el CDN tarda, el glifo sin
    cargar es más ancho que el botón y tapa al vecino. `el.click()` dispara el
    mismo evento sin el hit-test del ratón.
    """
    page.eval_on_selector(selector, "el => el.click()")


def visible(page, selector):
    return page.eval_on_selector(selector, "el => !!(el.offsetWidth || el.offsetHeight)")


def main():
    pedido_alfa, actividad_alfa, pedido_beta, _actividad_beta = sembrar()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(viewport=ANCHO_ESCRITORIO)
        page = context.new_page()
        page.set_default_timeout(20000)
        # El CDN de imágenes de muestra devuelve 403: se bloquea, no se mide.
        page.route("**lh3.googleusercontent.com/**", lambda route: route.abort())

        check(entrar(page), "inicia sesión con la cuenta e2e")

        # ---- A. Buscador del tablero -------------------------------------
        print("\n  -- A. Buscador del header --")
        ir(page, "/pedidos/")
        page.wait_for_load_state("domcontentloaded")
        check(pedido_alfa.codigo_pedido in page.content(), "el proceso Alfa está en el tablero")
        check(pedido_beta.codigo_pedido in page.content(), "el proceso Beta está en el tablero")

        page.fill("#buscador-q", f"Producto {MARK} Alfa")
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.press("#buscador-q", "Enter")
        check("q=" in page.url, f"el buscador envía ?q= en la URL ({page.url})")
        # Se mira solo el tablero: el panel de avisos del header menciona otros pedidos
        # («no tiene evidencias cargadas») y no forma parte del filtrado.
        cuerpo = page.inner_text("main")
        check(pedido_alfa.codigo_pedido in cuerpo, "el filtro deja el proceso Alfa")
        check(pedido_beta.codigo_pedido not in cuerpo, "el filtro quita el proceso Beta")
        check(
            "Buscando en procesos" in page.inner_text("header"),
            "el header dice qué se está filtrando",
        )

        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("link", name="Quitar filtro").click()
        check("q=" not in page.url, f"«Quitar filtro» limpia la query ({page.url})")
        check(pedido_alfa.codigo_pedido in page.content(), "vuelve el proceso Alfa")
        check(pedido_beta.codigo_pedido in page.content(), "vuelve el proceso Beta")

        # La búsqueda también cubre al trabajador de la actividad.
        page.fill("#buscador-q", f"Empleado {MARK} Beta")
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.press("#buscador-q", "Enter")
        cuerpo = page.inner_text("main")
        check(pedido_beta.codigo_pedido in cuerpo, "el filtro por trabajador deja el proceso Beta")
        check(pedido_alfa.codigo_pedido not in cuerpo, "el filtro por trabajador quita el proceso Alfa")

        # ---- B. Campana ---------------------------------------------------
        print("\n  -- B. Campana de avisos --")
        ir(page, "/pedidos/")
        page.wait_for_load_state("domcontentloaded")
        pulsar(page, "#btn-avisos")
        check(visible(page, "#panel-avisos"), "el panel de avisos se abre")
        check(
            page.get_attribute("#btn-avisos", "aria-expanded") == "true",
            "la campana marca aria-expanded=true",
        )
        avisos = page.locator("#panel-avisos li a")
        check(avisos.count() >= 1, f"hay al menos un aviso real ({avisos.count()})")
        texto_avisos = page.inner_text("#panel-avisos")
        check(
            pedido_alfa.codigo_pedido in texto_avisos or "Stock bajo" in texto_avisos,
            "el aviso nombra datos reales del taller",
        )
        page.keyboard.press("Escape")
        check(not visible(page, "#panel-avisos"), "Esc cierra el panel de avisos")

        # ---- D. Menú móvil ------------------------------------------------
        print("\n  -- E. Menú móvil (375 px) --")
        page.set_viewport_size(ANCHO_MOVIL)
        ir(page, "/pedidos/")
        page.wait_for_load_state("domcontentloaded")
        check(not visible(page, "#sidebar"), "en móvil el sidebar arranca cerrado")
        pulsar(page, "#btn-menu")
        check(visible(page, "#sidebar"), "la hamburguesa abre el sidebar")
        check(
            page.get_attribute("#btn-menu", "aria-expanded") == "true",
            "la hamburguesa marca aria-expanded=true",
        )
        check(visible(page, "#sidebar-fondo"), "aparece el fondo oscuro")
        page.keyboard.press("Escape")
        check(not visible(page, "#sidebar"), "Esc cierra el menú móvil")

        # ---- G. Cambio de estado desde el modal ---------------------------
        print("\n  -- G. Estado de una actividad desde el modal --")
        page.set_viewport_size(ANCHO_ESCRITORIO)
        ir(page, "/pedidos/")
        page.wait_for_load_state("domcontentloaded")
        selector = f'[data-detalle="actividad-{actividad_alfa.pk}"]'
        check(page.locator(selector).count() == 1, "la actividad del proceso está en la tarjeta")
        page.eval_on_selector(selector, "el => el.click()")
        page.wait_for_timeout(250)
        check(visible(page, "#modal-detalle"), "el modal de la actividad se abre")
        page.select_option("#modal-detalle-nuevo-estado", "completado")
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("button", name="Guardar estado").click()
        check(
            "pasó a «Completado»" in page.inner_text("main"),
            "se muestra el mensaje de éxito en español",
        )
        columna = page.evaluate(
            """() => {
                const card = document.querySelector('[data-pedido="%s"]');
                return card ? card.closest('section').dataset.columna : null;
            }""" % pedido_alfa.pk
        )
        check(columna == "completado", f"el pedido se movió a «Completado» (columna={columna})")
        actividad_alfa.refresh_from_db()
        check(actividad_alfa.estado == "completado", "el estado quedó guardado en la base")

        # ---- F. Conmutador Kanban / Lista ---------------------------------
        print("\n  -- F. Kanban / Lista en /pedidos/ --")
        ir(page, "/pedidos/?vista=lista")
        page.wait_for_load_state("domcontentloaded")
        check(visible(page, "#tabla-pedidos"), "la vista Lista muestra la tabla")
        check(
            page.get_attribute("#vista-lista", "aria-pressed") == "true",
            "el botón Lista queda marcado",
        )
        check(
            pedido_alfa.codigo_pedido in page.inner_text("#tabla-pedidos"),
            "la tabla trae el pedido sembrado",
        )
        with page.expect_navigation(wait_until="domcontentloaded"):
            pulsar(page, "#vista-kanban")
        check(page.locator("#tabla-pedidos").count() == 0, "volver a Kanban quita la tabla")
        check(
            page.get_attribute("#vista-kanban", "aria-pressed") == "true",
            "el botón Kanban queda marcado",
        )

        # ---- H. Sidebar y /tareas/ ---------------------------------------
        print("\n  -- H. Sidebar y redirección de /tareas/ --")
        ir(page, "/pedidos/")
        page.wait_for_load_state("domcontentloaded")
        sidebar = page.inner_text("#sidebar")
        for etiqueta in ("Procesos", "Productos", "Catálogo"):
            check(etiqueta in sidebar, f"el sidebar muestra «{etiqueta}»")
        for etiqueta in ("Tareas", "Inventario"):
            check(etiqueta not in sidebar, f"el sidebar ya no muestra «{etiqueta}»")
        ir(page, "/tareas/")
        page.wait_for_load_state("domcontentloaded")
        check(page.url.rstrip("/").endswith("/pedidos"), f"/tareas/ acaba en /pedidos/ ({page.url})")

        # ---- D. Cuenta y cierre de sesión ---------------------------------
        print("\n  -- D. Menú de cuenta --")
        page.set_viewport_size(ANCHO_MOVIL)
        ir(page, "/pedidos/")
        page.wait_for_load_state("domcontentloaded")
        pulsar(page, "#btn-cuenta")
        check(visible(page, "#panel-cuenta"), "el menú de cuenta se abre")
        texto_cuenta = page.inner_text("#panel-cuenta")
        check(USERNAME in texto_cuenta, "muestra el nombre/correo de la sesión")
        check("Administrador" in texto_cuenta, "muestra el rol real del usuario")
        check("Configuración" in texto_cuenta, "ofrece el enlace a Configuración")
        with page.expect_navigation(wait_until="domcontentloaded"):
            pulsar(page, "#panel-cuenta button[type=submit]")
        check("/login" in page.url, f"«Cerrar sesión» vuelve al login ({page.url})")
        check(page.locator("#id_username").count() == 1, "el login está visible tras salir")

        browser.close()

    limpiar()

    print()
    if failures:
        print(f"{len(failures)} chequeo(s) fallaron:")
        for fallo in failures:
            print(f"  - {fallo}")
        sys.exit(1)
    print("Todos los chequeos del header y del menú móvil pasaron.")


if __name__ == "__main__":
    main()
