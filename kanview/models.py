from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

# Reglas de negocio del taller


class Cliente(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de nacimiento")
    documento = models.CharField(max_length=20, default="", blank=True, verbose_name="Documento")
    celular = models.CharField(max_length=20, default="", blank=True, verbose_name="Celular")
    direccion = models.CharField(max_length=50, default="", blank=True, verbose_name="Dirección")
    # Se conserva por compatibilidad con los datos viejos, pero ya no se pide en el formulario:
    # la edad se deduce de la fecha de nacimiento.
    edad = models.IntegerField(default=0, verbose_name="Edad")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    # El correo identifica al cliente, pero puede estar en blanco: la unicidad
    # solo aplica a los correos escritos (ver Meta.constraints). Antes el
    # ``unique=True`` impedía dar de alta un segundo cliente sin correo.
    correo = models.EmailField(max_length=254, default="", blank=True, verbose_name="Correo")
    token = models.CharField(max_length=6, default="000000", verbose_name="Token")
    url_valida = models.BooleanField(default=False, verbose_name="Código vigente")
    # Cuenta de acceso del cliente. Es un vínculo explícito (no hay que adivinar
    # por el correo): el módulo Usuarios escribe SOLO este campo.
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cliente_kanview",
        verbose_name="Cuenta de acceso",
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["correo"],
                condition=~models.Q(correo=""),
                name="cliente_correo_unico_si_no_vacio",
                violation_error_message="Ya existe otro cliente con ese correo.",
            ),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        """Mantiene la edad sincronizada con la fecha de nacimiento."""
        from django.utils import timezone

        if self.fecha_nacimiento:
            hoy = timezone.localdate()
            self.edad = hoy.year - self.fecha_nacimiento.year - (
                (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        super().save(*args, **kwargs)


class Empleado(models.Model):
    CARGOS = (
        ("costr", "Costurero"),
        ("tapcr", "Tapicero"),
        ("gerente", "Gerente"),
        ("secre", "Secretario"),
    )

    documento = models.CharField(max_length=40, verbose_name="Documento")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    cargo = models.CharField(choices=CARGOS, max_length=10, default="tapcr", verbose_name="Cargo")
    celular = models.CharField(max_length=20, verbose_name="Celular")
    direccion = models.CharField(max_length=50, verbose_name="Dirección")
    salario = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        validators=[MinValueValidator(0, "El salario no puede ser negativo.")],
        verbose_name="Salario",
    )
    edad = models.IntegerField(default=0, verbose_name="Edad")
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de nacimiento")
    tareas_realizadas = models.IntegerField(default=0, verbose_name="Tareas realizadas")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    # El correo del trabajador es su identificador de acceso, igual que en
    # Cliente: único solo cuando está escrito, para que varios trabajadores
    # puedan quedar sin correo mientras se les crea la cuenta.
    correo = models.EmailField(max_length=254, default="", blank=True, verbose_name="Correo")
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="empleado_kanview",
        verbose_name="Cuenta de acceso",
    )

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["correo"],
                condition=~models.Q(correo=""),
                name="empleado_correo_unico_si_no_vacio",
                violation_error_message="Ya existe otro trabajador con ese correo.",
            ),
        ]

    def __str__(self):
        return self.nombre


class Administrador(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    celular = models.CharField(max_length=10, verbose_name="Celular")
    documento = models.CharField(max_length=50, verbose_name="Documento")
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="administrador_kanview",
        verbose_name="Cuenta de acceso",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class AnalisisFinanciero(models.Model):
    FUENTES_INGRESO = (
        ("directa", "Venta directa"),
        ("mayorista", "Mayorista"),
        ("personalizado", "Proyecto personalizado"),
        ("otro", "Otro"),
    )

    fecha = models.DateField(default=timezone.localdate, blank=True, verbose_name="Fecha")
    gastos = models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Gastos")
    fuentes_ingresos = models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Fuentes de ingresos")
    fuente_ingreso = models.CharField(
        choices=FUENTES_INGRESO,
        max_length=20,
        default="directa",
        blank=True,
        verbose_name="Fuente de ingreso",
    )
    productos_vendidos = models.IntegerField(verbose_name="Productos vendidos")
    id_administrador = models.ForeignKey(
        Administrador, on_delete=models.PROTECT, verbose_name="Administrador"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Análisis financiero"
        verbose_name_plural = "Análisis financieros"
        ordering = ["-id"]

    def __str__(self):
        return f"Análisis financiero #{self.pk}"


class Producto(models.Model):
    # Categorías fijas: en el formulario se eligen de una lista, no se escriben.
    CATEGORIAS = (
        ("tela", "Tela"),
        ("espuma", "Espuma"),
        ("madera", "Madera"),
        ("herraje", "Herraje"),
        ("hilo", "Hilo"),
        ("otro", "Otro"),
    )

    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    categoria = models.CharField(choices=CATEGORIAS, max_length=50, default="otro", verbose_name="Categoría")
    cantidad = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0, "La cantidad no puede ser negativa.")], verbose_name="Cantidad"
    )
    precio = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        validators=[MinValueValidator(0, "El precio no puede ser negativo.")],
        verbose_name="Precio",
    )
    descripcion = models.CharField(max_length=1000, verbose_name="Descripción")
    codigo_producto = models.CharField(max_length=6, verbose_name="Código")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


