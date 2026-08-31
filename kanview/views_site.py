from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView

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


class SidebarMixin:
    active_label = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nav_items"] = NAV_ITEMS
        ctx["active"] = self.active_label
        return ctx


class KanviewLoginView(LoginView):
    template_name = "kanview/login.html"
    redirect_authenticated_user = True


class KanviewLogoutView(LogoutView):
    next_page = "kanview:login"


class PedidosTableroView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/pedidos_tablero.html"
    active_label = "Orders"


class PedidoDetalleView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/pedidos_detalle.html"
    active_label = "Orders"


class TareasView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/tareas.html"
    active_label = "Tasks"


class CalendarioView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/calendario.html"
    active_label = "Calendar"


class InventarioView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/inventario.html"
    active_label = "Inventory"


class FinanzasView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/finanzas.html"
    active_label = "Finance"


class AuditoriaView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/auditoria.html"
    active_label = "Audit"


class MensajeriaView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/mensajeria.html"
    active_label = None


class ClientesView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/clientes.html"
    active_label = "Users"


class EmpleadosView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/empleados.html"
    active_label = None


class CatalogoView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/catalogo.html"
    active_label = "Catalog"
