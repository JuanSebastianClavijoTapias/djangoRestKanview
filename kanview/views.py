from random import randint

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

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
from .permisos import es_solo_cliente, puede
from .serializers import (
    ActividadesSerializer,
    AdministradorSerializer,
    AnalisisFinancieroSerializer,
    CalendarioSerializer,
    ClienteSerializer,
    EmpleadoSerializer,
    HistorialSerializer,
    PedidoSerializer,
    ProductoSerializer,
    TareasPedidoSerializer,
)


# ---------------------------------------------------------------------------
# Permisos de la API
#
# Antes bastaba con estar autenticado para leer y escribir TODO (incluido
# DELETE). Ahora cada recurso exige el mismo permiso por sección que la
# interfaz: la lectura usa la sección de consulta y la escritura (POST/PUT/
# PATCH/DELETE) la sección de gestión, que el rol Cliente no tiene.
# ---------------------------------------------------------------------------


class _PermisoSeccion(BasePermission):
    """Permiso DRF que resuelve el acceso con ``puede(usuario, seccion)``."""

    lectura = None
    escritura = None

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        seccion = self.escritura if request.method in ("POST", "PUT", "PATCH", "DELETE") else self.lectura
        return puede(request.user, seccion)


def permiso_de(lectura, escritura=None):
    """Crea la clase de permiso de un recurso: lectura / escritura."""
    nombre = "Permiso" + lectura.replace("-", " ").title().replace(" ", "")
    return type(nombre, (_PermisoSeccion,), {"lectura": lectura, "escritura": escritura or lectura})


def _desactivar(objeto):
    """DELETE de la API = desactivar: en este sistema nada se borra.

    Si un registro protegido impidiera la operación se responde 409 con un
    mensaje en español en vez de reventar con un error 500.
    """
    try:
        objeto.activo = False
        objeto.save(update_fields=["activo"])
    except ProtectedError:
        return Response(
            {"detalle": "No se puede desactivar: otros registros dependen de este."},
            status=status.HTTP_409_CONFLICT,
        )
    return Response({"detalle": "Registro desactivado. No se borró: puedes reactivarlo."})


# ---------------------------------------------------------------------------
# Cada modelo tiene dos vistas:
#   - lista:  GET (listar) y POST (crear)
#   - detalle: GET (ver uno), PUT (actualizar) y DELETE (desactivar)
# ---------------------------------------------------------------------------


# ---- Cliente --------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("usuarios")])
def clientes_lista(request):
    if request.method == "GET":
        clientes = Cliente.objects.all()
        serializer = ClienteSerializer(clientes, many=True)
        return Response(serializer.data)

    serializer = ClienteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("usuarios")])
def cliente_detalle(request, pk):
    try:
        cliente = Cliente.objects.get(pk=pk)
    except Cliente.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ClienteSerializer(cliente)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = ClienteSerializer(cliente, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(cliente)


# ---- Empleado -------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("usuarios")])
def empleados_lista(request):
    if request.method == "GET":
        empleados = Empleado.objects.all()
        serializer = EmpleadoSerializer(empleados, many=True)
        return Response(serializer.data)

    serializer = EmpleadoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("usuarios")])
def empleado_detalle(request, pk):
    try:
        empleado = Empleado.objects.get(pk=pk)
    except Empleado.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = EmpleadoSerializer(empleado)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = EmpleadoSerializer(empleado, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(empleado)


# ---- Administrador --------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("usuarios")])
def administradores_lista(request):
    if request.method == "GET":
        administradores = Administrador.objects.all()
        serializer = AdministradorSerializer(administradores, many=True)
        return Response(serializer.data)

    serializer = AdministradorSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("usuarios")])
def administrador_detalle(request, pk):
    try:
        administrador = Administrador.objects.get(pk=pk)
    except Administrador.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = AdministradorSerializer(administrador)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = AdministradorSerializer(administrador, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(administrador)


# ---- AnalisisFinanciero ---------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("finanzas")])
def analisis_financieros_lista(request):
    if request.method == "GET":
        analisis = AnalisisFinanciero.objects.all()
        serializer = AnalisisFinancieroSerializer(analisis, many=True)
        return Response(serializer.data)

    serializer = AnalisisFinancieroSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("finanzas")])
def analisis_financiero_detalle(request, pk):
    try:
        analisis = AnalisisFinanciero.objects.get(pk=pk)
    except AnalisisFinanciero.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = AnalisisFinancieroSerializer(analisis)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = AnalisisFinancieroSerializer(analisis, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(analisis)


# ---- Producto -------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("catalogo", "gestion-catalogo")])
def productos_lista(request):
    if request.method == "GET":
        productos = Producto.objects.all()
        serializer = ProductoSerializer(productos, many=True)
        return Response(serializer.data)

    serializer = ProductoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("gestion-catalogo")])