ESTADOS_KANBAN = (
    ("pendiente", "Pendiente"),
    ("en progreso", "En progreso"),
    ("completado", "Completado"),
)

#: Estados de las COLUMNAS del tablero de pedidos (distintos de los de tareas).
ESTADOS_PEDIDO_KANBAN = (
    ("pendiente", "Pendiente"),
    ("en proceso", "En proceso"),
    ("completado", "Completado"),
)


class Pedido(models.Model):
    ESTADOS = (
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
    )
    ESTADOS_APROBACION = (
        ("pendiente", "Pendiente de aprobación"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    )

    # El código se genera solo (PED-0001) al crear el pedido.
    codigo_pedido = models.CharField(max_length=20, unique=True, verbose_name="Código")
    fecha_creacion = models.DateField(verbose_name="Fecha de creación")
    hora_creacion = models.DateTimeField(verbose_name="Hora de creación")
    fecha_limite = models.DateField(null=True, blank=True, verbose_name="Fecha límite de entrega")
    estado = models.CharField(choices=ESTADOS, max_length=10, default="activo", verbose_name="Estado")
    # Estado manual del tablero. Vacío = se calcula a partir de las actividades.
    estado_kanban = models.CharField(
        choices=ESTADOS_PEDIDO_KANBAN,
        max_length=20,
        null=True,
        blank=True,
        default=None,
        verbose_name="Estado en el tablero",
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1, "La cantidad debe ser mayor que cero.")],
        verbose_name="Cantidad",
    )
    estado_aprobacion = models.CharField(
        choices=ESTADOS_APROBACION,
        max_length=10,
        default="pendiente",
        verbose_name="Aprobación",
    )
    motivo_rechazo = models.TextField(default="", blank=True, verbose_name="Motivo del rechazo")
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_aprobados",
        verbose_name="Aprobado por",
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de aprobación")
    # Campo heredado: se conserva por compatibilidad con los datos viejos.
    # Las imágenes del pedido ahora viven en el modelo EvidenciaPedido (galería).
    evidencias = models.CharField(max_length=255, default="", blank=True, verbose_name="Evidencias (heredado)")
    descripcion = models.CharField(max_length=1000, verbose_name="Descripción")
    id_cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    id_empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, verbose_name="Empleado")
    id_producto = models.ForeignKey(Producto, on_delete=models.PROTECT, verbose_name="Producto")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-id"]

    def __str__(self):
        return self.codigo_pedido

    @property
    def subtotal(self):
        return self.cantidad * self.id_producto.precio

    @property
    def estado_comercial(self):
        if self.estado_aprobacion == "rechazado":
            return "rechazado"
        if self.estado_aprobacion == "pendiente":
            return "pendiente-aprobacion"
        if not self.activo:
            return "inactivo"
        return "aprobado"


class EvidenciaPedido(models.Model):
    """Fotos y videos que se adjuntan al pedido."""

    TIPOS = (
        ("imagen", "Imagen"),
        ("video", "Video"),
    )

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="galeria", verbose_name="Pedido")
    archivo = models.FileField(upload_to="evidencias/%Y/%m/", verbose_name="Archivo")
    tipo = models.CharField(choices=TIPOS, max_length=10, default="imagen", verbose_name="Tipo")
    descripcion = models.CharField(max_length=255, default="", blank=True, verbose_name="Descripción")
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de carga")

    class Meta:
        verbose_name = "Evidencia de pedido"
        verbose_name_plural = "Evidencias de pedido"
        ordering = ["-id"]

    def __str__(self):
        return f"Evidencia #{self.pk} · {self.pedido}"


