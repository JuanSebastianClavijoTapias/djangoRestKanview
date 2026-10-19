from django.contrib import admin

from .models import (
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Cliente,
    Empleado,
    EvidenciaPedido,
    Historial,
    Pedido,
    Producto,
    TareasPedido,
)

admin.site.register(Cliente)
admin.site.register(Empleado)
admin.site.register(Administrador)
admin.site.register(AnalisisFinanciero)
admin.site.register(Producto)
admin.site.register(Pedido)
admin.site.register(EvidenciaPedido)
admin.site.register(TareasPedido)
admin.site.register(Actividades)
admin.site.register(Historial)
admin.site.register(Calendario)
