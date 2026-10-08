from django import forms

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


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "documento", "celular", "direccion", "fecha_nacimiento", "edad", "correo"]
        widgets = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            "nombre", "documento", "cargo", "celular", "direccion",
            "salario", "edad", "fecha_nacimiento", "tareas_realizadas",
        ]
        widgets = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class AdministradorForm(forms.ModelForm):
    class Meta:
        model = Administrador
        fields = ["nombre", "documento", "celular"]


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "codigo_producto", "cantidad", "precio", "descripcion"]


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "codigo_pedido", "estado", "id_cliente", "id_empleado", "id_producto",
            "fecha_creacion", "hora_creacion", "descripcion", "evidencias",
        ]
        widgets = {
            "fecha_creacion": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora_creacion": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }


class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ["cantidad", "id_producto"]


class CalendarioForm(forms.ModelForm):
    class Meta:
        model = Calendario
        fields = ["fecha", "anio", "mes", "nombre_mes", "dia", "nombre_dia", "id_pedido"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class TareasPedidoForm(forms.ModelForm):
    class Meta:
        model = TareasPedido
        fields = ["nombre", "descripcion", "fecha_inicio", "fecha_fin", "estado", "id_pedido"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class ActividadesForm(forms.ModelForm):
    class Meta:
        model = Actividades
        fields = ["nombre", "descripcion", "fecha_inicio", "fecha_fin", "estado", "id_tarea"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class CatalogoForm(forms.ModelForm):
    class Meta:
        model = Catalogo
        fields = ["categorias", "id_inventario", "id_producto"]


class HistorialForm(forms.ModelForm):
    class Meta:
        model = Historial
        fields = ["hora_creacion", "fecha_creacion", "id_cliente", "id_empleado", "id_producto"]
        widgets = {
            "hora_creacion": forms.TimeInput(attrs={"type": "time"}),
            "fecha_creacion": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
