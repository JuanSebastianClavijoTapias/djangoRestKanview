from django.contrib.auth.decorators import login_required

from .models import Cliente
from .views_site import _render


@login_required
def clientes(request):
    """Pantalla de Clientes (diseño Stitch) alimentada con datos reales."""
    lista_clientes = Cliente.objects.all()
    return _render(
        request,
        "kanview/clientes.html",
        "Users",
        clientes=lista_clientes,
        total_clientes=lista_clientes.count(),
    )
