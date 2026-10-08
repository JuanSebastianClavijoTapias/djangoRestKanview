from django.urls import path
from . import views

from .views import (
    actividades_lista,
    actividad_detalle,
    administrador_detalle,
    administradores_lista,
    analisis_financiero_detalle,
    analisis_financieros_lista,
    calendario_detalle,
    calendario_lista,
    catalogo_detalle,
    catalogos_lista,
    cliente_detalle,
    clientes_lista,
    empleado_detalle,
    empleados_lista,
    historial_detalle,
    historial_lista,
    inventario_detalle,
    inventarios_lista,
    pedido_detalle,
    pedidos_lista,
    producto_detalle,
    productos_lista,
    tarea_pedido_detalle,
    tareas_pedido_lista,
)

urlpatterns = [
    path("clientes/", clientes_lista, name="clientes-lista"),
    path("clientes/<int:pk>/", cliente_detalle, name="cliente-detalle"),

    path("empleados/", empleados_lista, name="empleados-lista"),
    path("empleados/<int:pk>/", empleado_detalle, name="empleado-detalle"),

    path("administradores/", administradores_lista, name="administradores-lista"),
    path("administradores/<int:pk>/", administrador_detalle, name="administrador-detalle"),

    path("analisis-financieros/", analisis_financieros_lista, name="analisis-financieros-lista"),
    path("analisis-financieros/<int:pk>/", analisis_financiero_detalle, name="analisis-financiero-detalle"),

    path("productos/", productos_lista, name="productos-lista"),
    path("productos/<int:pk>/", producto_detalle, name="producto-detalle"),

    path("inventarios/", inventarios_lista, name="inventarios-lista"),
    path("inventarios/<int:pk>/", inventario_detalle, name="inventario-detalle"),

    path("catalogos/", catalogos_lista, name="catalogos-lista"),
    path("catalogos/<int:pk>/", catalogo_detalle, name="catalogo-detalle"),

    path("pedidos/", pedidos_lista, name="pedidos-lista"),
    path("pedidos/<int:pk>/", pedido_detalle, name="pedido-detalle"),

    path("tareas-pedido/", tareas_pedido_lista, name="tareas-pedido-lista"),
    path("tareas-pedido/<int:pk>/", tarea_pedido_detalle, name="tarea-pedido-detalle"),

    path("actividades/", actividades_lista, name="actividades-lista"),
    path("actividades/<int:pk>/", actividad_detalle, name="actividad-detalle"),

    path("historial/", historial_lista, name="historial-lista"),
    path("historial/<int:pk>/", historial_detalle, name="historial-detalle"),

    path("calendario/", calendario_lista, name="calendario-lista"),
    path("calendario/<int:pk>/", calendario_detalle, name="calendario-detalle"),

    path('recuperar_clave/', views.recuperar_clave, name="recuperar_clave"),
    path('verificar_token/', views.verificar_token, name="verificar_token"),
]

