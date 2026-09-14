from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

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


def cerrar_sesion(request):
    logout(request)
    return redirect("kanview:login")


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
