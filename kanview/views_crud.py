"""CRUD de los módulos de Kanview, en FBV.

Reglas del proyecto que aplican aquí:

- Nada se borra: ``<mod>-eliminar`` pide confirmación (GET) y al confirmar pone
  ``activo = False`` (POST); ``<mod>-reactivar`` lo vuelve a poner en ``True``.
- Cada vista está protegida con ``@seccion_requerida(...)`` según el módulo.
- **No hay ``forms.py``**: los formularios se construyen aquí con
  ``modelform_factory`` (helper ``_form``) y cada módulo tiene su ``_form_<mod>``
  con los campos y widgets que le corresponden. Los campos que no deben verse
  (edad del cliente, código y fechas del pedido, evidencias) se quitan en la
  vista con ``form.fields.pop(...)``, y las validaciones extra se añaden con
  ``form.add_error(...)``.
- ``Producto`` es la única fuente de verdad del stock (``cantidad``) y de la
  categoría: no hay tablas de Inventario ni de Catálogo.
- Pedido: código ``PED-0001`` automático, fecha y hora automáticas, fecha límite
  de entrega y galería de imágenes/videos (``EvidenciaPedido``).
- La fecha fin de tareas y actividades no puede superar la fecha límite del pedido.
"""

import os

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .formato import CAMPOS_MONEDA, moneda_cop, normalizar_monto, normalizar_montos
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
from . import busqueda, historial
from .auditoria import registrar as registrar_auditoria
from .notificaciones import notificar_area, notificar_cliente, notificar_staff
from .permisos import ROL_CLIENTE, ROL_TRABAJADOR, SECCION_ESCRITURA, asignar_rol, es_solo_cliente, seccion_requerida
from .views_site import _nav

# ---- Helpers comunes ------------------------------------------------------

#: Secciones de escritura de los CRUD que también son de lectura para el Cliente.
SECCIONES_GESTION = {
    "pedido": SECCION_ESCRITURA["pedidos"],
    "producto": SECCION_ESCRITURA["catalogo"],
    "catalogo": SECCION_ESCRITURA["catalogo"],
}

#: Validación de los archivos que se adjuntan a un pedido.
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPES_IMAGEN = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
EXTENSIONES_VIDEO = {".mp4", ".webm", ".mov", ".m4v"}
CONTENT_TYPES_VIDEO = {"video/mp4", "video/webm", "video/quicktime", "video/x-m4v"}
MAX_IMAGENES = 5
MAX_BYTES_IMAGEN = 5 * 1024 * 1024
MAX_BYTES_VIDEO = settings.MAX_VIDEO_BYTES
MAX_BYTES_MULTIMEDIA = settings.MAX_BYTES_MULTIMEDIA


def _contexto_lista(request, nombre, titulo, columnas, filas, activo, crear=True):
    """Contexto estándar de `kanview/crud/list.html` para un módulo.

    Si el rol del usuario no puede gestionar el módulo (el Cliente solo tiene
    lectura de pedidos y catálogo), las acciones de escritura se ocultan.
    """
    seccion_gestion = SECCIONES_GESTION.get(nombre)
    puede_gestionar = seccion_gestion is None or _puede_gestionar(request, seccion_gestion)

    # El buscador del header también funciona en las 12 listas del CRUD: se
    # filtra sobre los valores que ya trae cada fila (sin consultas extra).
    q = busqueda.texto(request)
    if q:
        filas = [
            fila for fila in filas
            if busqueda.coincide(q, *[str(valor) for valor in fila["valores"]])
        ]

    return {
        "title": titulo,
        "columnas": columnas,
        "filas": filas,
        "crear_url": reverse(f"kanview:{nombre}-crear") if (crear and puede_gestionar) else None,
        "editar_url": f"kanview:{nombre}-editar" if puede_gestionar else None,
        "eliminar_url": f"kanview:{nombre}-eliminar" if puede_gestionar else None,
        "reactivar_url": f"kanview:{nombre}-reactivar" if puede_gestionar else None,
        **busqueda.contexto(request, f"Buscar en {titulo.lower()}...", titulo.lower()),
        **_nav(activo, request),
    }


def _puede_gestionar(request, seccion):
    """¿El usuario puede escribir en este módulo?"""
    from .permisos import puede

    return puede(request.user, seccion)


def _etiquetas_en_espanol(form):
    """Cambia el «- Select an option -» de los selects de FK por español.

    El texto del ``empty_label`` lo pone el formulario construido en la vista:
    aquí se reemplaza, para todos los selects de clave foránea del sistema.
    """
    for campo in form.fields.values():
        if isinstance(campo, forms.ModelChoiceField):
            campo.empty_label = "Selecciona una opción"
    return form


def _montos_como_texto(form):
    """Deja los campos de dinero como texto (no ``type="number"``).

    Hace falta para que el navegador pueda mostrar los puntos de miles
    (``250.000``): un ``input type=number`` descarta un valor así. El número
    limpio para guardar lo arma el JavaScript de ``crud/form.html`` y, si el
    navegador no ejecuta JavaScript, lo normaliza la vista
    (``kanview.formato.normalizar_montos``).
    """
    for nombre in CAMPOS_MONEDA:
        campo = form.fields.get(nombre)
        if campo is None:
            continue
        campo.widget = forms.TextInput(
            attrs={"inputmode": "decimal", "autocomplete": "off"}
        )
    return form


# ---- Formularios (se construyen aquí; no hay kanview/forms.py) --------------
#
# Un helper por modelo con los mismos campos y widgets que tenía el antiguo
# forms.py. ``_form`` es el constructor puro con ``modelform_factory`` y
# ``_form_vista`` añade lo que depende de la petición: dinero normalizado,
# etiquetas en español, montos como texto y archivos.

CAMPOS_CLIENTE = (
    "nombre", "documento", "celular", "direccion", "fecha_nacimiento", "correo",
)
WIDGETS_CLIENTE = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

CAMPOS_EMPLEADO = (
    "nombre", "documento", "cargo", "celular", "direccion",
    "salario", "fecha_nacimiento", "tareas_realizadas", "correo",
)
WIDGETS_EMPLEADO = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

