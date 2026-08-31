from django import forms

from .models import Administrador, Cliente, Empleado, Pedido, Producto

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
