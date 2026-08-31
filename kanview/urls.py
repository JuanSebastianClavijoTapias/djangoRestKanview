from rest_framework.routers import DefaultRouter

from .views import (
    ActividadesViewSet,
    AdministradorViewSet,
    AnalisisFinancieroViewSet,
    CalendarioViewSet,
    CatalogoViewSet,
    ClienteViewSet,
    EmpleadoViewSet,
    HistorialViewSet,
    InventarioViewSet,
    PedidoViewSet,
    ProductoViewSet,
    TareasPedidoViewSet,
)

router = DefaultRouter()
router.register(r"clientes", ClienteViewSet)
router.register(r"empleados", EmpleadoViewSet)
router.register(r"administradores", AdministradorViewSet)
router.register(r"analisis-financieros", AnalisisFinancieroViewSet)
router.register(r"productos", ProductoViewSet)
router.register(r"inventarios", InventarioViewSet)
router.register(r"catalogos", CatalogoViewSet)
router.register(r"pedidos", PedidoViewSet)
router.register(r"tareas-pedido", TareasPedidoViewSet)
router.register(r"actividades", ActividadesViewSet)
router.register(r"historial", HistorialViewSet)
router.register(r"calendario", CalendarioViewSet)

urlpatterns = router.urls