CAMPOS_ADMINISTRADOR = ("nombre", "documento", "celular")

CAMPOS_PRODUCTO = ("nombre", "categoria", "codigo_producto", "cantidad", "precio", "descripcion")

CAMPOS_PEDIDO = (
    "codigo_pedido", "estado", "cantidad", "id_cliente", "id_empleado", "id_producto",
    "fecha_creacion", "hora_creacion", "descripcion", "evidencias",
)
WIDGETS_PEDIDO = {
    "fecha_creacion": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    "hora_creacion": forms.DateTimeInput(
        attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
    ),
}

CAMPOS_CALENDARIO = (
    "fecha", "anio", "mes", "nombre_mes", "dia", "nombre_dia", "id_pedido",
)
WIDGETS_CALENDARIO = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

CAMPOS_TAREA = (
    "nombre", "descripcion", "fecha_inicio", "fecha_fin", "id_pedido", "id_empleado",
)
WIDGETS_TAREA = {
    "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
}

CAMPOS_ACTIVIDAD = (
    "nombre", "descripcion", "fecha_inicio", "fecha_fin", "id_tarea", "id_empleado",
)
WIDGETS_ACTIVIDAD = {
    "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    "fecha_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
}

CAMPOS_HISTORIAL = ("hora_creacion", "fecha_creacion", "id_cliente", "id_empleado", "id_producto")
WIDGETS_HISTORIAL = {
    "hora_creacion": forms.TimeInput(attrs={"type": "time"}),
    "fecha_creacion": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
}

CAMPOS_ANALISIS = (
    "fecha", "fuentes_ingresos", "gastos", "fuente_ingreso",
    "productos_vendidos", "id_administrador",
)
WIDGETS_ANALISIS = {
    "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
}


def _form(modelo, campos, widgets=None, instance=None, data=None, files=None):
    """Construye un ModelForm en la vista, sin pasar por un ``forms.py``.

    ``campos`` es la lista de campos que se muestran y ``widgets`` los widgets
    que necesitan los campos de fecha/hora (``type="date"``).
    """
    clase = modelform_factory(modelo, fields=list(campos), widgets=widgets or {})
    return clase(data=data, files=files, instance=instance)


def _form_vista(modelo, campos, widgets, request, instance=None, con_archivos=False):
    """Formulario del CRUD con los ajustes que dependen de la petición.

    - Normaliza los campos de dinero del ``request.POST`` antes de validar
      (``250.000`` y ``250,50`` se aceptan) y avisa en español si el valor no es
      un número.
    - Pone las etiquetas de los selects en español.
    - Deja los montos como texto, para poder mostrar los puntos de miles.
    """
    datos, errores = (None, {})
    if request.method == "POST":
        datos, errores = normalizar_montos(request.POST)
    archivos = (request.FILES or None) if con_archivos else None

    form = _form(modelo, campos, widgets, instance=instance, data=datos, files=archivos)
    _etiquetas_en_espanol(form)
    _montos_como_texto(form)
    for nombre, mensaje in errores.items():
        if nombre in form.fields:
            form.add_error(nombre, mensaje)
    return form


def _trabajador_en(form, obligatorio, etiqueta):
    """Ajusta el campo ``id_empleado`` del formulario (trabajador / responsable).

    En la actividad el trabajador es obligatorio; en la tarea es opcional. Solo
    se ofrecen los empleados vigentes.
    """
    campo = form.fields.get("id_empleado")
    if campo is not None:
        campo.queryset = Empleado.objects.filter(activo=True).order_by("nombre")
        campo.required = obligatorio
        campo.label = etiqueta
    return form


def _form_cliente(request, instance=None):
    """Cliente sin el campo edad; incluye la contraseña para crear su acceso."""
    form = _form_vista(Cliente, CAMPOS_CLIENTE, WIDGETS_CLIENTE, request, instance=instance)
    form.fields.pop("edad", None)
    form.fields["contrasena"] = forms.CharField(
        required=False,
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=(
            "Déjala vacía para conservar la contraseña actual."
            if instance is not None and instance.usuario_id
            else "Mínimo 8 caracteres. Si la escribes, se crea la cuenta de acceso con el correo."
        ),
    )
    return form


def _guardar_cliente_con_acceso(request, form):
    """Guarda el cliente y crea/actualiza su cuenta de acceso si se indicó clave."""
    cliente = form.instance
    clave = (form.cleaned_data.get("contrasena") or "").strip()
    correo = (form.cleaned_data.get("correo") or "").strip().lower()
    usuario = cliente.usuario if cliente.usuario_id else None

    if clave and len(clave) < 8:
        form.add_error("contrasena", "La contraseña debe tener al menos 8 caracteres.")
        return None
    if clave and not correo:
        form.add_error("correo", "Para crear la cuenta de acceso necesitas un correo.")
        return None
    if correo:
        existente = User.objects.filter(
            Q(username__iexact=correo) | Q(email__iexact=correo)
        ).first()
        if existente is not None and (usuario is None or existente.pk != usuario.pk):
            form.add_error("correo", "Ya existe una cuenta con ese correo.")
            return None

    with transaction.atomic():
        cliente = form.save()
        if usuario is None and clave:
            usuario = User(username=correo)
        if usuario is not None:
            usuario.username = correo
            usuario.email = correo
            usuario.first_name = cliente.nombre[:150]
            usuario.is_active = True
            if clave:
                usuario.set_password(clave)
            usuario.save()
            asignar_rol(usuario, ROL_CLIENTE)
            if cliente.usuario_id != usuario.pk:
                cliente.usuario = usuario
                cliente.save(update_fields=["usuario"])
        registrar_auditoria(
            request, "guardar", "Cliente", cliente,
            f"Cliente {cliente.nombre} guardado con acceso {'creado' if clave else 'sin cambios'}.",
        )
    return cliente


def _form_empleado(request, instance=None):
    form = _form_vista(Empleado, CAMPOS_EMPLEADO, WIDGETS_EMPLEADO, request, instance=instance)
    form.fields.pop("edad", None)
    if instance is None:
        form.fields.pop("tareas_realizadas", None)
    form.fields["contrasena"] = forms.CharField(
        required=False,
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=(
            "Déjala vacía para conservar la contraseña actual."
            if instance is not None and instance.usuario_id
            else "Mínimo 8 caracteres. El trabajador iniciará sesión con su documento."
        ),
    )
    return form


