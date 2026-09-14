from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    ActividadesForm,
    AdministradorForm,
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
from .views_site import _nav


# ---- Cliente --------------------------------------------------------------

@login_required
def cliente_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.nombre, obj.documento, obj.celular, obj.direccion, obj.edad]}
        for obj in Cliente.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Clientes",
        "columnas": ["Nombre", "Documento", "Celular", "Dirección", "Edad"],
        "filas": filas,
        "crear_url": reverse("kanview:cliente-crear"),
        "editar_url": "kanview:cliente-editar",
        "eliminar_url": "kanview:cliente-eliminar",
        **_nav("Usuarios"),
    })


@login_required
def cliente_crear(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente creado correctamente.")
            return redirect("kanview:cliente-lista")
    else:
        form = ClienteForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo cliente",
        "cancel_url": reverse("kanview:cliente-lista"),
        **_nav("Usuarios"),
    })


@login_required
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect("kanview:cliente-lista")
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar cliente",
        "cancel_url": reverse("kanview:cliente-lista"),
        **_nav("Usuarios"),
    })


@login_required
def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente.delete()
        messages.success(request, "Cliente eliminado.")
        return redirect("kanview:cliente-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": cliente,
        "title": "Eliminar cliente",
        "cancel_url": reverse("kanview:cliente-lista"),
        **_nav("Usuarios"),
    })


# ---- Empleado -------------------------------------------------------------

@login_required
def empleado_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.nombre, obj.documento, obj.cargo, obj.celular, obj.salario]}
        for obj in Empleado.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Empleados",
        "columnas": ["Nombre", "Documento", "Cargo", "Celular", "Salario"],
        "filas": filas,
        "crear_url": reverse("kanview:empleado-crear"),
        "editar_url": "kanview:empleado-editar",
        "eliminar_url": "kanview:empleado-eliminar",
        **_nav("Usuarios"),
    })


@login_required
def empleado_crear(request):
    if request.method == "POST":
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Empleado creado correctamente.")
            return redirect("kanview:empleado-lista")
    else:
        form = EmpleadoForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo empleado",
        "cancel_url": reverse("kanview:empleado-lista"),
        **_nav("Usuarios"),
    })


@login_required
def empleado_editar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    if request.method == "POST":
        form = EmpleadoForm(request.POST, instance=empleado)
        if form.is_valid():
            form.save()
            messages.success(request, "Empleado actualizado correctamente.")
            return redirect("kanview:empleado-lista")
    else:
        form = EmpleadoForm(instance=empleado)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar empleado",
        "cancel_url": reverse("kanview:empleado-lista"),
        **_nav("Usuarios"),
    })


@login_required
def empleado_eliminar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    if request.method == "POST":
        empleado.delete()
        messages.success(request, "Empleado eliminado.")
        return redirect("kanview:empleado-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": empleado,
        "title": "Eliminar empleado",
        "cancel_url": reverse("kanview:empleado-lista"),
        **_nav("Usuarios"),
    })


# ---- Administrador --------------------------------------------------------

@login_required
def administrador_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.nombre, obj.documento, obj.celular]}
        for obj in Administrador.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Administradores",
        "columnas": ["Nombre", "Documento", "Celular"],
        "filas": filas,
        "crear_url": reverse("kanview:administrador-crear"),
        "editar_url": "kanview:administrador-editar",
        "eliminar_url": "kanview:administrador-eliminar",
        **_nav("Panel"),
    })


@login_required
def administrador_crear(request):
    if request.method == "POST":
        form = AdministradorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Administrador creado correctamente.")
            return redirect("kanview:administrador-lista")
    else:
        form = AdministradorForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo administrador",
        "cancel_url": reverse("kanview:administrador-lista"),
        **_nav("Panel"),
    })


@login_required
def administrador_editar(request, pk):
    administrador = get_object_or_404(Administrador, pk=pk)
    if request.method == "POST":
        form = AdministradorForm(request.POST, instance=administrador)
        if form.is_valid():
            form.save()
            messages.success(request, "Administrador actualizado correctamente.")
            return redirect("kanview:administrador-lista")
    else:
        form = AdministradorForm(instance=administrador)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar administrador",
        "cancel_url": reverse("kanview:administrador-lista"),
        **_nav("Panel"),
    })


@login_required
def administrador_eliminar(request, pk):
    administrador = get_object_or_404(Administrador, pk=pk)
    if request.method == "POST":
        administrador.delete()
        messages.success(request, "Administrador eliminado.")
        return redirect("kanview:administrador-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": administrador,
        "title": "Eliminar administrador",
        "cancel_url": reverse("kanview:administrador-lista"),
        **_nav("Panel"),
    })


