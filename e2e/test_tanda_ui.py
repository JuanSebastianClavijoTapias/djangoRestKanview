"""Prueba E2E con Playwright de la tanda de UI de Kanview.

Cubre, con el navegador de verdad:

- A1. El precio con separador de miles: al escribir ``250000`` el input muestra
  ``250.000`` y en la base queda ``250000``.
- A4. El modal de detalle de una tarea: se abre desde la tarjeta y se cierra con
  ``Esc``; el foco vuelve a la tarjeta que lo abrió.
- B1. Que no haya desbordes horizontales a 375 px (y que el sidebar esté oculto
  en móvil y visible en escritorio).
- B2. Que el logo del sidebar cargue de verdad (``naturalWidth > 0``): el asset
  local del repo, no la imagen que devolvía 403.
- Estilo único del sidebar: en ``/`` (Panel) y ``/tareas/`` el ``<aside>`` y el
  ``<body>`` tienen que calcular EXACTAMENTE el mismo background-color y
  font-family, y el ítem activo del menú el mismo color de texto. Antes cada
  plantilla traía su propia configuración de Tailwind y el mismo sidebar se
  pintaba de dos maneras.

Requisitos:
- Servidor corriendo en el puerto del agente, p. ej.
  ``python manage.py runserver 127.0.0.1:8020`` y
  ``KANVIEW_BASE_URL=http://127.0.0.1:8020 python e2e/test_tanda_ui.py``
- ``pip install playwright``
- Navegador: usa el Chrome del sistema (``channel="chrome"``).
- **Este módulo SÍ deja cargar el CDN de Tailwind**: sin su CSS no se puede medir
  el layout (los otros suites lo bloquean porque solo miran el DOM).

Uso:
    python e2e/test_tanda_ui.py
"""
import os
import sys
import time
from datetime import date, timedelta
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
    Cliente,
    Empleado,
    Pedido,
    Producto,
    TareasPedido,
)

BASE_URL = os.environ.get("KANVIEW_BASE_URL", "http://127.0.0.1:8000")
USERNAME = "e2e@kanview.com"
PASSWORD = "E2ePass123!"

MARK = "TANDA-E2E"          # marcador de los datos que siembra esta prueba
CODIGO_PRODUCTO = "TNDE2E"  # código del producto que se crea desde la UI

ANCHO_MOVIL = {"width": 375, "height": 800}
ANCHO_ESCRITORIO = {"width": 1440, "height": 900}

#: Pantallas que se miden a 375 px (las que el QA reportó con desbordes + el resto).
PANTALLAS = [
    ("/", "dashboard"),
    ("/usuarios/", "usuarios"),
    ("/clientes/", "clientes"),
    ("/empleados/", "empleados"),
    ("/crud/pedidos/", "crud-pedidos"),
    ("/crud/productos/", "crud-productos"),
    ("/configuracion/", "configuracion"),
    ("/pedidos/", "pedidos-tablero"),
    ("/inventario/", "inventario"),
    ("/calendario/", "calendario"),
    ("/catalogo/", "catalogo"),
    ("/finanzas/", "finanzas"),
    ("/auditoria/", "auditoria"),
]

#: Pantallas que también se miden a 1440 px (donde el sidebar ya está visible).
PANTALLAS_ESCRITORIO = ["/clientes/", "/catalogo/"]

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
    Pedido.objects.filter(codigo_pedido=f"{MARK}-P1").delete()
    # El producto sembrado (TANDA-E2E1) y el que se crea desde la UI (TNDE2E):
    # se borran después de sus pedidos (las FK están en PROTECT).
    for producto in Producto.objects.filter(codigo_producto__in=[CODIGO_PRODUCTO, f"{MARK}1"]):
        Pedido.objects.filter(id_producto=producto).delete()
        producto.delete()
    Cliente.objects.filter(documento=MARK).delete()
    Empleado.objects.filter(documento=MARK).delete()