def _guardar_empleado_con_acceso(request, form):
    """Guarda el trabajador y crea/actualiza su cuenta de acceso si se indicó clave."""
    empleado = form.instance
    clave = (form.cleaned_data.get("contrasena") or "").strip()
    documento = (form.cleaned_data.get("documento") or "").strip()
    correo = (form.cleaned_data.get("correo") or "").strip().lower()
    usuario = empleado.usuario if empleado.usuario_id else None

    if clave and len(clave) < 8:
        form.add_error("contrasena", "La contraseña debe tener al menos 8 caracteres.")
        return None
    if documento and Empleado.objects.filter(
        documento__iexact=documento
    ).exclude(pk=empleado.pk).exists():
        form.add_error("documento", "Ya existe un trabajador con ese documento.")
        return None
    if usuario is None and clave:
        existente = User.objects.filter(
            Q(username__iexact=documento) | Q(email__iexact=correo)
        ).first() if correo else User.objects.filter(username__iexact=documento).first()
        if existente is not None:
            form.add_error("documento", "Ya existe una cuenta con ese documento o correo.")
            return None
    if usuario is not None and correo:
        existente = User.objects.filter(
            Q(username__iexact=correo) | Q(email__iexact=correo)
        ).exclude(pk=usuario.pk).first()
        if existente is not None:
            form.add_error("correo", "Ya existe una cuenta con ese correo.")
            return None

    with transaction.atomic():
        empleado = form.save()
        if usuario is None and clave:
            usuario = User(username=documento, email=correo, first_name=empleado.nombre[:150])
            usuario.set_password(clave)
            usuario.save()
            asignar_rol(usuario, ROL_TRABAJADOR)
        elif usuario is not None:
            usuario.email = correo
            usuario.first_name = empleado.nombre[:150]
            if clave:
                usuario.set_password(clave)
            usuario.save()
            if not usuario.groups.exists():
                asignar_rol(usuario, ROL_TRABAJADOR)
        if usuario is not None and empleado.usuario_id != usuario.pk:
            empleado.usuario = usuario
            empleado.save(update_fields=["usuario"])
        registrar_auditoria(
            request, "guardar", "Empleado", empleado,
            f"Trabajador {empleado.nombre} guardado con acceso {'actualizado' if clave else 'sin cambios'}.",
        )
    return empleado


def _form_administrador(request, instance=None):
    return _form_vista(Administrador, CAMPOS_ADMINISTRADOR, {}, request, instance=instance)


def _form_producto(request, instance=None):
    return _form_vista(Producto, CAMPOS_PRODUCTO, {}, request, instance=instance)


def _form_calendario(request, instance=None):
    return _form_vista(Calendario, CAMPOS_CALENDARIO, WIDGETS_CALENDARIO, request, instance=instance)


def _form_historial(request, instance=None):
    return _form_vista(Historial, CAMPOS_HISTORIAL, WIDGETS_HISTORIAL, request, instance=instance)


def _administrador_actual(usuario):
    """Devuelve (o crea) el registro de Administrador vinculado al usuario."""
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return None
    administrador = Administrador.objects.filter(usuario=usuario).first()
    if administrador is not None:
        return administrador

    documento = (usuario.get_username() or "")[:50]
    administrador = Administrador.objects.filter(
        usuario__isnull=True, documento__iexact=documento
    ).first()
    if administrador is not None:
        administrador.usuario = usuario
        administrador.save(update_fields=["usuario"])
        return administrador

    nombre = (usuario.get_full_name() or usuario.get_username() or "Administrador")[:100]
    return Administrador.objects.create(
        nombre=nombre,
        documento=documento,
        celular="",
        usuario=usuario,
    )


def _form_analisis(request, instance=None):
    form = _form_vista(
        AnalisisFinanciero, CAMPOS_ANALISIS, WIDGETS_ANALISIS, request, instance=instance
    )
    form.fields["fecha"].required = False
    form.fields["fuente_ingreso"].required = False
    if instance is None:
        administrador = _administrador_actual(getattr(request, "user", None))
        if administrador is not None:
            form.fields["id_administrador"].initial = administrador.pk
    return form


def _guardar_analisis(request, form):
    """Guarda el análisis con fecha y fuente aunque el formulario las omita."""
    obj = form.save(commit=False)
    obj.fecha = obj.fecha or timezone.localdate()
    obj.fuente_ingreso = obj.fuente_ingreso or "directa"
    obj.save()
    registrar_auditoria(
        request, "guardar", obj._meta.verbose_name, obj,
        f"{obj._meta.verbose_name} guardado: {obj}",
    )
    return obj


def _form_tarea(request, instance=None):
    form = _form_vista(TareasPedido, CAMPOS_TAREA, WIDGETS_TAREA, request, instance=instance)
    return _trabajador_en(form, obligatorio=False, etiqueta="Responsable")


def _form_actividad(request, instance=None):
    form = _form_vista(Actividades, CAMPOS_ACTIVIDAD, WIDGETS_ACTIVIDAD, request, instance=instance)
    return _trabajador_en(form, obligatorio=True, etiqueta="Trabajador")


def _fila(obj, valores, detalle_url=None):
    """Fila de lista: pk + valores + estado (activo) para la píldora."""
    return {
        "pk": obj.pk,
        "valores": valores,
        "activo": bool(obj.activo),
        "detalle_url": detalle_url,
    }


def _guardar_con_auditoria(request, form, accion="guardar"):
    """Guarda un ModelForm y deja constancia en el log de auditoría."""
    obj = form.save()
    registrar_auditoria(
        request, accion, obj._meta.verbose_name, obj,
        f"{obj._meta.verbose_name} {accion}: {obj}",
    )
    return obj