class TareasPedido(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.CharField(max_length=1000, verbose_name="Descripción")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de fin")
    estado = models.CharField(
        choices=ESTADOS_KANBAN, max_length=20, default="pendiente", verbose_name="Estado"
    )
    id_pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, verbose_name="Pedido")
    # Responsable opcional de la tarea (el trabajador se asigna, sobre todo, en
    # cada actividad).
    id_empleado = models.ForeignKey(
        Empleado,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="tareas_asignadas",
        verbose_name="Responsable",
    )
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tareas_confirmadas",
        verbose_name="Confirmado por",
    )
    fecha_confirmacion = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de confirmación"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tarea de pedido"
        verbose_name_plural = "Tareas de pedido"
        ordering = ["-id"]

    def __str__(self):
        return self.nombre


class Actividades(models.Model):
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    descripcion = models.CharField(max_length=1000, verbose_name="Descripción")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de fin")
    estado = models.CharField(
        choices=ESTADOS_KANBAN, max_length=20, default="pendiente", verbose_name="Estado"
    )
    id_tarea = models.ForeignKey(TareasPedido, on_delete=models.PROTECT, verbose_name="Tarea")
    # Trabajador que ejecuta la actividad: es quien se ve agrupado en el tablero.
    # Nullable en la tabla para no romper los registros viejos; obligatorio en el
    # formulario de la vista.
    id_empleado = models.ForeignKey(
        Empleado,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="actividades",
        verbose_name="Trabajador",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ["-id"]

    def __str__(self):
        return self.nombre


class Historial(models.Model):
    hora_creacion = models.TimeField(verbose_name="Hora de creación")
    fecha_creacion = models.DateField(verbose_name="Fecha de creación")
    id_cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    id_empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, verbose_name="Empleado")
    id_producto = models.ForeignKey(Producto, on_delete=models.PROTECT, verbose_name="Producto")
    id_pedido = models.ForeignKey(
        Pedido,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="historial",
        verbose_name="Pedido",
    )
    accion = models.CharField(max_length=60, default="registro", verbose_name="Acción")
    detalle = models.TextField(default="", blank=True, verbose_name="Detalle")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="historial_registrado",
        verbose_name="Usuario",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Historial"
        verbose_name_plural = "Historiales"
        ordering = ["-id"]

    def __str__(self):
        return f"Historial #{self.pk} · {self.fecha_creacion}"


class Calendario(models.Model):
    fecha = models.DateField(verbose_name="Fecha")
    anio = models.IntegerField(verbose_name="Año")
    mes = models.IntegerField(verbose_name="Mes")
    nombre_mes = models.CharField(max_length=20, verbose_name="Nombre del mes")
    dia = models.IntegerField(verbose_name="Día")
    nombre_dia = models.CharField(max_length=20, verbose_name="Nombre del día")
    id_pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, verbose_name="Pedido")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Calendario"
        verbose_name_plural = "Calendario"
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.nombre_dia} {self.dia} · {self.id_pedido}"