def sembrar():
    limpiar()
    hoy = timezone.localdate()

    user, _ = User.objects.get_or_create(
        username=USERNAME, defaults={"is_staff": True, "is_superuser": True}
    )
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        user.save()

    cliente = Cliente.objects.create(
        nombre=f"Cliente {MARK}", documento=MARK, fecha_nacimiento=date(1990, 1, 1)
    )
    empleado = Empleado.objects.create(
        documento=MARK, nombre=f"Empleado {MARK}", cargo="tapcr", celular="300",
        direccion="Calle", salario=1000, fecha_nacimiento=date(1990, 1, 1),
    )
    producto = Producto.objects.create(
        nombre=f"Producto {MARK}", categoria="tela", cantidad=4, precio=1000,
        descripcion="prueba de la tanda", codigo_producto=f"{MARK}1",
    )
    pedido = Pedido.objects.create(
        codigo_pedido=f"{MARK}-P1", fecha_creacion=hoy, hora_creacion=timezone.now(),
        estado="activo", evidencias="", descripcion=f"Pedido {MARK}",
        fecha_limite=hoy + timedelta(days=30),
        id_cliente=cliente, id_empleado=empleado, id_producto=producto,
    )
    tarea = TareasPedido.objects.create(
        nombre=f"{MARK} Tarea", descripcion="Cortar la tela y coser el forro",
        fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=2), estado="pendiente",
        id_pedido=pedido, id_empleado=empleado,
    )
    actividad = Actividades.objects.create(
        nombre=f"{MARK} Actividad", descripcion="Medir el asiento",
        fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=1), estado="en progreso",
        id_tarea=tarea, id_empleado=empleado,
    )
    return actividad


# ---- Comprobaciones ----------------------------------------------------------


def entrar(page):
    page.goto(f"{BASE_URL}/login/", wait_until="domcontentloaded")
    page.fill("#id_username", USERNAME)
    page.fill("#id_password", PASSWORD)
    page.get_by_role("button", name="Iniciar sesión").click()
    page.wait_for_load_state("domcontentloaded")
    return page.url.rstrip("/") == BASE_URL


def esperar_tailwind(page):
    """Espera a que el CSS del CDN esté aplicado (si no, no hay layout que medir)."""
    page.wait_for_function("() => typeof window.tailwind !== 'undefined'", timeout=20000)
    page.wait_for_timeout(250)
    return page.evaluate(
        "() => { const a = document.querySelector('aside');"
        " return a ? getComputedStyle(a).position : 'sin-sidebar'; }"
    )


def medir(page):
    """Devuelve las medidas de desborde horizontal de la página actual."""
    return page.evaluate(
        """() => {
            const raiz = document.documentElement;
            const main = document.querySelector('main');
            const aside = document.querySelector('aside');
            // Elementos cuyo borde derecho se sale de la pantalla (diagnóstico).
            const ancho = raiz.clientWidth;
            const fuera = [];
            document.querySelectorAll('body *').forEach((el) => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.right > ancho + 1) {
                    fuera.push(Math.round(r.right) + ':' + el.tagName.toLowerCase() +
                               '.' + (el.className || '').toString().split(' ').slice(0, 3).join('.'));
                }
            });
            // Una tabla más ancha que la pantalla tiene que estar dentro de un
            // contenedor con scroll horizontal: si solo la recorta un
            // overflow-hidden, sus columnas quedan inalcanzables.
            const tablasSinScroll = [];
            document.querySelectorAll('table').forEach((tabla) => {
                if (tabla.getBoundingClientRect().width <= ancho + 1) {
                    return;
                }
                let padre = tabla.parentElement;
                let conScroll = false;
                while (padre) {
                    const desborde = getComputedStyle(padre).overflowX;
                    if (desborde === 'auto' || desborde === 'scroll') {
                        conScroll = true;
                        break;
                    }
                    padre = padre.parentElement;
                }
                if (!conScroll) {
                    tablasSinScroll.push(tabla.className.slice(0, 40));
                }
            });
            return {
                scrollWidth: raiz.scrollWidth,
                clientWidth: raiz.clientWidth,
                bodyScrollWidth: document.body.scrollWidth,
                mainAncho: main ? Math.round(main.getBoundingClientRect().width) : 0,
                sidebar: aside ? getComputedStyle(aside).display : 'sin-sidebar',
                fuera: fuera.slice(0, 6),
                tablasSinScroll: tablasSinScroll,
            };
        }"""
    )