def _desactivar(request, obj, nombre, etiqueta, activo):
    """GET confirma, POST desactiva (nunca borra).

    Si el modelo tiene ``estado`` (Pedido), se alinea con ``activo`` para que el
    tablero y las pantallas operativas no sigan mostrándolo como vigente.
    """
    url_lista = reverse(f"kanview:{nombre}-lista")
    if request.method == "POST":
        obj.activo = False
        campos = ["activo"]
        if hasattr(obj, "estado") and getattr(obj, "estado", "") == "activo":
            obj.estado = "inactivo"
            campos.append("estado")
        obj.save(update_fields=campos)
        registrar_auditoria(
            request, "desactivar", obj._meta.verbose_name, obj,
            f"{etiqueta} desactivado",
        )
        if isinstance(obj, Pedido):
            historial.registrar(obj, "pedido_desactivado", f"{etiqueta} desactivado.", request.user)
        messages.success(
            request,
            f"{etiqueta} desactivado. No se borró: puedes reactivarlo cuando quieras.",
        )
        return redirect(url_lista)
    return render(request, "kanview/crud/confirm_delete.html", {
        "object": obj,
        "title": f"Desactivar {etiqueta.lower()}",
        "cancel_url": url_lista,
        **_nav(activo, request),
    })


def _reactivar(request, obj, nombre, etiqueta):
    """POST: vuelve a dejar el registro activo."""
    if request.method == "POST":
        obj.activo = True
        campos = ["activo"]
        if hasattr(obj, "estado") and getattr(obj, "estado", "") == "inactivo":
            obj.estado = "activo"
            campos.append("estado")
        obj.save(update_fields=campos)
        registrar_auditoria(
            request, "reactivar", obj._meta.verbose_name, obj,
            f"{etiqueta} reactivado",
        )
        if isinstance(obj, Pedido):
            historial.registrar(obj, "pedido_reactivado", f"{etiqueta} reactivado.", request.user)
        messages.success(request, f"{etiqueta} reactivado correctamente.")
    return redirect(f"kanview:{nombre}-lista")


# ---- Cliente --------------------------------------------------------------

@seccion_requerida("usuarios")
def cliente_lista(request):
    filas = [
        _fila(obj, [obj.nombre, obj.documento, obj.celular, obj.correo])
        for obj in Cliente.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "cliente", "Clientes", ["Nombre", "Documento", "Celular", "Correo"], filas, "Usuarios",
    ))


@seccion_requerida("usuarios")
def cliente_crear(request):
    form = _form_cliente(request)
    if request.method == "POST" and form.is_valid():
        cliente = _guardar_cliente_con_acceso(request, form)
        if cliente is not None and not form.errors:
            messages.success(request, "Cliente creado correctamente.")
            return redirect("kanview:cliente-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo cliente",
        "cancel_url": reverse("kanview:cliente-lista"),
        **_nav("Usuarios", request),
    })


@seccion_requerida("usuarios")
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = _form_cliente(request, instance=cliente)
    if request.method == "POST" and form.is_valid():
        cliente = _guardar_cliente_con_acceso(request, form)
        if cliente is not None and not form.errors:
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect("kanview:cliente-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar cliente",
        "cancel_url": reverse("kanview:cliente-lista"),
        **_nav("Usuarios", request),
    })


@seccion_requerida("usuarios")
def cliente_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Cliente, pk=pk), "cliente", "Cliente", "Usuarios")


@seccion_requerida("usuarios")
def cliente_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Cliente, pk=pk), "cliente", "Cliente")


# ---- Empleado -------------------------------------------------------------

@seccion_requerida("usuarios")
def empleado_lista(request):
    filas = [
        _fila(obj, [obj.nombre, obj.documento, obj.get_cargo_display(), obj.celular, moneda_cop(obj.salario)])
        for obj in Empleado.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "empleado", "Empleados", ["Nombre", "Documento", "Cargo", "Celular", "Salario"], filas, "Usuarios",
    ))


@seccion_requerida("usuarios")
def empleado_crear(request):
    form = _form_empleado(request)
    if request.method == "POST" and form.is_valid():
        empleado = _guardar_empleado_con_acceso(request, form)
        if empleado is not None and not form.errors:
            messages.success(request, "Empleado creado correctamente.")
            return redirect("kanview:empleado-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo empleado",
        "cancel_url": reverse("kanview:empleado-lista"),
        **_nav("Usuarios", request),
    })


@seccion_requerida("usuarios")
def empleado_editar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    form = _form_empleado(request, instance=empleado)
    if request.method == "POST" and form.is_valid():
        empleado = _guardar_empleado_con_acceso(request, form)
        if empleado is not None and not form.errors:
            messages.success(request, "Empleado actualizado correctamente.")
            return redirect("kanview:empleado-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar empleado",
        "cancel_url": reverse("kanview:empleado-lista"),
        **_nav("Usuarios", request),
    })


@seccion_requerida("usuarios")
def empleado_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Empleado, pk=pk), "empleado", "Empleado", "Usuarios")


@seccion_requerida("usuarios")
def empleado_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Empleado, pk=pk), "empleado", "Empleado")


# ---- Administrador --------------------------------------------------------

@seccion_requerida("usuarios")
def administrador_lista(request):
    filas = [
        _fila(obj, [obj.nombre, obj.documento, obj.celular])
        for obj in Administrador.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "administrador", "Administradores", ["Nombre", "Documento", "Celular"], filas, "Panel",
    ))


@seccion_requerida("usuarios")
def administrador_crear(request):
    form = _form_administrador(request)
    if request.method == "POST" and form.is_valid():
        _guardar_con_auditoria(request, form)
        messages.success(request, "Administrador creado correctamente.")
        return redirect("kanview:administrador-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo administrador",
        "cancel_url": reverse("kanview:administrador-lista"),
        **_nav("Panel", request),
    })


@seccion_requerida("usuarios")
def administrador_editar(request, pk):
    administrador = get_object_or_404(Administrador, pk=pk)
    form = _form_administrador(request, instance=administrador)
    if request.method == "POST" and form.is_valid():
        _guardar_con_auditoria(request, form)
        messages.success(request, "Administrador actualizado correctamente.")
        return redirect("kanview:administrador-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar administrador",
        "cancel_url": reverse("kanview:administrador-lista"),
        **_nav("Panel", request),
    })


