from django.urls import path

from .views_crud import (
    AdministradorCreateView,
    AdministradorDeleteView,
    AdministradorListView,
    AdministradorUpdateView,
    ClienteCreateView,
    ClienteDeleteView,
    ClienteListView,
    ClienteUpdateView,
    DashboardView,
    EmpleadoCreateView,
    EmpleadoDeleteView,
    EmpleadoListView,
    EmpleadoUpdateView,
    PedidoCreateView,
    PedidoDeleteView,
    PedidoListView,
    PedidoUpdateView,
    ProductoCreateView,
    ProductoDeleteView,
    ProductoListView,
    ProductoUpdateView,
)
from .views_site import (
    AuditoriaView,
    CalendarioView,
    CatalogoView,
    ClientesView,
    EmpleadosView,
    FinanzasView,
    InventarioView,
    KanviewLoginView,
    KanviewLogoutView,
    MensajeriaView,
    PedidoDetalleView,
    PedidosTableroView,
    TareasView,
)

app_name = "kanview"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", KanviewLoginView.as_view(), name="login"),
    path("logout/", KanviewLogoutView.as_view(), name="logout"),

    # Diseño (pantallas Stitch, solo lectura)
    path("pedidos/", PedidosTableroView.as_view(), name="pedidos-tablero"),
    path("pedidos/<int:pk>/", PedidoDetalleView.as_view(), name="pedido-detalle"),
    path("tareas/", TareasView.as_view(), name="tareas"),
    path("calendario/", CalendarioView.as_view(), name="calendario"),
    path("inventario/", InventarioView.as_view(), name="inventario"),
    path("finanzas/", FinanzasView.as_view(), name="finanzas"),
    path("auditoria/", AuditoriaView.as_view(), name="auditoria"),
    path("mensajeria/", MensajeriaView.as_view(), name="mensajeria"),
    path("clientes/", ClientesView.as_view(), name="clientes"),
    path("empleados/", EmpleadosView.as_view(), name="empleados"),
    path("catalogo/", CatalogoView.as_view(), name="catalogo"),

    # CRUD: Clientes
    path("crud/clientes/", ClienteListView.as_view(), name="cliente-lista"),
    path("crud/clientes/nuevo/", ClienteCreateView.as_view(), name="cliente-crear"),
    path("crud/clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="cliente-editar"),
    path("crud/clientes/<int:pk>/eliminar/", ClienteDeleteView.as_view(), name="cliente-eliminar"),

    # CRUD: Empleados
    path("crud/empleados/", EmpleadoListView.as_view(), name="empleado-lista"),
    path("crud/empleados/nuevo/", EmpleadoCreateView.as_view(), name="empleado-crear"),
    path("crud/empleados/<int:pk>/editar/", EmpleadoUpdateView.as_view(), name="empleado-editar"),
    path("crud/empleados/<int:pk>/eliminar/", EmpleadoDeleteView.as_view(), name="empleado-eliminar"),

    # CRUD: Administradores
    path("crud/administradores/", AdministradorListView.as_view(), name="administrador-lista"),
    path("crud/administradores/nuevo/", AdministradorCreateView.as_view(), name="administrador-crear"),
    path("crud/administradores/<int:pk>/editar/", AdministradorUpdateView.as_view(), name="administrador-editar"),
    path("crud/administradores/<int:pk>/eliminar/", AdministradorDeleteView.as_view(), name="administrador-eliminar"),

    # CRUD: Productos
    path("crud/productos/", ProductoListView.as_view(), name="producto-lista"),
    path("crud/productos/nuevo/", ProductoCreateView.as_view(), name="producto-crear"),
    path("crud/productos/<int:pk>/editar/", ProductoUpdateView.as_view(), name="producto-editar"),
    path("crud/productos/<int:pk>/eliminar/", ProductoDeleteView.as_view(), name="producto-eliminar"),

    # CRUD: Pedidos
    path("crud/pedidos/", PedidoListView.as_view(), name="pedido-lista"),
    path("crud/pedidos/nuevo/", PedidoCreateView.as_view(), name="pedido-crear"),
    path("crud/pedidos/<int:pk>/editar/", PedidoUpdateView.as_view(), name="pedido-editar"),
    path("crud/pedidos/<int:pk>/eliminar/", PedidoDeleteView.as_view(), name="pedido-eliminar"),
]
