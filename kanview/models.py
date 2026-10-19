from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

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
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class AnalisisFinanciero(models.Model):
    gastos = models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Gastos")
    fuentes_ingresos = models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Fuentes de ingresos")
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


class Pedido(models.Model):
    ESTADOS = (
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
    )

    # El código se genera solo (PED-0001) al crear el pedido.
    codigo_pedido = models.CharField(max_length=20, unique=True, verbose_name="Código")
    fecha_creacion = models.DateField(verbose_name="Fecha de creación")
    hora_creacion = models.DateTimeField(verbose_name="Hora de creación")
    fecha_limite = models.DateField(null=True, blank=True, verbose_name="Fecha límite de entrega")
    estado = models.CharField(choices=ESTADOS, max_length=10, default="activo", verbose_name="Estado")
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


class EvidenciaPedido(models.Model):
    """Imágenes que se suben al crear el pedido (galería de evidencias)."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="galeria", verbose_name="Pedido")
    imagen = models.ImageField(upload_to="evidencias/%Y/%m/", verbose_name="Imagen")
    descripcion = models.CharField(max_length=255, default="", blank=True, verbose_name="Descripción")
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de carga")

    class Meta:
        verbose_name = "Evidencia de pedido"
        verbose_name_plural = "Evidencias de pedido"
        ordering = ["-id"]

    def __str__(self):
        return f"Evidencia #{self.pk} · {self.pedido}"


ESTADOS_KANBAN = (
    ("pendiente", "Pendiente"),
    ("en progreso", "En progreso"),
    ("completado", "Completado"),
)


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