@seccion_requerida("usuarios")
def administrador_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Administrador, pk=pk), "administrador", "Administrador", "Panel")


@seccion_requerida("usuarios")
def administrador_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Administrador, pk=pk), "administrador", "Administrador")


# ---- Producto (crea/actualiza Inventario y Catálogo) ----------------------

def _avisos_negativos(request, form):
    """Aviso amable si cantidad o precio llegan negativos o mal escritos.

    Los campos de dinero se leen con el mismo criterio que la vista
    (``normalizar_monto``): así «1.250.000» no se confunde con un error.
    """
    for campo, etiqueta in (("cantidad", "La cantidad"), ("precio", "El precio")):
        if campo not in form.fields:
            continue
        crudo = (request.POST.get(campo) or "").strip()
        if not crudo:
            continue
        try:
            if campo in CAMPOS_MONEDA:
                valor = float(normalizar_monto(crudo))
            else:
                valor = float(crudo.replace(",", "."))
        except ValueError:
            form.add_error(campo, f"{etiqueta} debe ser un número válido.")
            continue
        if valor < 0:
            form.add_error(campo, f"{etiqueta} no puede ser negativa.")


# ---- Producto (única fuente del stock y de la categoría) ------------------
@seccion_requerida("catalogo")
def producto_lista(request):
    filas = [
        _fila(obj, [obj.nombre, obj.get_categoria_display(), obj.codigo_producto, obj.cantidad, moneda_cop(obj.precio)])
        for obj in Producto.objects.all().order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "producto", "Productos", ["Nombre", "Categoría", "Código", "Cantidad", "Precio"], filas, "Productos",
    ))


@seccion_requerida(SECCION_ESCRITURA["catalogo"])
def producto_crear(request):
    form = _form_producto(request)
    if request.method == "POST":
        _avisos_negativos(request, form)
        if form.is_valid():
            producto = _guardar_con_auditoria(request, form, "guardar")
            messages.success(
                request,
                f"Producto {producto.nombre} creado con {producto.cantidad} unidad(es) en stock.",
            )
            return redirect("kanview:producto-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo producto",
        "cancel_url": reverse("kanview:producto-lista"),
        **_nav("Productos", request),
    })


@seccion_requerida(SECCION_ESCRITURA["catalogo"])
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = _form_producto(request, instance=producto)
    if request.method == "POST":
        _avisos_negativos(request, form)
        if form.is_valid():
            producto = _guardar_con_auditoria(request, form, "guardar")
            messages.success(request, "Producto actualizado: su stock y su categoría quedaron al día.")
            return redirect("kanview:producto-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar producto",
        "cancel_url": reverse("kanview:producto-lista"),
        **_nav("Productos", request),
    })


@seccion_requerida(SECCION_ESCRITURA["catalogo"])
def producto_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Producto, pk=pk), "producto", "Producto", "Productos")


@seccion_requerida(SECCION_ESCRITURA["catalogo"])
def producto_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Producto, pk=pk), "producto", "Producto")


# ---- Pedido (código, fechas y galería automáticos) ------------------------

def siguiente_codigo_pedido():
    """Siguiente código consecutivo en formato ``PED-0001``."""
    mayor = 0
    for codigo in Pedido.objects.values_list("codigo_pedido", flat=True):
        if codigo and codigo.upper().startswith("PED-"):
            try:
                mayor = max(mayor, int(codigo[4:]))
            except ValueError:
                continue
    return f"PED-{mayor + 1:04d}"


def _guardar_pedido_con_codigo(pedido, intentos=5):
    """Guarda un pedido nuevo con el siguiente código libre, sin carreras.

    El código se calcula y se guarda dentro de la misma transacción: si dos
    peticiones simultáneas calculan el mismo ``PED-`` el ``unique`` falla en una
    y esa se reintenta con el código siguiente.
    """
    for _ in range(intentos):
        try:
            with transaction.atomic():
                pedido.codigo_pedido = siguiente_codigo_pedido()
                pedido.save()
            return pedido
        except IntegrityError:
            continue
    raise IntegrityError("No se pudo asignar un código único al pedido.")


def _validar_imagenes(request, form):
    """Valida imágenes y videos ANTES de guardar nada.

    Devuelve una lista de ``(archivo, tipo)``. Las imágenes se comprueban con
    Pillow; los videos se validan por extensión, content-type y tamaño. Si algo
    falla se agrega un error al formulario y no se guarda ningún archivo.
    """
    archivos = request.FILES.getlist("imagenes")
    if not archivos:
        return []

    if len(archivos) > MAX_IMAGENES:
        form.add_error(None, f"Puedes adjuntar máximo {MAX_IMAGENES} imágenes o videos por pedido.")
        return []

    total = 0
    validos = []
    for archivo in archivos:
        nombre = getattr(archivo, "name", "") or ""
        extension = os.path.splitext(nombre)[1].lower()
        content_type = (getattr(archivo, "content_type", "") or "").lower()
        tamano = getattr(archivo, "size", 0) or 0
        total += tamano

        if total > MAX_BYTES_MULTIMEDIA:
            form.add_error(None, "Los archivos superan el límite total permitido (60 MB).")
            return []

        if extension in EXTENSIONES_IMAGEN:
            if tamano > MAX_BYTES_IMAGEN:
                form.add_error(None, f"«{nombre}» pesa más de 5 MB. Sube una imagen más liviana.")
                return []
            if content_type not in CONTENT_TYPES_IMAGEN:
                form.add_error(None, f"«{nombre}» no parece una imagen válida.")
                return []
            try:
                Image.open(archivo).verify()
            except Exception:
                form.add_error(None, f"«{nombre}» no es una imagen válida o está dañada.")
                return []
            archivo.seek(0)
            validos.append((archivo, "imagen"))
            continue

        if extension in EXTENSIONES_VIDEO:
            if tamano > MAX_BYTES_VIDEO:
                form.add_error(None, f"«{nombre}» pesa más de 25 MB. Sube un video más liviano.")
                return []
            if content_type not in CONTENT_TYPES_VIDEO:
                form.add_error(None, f"«{nombre}» no parece un video válido.")
                return []
            archivo.seek(0)
            validos.append((archivo, "video"))
            continue

        form.add_error(
            None,
            f"«{nombre}» no es una imagen permitida. Solo se aceptan imágenes JPG, PNG, WEBP o videos MP4, WEBM, MOV.",
        )
        return []
    return validos


