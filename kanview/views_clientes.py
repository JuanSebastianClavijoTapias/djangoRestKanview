"""Pantalla de Clientes (diseño Stitch) alimentada con datos reales.

El buscador del header filtra en el servidor con ``?q=`` por nombre, documento o
celular.
"""

from . import busqueda
from .models import Cliente
from .permisos import seccion_requerida
from .views_site import _render


@seccion_requerida("usuarios")
def clientes(request):
    """Lista de clientes vigentes (con el buscador del header ya aplicado)."""
    q = busqueda.texto(request)
    lista_clientes = busqueda.filtrar(
        Cliente.objects.filter(activo=True),
        q,
        ("nombre", "documento", "celular", "correo"),
    )
    return _render(
        request,
        "kanview/clientes.html",
        "Usuarios",
        clientes=lista_clientes,
        total_clientes=lista_clientes.count(),
        **busqueda.contexto(request, "Buscar clientes...", "clientes"),
    )
