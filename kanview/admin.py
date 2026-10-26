from django.contrib import admin

from .models import (
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Cliente,
    Conversacion,
    Empleado,
    EvidenciaPedido,
    Factura,
    Historial,
    Mensaje,
    Notificacion,
    Pedido,
    PerfilUsuario,
    Producto,
    RegistroAuditoria,
    SolicitudModificacionPedido,
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

admin.site.register(Notificacion)
admin.site.register(SolicitudModificacionPedido)
admin.site.register(Factura)
admin.site.register(PerfilUsuario)
admin.site.register(RegistroAuditoria)
admin.site.register(Conversacion)
admin.site.register(Mensaje)