# ---- Producto -------------------------------------------------------------

@login_required
def producto_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.nombre, obj.categoria, obj.codigo_producto, obj.cantidad, obj.precio]}
        for obj in Producto.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Productos",
        "columnas": ["Nombre", "Categoría", "Código", "Cantidad", "Precio"],
        "filas": filas,
        "crear_url": reverse("kanview:producto-crear"),
        "editar_url": "kanview:producto-editar",
        "eliminar_url": "kanview:producto-eliminar",
        **_nav("Catálogo"),
    })


@login_required
def producto_crear(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado correctamente.")
            return redirect("kanview:producto-lista")
    else:
        form = ProductoForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo producto",
        "cancel_url": reverse("kanview:producto-lista"),
        **_nav("Catálogo"),
    })


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado correctamente.")
            return redirect("kanview:producto-lista")
    else:
        form = ProductoForm(instance=producto)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar producto",
        "cancel_url": reverse("kanview:producto-lista"),
        **_nav("Catálogo"),
    })


@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        producto.delete()
        messages.success(request, "Producto eliminado.")
        return redirect("kanview:producto-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": producto,
        "title": "Eliminar producto",
        "cancel_url": reverse("kanview:producto-lista"),
        **_nav("Catálogo"),
    })


# ---- Pedido ---------------------------------------------------------------

@login_required
def pedido_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.codigo_pedido, obj.id_cliente, obj.id_empleado, obj.estado, obj.fecha_creacion]}
        for obj in Pedido.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Pedidos",
        "columnas": ["Código", "Cliente", "Empleado", "Estado", "Fecha"],
        "filas": filas,
        "crear_url": reverse("kanview:pedido-crear"),
        "editar_url": "kanview:pedido-editar",
        "eliminar_url": "kanview:pedido-eliminar",
        **_nav("Pedidos"),
    })


@login_required
def pedido_crear(request):
    if request.method == "POST":
        form = PedidoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Pedido creado correctamente.")
            return redirect("kanview:pedido-lista")
    else:
        form = PedidoForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo pedido",
        "cancel_url": reverse("kanview:pedido-lista"),
        **_nav("Pedidos"),
    })


@login_required
def pedido_editar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, "Pedido actualizado correctamente.")
            return redirect("kanview:pedido-lista")
    else:
        form = PedidoForm(instance=pedido)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar pedido",
        "cancel_url": reverse("kanview:pedido-lista"),
        **_nav("Pedidos"),
    })


@login_required
def pedido_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        pedido.delete()
        messages.success(request, "Pedido eliminado.")
        return redirect("kanview:pedido-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": pedido,
        "title": "Eliminar pedido",
        "cancel_url": reverse("kanview:pedido-lista"),
        **_nav("Pedidos"),
    })


# ---- Inventario -----------------------------------------------------------

@login_required
def inventario_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.cantidad, obj.id_producto]}
        for obj in Inventario.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Inventario",
        "columnas": ["Cantidad", "Producto"],
        "filas": filas,
        "crear_url": reverse("kanview:inventario-crear"),
        "editar_url": "kanview:inventario-editar",
        "eliminar_url": "kanview:inventario-eliminar",
        **_nav("Inventario"),
    })


@login_required
def inventario_crear(request):
    if request.method == "POST":
        form = InventarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Inventario creado correctamente.")
            return redirect("kanview:inventario-lista")
    else:
        form = InventarioForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo inventario",
        "cancel_url": reverse("kanview:inventario-lista"),
        **_nav("Inventario"),
    })


@login_required
def inventario_editar(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == "POST":
        form = InventarioForm(request.POST, instance=inventario)
        if form.is_valid():
            form.save()
            messages.success(request, "Inventario actualizado correctamente.")
            return redirect("kanview:inventario-lista")
    else:
        form = InventarioForm(instance=inventario)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar inventario",
        "cancel_url": reverse("kanview:inventario-lista"),
        **_nav("Inventario"),
    })


@login_required
def inventario_eliminar(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == "POST":
        inventario.delete()
        messages.success(request, "Inventario eliminado.")
        return redirect("kanview:inventario-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": inventario,
        "title": "Eliminar inventario",
        "cancel_url": reverse("kanview:inventario-lista"),
        **_nav("Inventario"),
    })


# ---- Calendario -----------------------------------------------------------

