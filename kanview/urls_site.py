from django.urls import path

from .views_crud import (
    actividad_crear,
    actividad_editar,
    actividad_eliminar,
    actividad_lista,
    administrador_crear,
    administrador_editar,
    administrador_eliminar,
    administrador_lista,
    calendario_crear,
    calendario_crud_lista,
    calendario_editar,
    calendario_eliminar,
    catalogo_crear,
    catalogo_crud_lista,
    catalogo_editar,
    catalogo_eliminar,
    cliente_crear,
    cliente_editar,
    cliente_eliminar,
    cliente_lista,
    empleado_crear,
    empleado_editar,
    empleado_eliminar,
    empleado_lista,
    historial_crear,
    historial_crud_lista,
    historial_editar,
    historial_eliminar,
    inventario_crear,
    inventario_editar,
    inventario_eliminar,
    inventario_lista,
    pedido_crear,
    pedido_editar,
    pedido_eliminar,
    pedido_lista,
    producto_crear,
    producto_editar,
    producto_eliminar,
    producto_lista,
    tarea_crear,
    tarea_editar,
    tarea_eliminar,
    tarea_lista,
)
from .views_site import (
    auditoria,
    calendario,
    catalogo,
    cerrar_sesion,
    clientes,
    dashboard,
    empleados,
    finanzas,
    iniciar_sesion,
    inventario,
    mensajeria,
    pedido_detalle,
    pedidos_tablero,
    recuperar_solicitar,
    recuperar_verificar,
    registrarse,
    tareas,
)

app_name = "kanview"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("login/", iniciar_sesion, name="login"),
    path("registro/", registrarse, name="registro"),
    path("logout/", cerrar_sesion, name="logout"),
    path("recuperar/", recuperar_solicitar, name="recuperar"),
    path("recuperar/verificar/", recuperar_verificar, name="recuperar-verificar"),

    # Diseño (pantallas Stitch, solo lectura)
    path("pedidos/", pedidos_tablero, name="pedidos-tablero"),
    path("pedidos/<int:pk>/", pedido_detalle, name="pedido-detalle"),
    path("tareas/", tareas, name="tareas"),
    path("calendario/", calendario, name="calendario"),
    path("inventario/", inventario, name="inventario"),
    path("finanzas/", finanzas, name="finanzas"),
    path("auditoria/", auditoria, name="auditoria"),
    path("mensajeria/", mensajeria, name="mensajeria"),
    path("clientes/", clientes, name="clientes"),
    path("empleados/", empleados, name="empleados"),
    path("catalogo/", catalogo, name="catalogo"),

    # CRUD: Clientes
    path("crud/clientes/", cliente_lista, name="cliente-lista"),
    path("crud/clientes/nuevo/", cliente_crear, name="cliente-crear"),
    path("crud/clientes/<int:pk>/editar/", cliente_editar, name="cliente-editar"),
    path("crud/clientes/<int:pk>/eliminar/", cliente_eliminar, name="cliente-eliminar"),

    # CRUD: Empleados
    path("crud/empleados/", empleado_lista, name="empleado-lista"),
    path("crud/empleados/nuevo/", empleado_crear, name="empleado-crear"),
    path("crud/empleados/<int:pk>/editar/", empleado_editar, name="empleado-editar"),
    path("crud/empleados/<int:pk>/eliminar/", empleado_eliminar, name="empleado-eliminar"),

    # CRUD: Administradores
    path("crud/administradores/", administrador_lista, name="administrador-lista"),
    path("crud/administradores/nuevo/", administrador_crear, name="administrador-crear"),
    path("crud/administradores/<int:pk>/editar/", administrador_editar, name="administrador-editar"),
    path("crud/administradores/<int:pk>/eliminar/", administrador_eliminar, name="administrador-eliminar"),

    # CRUD: Productos
    path("crud/productos/", producto_lista, name="producto-lista"),
    path("crud/productos/nuevo/", producto_crear, name="producto-crear"),
    path("crud/productos/<int:pk>/editar/", producto_editar, name="producto-editar"),
    path("crud/productos/<int:pk>/eliminar/", producto_eliminar, name="producto-eliminar"),

    # CRUD: Pedidos
    path("crud/pedidos/", pedido_lista, name="pedido-lista"),
    path("crud/pedidos/nuevo/", pedido_crear, name="pedido-crear"),
    path("crud/pedidos/<int:pk>/editar/", pedido_editar, name="pedido-editar"),
    path("crud/pedidos/<int:pk>/eliminar/", pedido_eliminar, name="pedido-eliminar"),

    # CRUD: Inventario
    path("crud/inventario/", inventario_lista, name="inventario-lista"),
    path("crud/inventario/nuevo/", inventario_crear, name="inventario-crear"),
    path("crud/inventario/<int:pk>/editar/", inventario_editar, name="inventario-editar"),
    path("crud/inventario/<int:pk>/eliminar/", inventario_eliminar, name="inventario-eliminar"),

    # CRUD: Calendario
    path("crud/calendario/", calendario_crud_lista, name="calendario-lista"),
    path("crud/calendario/nuevo/", calendario_crear, name="calendario-crear"),
    path("crud/calendario/<int:pk>/editar/", calendario_editar, name="calendario-editar"),
    path("crud/calendario/<int:pk>/eliminar/", calendario_eliminar, name="calendario-eliminar"),

    # CRUD: Tareas
    path("crud/tareas/", tarea_lista, name="tarea-lista"),
    path("crud/tareas/nuevo/", tarea_crear, name="tarea-crear"),
    path("crud/tareas/<int:pk>/editar/", tarea_editar, name="tarea-editar"),
    path("crud/tareas/<int:pk>/eliminar/", tarea_eliminar, name="tarea-eliminar"),

    # CRUD: Actividades (Auditoría)
    path("crud/actividades/", actividad_lista, name="actividad-lista"),
    path("crud/actividades/nuevo/", actividad_crear, name="actividad-crear"),
    path("crud/actividades/<int:pk>/editar/", actividad_editar, name="actividad-editar"),
    path("crud/actividades/<int:pk>/eliminar/", actividad_eliminar, name="actividad-eliminar"),

    # CRUD: Catálogo
    path("crud/catalogo/", catalogo_crud_lista, name="catalogo-lista"),
    path("crud/catalogo/nuevo/", catalogo_crear, name="catalogo-crear"),
    path("crud/catalogo/<int:pk>/editar/", catalogo_editar, name="catalogo-editar"),
    path("crud/catalogo/<int:pk>/eliminar/", catalogo_eliminar, name="catalogo-eliminar"),

    # CRUD: Historial
    path("crud/historial/", historial_crud_lista, name="historial-lista"),
    path("crud/historial/nuevo/", historial_crear, name="historial-crear"),
    path("crud/historial/<int:pk>/editar/", historial_editar, name="historial-editar"),
    path("crud/historial/<int:pk>/eliminar/", historial_eliminar, name="historial-eliminar"),
]