def abrir_modal(page, actividad):
    """Clic en la actividad de la tarjeta del pedido y comprobación del modal."""
    tarjeta = page.locator(f'[data-detalle="actividad-{actividad.pk}"]')
    check(tarjeta.count() == 1, "la actividad existe en el tablero de procesos")
    check(
        tarjeta.get_attribute("aria-label") == f"Ver el detalle de la actividad «{actividad.nombre}»",
        "la actividad que abre el modal tiene aria-label en español",
    )
    tarjeta.click()
    page.wait_for_timeout(250)

    modal = page.locator("#modal-detalle")
    check(modal.is_visible(), "el modal se abre al clicar la actividad")
    check(modal.get_attribute("aria-modal") == "true", "el modal lleva aria-modal=true")
    check(
        page.locator("#modal-detalle-titulo").inner_text().strip() == actividad.nombre,
        "el modal muestra el nombre de la actividad",
    )
    descripcion = page.locator("#modal-detalle-descripcion").inner_text().strip()
    check(descripcion == actividad.descripcion, f"el modal muestra la descripción ({descripcion!r})")
    check(
        page.locator("#modal-detalle-estado").inner_text().strip() == "En progreso",
        "el modal muestra el estado",
    )
    for campo, esperado in (
        ("#modal-detalle-inicio", actividad.fecha_inicio.strftime("%d/%m/%Y")),
        ("#modal-detalle-fin", actividad.fecha_fin.strftime("%d/%m/%Y")),
        ("#modal-detalle-pedido", actividad.id_tarea.id_pedido.codigo_pedido),
        ("#modal-detalle-cliente", actividad.id_tarea.id_pedido.id_cliente.nombre),
        ("#modal-detalle-empleado", actividad.id_empleado.nombre),
    ):
        valor = page.locator(campo).inner_text().strip()
        check(valor == esperado, f"el modal muestra {campo} = {esperado!r} (leyó {valor!r})")
    return tarjeta


#: Propiedades que se comparan del sidebar entre dos pantallas.
ESTILOS_SIDEBAR = """() => {
    const leer = (el, props) => {
        if (!el) return null;
        const s = getComputedStyle(el);
        const r = {};
        props.forEach((p) => { r[p] = s[p]; });
        return r;
    };
    const aside = document.querySelector('aside');
    const activo = aside.querySelector('a.bg-primary-container');
    return {
        asideBg: aside ? getComputedStyle(aside).backgroundColor : null,
        asideFuente: aside ? getComputedStyle(aside).fontFamily : null,
        bodyBg: getComputedStyle(document.body).backgroundColor,
        bodyFuente: getComputedStyle(document.body).fontFamily,
        activoColor: activo ? getComputedStyle(activo).color : null,
        activoFondo: activo ? getComputedStyle(activo).backgroundColor : null,
        icono: leer(aside.querySelector('a.bg-primary-container .material-symbols-outlined'),
                    ['fontSize', 'color']),
        marca: leer(aside.querySelector('span.text-primary'), ['color', 'fontSize']),
        bloquesConfig: document.querySelectorAll('script#tailwind-config').length,
    };
}"""