def _guardar_evidencias(pedido, archivos):
    """Guarda en la galería los archivos ya validados."""
    creadas = 0
    for archivo, tipo in archivos:
        EvidenciaPedido.objects.create(pedido=pedido, archivo=archivo, tipo=tipo)
        creadas += 1
    return creadas


def _form_pedido(request, instance=None):
    """Pedido sin código, fechas de creación ni evidencias (los pone la vista).

    ``fecha_limite`` se añade aquí como DateField para que se pueda capturar
    desde la interfaz y para que una fecha inválida avise en vez de ignorarse.
    """
    form = _form_vista(
        Pedido, CAMPOS_PEDIDO, WIDGETS_PEDIDO, request, instance=instance, con_archivos=True
    )
    for campo in ("codigo_pedido", "fecha_creacion", "hora_creacion", "evidencias"):
        form.fields.pop(campo, None)
    form.fields["fecha_limite"] = forms.DateField(
        required=False,
        label="Fecha límite de entrega",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "Ingresa una fecha límite válida (año-mes-día)."},
    )
    return form


@seccion_requerida("pedidos")
def pedido_lista(request):
    """Lista de pedidos. El rol Cliente solo ve los que son suyos."""
    consulta = Pedido.objects.select_related("id_cliente", "id_empleado", "id_producto").order_by("-id")
    if es_solo_cliente(request.user):
        consulta = consulta.filter(id_cliente__correo__iexact=request.user.email)
    filas = [
        _fila(
            obj,
            [obj.codigo_pedido, obj.id_cliente, obj.id_producto, obj.cantidad,
             obj.get_estado_aprobacion_display(), obj.fecha_creacion],
            detalle_url=reverse("kanview:pedido-detalle", args=[obj.pk]),
        )
        for obj in consulta
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "pedido", "Pedidos",
        ["Código", "Cliente", "Producto", "Cantidad", "Aprobación", "Fecha"],
        filas, "Pedidos",
    ))


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
def pedido_crear(request):
    form = _form_pedido(request)
    if request.method == "POST":
        form.is_valid()
        archivos = _validar_imagenes(request, form)
        if not form.errors:
            pedido = form.save(commit=False)
            pedido.fecha_creacion = timezone.localdate()
            pedido.hora_creacion = timezone.now()
            pedido.evidencias = ""
            pedido.fecha_limite = form.cleaned_data.get("fecha_limite")
            _guardar_pedido_con_codigo(pedido)
            imagenes = _guardar_evidencias(pedido, archivos)
            aviso = f" con {imagenes} archivo{'s' if imagenes != 1 else ''}" if imagenes else ""
            historial.registrar(
                pedido, "pedido_creado",
                f"Pedido {pedido.codigo_pedido} creado con {pedido.cantidad} unidad(es).",
                request.user,
            )
            registrar_auditoria(
                request, "crear", "Pedido", pedido,
                f"Pedido {pedido.codigo_pedido} creado",
                {"cliente": pedido.id_cliente_id, "producto": pedido.id_producto_id},
            )
            notificar_staff(
                "pedido",
                f"Nuevo pedido {pedido.codigo_pedido} para {pedido.id_cliente.nombre}.",
                reverse("kanview:pedido-detalle", args=[pedido.pk]),
            )
            messages.success(request, f"Pedido {pedido.codigo_pedido} creado{aviso}.")
            return redirect("kanview:pedido-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo pedido",
        "cancel_url": reverse("kanview:pedido-lista"),
        "permite_imagenes": True,
        "aviso_imagenes": (
            "Adjunta imágenes o videos (JPG, PNG, WEBP, MP4, WEBM; máximo 5 archivos, "
            "5 MB por imagen y 25 MB por video). Se guardarán en la galería del pedido."
        ),
        **_nav("Pedidos", request),
    })


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
def pedido_editar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    form = _form_pedido(request, instance=pedido)
    if request.method == "POST":
        form.is_valid()
        archivos = _validar_imagenes(request, form)
        if not form.errors:
            pedido = form.save(commit=False)
            # Una fecha vacía borra la fecha límite (se puede dejar sin fecha).
            pedido.fecha_limite = form.cleaned_data.get("fecha_limite")
            pedido.save()
            imagenes = _guardar_evidencias(pedido, archivos)
            aviso = f" Se agregaron {imagenes} archivos a su galería." if imagenes else ""
            historial.registrar(
                pedido, "pedido_actualizado",
                f"Pedido {pedido.codigo_pedido} actualizado.{aviso}",
                request.user,
            )
            registrar_auditoria(
                request, "editar", "Pedido", pedido,
                f"Pedido {pedido.codigo_pedido} actualizado",
            )
            notificar_cliente(
                pedido.id_cliente,
                "pedido",
                f"Tu pedido {pedido.codigo_pedido} fue actualizado.",
                reverse("kanview:pedido-detalle", args=[pedido.pk]),
                asunto="Kanview · Pedido actualizado",
            )
            messages.success(request, f"Pedido {pedido.codigo_pedido} actualizado.{aviso}")
            return redirect("kanview:pedido-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar pedido",
        "cancel_url": reverse("kanview:pedido-lista"),
        "permite_imagenes": True,
        "aviso_imagenes": (
            "Puedes adjuntar más imágenes o videos para ampliar la galería (máximo 5 archivos, "
            "5 MB por imagen y 25 MB por video). Deja la fecha límite vacía para quitarla."
        ),
        **_nav("Pedidos", request),
    })


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
def pedido_eliminar(request, pk):
    """Elimina el pedido del tablero (desactivación reversible, no borrado físico)."""
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        return _desactivar(request, pedido, "pedido", "Pedido", "Pedidos")
    return render(request, "kanview/pedido_confirm_delete.html", {
        "pedido": pedido,
        "cancel_url": reverse("kanview:pedido-detalle", args=[pedido.pk]),
        "cabecera_titulo": f"Eliminar pedido {pedido.codigo_pedido}",
        **_nav("Pedidos", request),
    })


