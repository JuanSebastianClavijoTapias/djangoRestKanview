from random import randint

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import Cliente, Empleado, Pedido, Producto

# Elementos del menú lateral: (icono, etiqueta, nombre de la URL)
NAV_ITEMS = [
    ("dashboard", "Panel", "kanview:dashboard"),
    ("shopping_cart", "Pedidos", "kanview:pedidos-tablero"),
    ("inventory_2", "Inventario", "kanview:inventario"),
    ("menu_book", "Catálogo", "kanview:catalogo"),
    ("assignment", "Tareas", "kanview:tareas"),
    ("history", "Actividades", "kanview:tareas"),
    ("calendar_today", "Calendario", "kanview:calendario"),
    ("fact_check", "Auditoría", "kanview:auditoria"),
    ("group", "Usuarios", "kanview:clientes"),
    ("payments", "Finanzas", "kanview:finanzas"),
]


def _nav(activo=None):
    """Contexto que necesita la plantilla _sidebar.html en todas las páginas."""
    return {"nav_items": NAV_ITEMS, "active": activo}


# ---- Autenticación --------------------------------------------------------

def iniciar_sesion(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.get_user()
        login(request, usuario)
        siguiente = request.POST.get("next") or request.GET.get("next")
        if siguiente:
            return redirect(siguiente)
        return redirect("kanview:dashboard")
    return render(request, "kanview/login.html", {"form": form, "next": request.GET.get("next", "")})


def registrarse(request):
    """Crea User de Django (username=correo) + Cliente de kanview y loguea."""
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
        Cliente.objects.create(
            nombre=nombre, correo=correo,
            documento="", celular="", direccion="", edad=0, fecha_nacimiento=None,
        )
        login(request, user)
        messages.success(request, f"Cuenta creada. Bienvenido, {nombre}.")
        return redirect("kanview:dashboard")

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
                settings.EMAIL_HOST_USER,
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
    contexto = {
        "total_clientes": Cliente.objects.count(),
        "total_empleados": Empleado.objects.count(),
        "total_productos": Producto.objects.count(),
        "total_pedidos": Pedido.objects.count(),
        "pedidos_activos": Pedido.objects.filter(estado="activo").count(),
        "ultimos_pedidos": Pedido.objects.order_by("-id")[:5],
        **_nav("Panel"),
    }
    return render(request, "kanview/dashboard.html", contexto)


# ---- Páginas de la interfaz (diseño Stitch) -------------------------------

@login_required
def pedidos_tablero(request):
    return render(request, "kanview/pedidos_tablero.html", _nav("Pedidos"))


@login_required
def pedido_detalle(request, pk):
    return render(request, "kanview/pedidos_detalle.html", _nav("Pedidos"))


@login_required
def tareas(request):
    return render(request, "kanview/tareas.html", _nav("Tareas"))


@login_required
def calendario(request):
    return render(request, "kanview/calendario.html", _nav("Calendario"))


@login_required
def inventario(request):
    return render(request, "kanview/inventario.html", _nav("Inventario"))


@login_required
def finanzas(request):
    return render(request, "kanview/finanzas.html", _nav("Finanzas"))


@login_required
def auditoria(request):
    return render(request, "kanview/auditoria.html", _nav("Auditoría"))


@login_required
def mensajeria(request):
    return render(request, "kanview/mensajeria.html", _nav(None))


@login_required
def clientes(request):
    return render(request, "kanview/clientes.html", _nav("Usuarios"))


@login_required
def empleados(request):
    return render(request, "kanview/empleados.html", _nav(None))


@login_required
def catalogo(request):
    return render(request, "kanview/catalogo.html", _nav("Catálogo"))