@login_required
def calendario_crud_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.fecha, obj.nombre_mes, obj.nombre_dia, obj.id_pedido]}
        for obj in Calendario.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Calendario",
        "columnas": ["Fecha", "Mes", "Día", "Pedido"],
        "filas": filas,
        "crear_url": reverse("kanview:calendario-crear"),
        "editar_url": "kanview:calendario-editar",
        "eliminar_url": "kanview:calendario-eliminar",
        **_nav("Calendario"),
    })


@login_required
def calendario_crear(request):
    if request.method == "POST":
        form = CalendarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de calendario creado correctamente.")
            return redirect("kanview:calendario-lista")
    else:
        form = CalendarioForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo registro de calendario",
        "cancel_url": reverse("kanview:calendario-lista"),
        **_nav("Calendario"),
    })


@login_required
def calendario_editar(request, pk):
    registro = get_object_or_404(Calendario, pk=pk)
    if request.method == "POST":
        form = CalendarioForm(request.POST, instance=registro)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de calendario actualizado correctamente.")
            return redirect("kanview:calendario-lista")
    else:
        form = CalendarioForm(instance=registro)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar registro de calendario",
        "cancel_url": reverse("kanview:calendario-lista"),
        **_nav("Calendario"),
    })


@login_required
def calendario_eliminar(request, pk):
    registro = get_object_or_404(Calendario, pk=pk)
    if request.method == "POST":
        registro.delete()
        messages.success(request, "Registro de calendario eliminado.")
        return redirect("kanview:calendario-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": registro,
        "title": "Eliminar registro de calendario",
        "cancel_url": reverse("kanview:calendario-lista"),
        **_nav("Calendario"),
    })


# ---- TareasPedido ---------------------------------------------------------

@login_required
def tarea_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.nombre, obj.estado, obj.fecha_inicio, obj.fecha_fin, obj.id_pedido]}
        for obj in TareasPedido.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Tareas",
        "columnas": ["Nombre", "Estado", "Inicio", "Fin", "Pedido"],
        "filas": filas,
        "crear_url": reverse("kanview:tarea-crear"),
        "editar_url": "kanview:tarea-editar",
        "eliminar_url": "kanview:tarea-eliminar",
        **_nav("Tareas"),
    })


@login_required
def tarea_crear(request):
    if request.method == "POST":
        form = TareasPedidoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tarea creada correctamente.")
            return redirect("kanview:tarea-lista")
    else:
        form = TareasPedidoForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nueva tarea",
        "cancel_url": reverse("kanview:tarea-lista"),
        **_nav("Tareas"),
    })


@login_required
def tarea_editar(request, pk):
    tarea = get_object_or_404(TareasPedido, pk=pk)
    if request.method == "POST":
        form = TareasPedidoForm(request.POST, instance=tarea)
        if form.is_valid():
            form.save()
            messages.success(request, "Tarea actualizada correctamente.")
            return redirect("kanview:tarea-lista")
    else:
        form = TareasPedidoForm(instance=tarea)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar tarea",
        "cancel_url": reverse("kanview:tarea-lista"),
        **_nav("Tareas"),
    })


@login_required
def tarea_eliminar(request, pk):
    tarea = get_object_or_404(TareasPedido, pk=pk)
    if request.method == "POST":
        tarea.delete()
        messages.success(request, "Tarea eliminada.")
        return redirect("kanview:tarea-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": tarea,
        "title": "Eliminar tarea",
        "cancel_url": reverse("kanview:tarea-lista"),
        **_nav("Tareas"),
    })


# ---- Actividades (Auditoría) ----------------------------------------------

@login_required
def actividad_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.nombre, obj.estado, obj.fecha_inicio, obj.fecha_fin, obj.id_tarea]}
        for obj in Actividades.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Actividades",
        "columnas": ["Nombre", "Estado", "Inicio", "Fin", "Tarea"],
        "filas": filas,
        "crear_url": reverse("kanview:actividad-crear"),
        "editar_url": "kanview:actividad-editar",
        "eliminar_url": "kanview:actividad-eliminar",
        **_nav("Auditoría"),
    })


@login_required
def actividad_crear(request):
    if request.method == "POST":
        form = ActividadesForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Actividad creada correctamente.")
            return redirect("kanview:actividad-lista")
    else:
        form = ActividadesForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nueva actividad",
        "cancel_url": reverse("kanview:actividad-lista"),
        **_nav("Auditoría"),
    })


