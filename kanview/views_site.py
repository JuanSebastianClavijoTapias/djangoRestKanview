from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView

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
    active_label = "Pedidos"


class PedidoDetalleView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/pedidos_detalle.html"
    active_label = "Pedidos"


class TareasView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/tareas.html"
    active_label = "Tareas"


class CalendarioView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/calendario.html"
    active_label = "Calendario"


class InventarioView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/inventario.html"
    active_label = "Inventario"


class FinanzasView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/finanzas.html"
    active_label = "Finanzas"


class AuditoriaView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/auditoria.html"
    active_label = "Auditoría"


class MensajeriaView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/mensajeria.html"
    active_label = None


class ClientesView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/clientes.html"
    active_label = "Usuarios"


class EmpleadosView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/empleados.html"
    active_label = None


class CatalogoView(LoginRequiredMixin, SidebarMixin, TemplateView):
    template_name = "kanview/catalogo.html"
    active_label = "Catálogo"