@seccion_requerida(SECCION_ESCRITURA["pedidos"])
def pedido_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Pedido, pk=pk), "pedido", "Pedido")


# ---- Calendario -----------------------------------------------------------

@seccion_requerida("calendario")
def calendario_crud_lista(request):
    filas = [
        _fila(obj, [obj.fecha, obj.nombre_mes, obj.nombre_dia, obj.id_pedido])
        for obj in Calendario.objects.select_related("id_pedido").order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "calendario", "Calendario", ["Fecha", "Mes", "Día", "Pedido"], filas, "Calendario",
    ))


@seccion_requerida("calendario")
def calendario_crear(request):
    form = _form_calendario(request)
    if request.method == "POST" and form.is_valid():
        _guardar_con_auditoria(request, form)
        messages.success(request, "Registro de calendario creado correctamente.")
        return redirect("kanview:calendario-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo registro de calendario",
        "cancel_url": reverse("kanview:calendario-lista"),
        **_nav("Calendario", request),
    })


@seccion_requerida("calendario")
def calendario_editar(request, pk):
    registro = get_object_or_404(Calendario, pk=pk)
    form = _form_calendario(request, instance=registro)
    if request.method == "POST" and form.is_valid():
        _guardar_con_auditoria(request, form)
        messages.success(request, "Registro de calendario actualizado correctamente.")
        return redirect("kanview:calendario-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar registro de calendario",
        "cancel_url": reverse("kanview:calendario-lista"),
        **_nav("Calendario", request),
    })


@seccion_requerida("calendario")
def calendario_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Calendario, pk=pk), "calendario", "Registro de calendario", "Calendario")


@seccion_requerida("calendario")
def calendario_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Calendario, pk=pk), "calendario", "Registro de calendario")


# ---- TareasPedido ---------------------------------------------------------

def _validar_fecha_limite(form, pedido):
    """La fecha fin no puede superar la fecha límite de entrega del pedido."""
    fecha_fin = form.cleaned_data.get("fecha_fin")
    limite = getattr(pedido, "fecha_limite", None) if pedido else None
    if fecha_fin and limite and fecha_fin > limite:
        form.add_error(
            "fecha_fin",
            f"La fecha de fin no puede superar la fecha límite de entrega del pedido ({limite:%d/%m/%Y}).",
        )


@seccion_requerida("tareas")
def tarea_lista(request):
    filas = [
        _fila(
            obj,
            [obj.nombre, obj.get_estado_display(), obj.fecha_inicio, obj.fecha_fin, obj.id_pedido],
            detalle_url=reverse("kanview:tarea-detalle", args=[obj.pk]),
        )
        for obj in TareasPedido.objects.select_related("id_pedido").order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "tarea", "Tareas", ["Nombre", "Estado", "Inicio", "Fin", "Pedido"], filas, "Tareas",
    ))


@seccion_requerida("tareas")
def tarea_crear(request):
    form = _form_tarea(request)
    if request.method == "POST" and form.is_valid():
        _validar_fecha_limite(form, form.cleaned_data.get("id_pedido"))
        if not form.errors:
            tarea = _guardar_con_auditoria(request, form)
            historial.registrar(
                tarea.id_pedido, "tarea_creada",
                f"Tarea «{tarea.nombre}» creada para {tarea.id_pedido.codigo_pedido}.",
                request.user,
            )
            if tarea.id_empleado:
                from .notificaciones import notificar_empleado

                notificar_empleado(
                    tarea.id_empleado,
                    "tarea",
                    f"Se te asignó la tarea «{tarea.nombre}» del pedido "
                    f"{tarea.id_pedido.codigo_pedido}.",
                    reverse("kanview:tarea-detalle", args=[tarea.pk]),
                )
            messages.success(request, "Tarea creada correctamente.")
            return redirect("kanview:tareas")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nueva tarea",
        "cancel_url": reverse("kanview:tarea-lista"),
        **_nav("Actividades", request),
    })


@seccion_requerida("tareas")
def tarea_editar(request, pk):
    tarea = get_object_or_404(TareasPedido, pk=pk)
    form = _form_tarea(request, instance=tarea)
    if request.method == "POST" and form.is_valid():
        _validar_fecha_limite(form, form.cleaned_data.get("id_pedido"))
        if not form.errors:
            tarea = _guardar_con_auditoria(request, form)
            historial.registrar(
                tarea.id_pedido, "tarea_actualizada",
                f"Tarea «{tarea.nombre}» actualizada.",
                request.user,
            )
            messages.success(request, "Tarea actualizada correctamente.")
            return redirect("kanview:tareas")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar tarea",
        "cancel_url": reverse("kanview:tarea-lista"),
        **_nav("Actividades", request),
    })


@seccion_requerida("tareas")
def tarea_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(TareasPedido, pk=pk), "tarea", "Tarea", "Actividades")


@seccion_requerida("tareas")
def tarea_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(TareasPedido, pk=pk), "tarea", "Tarea")


# ---- Actividades (Auditoría) ----------------------------------------------

@seccion_requerida("tareas")
def actividad_lista(request):
    filas = [
        _fila(obj, [obj.nombre, obj.get_estado_display(), obj.fecha_inicio, obj.fecha_fin, obj.id_tarea])
        for obj in Actividades.objects.select_related("id_tarea").order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "actividad", "Actividades", ["Nombre", "Estado", "Inicio", "Fin", "Tarea"], filas, "Actividades",
    ))


