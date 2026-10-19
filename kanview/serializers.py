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


class TareasPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TareasPedido
        fields = "__all__"


class ActividadesSerializer(serializers.ModelSerializer):
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
