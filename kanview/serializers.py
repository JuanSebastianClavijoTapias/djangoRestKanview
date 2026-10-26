from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Cliente,
    Empleado,
    Historial,
    Pedido,
    Producto,
    TareasPedido,
)


class ValidacionDeModeloMixin:
    """Reutiliza ``Model.clean()`` para no duplicar reglas de negocio en la API."""

    def validate(self, attrs):
        datos = super().validate(attrs)
        objeto = self.instance or self.Meta.model()
        campos = {campo.name for campo in objeto._meta.concrete_fields}
        for campo, valor in datos.items():
            if campo in campos:
                setattr(objeto, campo, valor)
        try:
            objeto.clean()
        except DjangoValidationError as exc:
            errores = getattr(exc, "message_dict", None)
            if errores is None:
                errores = {"__all__": list(getattr(exc, "messages", [str(exc)]))}
            raise serializers.ValidationError(errores)
        return datos


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"


class EmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empleado
        fields = "__all__"


class AdministradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrador
        fields = "__all__"


class AnalisisFinancieroSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalisisFinanciero
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"


class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = "__all__"


class TareasPedidoSerializer(ValidacionDeModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = TareasPedido
        fields = "__all__"


class ActividadesSerializer(ValidacionDeModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = Actividades
        fields = "__all__"


class HistorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Historial
        fields = "__all__"


class CalendarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendario
        fields = "__all__"
