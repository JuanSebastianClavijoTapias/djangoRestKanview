from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode

from .auditoria import registrar as registrar_auditoria
from .correo import enviar_correo
from .models import Cliente, Empleado, Pedido, Producto
from .seguridad import consumir_codigo_respaldo, perfil_de, verificar_totp
from .permisos import (
    ROL_CLIENTE,
    SECCIONES,
    asignar_rol,
    es_administrador,
    es_solo_cliente,
    puede,
    rol_principal,
    seccion_requerida,
)

# Elementos del menú lateral: (icono, etiqueta, nombre de la URL, sección que lo protege).
# La vista filtra esta lista según el rol del usuario (ver _nav).
# Un solo tablero: «Procesos» (/pedidos/). Las tareas y sus actividades se
# gestionan desde el módulo «Tareas»; el stock se gestiona en «Productos».
NAV_ITEMS = [
    ("dashboard", "Panel", "kanview:dashboard", "panel"),
    ("view_kanban", "Procesos", "kanview:pedidos-tablero", "pedidos"),
    ("assignment", "Tareas", "kanview:tareas", "tareas"),
    ("history", "Actividades", "kanview:actividades", "tareas"),
    ("forum", "Mensajería", "kanview:mensajeria", "mensajeria"),
    ("sell", "Productos", "kanview:producto-lista", "gestion-catalogo"),
    ("menu_book", "Catálogo", "kanview:catalogo", "catalogo"),
    ("calendar_today", "Calendario", "kanview:calendario", "calendario"),
    ("fact_check", "Auditoría", "kanview:auditoria", "auditoria"),
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

def _destino_seguro(request, siguiente, usuario=None):
    if siguiente and url_has_allowed_host_and_scheme(
        siguiente,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return siguiente
    if usuario is not None and es_solo_cliente(usuario):
        return reverse("kanview:pedidos-tablero")
    return reverse("kanview:dashboard")


def iniciar_sesion(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.get_user()
        siguiente = _destino_seguro(
            request, request.POST.get("next") or request.GET.get("next"), usuario
        )
        perfil = perfil_de(usuario)
        if perfil and perfil.totp_habilitado:
            request.session.cycle_key()
            request.session["pre_2fa_user_id"] = usuario.pk
            request.session["pre_2fa_next"] = siguiente
            return redirect("kanview:login-2fa")
        login(request, usuario)
        registrar_auditoria(request, "login", "Usuario", usuario, f"Inicio de sesión de {usuario}", usuario=usuario)
        return redirect(siguiente)
    if request.method == "POST":
        registrar_auditoria(
            request, "login_fallido", "Usuario",
            descripcion=f"Intento de inicio de sesión fallido: {request.POST.get('username', '')[:80]}",
        )
    return render(request, "kanview/login.html", {"form": form, "next": request.GET.get("next", "")})


def login_2fa(request):
    """Segundo factor: código TOTP o código de respaldo."""
    usuario_id = request.session.get("pre_2fa_user_id")
    if not usuario_id:
        return redirect("kanview:login")
    usuario = User.objects.filter(pk=usuario_id, is_active=True).first()
    if usuario is None:
        request.session.pop("pre_2fa_user_id", None)
        return redirect("kanview:login")
    perfil = perfil_de(usuario)
    if not perfil.totp_habilitado:
        login(request, usuario)
        return redirect(_destino_seguro(request, request.session.pop("pre_2fa_next", ""), usuario))
    if request.method == "POST":
        codigo = (request.POST.get("codigo") or "").strip()
        valido = verificar_totp(perfil.totp_secret, codigo) or consumir_codigo_respaldo(perfil, codigo)
        if valido:
            siguiente = request.session.pop("pre_2fa_next", "")
            request.session.pop("pre_2fa_user_id", None)
            login(request, usuario)
            registrar_auditoria(request, "login_2fa", "Usuario", usuario, f"Inicio de sesión con 2FA de {usuario}", usuario=usuario)
            return redirect(_destino_seguro(request, siguiente, usuario))
        registrar_auditoria(
            request, "2fa_fallido", "Usuario", usuario,
            f"Código 2FA incorrecto para {usuario}", usuario=usuario,
        )
        messages.error(request, "Código de verificación incorrecto.")
    return render(request, "kanview/login_2fa.html", {"usuario": usuario})


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
            nombre=nombre, correo=correo, usuario=user,
            documento="", celular="", direccion="", fecha_nacimiento=None,
        )
        registrar_auditoria(request, "crear", "Usuario", user, f"Cuenta creada para {nombre}")
        messages.success(request, f"Cuenta creada para {nombre}.")
        return redirect("kanview:usuarios")

    return render(request, "kanview/registro.html", {})


def cerrar_sesion(request):
    if request.user.is_authenticated:
        registrar_auditoria(request, "logout", "Usuario", request.user, f"Cierre de sesión de {request.user}")
    logout(request)
    return redirect("kanview:login")


# ---- Recuperar clave -------------------------------------------------------

def recuperar_solicitar(request):
    """Paso 1: envía un enlace de restablecimiento sin revelar si el correo existe."""
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip().lower()
        if not correo:
            messages.error(request, "Ingresa tu correo electrónico.")
        else:
            usuarios = list(User.objects.filter(email__iexact=correo, is_active=True)[:2])
            if len(usuarios) == 1:
                usuario = usuarios[0]
                uid = urlsafe_base64_encode(force_bytes(usuario.pk))
                token = default_token_generator.make_token(usuario)
                url = request.build_absolute_uri(
                    reverse("kanview:recuperar-restablecer", args=[uid, token])
                )
                enviado = enviar_correo(
                    "Kanview · Restablece tu contraseña",
                    f"Hola,\n\nPara definir una nueva contraseña abre este enlace:\n{url}\n\n"
                    "El enlace es de un solo uso y vence pronto.",
                    [correo],
                )
                if not enviado:
                    # Si el SMTP falla hay que avisar: si no, el usuario espera un
                    # correo que nunca llega. Aunque esto rompe el secreto absoluto
                    # de la existencia de la cuenta (solo ante un fallo de envío),
                    # es preferible a dejarlo bloqueado sin explicación.
                    messages.error(
                        request,
                        "No pudimos enviar el correo por un problema del servidor "
                        "de mensajes (tu cuenta no está en causa). Intenta de nuevo "
                        "en unos minutos o avisa al administrador.",
                    )
                    return redirect("kanview:recuperar")
            messages.success(
                request,
                "Si el correo está registrado, enviamos un enlace para restablecer la contraseña.",
            )
        return redirect("kanview:recuperar")
    return render(request, "kanview/recuperar.html", {"correo": request.GET.get("correo", "")})


def recuperar_restablecer(request, uidb64, token):
    """Paso 2: valida el enlace y guarda la nueva contraseña."""
    try:
        usuario = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        usuario = None
    if usuario is None or not default_token_generator.check_token(usuario, token):
        messages.error(request, "El enlace no es válido o ya venció.")
        return redirect("kanview:recuperar")
    if request.method == "POST":
        nueva = request.POST.get("nueva") or ""
        repetida = request.POST.get("repetida") or ""
        if len(nueva) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
        elif nueva != repetida:
            messages.error(request, "Las contraseñas no coinciden.")
        else:
            usuario.set_password(nueva)
            usuario.save(update_fields=["password"])
            registrar_auditoria(request, "recuperar_password", "Usuario", usuario, f"Contraseña restablecida por {usuario}")
            messages.success(request, "Contraseña actualizada. Ya puedes iniciar sesión.")
            return redirect("kanview:login")
    return render(request, "kanview/recuperar_restablecer.html", {"uidb64": uidb64, "token": token})


# ---- Panel ----------------------------------------------------------------

@login_required
def dashboard(request):
    """Panel general. El Cliente no tiene panel: va directo a sus procesos."""
    if es_solo_cliente(request.user):
        return redirect("kanview:pedidos-tablero")
    pedidos = Pedido.objects.filter(activo=True)
    clientes = Cliente.objects.filter(activo=True)

    if es_solo_cliente(request.user):
        pedidos = pedidos.filter(id_cliente__correo__iexact=request.user.email)
        clientes = clientes.filter(correo__iexact=request.user.email)

    rol = rol_principal(request.user)
    contexto = {
        "total_clientes": clientes.count(),
        "total_empleados": Empleado.objects.filter(activo=True).count(),
        "total_productos": Producto.objects.filter(activo=True).count(),
        "total_pedidos": pedidos.count(),
        "pedidos_activos": pedidos.filter(estado="activo").count(),
        "ultimos_pedidos": pedidos.order_by("-id")[:5],
        "rol": rol,
        "es_trabajador": rol == "Trabajador",
        "cabecera_titulo": "Panel",
        **_nav("Panel", request),
    }
    return render(request, "kanview/dashboard.html", contexto)


# ---- Helper de render para las pantallas conectadas a datos ----------------

def _render(request, template, active=None, **context):
    """Renderiza una plantilla con el contexto del sidebar (nav_items + active)."""
    return render(request, template, {**context, **_nav(active, request)})


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
        "puede_respaldos": es_administrador(request.user),
        "cabecera_titulo": "Configuración",
        **_nav(None, request),
    }
    return render(request, "kanview/configuracion.html", contexto)
