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

WIDGET_ATTRS = {
    "class": (
        "w-full bg-white border border-gray-300 rounded-xl px-4 py-2.5 text-sm "
        "focus:ring-2 focus:ring-[#008080]/30 focus:border-[#008080] outline-none transition-all"
    )
}


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " " + WIDGET_ATTRS["class"]).strip()
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 3)


class ClienteForm(StyledModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "documento", "celular", "direccion", "fecha_nacimiento", "edad"]
        widgets = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class EmpleadoForm(StyledModelForm):
    class Meta:
        model = Empleado
        fields = [
            "nombre", "documento", "cargo", "celular", "direccion",
            "salario", "edad", "fecha_nacimiento", "tareas_realizadas",
        ]
        widgets = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class AdministradorForm(StyledModelForm):
    class Meta:
        model = Administrador
        fields = ["nombre", "documento", "celular"]


class ProductoForm(StyledModelForm):
    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "codigo_producto", "cantidad", "precio", "descripcion"]


class PedidoForm(StyledModelForm):
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


class InventarioForm(StyledModelForm):
    class Meta:
        model = Inventario
        fields = ["cantidad", "id_producto"]


class CalendarioForm(StyledModelForm):
    class Meta:
        model = Calendario
        fields = ["fecha", "anio", "mes", "nombre_mes", "dia", "nombre_dia", "id_pedido"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class TareasPedidoForm(StyledModelForm):
    class Meta:
        model = TareasPedido
        fields = ["nombre", "descripcion", "fecha_inicio", "fecha_fin", "estado", "id_pedido"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class ActividadesForm(StyledModelForm):
    class Meta:
        model = Actividades
        fields = ["nombre", "descripcion", "fecha_inicio", "fecha_fin", "estado", "id_tarea"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class CatalogoForm(StyledModelForm):
    class Meta:
        model = Catalogo
        fields = ["categorias", "id_inventario", "id_producto"]


class HistorialForm(StyledModelForm):
    class Meta:
        model = Historial
        fields = ["hora_creacion", "fecha_creacion", "id_cliente", "id_empleado", "id_producto"]
        widgets = {
            "hora_creacion": forms.TimeInput(attrs={"type": "time"}),
            "fecha_creacion": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