def estilo_sidebar(page, url):
    """Estilos calculados del sidebar en una pantalla."""
    page.set_viewport_size(ANCHO_ESCRITORIO)
    page.goto(f"{BASE_URL}{url}", wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    esperar_tailwind(page)
    page.wait_for_timeout(200)
    return page.evaluate(ESTILOS_SIDEBAR)


def main():
    actividad = sembrar()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(viewport=ANCHO_ESCRITORIO)
        page = context.new_page()
        page.set_default_timeout(20000)
        # Los CDN de fuentes de Google no responden en todos los entornos: se da
        # más margen a la navegación sin tocar ninguna comprobación.
        page.set_default_navigation_timeout(45000)
        # Solo se bloquean las imágenes del CDN roto (403): el CSS de Tailwind y
        # las fuentes se dejan cargar porque hacen falta para medir el layout.
        page.route(
            "**lh3.googleusercontent.com/**",
            lambda route: route.abort(),
        )

        check(entrar(page), "login ok")

        # ---- A1: precio con separador de miles -----------------------------
        page.goto(f"{BASE_URL}{reverse('kanview:producto-crear')}", wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")
        page.fill("#id_nombre", f"Producto UI {MARK}")
        page.select_option("#id_categoria", "tela")
        page.fill("#id_codigo_producto", CODIGO_PRODUCTO)
        page.fill("#id_cantidad", "4")
        page.fill("#id_descripcion", "creado por la prueba de la tanda")

        # Se escribe dígito a dígito, como una persona.
        precio = page.locator("#id_precio")
        precio.click()
        for digito in "250000":
            page.keyboard.type(digito)
            page.wait_for_timeout(30)
        valor_visible = precio.input_value()
        check(
            valor_visible == "250.000",
            f"al escribir 250000 el input muestra «250.000» (mostró «{valor_visible}»)",
        )
        check(
            page.evaluate("() => document.activeElement.selectionStart") == len(valor_visible),
            "el cursor queda al final del número formateado",
        )

        page.get_by_role("button", name="Guardar").click()
        page.wait_for_load_state("domcontentloaded")
        check("/crud/productos/" in page.url, f"el producto se guardó (302 -> lista): {page.url}")

        creado = Producto.objects.filter(codigo_producto=CODIGO_PRODUCTO).first()
        check(creado is not None, "el producto existe en la base")
        if creado is not None:
            check(
                str(creado.precio) == "250000.00",
                f"en la base quedó 250000 (leyó {creado.precio})",
            )
            check("250.000" in page.content(), "la lista de productos muestra 250.000 con puntos")

            # Al volver a editar, el valor se ve con puntos y se guarda igual.
            page.goto(f"{BASE_URL}{reverse('kanview:producto-editar', args=[creado.pk])}", wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            check(
                page.locator("#id_precio").input_value() == "250.000",
                f"el formulario de edición muestra 250.000 (mostró "
                f"«{page.locator('#id_precio').input_value()}»)",
            )
            page.get_by_role("button", name="Guardar").click()
            page.wait_for_load_state("domcontentloaded")
            creado.refresh_from_db()
            check(str(creado.precio) == "250000.00", "volver a guardar sin tocar el precio no lo cambia")

            # Un valor que no es número avisa en español y no guarda. El input ya
            # filtra las letras, así que se usa un separador suelto.
            page.goto(f"{BASE_URL}{reverse('kanview:producto-editar', args=[creado.pk])}", wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            page.fill("#id_precio", ",")
            page.get_by_role("button", name="Guardar").click()
            page.wait_for_load_state("domcontentloaded")
            check("no es un número válido" in page.content(), "un precio inválido avisa en español")
            creado.refresh_from_db()
            check(str(creado.precio) == "250000.00", "el precio inválido no se guardó")

            # ---- A1 sin JavaScript: lo normaliza la vista --------------------
            sin_js = browser.new_context(viewport=ANCHO_ESCRITORIO, java_script_enabled=False)
            pagina_sin_js = sin_js.new_page()
            pagina_sin_js.set_default_timeout(20000)
            check(entrar(pagina_sin_js), "login ok con JavaScript desactivado")
            ruta_editar = f"{BASE_URL}{reverse('kanview:producto-editar', args=[creado.pk])}"
            pagina_sin_js.goto(ruta_editar, wait_until="domcontentloaded")
            pagina_sin_js.fill("#id_precio", "1.250.000")
            pagina_sin_js.get_by_role("button", name="Guardar").click()
            pagina_sin_js.wait_for_load_state("domcontentloaded")
            creado.refresh_from_db()
            check(
                str(creado.precio) == "1250000.00",
                f"sin JS la vista también acepta «1.250.000» (guardó {creado.precio})",
            )
            pagina_sin_js.goto(ruta_editar, wait_until="domcontentloaded")
            pagina_sin_js.fill("#id_precio", "mil pesos")
            pagina_sin_js.get_by_role("button", name="Guardar").click()
            pagina_sin_js.wait_for_load_state("domcontentloaded")
            check(
                "no es un número válido" in pagina_sin_js.content(),
                "sin JS un precio inválido avisa en español",
            )
            creado.refresh_from_db()
            check(str(creado.precio) == "1250000.00", "el precio inválido no se guardó (sin JS)")
            sin_js.close()

        # ---- A4: modal de detalle de la actividad --------------------------
        page.set_viewport_size(ANCHO_ESCRITORIO)
        page.goto(f"{BASE_URL}{reverse('kanview:pedidos-tablero')}", wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")
        tarjeta = abrir_modal(page, actividad)

        # Se cierra con Esc y el foco vuelve a la actividad.
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        check(not page.locator("#modal-detalle").is_visible(), "el modal se cierra con Esc")
        check(
            page.evaluate('() => document.activeElement.dataset.detalle || ""')
            == f"actividad-{actividad.pk}",
            "al cerrar con Esc el foco vuelve a la actividad que abrió el modal",
        )

        # Se abre con el teclado y se cierra con la X.
        tarjeta.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        check(page.locator("#modal-detalle").is_visible(), "el modal también abre con Enter (teclado)")
        page.locator("#modal-detalle-cerrar").click()
        page.wait_for_timeout(200)
        check(not page.locator("#modal-detalle").is_visible(), "el modal se cierra con el botón X")

        # Se abre de nuevo y se cierra clicando fuera.
        tarjeta.click()
        page.wait_for_timeout(200)
        check(page.locator("#modal-detalle").is_visible(), "el modal de la actividad se abre")
        # text_content(): el texto tal cual, sin el text-transform: uppercase del CSS.
        tipo_modal = page.locator("#modal-detalle-tipo").text_content().strip()
        check(tipo_modal == "Actividad", f"el modal distingue una actividad (tipo={tipo_modal!r})")
        page.mouse.click(5, 5)
        page.wait_for_timeout(200)
        check(not page.locator("#modal-detalle").is_visible(), "clicar fuera cierra el modal")

        # ---- B2: el logo carga de verdad -----------------------------------
        page.goto(f"{BASE_URL}{reverse('kanview:dashboard')}", wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")
        check(esperar_tailwind(page) == "fixed", "el sidebar queda fijo en escritorio (Tailwind cargado)")
        logo = page.evaluate(
            """() => { const img = document.querySelector('aside img');
                       return img ? {src: img.getAttribute('src'), ancho: img.naturalWidth} : null; }"""
        )
        check(logo is not None, "el sidebar tiene logo")
        if logo:
            check(
                "lh3.googleusercontent" not in logo["src"],
                f"el logo ya no apunta a la imagen que daba 403 ({logo['src']})",
            )
            page.wait_for_function(
                "() => { const i = document.querySelector('aside img'); return i && i.complete && i.naturalWidth > 0; }",
                timeout=10000,
            )
            ancho_logo = page.evaluate("() => document.querySelector('aside img').naturalWidth")
            check(ancho_logo > 0, f"el logo carga de verdad (naturalWidth={ancho_logo})")

        # ---- Estilo único del sidebar (Panel vs Procesos) ------------------
        print("\n  -- Estilo del sidebar: / vs /pedidos/ --")
        panel = estilo_sidebar(page, "/")
        tablero_estilo = estilo_sidebar(page, "/pedidos/")
        print(f"     /        → aside bg={panel['asideBg']} fuente={panel['asideFuente']!r} "
              f"body bg={panel['bodyBg']} fuente={panel['bodyFuente']!r} "
              f"activo={panel['activoColor']}")
        print(f"     /pedidos/ → aside bg={tablero_estilo['asideBg']} fuente={tablero_estilo['asideFuente']!r} "
              f"body bg={tablero_estilo['bodyBg']} fuente={tablero_estilo['bodyFuente']!r} "
              f"activo={tablero_estilo['activoColor']}")
        for clave in ("asideBg", "asideFuente", "bodyBg", "bodyFuente", "activoColor",
                      "activoFondo", "icono", "marca"):
            check(
                panel[clave] == tablero_estilo[clave],
                f"el sidebar se pinta igual en / y /pedidos/ para {clave}: "
                f"«{panel[clave]}» vs «{tablero_estilo[clave]}»",
            )
        check(
            panel["bloquesConfig"] == 1 and tablero_estilo["bloquesConfig"] == 1,
            f"cada página renderiza un solo bloque de configuración de Tailwind "
            f"(/={panel['bloquesConfig']}, /pedidos/={tablero_estilo['bloquesConfig']})",
        )

        # ---- B1: nada se sale de la pantalla en móvil ----------------------
        print("\n  -- Overflow horizontal (375 px) --")
        for url, nombre in PANTALLAS:
            page.set_viewport_size(ANCHO_MOVIL)
            page.goto(f"{BASE_URL}{url}", wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            estado = esperar_tailwind(page)
            medidas = medir(page)
            check(
                medidas["scrollWidth"] <= medidas["clientWidth"],
                f"{url} no desborda a 375 px (scrollWidth={medidas['scrollWidth']} "
                f"clientWidth={medidas['clientWidth']}, fuera={medidas['fuera']})",
            )
            check(
                medidas["sidebar"] == "none",
                f"{url} oculta el sidebar en móvil (display={medidas['sidebar']}, tailwind={estado})",
            )
            check(
                medidas["mainAncho"] >= 300,
                f"{url} usa el ancho de la pantalla en móvil (main={medidas['mainAncho']} px)",
            )
            check(
                not medidas["tablasSinScroll"],
                f"{url} deja las tablas anchas con scroll horizontal "
                f"(sin scroll: {medidas['tablasSinScroll']})",
            )

        print("\n  -- Overflow horizontal (1440 px) --")
        for url in PANTALLAS_ESCRITORIO:
            page.set_viewport_size(ANCHO_ESCRITORIO)
            page.goto(f"{BASE_URL}{url}", wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            estado = esperar_tailwind(page)
            medidas = medir(page)
            check(
                medidas["scrollWidth"] <= medidas["clientWidth"],
                f"{url} no desborda a 1440 px (scrollWidth={medidas['scrollWidth']} "
                f"clientWidth={medidas['clientWidth']}, fuera={medidas['fuera']})",
            )
            check(
                medidas["sidebar"] != "none",
                f"{url} muestra el sidebar en escritorio (display={medidas['sidebar']}, tailwind={estado})",
            )

        browser.close()

    # Deja la base como estaba.
    limpiar()

    print()
    if failures:
        print(f"{len(failures)} chequeo(s) fallaron:")
        for fallo in failures:
            print(f"  - {fallo}")
        sys.exit(1)
    print("Todos los chequeos de la tanda de UI pasaron.")


if __name__ == "__main__":
    main()