@login_required
def actividad_editar(request, pk):
    actividad = get_object_or_404(Actividades, pk=pk)
    if request.method == "POST":
        form = ActividadesForm(request.POST, instance=actividad)
        if form.is_valid():
            form.save()
            messages.success(request, "Actividad actualizada correctamente.")
            return redirect("kanview:actividad-lista")
    else:
        form = ActividadesForm(instance=actividad)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar actividad",
        "cancel_url": reverse("kanview:actividad-lista"),
        **_nav("Auditoría"),
    })


@login_required
def actividad_eliminar(request, pk):
    actividad = get_object_or_404(Actividades, pk=pk)
    if request.method == "POST":
        actividad.delete()
        messages.success(request, "Actividad eliminada.")
        return redirect("kanview:actividad-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": actividad,
        "title": "Eliminar actividad",
        "cancel_url": reverse("kanview:actividad-lista"),
        **_nav("Auditoría"),
    })


# ---- Catalogo -------------------------------------------------------------

@login_required
def catalogo_crud_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.categorias, obj.id_inventario, obj.id_producto]}
        for obj in Catalogo.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Catálogo",
        "columnas": ["Categorías", "Inventario", "Producto"],
        "filas": filas,
        "crear_url": reverse("kanview:catalogo-crear"),
        "editar_url": "kanview:catalogo-editar",
        "eliminar_url": "kanview:catalogo-eliminar",
        **_nav("Catálogo"),
    })


@login_required
def catalogo_crear(request):
    if request.method == "POST":
        form = CatalogoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de catálogo creado correctamente.")
            return redirect("kanview:catalogo-lista")
    else:
        form = CatalogoForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo registro de catálogo",
        "cancel_url": reverse("kanview:catalogo-lista"),
        **_nav("Catálogo"),
    })


@login_required
def catalogo_editar(request, pk):
    registro = get_object_or_404(Catalogo, pk=pk)
    if request.method == "POST":
        form = CatalogoForm(request.POST, instance=registro)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de catálogo actualizado correctamente.")
            return redirect("kanview:catalogo-lista")
    else:
        form = CatalogoForm(instance=registro)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar registro de catálogo",
        "cancel_url": reverse("kanview:catalogo-lista"),
        **_nav("Catálogo"),
    })


@login_required
def catalogo_eliminar(request, pk):
    registro = get_object_or_404(Catalogo, pk=pk)
    if request.method == "POST":
        registro.delete()
        messages.success(request, "Registro de catálogo eliminado.")
        return redirect("kanview:catalogo-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": registro,
        "title": "Eliminar registro de catálogo",
        "cancel_url": reverse("kanview:catalogo-lista"),
        **_nav("Catálogo"),
    })


# ---- Historial ------------------------------------------------------------

@login_required
def historial_crud_lista(request):
    filas = [
        {"pk": obj.pk, "valores": [obj.hora_creacion, obj.fecha_creacion, obj.id_cliente, obj.id_empleado, obj.id_producto]}
        for obj in Historial.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", {
        "title": "Historial",
        "columnas": ["Hora", "Fecha", "Cliente", "Empleado", "Producto"],
        "filas": filas,
        "crear_url": reverse("kanview:historial-crear"),
        "editar_url": "kanview:historial-editar",
        "eliminar_url": "kanview:historial-eliminar",
        **_nav("Auditoría"),
    })


@login_required
def historial_crear(request):
    if request.method == "POST":
        form = HistorialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de historial creado correctamente.")
            return redirect("kanview:historial-lista")
    else:
        form = HistorialForm()
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo registro de historial",
        "cancel_url": reverse("kanview:historial-lista"),
        **_nav("Auditoría"),
    })


@login_required
def historial_editar(request, pk):
    registro = get_object_or_404(Historial, pk=pk)
    if request.method == "POST":
        form = HistorialForm(request.POST, instance=registro)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de historial actualizado correctamente.")
            return redirect("kanview:historial-lista")
    else:
        form = HistorialForm(instance=registro)
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar registro de historial",
        "cancel_url": reverse("kanview:historial-lista"),
        **_nav("Auditoría"),
    })


@login_required
def historial_eliminar(request, pk):
    registro = get_object_or_404(Historial, pk=pk)
    if request.method == "POST":
        registro.delete()
        messages.success(request, "Registro de historial eliminado.")
        return redirect("kanview:historial-lista")
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": registro,
        "title": "Eliminar registro de historial",
        "cancel_url": reverse("kanview:historial-lista"),
        **_nav("Auditoría"),
    })
