from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import AdministradorForm, ClienteForm, EmpleadoForm, PedidoForm, ProductoForm
from .models import Administrador, Cliente, Empleado, Pedido, Producto
from .views_site import SidebarMixin

NavContextMixin = SidebarMixin  # shared sidebar context (see views_site.NAV_ITEMS)


class DashboardView(LoginRequiredMixin, NavContextMixin, TemplateView):
    template_name = "kanview/dashboard.html"
    active_label = "Dashboard"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_clientes"] = Cliente.objects.count()
        ctx["total_empleados"] = Empleado.objects.count()
        ctx["total_productos"] = Producto.objects.count()
        ctx["total_pedidos"] = Pedido.objects.count()
        ctx["pedidos_activos"] = Pedido.objects.filter(estado="activo").count()
        ctx["ultimos_pedidos"] = Pedido.objects.order_by("-id")[:5]
        return ctx


# ---- Generic CRUD scaffolding -------------------------------------------

class BaseListView(LoginRequiredMixin, NavContextMixin, ListView):
    template_name = "kanview/crud/list.html"
    paginate_by = 20
    ordering = "-id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.title
        ctx["columns"] = self.columns
        ctx["create_url"] = reverse(self.create_url_name)
        ctx["update_url_name"] = self.update_url_name
        ctx["delete_url_name"] = self.delete_url_name
        return ctx


class BaseCreateView(LoginRequiredMixin, NavContextMixin, CreateView):
    template_name = "kanview/crud/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Nuevo {self.object_label}"
        ctx["cancel_url"] = reverse(self.list_url_name)
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.object_label} creado correctamente.")
        return super().form_valid(form)


class BaseUpdateView(LoginRequiredMixin, NavContextMixin, UpdateView):
    template_name = "kanview/crud/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Editar {self.object_label}"
        ctx["cancel_url"] = reverse(self.list_url_name)
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.object_label} actualizado correctamente.")
        return super().form_valid(form)


class BaseDeleteView(LoginRequiredMixin, NavContextMixin, DeleteView):
    template_name = "kanview/crud/confirm_delete.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Eliminar {self.object_label}"
        ctx["cancel_url"] = reverse(self.list_url_name)
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.object_label} eliminado.")
        return super().form_valid(form)


# ---- Cliente ---------------------------------------------------------------

class ClienteListView(BaseListView):
    model = Cliente
    active_label = "Users"
    title = "Clientes"
    columns = ["nombre", "documento", "celular", "direccion", "edad"]
    create_url_name = "kanview:cliente-crear"
    update_url_name = "kanview:cliente-editar"
    delete_url_name = "kanview:cliente-eliminar"


class ClienteCreateView(BaseCreateView):
    model = Cliente
    form_class = ClienteForm
    active_label = "Users"
    object_label = "Cliente"
    list_url_name = "kanview:cliente-lista"
    success_url = reverse_lazy("kanview:cliente-lista")


class ClienteUpdateView(BaseUpdateView):
    model = Cliente
    form_class = ClienteForm
    active_label = "Users"
    object_label = "Cliente"
    list_url_name = "kanview:cliente-lista"
    success_url = reverse_lazy("kanview:cliente-lista")


class ClienteDeleteView(BaseDeleteView):
    model = Cliente
    active_label = "Users"
    object_label = "Cliente"
    list_url_name = "kanview:cliente-lista"
    success_url = reverse_lazy("kanview:cliente-lista")


# ---- Empleado ---------------------------------------------------------------

class EmpleadoListView(BaseListView):
    model = Empleado
    active_label = "Users"
    title = "Empleados"
    columns = ["nombre", "documento", "cargo", "celular", "salario"]
    create_url_name = "kanview:empleado-crear"
    update_url_name = "kanview:empleado-editar"
    delete_url_name = "kanview:empleado-eliminar"


class EmpleadoCreateView(BaseCreateView):
    model = Empleado
    form_class = EmpleadoForm
    active_label = "Users"
    object_label = "Empleado"
    list_url_name = "kanview:empleado-lista"
    success_url = reverse_lazy("kanview:empleado-lista")