def producto_detalle(request, pk):
    try:
        producto = Producto.objects.get(pk=pk)
    except Producto.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProductoSerializer(producto)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = ProductoSerializer(producto, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(producto)


# ---- Pedido ---------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("pedidos", "gestion-pedidos")])
def pedidos_lista(request):
    if request.method == "GET":
        pedidos = Pedido.objects.all()
        # El rol Cliente solo ve sus propios pedidos.
        if es_solo_cliente(request.user):
            pedidos = pedidos.filter(id_cliente__correo__iexact=request.user.email)
        serializer = PedidoSerializer(pedidos, many=True)
        return Response(serializer.data)

    serializer = PedidoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("pedidos", "gestion-pedidos")])
def pedido_detalle(request, pk):
    try:
        pedido = Pedido.objects.get(pk=pk)
    except Pedido.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if es_solo_cliente(request.user) and (pedido.id_cliente.correo or "").lower() != (request.user.email or "").lower():
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = PedidoSerializer(pedido, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(pedido)


# ---- TareasPedido ---------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("tareas")])
def tareas_pedido_lista(request):
    if request.method == "GET":
        tareas = TareasPedido.objects.all()
        serializer = TareasPedidoSerializer(tareas, many=True)
        return Response(serializer.data)

    serializer = TareasPedidoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("tareas")])
def tarea_pedido_detalle(request, pk):
    try:
        tarea = TareasPedido.objects.get(pk=pk)
    except TareasPedido.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = TareasPedidoSerializer(tarea)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = TareasPedidoSerializer(tarea, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(tarea)


# ---- Actividades ----------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("auditoria")])
def actividades_lista(request):
    if request.method == "GET":
        actividades = Actividades.objects.all()
        serializer = ActividadesSerializer(actividades, many=True)
        return Response(serializer.data)

    serializer = ActividadesSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("auditoria")])
def actividad_detalle(request, pk):
    try:
        actividad = Actividades.objects.get(pk=pk)
    except Actividades.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ActividadesSerializer(actividad)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = ActividadesSerializer(actividad, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(actividad)


# ---- Historial ------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("auditoria")])
def historial_lista(request):
    if request.method == "GET":
        historial = Historial.objects.all()
        serializer = HistorialSerializer(historial, many=True)
        return Response(serializer.data)

    serializer = HistorialSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("auditoria")])
def historial_detalle(request, pk):
    try:
        registro = Historial.objects.get(pk=pk)
    except Historial.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = HistorialSerializer(registro)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = HistorialSerializer(registro, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(registro)


# ---- Calendario -----------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([permiso_de("calendario")])
def calendario_lista(request):
    if request.method == "GET":
        eventos = Calendario.objects.all()
        serializer = CalendarioSerializer(eventos, many=True)
        return Response(serializer.data)

    serializer = CalendarioSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permiso_de("calendario")])
def calendario_detalle(request, pk):
    try:
        evento = Calendario.objects.get(pk=pk)
    except Calendario.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = CalendarioSerializer(evento)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = CalendarioSerializer(evento, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return _desactivar(evento)


def recuperar_clave(request):
    """Endpoint API /api/recuperar_clave/: genera token para Cliente y lo envía."""
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip()
        if not correo:
            return HttpResponse("Ingresa tu correo.", status=400)
        try:
            cliente = Cliente.objects.get(correo=correo)
        except Cliente.DoesNotExist:
            # No revelar si existe o no (misma respuesta genérica).
            return HttpResponse("Si el correo existe, revisa tu bandeja para recuperar...!")
        token = f"{randint(100000, 999999):06d}"
        cliente.token = token
        cliente.url_valida = True
        cliente.save(update_fields=["token", "url_valida"])
        try:
            send_mail(
                "Kanview - Código de recuperación",
                f"Hola {cliente.nombre},\n\nTu código de recuperación es: {token}",
                settings.DEFAULT_FROM_EMAIL,
                [correo],
                fail_silently=False,
            )
        except Exception:
            pass
        return HttpResponse("Revise su correo para recuperar...!")

    return render(request, "kanview/recuperar.html", {"correo": ""})

def verificar_token(request):
    """GET ?correo=: muestra el form si url_valida=True. POST: consume el token (single-use)."""
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip()
        token = (request.POST.get("token") or "").strip()
        if not correo or not token:
            return HttpResponse("Ingresa correo y código de 6 dígitos.", status=400)
        try:
            cliente = Cliente.objects.get(correo=correo, token=token, url_valida=True)
        except Cliente.DoesNotExist:
            return HttpResponse("Código incorrecto o URL no válida!", status=400)
        cliente.url_valida = False
        cliente.save(update_fields=["url_valida"])
        return HttpResponse(f"Código verificado. Hola {cliente.nombre}, ya puedes iniciar sesión.")

    correo = request.GET.get("correo")
    if not correo:
        return HttpResponse("Falta el correo.", status=400)
    try:
        cliente = Cliente.objects.get(correo=correo)
    except Cliente.DoesNotExist:
        return HttpResponse("URL no válida!")
    if not cliente.url_valida:
        return HttpResponse("URL no válida!")
    return render(request, "kanview/recuperar_verificar.html", {"correo": correo})