class Notificacion(models.Model):
    """Aviso persistente para un usuario (campana del header)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones_kanview",
        verbose_name="Usuario",
    )
    tipo = models.CharField(max_length=40, verbose_name="Tipo")
    mensaje = models.CharField(max_length=255, verbose_name="Mensaje")
    url = models.CharField(max_length=500, default="", blank=True, verbose_name="Enlace")
    leida = models.BooleanField(default=False, verbose_name="Leída")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-fecha_creacion", "-id"]
        indexes = [
            models.Index(fields=["usuario", "leida"]),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.mensaje[:40]}"


class SolicitudModificacionPedido(models.Model):
    """Cambio solicitado por el cliente sobre un pedido."""

    ESTADOS = (
        ("pendiente", "Pendiente"),
        ("aceptada", "Aceptada"),
        ("rechazada", "Rechazada"),
    )

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="solicitudes_modificacion",
        verbose_name="Pedido",
    )
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="solicitudes_modificacion",
        verbose_name="Solicitado por",
    )
    descripcion = models.TextField(verbose_name="Cambio solicitado")
    estado = models.CharField(choices=ESTADOS, max_length=10, default="pendiente", verbose_name="Estado")
    respuesta = models.TextField(default="", blank=True, verbose_name="Respuesta")
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="solicitudes_revisadas",
        verbose_name="Revisado por",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Solicitud de modificación"
        verbose_name_plural = "Solicitudes de modificación"
        ordering = ["-id"]

    def __str__(self):
        return f"Solicitud #{self.pk} · {self.pedido}"


class Factura(models.Model):
    """Factura emitida para un pedido; el PDF se genera a partir de estos datos."""

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name="factura",
        verbose_name="Pedido",
    )
    numero = models.CharField(max_length=30, unique=True, verbose_name="Número")
    fecha_emision = models.DateTimeField(default=timezone.now, verbose_name="Fecha de emisión")
    cliente_nombre = models.CharField(max_length=100, verbose_name="Cliente")
    cliente_documento = models.CharField(max_length=20, default="", blank=True, verbose_name="Documento del cliente")
    cliente_correo = models.EmailField(max_length=254, default="", blank=True, verbose_name="Correo del cliente")
    cliente_direccion = models.CharField(max_length=50, default="", blank=True, verbose_name="Dirección del cliente")
    producto_nombre = models.CharField(max_length=100, verbose_name="Producto")
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    precio_unitario = models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Precio unitario")
    subtotal = models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Subtotal")
    iva_porcentaje = models.DecimalField(decimal_places=2, max_digits=5, default=0, verbose_name="IVA (%)")
    iva_valor = models.DecimalField(decimal_places=2, max_digits=14, default=0, verbose_name="IVA")
    total = models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Total")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="facturas_creadas",
        verbose_name="Creado por",
    )

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-fecha_emision", "-id"]

    def __str__(self):
        return f"Factura {self.numero} · {self.pedido}"


class PerfilUsuario(models.Model):
    """Preferencias de seguridad y aceptación de términos de una cuenta."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_kanview",
        verbose_name="Usuario",
    )
    totp_secret = models.CharField(max_length=64, default="", blank=True, verbose_name="Secreto TOTP")
    totp_habilitado = models.BooleanField(default=False, verbose_name="2FA activo")
    codigos_respaldo = models.JSONField(default=list, blank=True, verbose_name="Códigos de respaldo")
    terminos_version = models.CharField(max_length=20, default="", blank=True, verbose_name="Versión de términos")
    terminos_aceptados_en = models.DateTimeField(null=True, blank=True, verbose_name="Términos aceptados en")

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"Perfil de {self.usuario}"


class RegistroAuditoria(models.Model):
    """Log de acciones relevantes del sistema."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_auditoria",
        verbose_name="Usuario",
    )
    accion = models.CharField(max_length=60, verbose_name="Acción")
    entidad = models.CharField(max_length=60, verbose_name="Entidad")
    objeto_id = models.CharField(max_length=40, default="", blank=True, verbose_name="ID afectado")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    user_agent = models.CharField(max_length=255, default="", blank=True, verbose_name="Navegador")
    datos = models.JSONField(default=dict, blank=True, verbose_name="Datos adicionales")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-fecha_creacion", "-id"]
        indexes = [
            models.Index(fields=["entidad", "objeto_id"]),
            models.Index(fields=["usuario", "fecha_creacion"]),
        ]

    def __str__(self):
        return f"{self.fecha_creacion:%Y-%m-%d %H:%M} · {self.accion} · {self.entidad}"


class Conversacion(models.Model):
    """Conversación directa entre dos usuarios."""

    usuario_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversaciones_iniciadas",
        verbose_name="Usuario A",
    )
    usuario_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversaciones_recibidas",
        verbose_name="Usuario B",
    )
    creada = models.DateTimeField(auto_now_add=True, verbose_name="Creada")
    actualizada = models.DateTimeField(auto_now=True, verbose_name="Actualizada")

    class Meta:
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"
        ordering = ["-actualizada"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario_a", "usuario_b"],
                name="conversacion_directa_unica",
            ),
        ]

    def __str__(self):
        return f"{self.usuario_a} ↔ {self.usuario_b}"

    def otro(self, usuario):
        return self.usuario_b if self.usuario_a_id == usuario.pk else self.usuario_a

    def incluye(self, usuario):
        return usuario.pk in (self.usuario_a_id, self.usuario_b_id)


class Mensaje(models.Model):
    """Mensaje enviado dentro de una conversación directa."""

    conversacion = models.ForeignKey(
        Conversacion,
        on_delete=models.CASCADE,
        related_name="mensajes",
        verbose_name="Conversación",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mensajes_chat",
        verbose_name="Autor",
    )
    texto = models.TextField(verbose_name="Mensaje")
    creado = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    leido = models.BooleanField(default=False, verbose_name="Leído")

    class Meta:
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        ordering = ["creado", "id"]
        indexes = [
            models.Index(fields=["conversacion", "creado"]),
        ]

    def __str__(self):
        return f"{self.autor}: {self.texto[:40]}"