class EmpleadoUpdateView(BaseUpdateView):
    model = Empleado
    form_class = EmpleadoForm
    active_label = "Users"
    object_label = "Empleado"
    list_url_name = "kanview:empleado-lista"
    success_url = reverse_lazy("kanview:empleado-lista")


class EmpleadoDeleteView(BaseDeleteView):
    model = Empleado
    active_label = "Users"
    object_label = "Empleado"
    list_url_name = "kanview:empleado-lista"
    success_url = reverse_lazy("kanview:empleado-lista")


# ---- Administrador ------------------------------------------------------

class AdministradorListView(BaseListView):
    model = Administrador
    active_label = "Dashboard"
    title = "Administradores"
    columns = ["nombre", "documento", "celular"]
    create_url_name = "kanview:administrador-crear"
    update_url_name = "kanview:administrador-editar"
    delete_url_name = "kanview:administrador-eliminar"


class AdministradorCreateView(BaseCreateView):
    model = Administrador
    form_class = AdministradorForm
    active_label = "Dashboard"
    object_label = "Administrador"
    list_url_name = "kanview:administrador-lista"
    success_url = reverse_lazy("kanview:administrador-lista")


class AdministradorUpdateView(BaseUpdateView):
    model = Administrador
    form_class = AdministradorForm
    active_label = "Dashboard"
    object_label = "Administrador"
    list_url_name = "kanview:administrador-lista"
    success_url = reverse_lazy("kanview:administrador-lista")


class AdministradorDeleteView(BaseDeleteView):
    model = Administrador
    active_label = "Dashboard"
    object_label = "Administrador"
    list_url_name = "kanview:administrador-lista"
    success_url = reverse_lazy("kanview:administrador-lista")


# ---- Producto ---------------------------------------------------------------

class ProductoListView(BaseListView):
    model = Producto
    active_label = "Catalog"
    title = "Productos"
    columns = ["nombre", "categoria", "codigo_producto", "cantidad", "precio"]
    create_url_name = "kanview:producto-crear"
    update_url_name = "kanview:producto-editar"
    delete_url_name = "kanview:producto-eliminar"


class ProductoCreateView(BaseCreateView):
    model = Producto
    form_class = ProductoForm
    active_label = "Catalog"
    object_label = "Producto"
    list_url_name = "kanview:producto-lista"
    success_url = reverse_lazy("kanview:producto-lista")


class ProductoUpdateView(BaseUpdateView):
    model = Producto
    form_class = ProductoForm
    active_label = "Catalog"
    object_label = "Producto"
    list_url_name = "kanview:producto-lista"
    success_url = reverse_lazy("kanview:producto-lista")


class ProductoDeleteView(BaseDeleteView):
    model = Producto
    active_label = "Catalog"
    object_label = "Producto"
    list_url_name = "kanview:producto-lista"
    success_url = reverse_lazy("kanview:producto-lista")


# ---- Pedido ---------------------------------------------------------------

class PedidoListView(BaseListView):
    model = Pedido
    active_label = "Orders"
    title = "Pedidos"
    columns = ["codigo_pedido", "id_cliente", "id_empleado", "estado", "fecha_creacion"]
    create_url_name = "kanview:pedido-crear"
    update_url_name = "kanview:pedido-editar"
    delete_url_name = "kanview:pedido-eliminar"


class PedidoCreateView(BaseCreateView):
    model = Pedido
    form_class = PedidoForm
    active_label = "Orders"
    object_label = "Pedido"
    list_url_name = "kanview:pedido-lista"
    success_url = reverse_lazy("kanview:pedido-lista")


class PedidoUpdateView(BaseUpdateView):
    model = Pedido
    form_class = PedidoForm
    active_label = "Orders"
    object_label = "Pedido"
    list_url_name = "kanview:pedido-lista"
    success_url = reverse_lazy("kanview:pedido-lista")


class PedidoDeleteView(BaseDeleteView):
    model = Pedido
    active_label = "Orders"
    object_label = "Pedido"
    list_url_name = "kanview:pedido-lista"
    success_url = reverse_lazy("kanview:pedido-lista")
