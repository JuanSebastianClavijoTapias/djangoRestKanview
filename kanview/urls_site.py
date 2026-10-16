from django.urls import path

from . import (
    views_auditoria,
    views_calendario,
    views_catalogo,
    views_clientes,
    views_crud,
    views_empleados,
    views_finanzas,
    views_inventario,
    views_pedidos,
    views_site,
    views_tareas,
)

app_name = "kanview"

urlpatterns = [
    path("", views_site.dashboard, name="dashboard"),
    path("login/", views_site.login_view, name="login"),
    path("logout/", views_site.logout_view, name="logout"),

    # Pantallas de diseño (Stitch) conectadas a datos reales
    path("pedidos/", views_pedidos.pedidos_tablero, name="pedidos-tablero"),
    path("pedidos/<int:pk>/", views_pedidos.pedido_detalle, name="pedido-detalle"),
    path("tareas/", views_tareas.tareas, name="tareas"),
    path("calendario/", views_calendario.calendario, name="calendario"),
    path("inventario/", views_inventario.inventario, name="inventario"),
    path("finanzas/", views_finanzas.finanzas, name="finanzas"),
    path("auditoria/", views_auditoria.auditoria, name="auditoria"),
    path("mensajeria/", views_site.mensajeria, name="mensajeria"),
    path("clientes/", views_clientes.clientes, name="clientes"),
    path("empleados/", views_empleados.empleados, name="empleados"),
    path("catalogo/", views_catalogo.catalogo, name="catalogo"),

    # CRUD: Clientes
    path("crud/clientes/", views_crud.cliente_lista, name="cliente-lista"),
    path("crud/clientes/nuevo/", views_crud.cliente_crear, name="cliente-crear"),
    path("crud/clientes/<int:pk>/editar/", views_crud.cliente_editar, name="cliente-editar"),
    path("crud/clientes/<int:pk>/eliminar/", views_crud.cliente_eliminar, name="cliente-eliminar"),

    # CRUD: Empleados
    path("crud/empleados/", views_crud.empleado_lista, name="empleado-lista"),
    path("crud/empleados/nuevo/", views_crud.empleado_crear, name="empleado-crear"),
    path("crud/empleados/<int:pk>/editar/", views_crud.empleado_editar, name="empleado-editar"),
    path("crud/empleados/<int:pk>/eliminar/", views_crud.empleado_eliminar, name="empleado-eliminar"),

    # CRUD: Administradores
    path("crud/administradores/", views_crud.administrador_lista, name="administrador-lista"),
    path("crud/administradores/nuevo/", views_crud.administrador_crear, name="administrador-crear"),
    path("crud/administradores/<int:pk>/editar/", views_crud.administrador_editar, name="administrador-editar"),
    path("crud/administradores/<int:pk>/eliminar/", views_crud.administrador_eliminar, name="administrador-eliminar"),

    # CRUD: Productos
    path("crud/productos/", views_crud.producto_lista, name="producto-lista"),
    path("crud/productos/nuevo/", views_crud.producto_crear, name="producto-crear"),
    path("crud/productos/<int:pk>/editar/", views_crud.producto_editar, name="producto-editar"),
    path("crud/productos/<int:pk>/eliminar/", views_crud.producto_eliminar, name="producto-eliminar"),

    # CRUD: Pedidos
    path("crud/pedidos/", views_crud.pedido_lista, name="pedido-lista"),
    path("crud/pedidos/nuevo/", views_crud.pedido_crear, name="pedido-crear"),
    path("crud/pedidos/<int:pk>/editar/", views_crud.pedido_editar, name="pedido-editar"),
    path("crud/pedidos/<int:pk>/eliminar/", views_crud.pedido_eliminar, name="pedido-eliminar"),

    # CRUD: Análisis financiero
    path("crud/analisis-financieros/", views_crud.analisis_financiero_lista, name="analisis-financiero-lista"),
    path("crud/analisis-financieros/nuevo/", views_crud.analisis_financiero_crear, name="analisis-financiero-crear"),
    path("crud/analisis-financieros/<int:pk>/editar/", views_crud.analisis_financiero_editar, name="analisis-financiero-editar"),
    path("crud/analisis-financieros/<int:pk>/eliminar/", views_crud.analisis_financiero_eliminar, name="analisis-financiero-eliminar"),

    # CRUD: Inventario
    path("crud/inventarios/", views_crud.inventario_lista, name="inventario-lista"),
    path("crud/inventarios/nuevo/", views_crud.inventario_crear, name="inventario-crear"),
    path("crud/inventarios/<int:pk>/editar/", views_crud.inventario_editar, name="inventario-editar"),
    path("crud/inventarios/<int:pk>/eliminar/", views_crud.inventario_eliminar, name="inventario-eliminar"),

    # CRUD: Catálogo
    path("crud/catalogos/", views_crud.catalogo_lista, name="catalogo-lista"),
    path("crud/catalogos/nuevo/", views_crud.catalogo_crear, name="catalogo-crear"),
    path("crud/catalogos/<int:pk>/editar/", views_crud.catalogo_editar, name="catalogo-editar"),
    path("crud/catalogos/<int:pk>/eliminar/", views_crud.catalogo_eliminar, name="catalogo-eliminar"),

    # CRUD: Tareas de pedido
    path("crud/tareas/", views_crud.tarea_lista, name="tarea-lista"),
    path("crud/tareas/nuevo/", views_crud.tarea_crear, name="tarea-crear"),
    path("crud/tareas/<int:pk>/editar/", views_crud.tarea_editar, name="tarea-editar"),
    path("crud/tareas/<int:pk>/eliminar/", views_crud.tarea_eliminar, name="tarea-eliminar"),

    # CRUD: Actividades
    path("crud/actividades/", views_crud.actividad_lista, name="actividad-lista"),
    path("crud/actividades/nuevo/", views_crud.actividad_crear, name="actividad-crear"),
    path("crud/actividades/<int:pk>/editar/", views_crud.actividad_editar, name="actividad-editar"),
    path("crud/actividades/<int:pk>/eliminar/", views_crud.actividad_eliminar, name="actividad-eliminar"),

    # CRUD: Historial
    path("crud/historial/", views_crud.historial_lista, name="historial-lista"),
    path("crud/historial/nuevo/", views_crud.historial_crear, name="historial-crear"),
    path("crud/historial/<int:pk>/editar/", views_crud.historial_editar, name="historial-editar"),
    path("crud/historial/<int:pk>/eliminar/", views_crud.historial_eliminar, name="historial-eliminar"),

    # CRUD: Calendario
    path("crud/calendario/", views_crud.calendario_lista, name="calendario-lista"),
    path("crud/calendario/nuevo/", views_crud.calendario_crear, name="calendario-crear"),
    path("crud/calendario/<int:pk>/editar/", views_crud.calendario_editar, name="calendario-editar"),
    path("crud/calendario/<int:pk>/eliminar/", views_crud.calendario_eliminar, name="calendario-eliminar"),
]