@seccion_requerida("tareas")
def actividad_crear(request):
    form = _form_actividad(request)
    if request.method == "POST" and form.is_valid():
        tarea = form.cleaned_data.get("id_tarea")
        _validar_fecha_limite(form, tarea.id_pedido if tarea else None)
        if not form.errors:
            actividad = _guardar_con_auditoria(request, form)
            historial.registrar(
                tarea.id_pedido if tarea else None,
                "actividad_creada",
                f"Actividad «{actividad.nombre}» creada.",
                request.user,
            )
            if actividad.id_empleado:
                from .notificaciones import notificar_empleado

                notificar_empleado(
                    actividad.id_empleado,
                    "actividad",
                    f"Se te asignó la actividad «{actividad.nombre}» del pedido "
                    f"{actividad.id_tarea.id_pedido.codigo_pedido}.",
                    reverse("kanview:actividades"),
                )
                notificar_area(
                    actividad.id_empleado.cargo,
                    "actividad",
                    f"Nueva actividad «{actividad.nombre}» en el área de "
                    f"{actividad.id_empleado.get_cargo_display()}.",
                    reverse("kanview:actividades"),
                    excepto=actividad.id_empleado_id,
                )
            messages.success(request, "Actividad creada correctamente.")
            return redirect("kanview:actividades")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nueva actividad",
        "cancel_url": reverse("kanview:actividad-lista"),
        **_nav("Actividades", request),
    })


@seccion_requerida("tareas")
def actividad_editar(request, pk):
    actividad = get_object_or_404(Actividades, pk=pk)
    form = _form_actividad(request, instance=actividad)
    if request.method == "POST" and form.is_valid():
        tarea = form.cleaned_data.get("id_tarea")
        _validar_fecha_limite(form, tarea.id_pedido if tarea else None)
        if not form.errors:
            actividad = _guardar_con_auditoria(request, form)
            historial.registrar(
                tarea.id_pedido if tarea else None,
                "actividad_actualizada",
                f"Actividad «{actividad.nombre}» actualizada.",
                request.user,
            )
            if actividad.id_empleado:
                from .notificaciones import notificar_empleado

                notificar_empleado(
                    actividad.id_empleado,
                    "actividad",
                    f"Se actualizó la actividad «{actividad.nombre}» del pedido "
                    f"{actividad.id_tarea.id_pedido.codigo_pedido}.",
                    reverse("kanview:actividades"),
                )
            messages.success(request, "Actividad actualizada correctamente.")
            return redirect("kanview:actividades")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar actividad",
        "cancel_url": reverse("kanview:actividad-lista"),
        **_nav("Actividades", request),
    })


@seccion_requerida("tareas")
def actividad_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Actividades, pk=pk), "actividad", "Actividad", "Auditoría")


@seccion_requerida("tareas")
def actividad_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Actividades, pk=pk), "actividad", "Actividad")


# ---- Historial ------------------------------------------------------------

@seccion_requerida("auditoria")
def historial_crud_lista(request):
    filas = [
        _fila(obj, [obj.hora_creacion, obj.fecha_creacion, obj.id_cliente, obj.id_empleado, obj.id_producto])
        for obj in Historial.objects.select_related("id_cliente", "id_empleado", "id_producto").order_by("-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "historial", "Historial", ["Hora", "Fecha", "Cliente", "Empleado", "Producto"], filas, "Auditoría",
    ))


@seccion_requerida("auditoria")
def historial_crear(request):
    form = _form_historial(request)
    if request.method == "POST" and form.is_valid():
        _guardar_con_auditoria(request, form)
        messages.success(request, "Registro de historial creado correctamente.")
        return redirect("kanview:historial-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo registro de historial",
        "cancel_url": reverse("kanview:historial-lista"),
        **_nav("Auditoría", request),
    })


@seccion_requerida("auditoria")
def historial_editar(request, pk):
    registro = get_object_or_404(Historial, pk=pk)
    form = _form_historial(request, instance=registro)
    if request.method == "POST" and form.is_valid():
        _guardar_con_auditoria(request, form)
        messages.success(request, "Registro de historial actualizado correctamente.")
        return redirect("kanview:historial-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar registro de historial",
        "cancel_url": reverse("kanview:historial-lista"),
        **_nav("Auditoría", request),
    })


@seccion_requerida("auditoria")
def historial_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(Historial, pk=pk), "historial", "Registro de historial", "Auditoría")


@seccion_requerida("auditoria")
def historial_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(Historial, pk=pk), "historial", "Registro de historial")


# ---- Análisis financiero --------------------------------------------------

@seccion_requerida("finanzas")
def analisis_financiero_lista(request):
    filas = [
        _fila(
            obj,
            [obj.fecha, obj.get_fuente_ingreso_display(), moneda_cop(obj.fuentes_ingresos),
             moneda_cop(obj.gastos), obj.productos_vendidos, obj.id_administrador],
        )
        for obj in AnalisisFinanciero.objects.select_related("id_administrador").order_by("-fecha", "-id")
    ]
    return render(request, "kanview/crud/list.html", _contexto_lista(
        request,
        "analisis-financiero", "Análisis financiero",
        ["Fecha", "Fuente", "Ingresos", "Gastos", "Productos vendidos", "Administrador"],
        filas, "Finanzas",
    ))


@seccion_requerida("finanzas")
def analisis_financiero_crear(request):
    form = _form_analisis(request)
    if request.method == "POST" and form.is_valid():
        _guardar_analisis(request, form)
        messages.success(request, "Análisis financiero creado correctamente.")
        return redirect("kanview:analisis-financiero-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Nuevo análisis financiero",
        "cancel_url": reverse("kanview:analisis-financiero-lista"),
        **_nav("Finanzas", request),
    })


@seccion_requerida("finanzas")
def analisis_financiero_editar(request, pk):
    registro = get_object_or_404(AnalisisFinanciero, pk=pk)
    form = _form_analisis(request, instance=registro)
    if request.method == "POST" and form.is_valid():
        _guardar_analisis(request, form)
        messages.success(request, "Análisis financiero actualizado correctamente.")
        return redirect("kanview:analisis-financiero-lista")
    return render(request, "kanview/crud/form.html", {
        "form": form,
        "title": "Editar análisis financiero",
        "cancel_url": reverse("kanview:analisis-financiero-lista"),
        **_nav("Finanzas", request),
    })


@seccion_requerida("finanzas")
def analisis_financiero_eliminar(request, pk):
    return _desactivar(request, get_object_or_404(AnalisisFinanciero, pk=pk), "analisis-financiero", "Análisis financiero", "Finanzas")


@seccion_requerida("finanzas")
def analisis_financiero_reactivar(request, pk):
    return _reactivar(request, get_object_or_404(AnalisisFinanciero, pk=pk), "analisis-financiero", "Análisis financiero")
