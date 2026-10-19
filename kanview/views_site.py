from random import randint

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Cliente, Empleado, Pedido, Producto
from .permisos import (
    ROL_CLIENTE,
    SECCIONES,
    asignar_rol,
    es_solo_cliente,
    puede,
    rol_principal,
    seccion_requerida,
)

# Elementos del menú lateral: (icono, etiqueta, nombre de la URL, sección que lo protege).
# La vista filtra esta lista según el rol del usuario (ver _nav).
# Un solo tablero: «Procesos» (/pedidos/). El CRUD de tareas vive fuera del menú,
# enlazado desde el propio tablero; el stock se gestiona en «Productos».
NAV_ITEMS = [
    ("dashboard", "Panel", "kanview:dashboard", "panel"),
    ("view_kanban", "Procesos", "kanview:pedidos-tablero", "pedidos"),
    ("sell", "Productos", "kanview:producto-lista", "catalogo"),
    ("menu_book", "Catálogo", "kanview:catalogo", "catalogo"),
    ("calendar_today", "Calendario", "kanview:calendario", "calendario"),
    ("fact_check", "Auditoría", "kanview:auditoria", "auditoria"),
    ("forum", "Mensajería", "kanview:mensajeria", "mensajeria"),
    ("group", "Usuarios", "kanview:usuarios", "usuarios"),
    ("payments", "Finanzas", "kanview:finanzas", "finanzas"),
]


def _nav(activo=None, request=None):
    """Contexto que necesita la plantilla _sidebar.html en todas las páginas.

    Devuelve los ítems del menú como 4-tuplas ``(icono, etiqueta, url, seccion)``,
    ya filtrados por el rol del usuario: cada rol solo ve las secciones que le
    corresponden (ver ``kanview/permisos.py``).
    """
    usuario = getattr(request, "user", None) if request is not None else None
    if usuario is not None and usuario.is_authenticated:
        items = [item for item in NAV_ITEMS if puede(usuario, item[3])]
    else:
        items = list(NAV_ITEMS)
    return {"nav_items": items, "active": activo}


# ---- Autenticación --------------------------------------------------------

