from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .forms import (
    ActividadesForm,
    AdministradorForm,
    AnalisisFinancieroForm,
    CalendarioForm,
    CatalogoForm,
    ClienteForm,
    EmpleadoForm,
    HistorialForm,
    InventarioForm,
    PedidoForm,
    ProductoForm,
    TareasPedidoForm,
)
from .models import (
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Catalogo,
    Cliente,
    Empleado,
    Historial,
    Inventario,
    Pedido,
    Producto,
    TareasPedido,
)
from .views_site import _render


# ---- Helpers (funciones, no clases) --------------------------------------

def _lista(request, modelo, active, title, columns, name):
    objetos = modelo.objects.all().order_by("-id")
    paginator = Paginator(objetos, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return _render(
        request,
        "kanview/crud/list.html",
        active,
        title=title,
        columns=columns,
        object_list=page_obj.object_list,
        paginator=paginator,
        page_obj=page_obj,
        is_paginated=page_obj.has_other_pages(),
        create_url=reverse(f"kanview:{name}-crear"),
        update_url_name=f"kanview:{name}-editar",
        delete_url_name=f"kanview:{name}-eliminar",
    )


def _crear(request, form_class, active, label, name):
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{label} creado correctamente.")
            return redirect(f"kanview:{name}-lista")
    else:
        form = form_class()
    return _render(
        request,
        "kanview/crud/form.html",
        active,
        title=f"Nuevo {label}",
        form=form,
        cancel_url=reverse(f"kanview:{name}-lista"),
    )


def _editar(request, modelo, form_class, active, label, name, pk):
    objeto = get_object_or_404(modelo, pk=pk)
    if request.method == "POST":
        form = form_class(request.POST, instance=objeto)
        if form.is_valid():
            form.save()
            messages.success(request, f"{label} actualizado correctamente.")
            return redirect(f"kanview:{name}-lista")
    else:
        form = form_class(instance=objeto)
    return _render(
        request,
        "kanview/crud/form.html",
        active,
        title=f"Editar {label}",
        form=form,
        cancel_url=reverse(f"kanview:{name}-lista"),
    )


def _eliminar(request, modelo, active, label, name, pk):
    objeto = get_object_or_404(modelo, pk=pk)
    if request.method == "POST":
        objeto.delete()
        messages.success(request, f"{label} eliminado.")
        return redirect(f"kanview:{name}-lista")
    return _render(
        request,
        "kanview/crud/confirm_delete.html",
        active,
        title=f"Eliminar {label}",
        object=objeto,
        cancel_url=reverse(f"kanview:{name}-lista"),
    )


# ---- Cliente ---------------------------------------------------------------

@login_required
def cliente_lista(request):
    return _lista(request, Cliente, "Users", "Clientes", ["nombre", "documento", "celular", "direccion", "edad"], "cliente")


@login_required
def cliente_crear(request):
    return _crear(request, ClienteForm, "Users", "Cliente", "cliente")


@login_required
def cliente_editar(request, pk):
    return _editar(request, Cliente, ClienteForm, "Users", "Cliente", "cliente", pk)


@login_required
def cliente_eliminar(request, pk):
    return _eliminar(request, Cliente, "Users", "Cliente", "cliente", pk)


# ---- Empleado ---------------------------------------------------------------

@login_required
def empleado_lista(request):
    return _lista(request, Empleado, "Users", "Empleados", ["nombre", "documento", "cargo", "celular", "salario"], "empleado")


@login_required
def empleado_crear(request):
    return _crear(request, EmpleadoForm, "Users", "Empleado", "empleado")


@login_required
def empleado_editar(request, pk):
    return _editar(request, Empleado, EmpleadoForm, "Users", "Empleado", "empleado", pk)


@login_required
def empleado_eliminar(request, pk):
    return _eliminar(request, Empleado, "Users", "Empleado", "empleado", pk)


# ---- Administrador ------------------------------------------------------

@login_required
def administrador_lista(request):
    return _lista(request, Administrador, "Dashboard", "Administradores", ["nombre", "documento", "celular"], "administrador")


@login_required
def administrador_crear(request):
    return _crear(request, AdministradorForm, "Dashboard", "Administrador", "administrador")


@login_required
def administrador_editar(request, pk):
    return _editar(request, Administrador, AdministradorForm, "Dashboard", "Administrador", "administrador", pk)


@login_required
def administrador_eliminar(request, pk):
    return _eliminar(request, Administrador, "Dashboard", "Administrador", "administrador", pk)


# ---- Producto ---------------------------------------------------------------

@login_required
def producto_lista(request):
    return _lista(request, Producto, "Catalog", "Productos", ["nombre", "categoria", "codigo_producto", "cantidad", "precio"], "producto")


@login_required
def producto_crear(request):
    return _crear(request, ProductoForm, "Catalog", "Producto", "producto")


@login_required
def producto_editar(request, pk):
    return _editar(request, Producto, ProductoForm, "Catalog", "Producto", "producto", pk)


@login_required
def producto_eliminar(request, pk):
    return _eliminar(request, Producto, "Catalog", "Producto", "producto", pk)


# ---- Pedido ---------------------------------------------------------------

@login_required
def pedido_lista(request):
    return _lista(request, Pedido, "Orders", "Pedidos", ["codigo_pedido", "id_cliente", "id_empleado", "estado", "fecha_creacion"], "pedido")


@login_required
def pedido_crear(request):
    return _crear(request, PedidoForm, "Orders", "Pedido", "pedido")


@login_required
def pedido_editar(request, pk):
    return _editar(request, Pedido, PedidoForm, "Orders", "Pedido", "pedido", pk)


@login_required
def pedido_eliminar(request, pk):
    return _eliminar(request, Pedido, "Orders", "Pedido", "pedido", pk)


# ---- Análisis financiero --------------------------------------------------

@login_required
def analisis_financiero_lista(request):
    return _lista(request, AnalisisFinanciero, "Finance", "Análisis financiero", ["gastos", "fuentes_ingresos", "productos_vendidos", "id_administrador"], "analisis-financiero")


@login_required
def analisis_financiero_crear(request):
    return _crear(request, AnalisisFinancieroForm, "Finance", "Análisis financiero", "analisis-financiero")


@login_required
def analisis_financiero_editar(request, pk):
    return _editar(request, AnalisisFinanciero, AnalisisFinancieroForm, "Finance", "Análisis financiero", "analisis-financiero", pk)


@login_required
def analisis_financiero_eliminar(request, pk):
    return _eliminar(request, AnalisisFinanciero, "Finance", "Análisis financiero", "analisis-financiero", pk)


# ---- Inventario -----------------------------------------------------------

@login_required
def inventario_lista(request):
    return _lista(request, Inventario, "Inventory", "Inventario", ["cantidad", "id_producto"], "inventario")


@login_required
def inventario_crear(request):
    return _crear(request, InventarioForm, "Inventory", "Inventario", "inventario")


@login_required
def inventario_editar(request, pk):
    return _editar(request, Inventario, InventarioForm, "Inventory", "Inventario", "inventario", pk)


@login_required
def inventario_eliminar(request, pk):
    return _eliminar(request, Inventario, "Inventory", "Inventario", "inventario", pk)


# ---- Catálogo -------------------------------------------------------------

@login_required
def catalogo_lista(request):
    return _lista(request, Catalogo, "Catalog", "Catálogo", ["categorias", "id_inventario", "id_producto"], "catalogo")


@login_required
def catalogo_crear(request):
    return _crear(request, CatalogoForm, "Catalog", "Catálogo", "catalogo")


@login_required
def catalogo_editar(request, pk):
    return _editar(request, Catalogo, CatalogoForm, "Catalog", "Catálogo", "catalogo", pk)


@login_required
def catalogo_eliminar(request, pk):
    return _eliminar(request, Catalogo, "Catalog", "Catálogo", "catalogo", pk)


# ---- Tareas de pedido -----------------------------------------------------

@login_required
def tarea_lista(request):
    return _lista(request, TareasPedido, "Tasks", "Tareas", ["nombre", "estado", "fecha_inicio", "fecha_fin", "id_pedido"], "tarea")


@login_required
def tarea_crear(request):
    return _crear(request, TareasPedidoForm, "Tasks", "Tarea", "tarea")


@login_required
def tarea_editar(request, pk):
    return _editar(request, TareasPedido, TareasPedidoForm, "Tasks", "Tarea", "tarea", pk)


@login_required
def tarea_eliminar(request, pk):
    return _eliminar(request, TareasPedido, "Tasks", "Tarea", "tarea", pk)


# ---- Actividades ----------------------------------------------------------

@login_required
def actividad_lista(request):
    return _lista(request, Actividades, "Activities", "Actividades", ["nombre", "estado", "fecha_inicio", "fecha_fin", "id_tarea"], "actividad")


@login_required
def actividad_crear(request):
    return _crear(request, ActividadesForm, "Activities", "Actividad", "actividad")


@login_required
def actividad_editar(request, pk):
    return _editar(request, Actividades, ActividadesForm, "Activities", "Actividad", "actividad", pk)


@login_required
def actividad_eliminar(request, pk):
    return _eliminar(request, Actividades, "Activities", "Actividad", "actividad", pk)


# ---- Historial ------------------------------------------------------------

@login_required
def historial_lista(request):
    return _lista(request, Historial, "Audit", "Historial", ["fecha_creacion", "hora_creacion", "id_cliente", "id_empleado", "id_producto"], "historial")


@login_required
def historial_crear(request):
    return _crear(request, HistorialForm, "Audit", "Historial", "historial")


@login_required
def historial_editar(request, pk):
    return _editar(request, Historial, HistorialForm, "Audit", "Historial", "historial", pk)


@login_required
def historial_eliminar(request, pk):
    return _eliminar(request, Historial, "Audit", "Historial", "historial", pk)


# ---- Calendario -----------------------------------------------------------

@login_required
def calendario_lista(request):
    return _lista(request, Calendario, "Calendar", "Calendario", ["fecha", "nombre_mes", "nombre_dia", "dia", "id_pedido"], "calendario")


@login_required
def calendario_crear(request):
    return _crear(request, CalendarioForm, "Calendar", "Calendario", "calendario")


@login_required
def calendario_editar(request, pk):
    return _editar(request, Calendario, CalendarioForm, "Calendar", "Calendario", "calendario", pk)


@login_required
def calendario_eliminar(request, pk):
    return _eliminar(request, Calendario, "Calendar", "Calendario", "calendario", pk)
