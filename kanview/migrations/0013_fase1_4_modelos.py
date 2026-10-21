from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("kanview", "0012_alter_cliente_cliente_correo_unico_si_no_vacio_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="evidenciapedido",
            old_name="imagen",
            new_name="archivo",
        ),
        migrations.AlterField(
            model_name="evidenciapedido",
            name="archivo",
            field=models.FileField(upload_to="evidencias/%Y/%m/", verbose_name="Archivo"),
        ),
        migrations.AddField(
            model_name="evidenciapedido",
            name="tipo",
            field=models.CharField(
                choices=[("imagen", "Imagen"), ("video", "Video")],
                default="imagen",
                max_length=10,
                verbose_name="Tipo",
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="cantidad",
            field=models.PositiveIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1, "La cantidad debe ser mayor que cero.")],
                verbose_name="Cantidad",
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="estado_aprobacion",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente de aprobación"),
                    ("aprobado", "Aprobado"),
                    ("rechazado", "Rechazado"),
                ],
                default="pendiente",
                max_length=10,
                verbose_name="Aprobación",
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="motivo_rechazo",
            field=models.TextField(blank=True, default="", verbose_name="Motivo del rechazo"),
        ),
        migrations.AddField(
            model_name="pedido",
            name="aprobado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_aprobados",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Aprobado por",
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="fecha_aprobacion",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Fecha de aprobación"),
        ),
        migrations.AddField(
            model_name="tareaspedido",
            name="confirmado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tareas_confirmadas",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Confirmado por",
            ),
        ),
        migrations.AddField(
            model_name="tareaspedido",
            name="fecha_confirmacion",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Fecha de confirmación"),
        ),
        migrations.AddField(
            model_name="historial",
            name="id_pedido",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="historial",
                to="kanview.pedido",
                verbose_name="Pedido",
            ),
        ),
        migrations.AddField(
            model_name="historial",
            name="accion",
            field=models.CharField(default="registro", max_length=60, verbose_name="Acción"),
        ),
        migrations.AddField(
            model_name="historial",
            name="detalle",
            field=models.TextField(blank=True, default="", verbose_name="Detalle"),
        ),
        migrations.AddField(
            model_name="historial",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="historial_registrado",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Usuario",
            ),
        ),
        migrations.CreateModel(
            name="Notificacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(max_length=40, verbose_name="Tipo")),
                ("mensaje", models.CharField(max_length=255, verbose_name="Mensaje")),
                ("url", models.CharField(blank=True, default="", max_length=500, verbose_name="Enlace")),
                ("leida", models.BooleanField(default=False, verbose_name="Leída")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, verbose_name="Fecha")),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notificaciones_kanview",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notificación",
                "verbose_name_plural": "Notificaciones",
                "ordering": ["-fecha_creacion", "-id"],
                "indexes": [models.Index(fields=["usuario", "leida"], name="kanview_not_usuario_7c0d8a_idx")],
            },
        ),
        migrations.CreateModel(
            name="SolicitudModificacionPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descripcion", models.TextField(verbose_name="Cambio solicitado")),
                (
                    "estado",
                    models.CharField(
                        choices=[("pendiente", "Pendiente"), ("aceptada", "Aceptada"), ("rechazada", "Rechazada")],
                        default="pendiente",
                        max_length=10,
                        verbose_name="Estado",
                    ),
                ),
                ("respuesta", models.TextField(blank=True, default="", verbose_name="Respuesta")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True, verbose_name="Última actualización")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                (
                    "pedido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitudes_modificacion",
                        to="kanview.pedido",
                        verbose_name="Pedido",
                    ),
                ),
                (
                    "revisado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="solicitudes_revisadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Revisado por",
                    ),
                ),
                (
                    "solicitado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="solicitudes_modificacion",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Solicitado por",
                    ),
                ),
            ],
            options={
                "verbose_name": "Solicitud de modificación",
                "verbose_name_plural": "Solicitudes de modificación",
                "ordering": ["-id"],
            },
        ),
        migrations.CreateModel(
            name="Factura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.CharField(max_length=30, unique=True, verbose_name="Número")),
                ("fecha_emision", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Fecha de emisión")),
                ("cliente_nombre", models.CharField(max_length=100, verbose_name="Cliente")),
                ("cliente_documento", models.CharField(blank=True, default="", max_length=20, verbose_name="Documento del cliente")),
                ("cliente_correo", models.EmailField(blank=True, default="", max_length=254, verbose_name="Correo del cliente")),
                ("cliente_direccion", models.CharField(blank=True, default="", max_length=50, verbose_name="Dirección del cliente")),
                ("producto_nombre", models.CharField(max_length=100, verbose_name="Producto")),
                ("cantidad", models.PositiveIntegerField(default=1, verbose_name="Cantidad")),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Precio unitario")),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Subtotal")),
                ("iva_porcentaje", models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name="IVA (%)")),
                ("iva_valor", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="IVA")),
                ("total", models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Total")),
                (
                    "creado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="facturas_creadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creado por",
                    ),
                ),
                (
                    "pedido",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="factura",
                        to="kanview.pedido",
                        verbose_name="Pedido",
                    ),
                ),
            ],
            options={
                "verbose_name": "Factura",
                "verbose_name_plural": "Facturas",
                "ordering": ["-fecha_emision", "-id"],
            },
        ),
        migrations.CreateModel(
            name="PerfilUsuario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("totp_secret", models.CharField(blank=True, default="", max_length=64, verbose_name="Secreto TOTP")),
                ("totp_habilitado", models.BooleanField(default=False, verbose_name="2FA activo")),
                ("codigos_respaldo", models.JSONField(blank=True, default=list, verbose_name="Códigos de respaldo")),
                ("terminos_version", models.CharField(blank=True, default="", max_length=20, verbose_name="Versión de términos")),
                ("terminos_aceptados_en", models.DateTimeField(blank=True, null=True, verbose_name="Términos aceptados en")),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perfil_kanview",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Perfil de usuario",
                "verbose_name_plural": "Perfiles de usuario",
            },
        ),
        migrations.CreateModel(
            name="RegistroAuditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accion", models.CharField(max_length=60, verbose_name="Acción")),
                ("entidad", models.CharField(max_length=60, verbose_name="Entidad")),
                ("objeto_id", models.CharField(blank=True, default="", max_length=40, verbose_name="ID afectado")),
                ("descripcion", models.CharField(max_length=255, verbose_name="Descripción")),
                ("ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("user_agent", models.CharField(blank=True, default="", max_length=255, verbose_name="Navegador")),
                ("datos", models.JSONField(blank=True, default=dict, verbose_name="Datos adicionales")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, verbose_name="Fecha")),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registros_auditoria",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro de auditoría",
                "verbose_name_plural": "Registros de auditoría",
                "ordering": ["-fecha_creacion", "-id"],
                "indexes": [
                    models.Index(fields=["entidad", "objeto_id"], name="kanview_reg_entidad_48a4b3_idx"),
                    models.Index(fields=["usuario", "fecha_creacion"], name="kanview_reg_usuario_2f6c1e_idx"),
                ],
            },
        ),
    ]