def iniciar_sesion(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.get_user()
        login(request, usuario)
        siguiente = request.POST.get("next") or request.GET.get("next")
        # Solo se acepta un destino del propio sitio: evita el open redirect
        # (/login/?next=https://example.com/ ya no saca al usuario del sitio).
        if siguiente and url_has_allowed_host_and_scheme(
            siguiente,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(siguiente)
        return redirect("kanview:dashboard")
    return render(request, "kanview/login.html", {"form": form, "next": request.GET.get("next", "")})


@seccion_requerida("usuarios")
def registrarse(request):
    """Crea User de Django (username=correo) + Cliente y le da rol Cliente.

    Ya no es un registro público: solo el administrador (o Secretaría) puede
    dar de alta cuentas; el formulario se reutiliza desde el módulo Usuarios.
    """
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        correo = (request.POST.get("correo") or "").strip().lower()
        clave1 = request.POST.get("clave1") or ""
        clave2 = request.POST.get("clave2") or ""

        def error(msg):
            messages.error(request, msg)
            return render(request, "kanview/registro.html", {
                "nombre": nombre, "correo": correo,
            })

        if not nombre or not correo or not clave1:
            return error("Nombre, correo y contraseña son obligatorios.")
        if "@" not in correo or "." not in correo:
            return error("Ingresa un correo válido.")
        if len(clave1) < 8:
            return error("La contraseña debe tener al menos 8 caracteres.")
        if clave1 != clave2:
            return error("Las contraseñas no coinciden.")
        if User.objects.filter(username=correo).exists() or User.objects.filter(email=correo).exists():
            return error("Ya existe una cuenta con ese correo.")
        if Cliente.objects.filter(correo=correo).exists():
            return error("Ya existe un cliente con ese correo.")

        user = User.objects.create_user(
            username=correo, email=correo, password=clave1, first_name=nombre,
        )
        asignar_rol(user, ROL_CLIENTE)
        Cliente.objects.create(
            nombre=nombre, correo=correo,
            documento="", celular="", direccion="", fecha_nacimiento=None,
        )
        messages.success(request, f"Cuenta creada para {nombre}.")
        return redirect("kanview:usuarios")

    return render(request, "kanview/registro.html", {})


def cerrar_sesion(request):
    logout(request)
    return redirect("kanview:login")


# ---- Recuperar clave (Cliente: correo -> token) ----------------------------

def recuperar_solicitar(request):
    """Paso 1: pide el correo, genera token de 6 dígitos y lo envía por email."""
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip()
        if not correo:
            messages.error(request, "Ingresa tu correo electrónico.")
            return render(request, "kanview/recuperar.html", {"correo": correo})

        try:
            cliente = Cliente.objects.get(correo=correo)
        except Cliente.DoesNotExist:
            messages.error(request, "No encontramos un cliente con ese correo.")
            return render(request, "kanview/recuperar.html", {"correo": correo})

        token = f"{randint(100000, 999999):06d}"
        cliente.token = token
        cliente.url_valida = True
        cliente.save(update_fields=["token", "url_valida"])

        try:
            send_mail(
                "Kanview - Código de recuperación",
                f"Hola {cliente.nombre},\n\nTu código de recuperación es: {token}\n\n"
                "Ingrésalo en la página de verificación para continuar.",
                settings.DEFAULT_FROM_EMAIL,
                [correo],
                fail_silently=False,
            )
            messages.success(request, "Te enviamos un código de 6 dígitos a tu correo.")
        except Exception:
            messages.warning(
                request,
                f"No se pudo enviar el correo (SMTP). Tu código es: {token}",
            )
        url = reverse("kanview:recuperar-verificar")
        return redirect(f"{url}?correo={correo}")

    return render(request, "kanview/recuperar.html", {"correo": request.GET.get("correo", "")})


def recuperar_verificar(request):
    """Paso 2: verifica correo + token vigente (url_valida=True) y lo consume."""
    correo_inicial = request.GET.get("correo", "") or request.POST.get("correo", "")
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip()
        token = (request.POST.get("token") or "").strip()
        if not correo or not token:
            messages.error(request, "Ingresa correo y código de 6 dígitos.")
            return render(request, "kanview/recuperar_verificar.html", {"correo": correo})

        try:
            cliente = Cliente.objects.get(correo=correo, token=token, url_valida=True)
        except Cliente.DoesNotExist:
            messages.error(request, "Código incorrecto o ya usado. Solicita uno nuevo.")
            return render(request, "kanview/recuperar_verificar.html", {"correo": correo})

        cliente.url_valida = False
        cliente.save(update_fields=["url_valida"])
        messages.success(
            request,
            f"Código verificado (enlace de un solo uso). Hola {cliente.nombre}, ya puedes iniciar sesión.",
        )
        return redirect("kanview:login")

    return render(request, "kanview/recuperar_verificar.html", {"correo": correo_inicial})


# ---- Panel ----------------------------------------------------------------

@login_required
def dashboard(request):
    """Panel general. Solo cuentan los registros vigentes; el rol Cliente solo
    ve sus propios pedidos."""
    pedidos = Pedido.objects.filter(activo=True)
    clientes = Cliente.objects.filter(activo=True)

    if es_solo_cliente(request.user):
        pedidos = pedidos.filter(id_cliente__correo__iexact=request.user.email)
        clientes = clientes.filter(correo__iexact=request.user.email)

    contexto = {
        "total_clientes": clientes.count(),
        "total_empleados": Empleado.objects.filter(activo=True).count(),
        "total_productos": Producto.objects.filter(activo=True).count(),
        "total_pedidos": pedidos.count(),
        "pedidos_activos": pedidos.filter(estado="activo").count(),
        "ultimos_pedidos": pedidos.order_by("-id")[:5],
        "rol": rol_principal(request.user),
        "cabecera_titulo": "Panel",
        **_nav("Panel", request),
    }
    return render(request, "kanview/dashboard.html", contexto)


# ---- Helper de render para las pantallas conectadas a datos ----------------

def _render(request, template, active=None, **context):
    """Renderiza una plantilla con el contexto del sidebar (nav_items + active)."""
    return render(request, template, {**context, **_nav(active, request)})


# ---- Mensajería (maqueta estática por ahora: no hay modelo de mensajería) --

@seccion_requerida("mensajeria")
def mensajeria(request):
    """Pantalla de mensajería.

    El modelo de mensajes todavía no existe, así que el buscador del header no
    puede filtrar en el servidor: se marca la pantalla para que el JavaScript
    del header filtre en vivo los chats ya pintados (mismo criterio para el
    usuario, sin inventar datos).
    """
    return render(
        request,
        "kanview/mensajeria.html",
        {
            **_nav("Mensajería", request),
            "mostrar_buscador": True,
            "busqueda_cliente": True,
            "q": "",
            "buscar_placeholder": "Buscar chats, contactos o mensajes...",
            "buscar_alcance": "mensajería",
        },
    )


# ---- Configuración --------------------------------------------------------

@seccion_requerida("configuracion")
def configuracion(request):
    """Pantalla de Configuración (reemplaza el enlace al admin de Django)."""
    roles = [
        {"nombre": rol, "total": User.objects.filter(groups__name=rol).count()}
        for rol in ("Administrador", "Secretaria", "Trabajador", "Cliente")
    ]
    secciones = [
        {"nombre": nombre, "roles": list(cuales)}
        for nombre, cuales in SECCIONES.items()
    ]
    contexto = {
        "roles": roles,
        "total_usuarios": User.objects.count(),
        "usuarios_url": reverse("kanview:usuarios"),
        # Dato genérico del taller: la cuenta real con la que se envían los
        # correos NO se publica en pantalla.
        "correo_contacto": settings.CORREO_CONTACTO,
        "secciones": secciones,
        "cabecera_titulo": "Configuración",
        **_nav(None, request),
    }
    return render(request, "kanview/configuracion.html", contexto)
