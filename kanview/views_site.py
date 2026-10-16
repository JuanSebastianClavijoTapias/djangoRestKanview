from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .models import Cliente, Empleado, Pedido, Producto

NAV_ITEMS = [
    ("dashboard", "Dashboard", "kanview:dashboard"),
    ("shopping_cart", "Orders", "kanview:pedidos-tablero"),
    ("inventory_2", "Inventory", "kanview:inventario"),
    ("menu_book", "Catalog", "kanview:catalogo"),
    ("assignment", "Tasks", "kanview:tareas"),
    ("history", "Activities", "kanview:tareas"),
    ("calendar_today", "Calendar", "kanview:calendario"),
    ("fact_check", "Audit", "kanview:auditoria"),
    ("group", "Users", "kanview:clientes"),
    ("payments", "Finance", "kanview:finanzas"),
]


def _render(request, template, active=None, **context):
    """Renderiza una página con el contexto del sidebar (nav_items + active)."""
    context["nav_items"] = NAV_ITEMS
    context["active"] = active
    return render(request, template, context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("kanview:dashboard")

    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(next_url or "kanview:dashboard")
    else:
        form = AuthenticationForm()

    return render(request, "kanview/login.html", {"form": form, "next": next_url})


def logout_view(request):
    logout(request)
    return redirect("kanview:login")


@login_required
def dashboard(request):
    return _render(
        request,
        "kanview/dashboard.html",
        "Dashboard",
        total_clientes=Cliente.objects.count(),
        total_empleados=Empleado.objects.count(),
        total_productos=Producto.objects.count(),
        total_pedidos=Pedido.objects.count(),
        pedidos_activos=Pedido.objects.filter(estado="activo").count(),
        ultimos_pedidos=Pedido.objects.order_by("-id")[:5],
    )


@login_required
def mensajeria(request):
    # Maqueta estática por ahora (no hay modelo de mensajería).
    return _render(request, "kanview/mensajeria.html", None)
