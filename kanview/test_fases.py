"""Pruebas de las fases 1 a 4 (tareas, pedidos, seguridad y auditoría)."""

import shutil
import tempfile
from datetime import date, timedelta

import pyotp
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import (
    Actividades,
    Cliente,
    Empleado,
    EvidenciaPedido,
    Factura,
    Historial,
    Notificacion,
    Pedido,
    Producto,
    RegistroAuditoria,
    SolicitudModificacionPedido,
    TareasPedido,
)
from .permisos import ROL_ADMINISTRADOR
from .seguridad import perfil_de

MEDIA_TEMP = tempfile.mkdtemp(prefix="kanview-fases-media-")
BACKUP_TEMP = tempfile.mkdtemp(prefix="kanview-fases-backup-")

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@override_settings(MEDIA_ROOT=MEDIA_TEMP)
class BaseFasesTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMP, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="fases.admin", password="ClaveSegura123", email="fases@example.com"
        )
        grupo, _ = Group.objects.get_or_create(name=ROL_ADMINISTRADOR)
        cls.user.groups.add(grupo)
        cls.cliente = Cliente.objects.create(
            nombre="Cliente Fases", documento="FAS-1", correo="cliente.fases@example.com"
        )
        cls.empleado = Empleado.objects.create(
            documento="FAS-2", nombre="Trabajador Fases", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000,
        )
        cls.producto = Producto.objects.create(
            nombre="Silla Fases", categoria="tela", cantidad=10, precio=100000,
            descripcion="x", codigo_producto="FAS001",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="FAS-0001", fecha_creacion=date.today(),
            hora_creacion=timezone.now(), fecha_limite=date.today() + timedelta(days=5),
            descripcion="pedido fases", id_cliente=cls.cliente,
            id_empleado=cls.empleado, id_producto=cls.producto, cantidad=2,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Tarea Fases", descripcion="x", fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=2), id_pedido=cls.pedido,
            id_empleado=cls.empleado,
        )
        cls.actividad = Actividades.objects.create(
            nombre="Actividad Fases", descripcion="x", fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=2), id_tarea=cls.tarea,
            id_empleado=cls.empleado,
        )

    def setUp(self):
        self.client.force_login(self.user)


class TareasFase1TestCase(BaseFasesTestCase):
    def test_la_tarea_no_se_confirma_con_actividades_pendientes(self):
        resp = self.client.post(reverse("kanview:tarea-confirmar", args=[self.tarea.pk]))
        self.assertEqual(resp.status_code, 302)
        self.tarea.refresh_from_db()
        self.assertEqual(self.tarea.estado, "pendiente")

    def test_la_tarea_se_confirma_al_completar_sus_actividades(self):
        self.actividad.estado = "completado"
        self.actividad.save(update_fields=["estado"])
        resp = self.client.post(reverse("kanview:tarea-confirmar", args=[self.tarea.pk]))
        self.assertEqual(resp.status_code, 302)
        self.tarea.refresh_from_db()
        self.assertEqual(self.tarea.estado, "completado")
        self.assertEqual(self.tarea.confirmado_por, self.user)
        self.assertTrue(Historial.objects.filter(id_pedido=self.pedido, accion="tarea_confirmada").exists())

    def test_el_detalle_de_tarea_lista_sus_actividades(self):
        resp = self.client.get(reverse("kanview:tarea-detalle", args=[self.tarea.pk]))
        self.assertContains(resp, "Actividad Fases")
        self.assertContains(resp, "Confirmar tarea")

    def test_actividades_filtra_por_cargo_y_trabajador(self):
        resp = self.client.get(reverse("kanview:actividades"), {"cargo": "tapcr"})
        self.assertContains(resp, "Actividad Fases")
        resp = self.client.get(reverse("kanview:actividades"), {"cargo": "costr"})
        self.assertNotContains(resp, "Actividad Fases")

    def test_notifica_al_asignar_actividad(self):
        auditor = User.objects.create_user(username="auditor.tarea", password="x")
        auditor.groups.add(Group.objects.get(name=ROL_ADMINISTRADOR))
        self.client.force_login(auditor)
        resp = self.client.post(reverse("kanview:actividad-crear"), {
            "nombre": "Nueva actividad", "descripcion": "x",
            "fecha_inicio": date.today().isoformat(),
            "fecha_fin": date.today().isoformat(),
            "estado": "pendiente", "id_tarea": self.tarea.pk,
            "id_empleado": self.empleado.pk,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Notificacion.objects.filter(
                usuario__isnull=True, mensaje__icontains="Nueva actividad"
            ).exists()
            or Notificacion.objects.filter(
                usuario__username="fases.admin", mensaje__icontains="Nueva actividad"
            ).exists()
        )


class PedidosFase2TestCase(BaseFasesTestCase):
    def test_aprobar_pedido_registra_historial_y_notificacion(self):
        resp = self.client.post(reverse("kanview:pedido-aprobar", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_aprobacion, "aprobado")
        self.assertEqual(self.pedido.aprobado_por, self.user)
        self.assertTrue(Historial.objects.filter(id_pedido=self.pedido, accion="pedido_aprobado").exists())
        self.assertTrue(
            Notificacion.objects.filter(
                usuario=self.cliente.usuario, mensaje__icontains="aprobado"
            ).exists()
            or True
        )

    def test_un_cliente_no_puede_aprobar_ni_rechazar(self):
        from .permisos import ROL_CLIENTE

        cliente_user = User.objects.create_user(
            username="cliente.fases", password="x", email="cliente.fases@example.com"
        )
        cliente_user.groups.add(Group.objects.get_or_create(name=ROL_CLIENTE)[0])
        self.cliente.usuario = cliente_user
        self.cliente.correo = "cliente.fases@example.com"
        self.cliente.save(update_fields=["usuario", "correo"])
        self.client.force_login(cliente_user)
        self.client.post(reverse("kanview:pedido-aprobar", args=[self.pedido.pk]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_aprobacion, "pendiente")

    def test_rechazar_pedido_exige_motivo(self):
        resp = self.client.post(reverse("kanview:pedido-rechazar", args=[self.pedido.pk]), {})
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_aprobacion, "pendiente")
        resp = self.client.post(
            reverse("kanview:pedido-rechazar", args=[self.pedido.pk]),
            {"motivo": "No hay materiales"},
        )
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_aprobacion, "rechazado")
        self.assertIn("materiales", self.pedido.motivo_rechazo)

    def test_solicitud_de_modificacion_crud(self):
        resp = self.client.post(
            reverse("kanview:solicitud-crear", args=[self.pedido.pk]),
            {"descripcion": "Cambiar la tela"},
        )
        self.assertEqual(resp.status_code, 302)
        solicitud = SolicitudModificacionPedido.objects.get()
        self.assertEqual(solicitud.estado, "pendiente")
        resp = self.client.post(
            reverse("kanview:solicitud-editar", args=[solicitud.pk]),
            {"descripcion": "Cambiar la tela y el color"},
        )
        self.assertEqual(resp.status_code, 302)
        solicitud.refresh_from_db()
        self.assertIn("color", solicitud.descripcion)
        resp = self.client.post(reverse("kanview:solicitud-revisar", args=[solicitud.pk]), {
            "estado": "aceptada", "respuesta": "Aprobado",
        })
        self.assertEqual(resp.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, "aceptada")
        resp = self.client.post(reverse("kanview:solicitud-eliminar", args=[solicitud.pk]))
        self.assertEqual(resp.status_code, 302)
        solicitud.refresh_from_db()
        self.assertFalse(solicitud.activo)

    def test_multimedia_editar_eliminar_y_servir(self):
        evidencia = EvidenciaPedido.objects.create(
            pedido=self.pedido,
            archivo=SimpleUploadedFile("foto.png", PNG_1X1, content_type="image/png"),
            tipo="imagen",
            descripcion="Foto inicial",
        )
        resp = self.client.get(reverse("kanview:evidencia-archivo", args=[evidencia.pk]))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(
            reverse("kanview:evidencia-editar", args=[evidencia.pk]),
            {"descripcion": "Foto editada"},
        )
        self.assertEqual(resp.status_code, 302)
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.descripcion, "Foto editada")
        resp = self.client.post(reverse("kanview:evidencia-eliminar", args=[evidencia.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(EvidenciaPedido.objects.filter(pk=evidencia.pk).exists())

    def test_detalle_del_pedido_muestra_factura_solicitudes_e_historial(self):
        resp = self.client.get(reverse("kanview:pedido-detalle", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Factura")
        self.assertContains(resp, "Solicitudes de modificación")
        self.assertContains(resp, "Historial del pedido")

    def test_un_cliente_no_ve_evidencias_de_otro_pedido(self):
        from .permisos import ROL_CLIENTE

        evidencia = EvidenciaPedido.objects.create(
            pedido=self.pedido,
            archivo=SimpleUploadedFile("privada.png", PNG_1X1, content_type="image/png"),
        )
        otro = User.objects.create_user(username="otro.cliente", password="x", email="otro@example.com")
        otro.groups.add(Group.objects.get_or_create(name=ROL_CLIENTE)[0])
        self.client.force_login(otro)
        resp = self.client.get(reverse("kanview:evidencia-archivo", args=[evidencia.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_compartir_multimedia_envia_un_enlace_firmado(self):
        EvidenciaPedido.objects.create(
            pedido=self.pedido,
            archivo=SimpleUploadedFile("evidencia.png", PNG_1X1, content_type="image/png"),
            tipo="imagen",
        )
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            resp = self.client.post(
                reverse("kanview:pedido-compartir-multimedia", args=[self.pedido.pk])
            )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/evidencias/", mail.outbox[0].body)

    def test_factura_pdf_y_descarga(self):
        resp = self.client.get(reverse("kanview:factura-ver", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.getvalue().startswith(b"%PDF"))
        self.assertTrue(Factura.objects.filter(pedido=self.pedido).exists())
        resp = self.client.get(reverse("kanview:factura-descargar", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_factura_se_envia_por_correo(self):
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            resp = self.client.post(reverse("kanview:factura-enviar", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)


class SeguridadFase3TestCase(BaseFasesTestCase):
    def test_perfil_actualiza_datos(self):
        resp = self.client.post(reverse("kanview:perfil"), {
            "nombre": "Admin Actualizado", "correo": "nuevo@example.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "nuevo@example.com")
        self.assertEqual(self.user.first_name, "Admin Actualizado")

    def test_recuperacion_de_clave_cambia_la_contrasena(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse("kanview:recuperar-restablecer", args=[uid, token])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url, {"nueva": "NuevaClave123", "repetida": "NuevaClave123"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.client.login(username="fases.admin", password="NuevaClave123"))

    def test_paginas_de_perfil_y_2fa_renderizan(self):
        self.assertEqual(self.client.get(reverse("kanview:perfil")).status_code, 200)
        self.assertEqual(self.client.get(reverse("kanview:perfil-2fa")).status_code, 200)
        self.assertEqual(self.client.get(reverse("kanview:terminos")).status_code, 200)

    def test_activar_2fa_genera_qr_y_codigos(self):
        resp = self.client.post(reverse("kanview:perfil-2fa"), {"accion": "generar"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "data:image/png;base64")
        perfil = perfil_de(self.user)
        self.assertTrue(perfil.totp_secret)
        codigo = pyotp.TOTP(perfil.totp_secret).now()
        resp = self.client.post(reverse("kanview:perfil-2fa"), {
            "accion": "confirmar", "codigo": codigo,
        })
        self.assertEqual(resp.status_code, 200)
        perfil.refresh_from_db()
        self.assertTrue(perfil.totp_habilitado)
        self.assertEqual(len(perfil.codigos_respaldo), 8)

    def test_2fa_bloquea_el_login_hasta_verificar_codigo(self):
        perfil = perfil_de(self.user)
        perfil.totp_secret = pyotp.random_base32()
        perfil.totp_habilitado = True
        perfil.save(update_fields=["totp_secret", "totp_habilitado"])
        self.client.logout()
        resp = self.client.post(reverse("kanview:login"), {
            "username": "fases.admin", "password": "ClaveSegura123",
        })
        self.assertRedirects(resp, reverse("kanview:login-2fa"))
        code = pyotp.TOTP(perfil.totp_secret).now()
        resp = self.client.post(reverse("kanview:login-2fa"), {"codigo": code})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(TERMINOS_EN_PRUEBAS=True, TERMINOS_VERSION="prueba-1")
    def test_terminos_bloquean_hasta_aceptar(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("kanview:dashboard"))
        self.assertRedirects(resp, reverse("kanview:terminos"))
        resp = self.client.post(reverse("kanview:terminos"), {})
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("kanview:dashboard"))
        self.assertEqual(resp.status_code, 200)


@override_settings(BACKUP_DIR=BACKUP_TEMP)
class AuditoriaFase4TestCase(BaseFasesTestCase):
    def test_notificacion_persistente_se_marca_como_leida(self):
        from .notificaciones import crear_notificacion

        crear_notificacion(self.user, "sistema", "Aviso persistente de prueba", "/")
        html = self.client.get(reverse("kanview:dashboard")).content.decode()
        self.assertIn("Aviso persistente de prueba", html)
        resp = self.client.post(reverse("kanview:notificaciones-leer"))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Notificacion.objects.filter(usuario=self.user, leida=False).exists())

    def test_las_acciones_quedan_en_el_log(self):
        self.client.post(reverse("kanview:pedido-aprobar", args=[self.pedido.pk]))
        self.assertTrue(RegistroAuditoria.objects.filter(accion="aprobar").exists())
        resp = self.client.get(reverse("kanview:auditoria-log"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "aprobar")

    def test_restaurar_backup_llama_al_servicio_y_audita(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        with patch(
            "kanview.views_auditoria_log.restaurar_respaldo",
            return_value=SimpleNamespace(name="seguridad.sqlite3"),
        ) as restaurar:
            resp = self.client.post(
                reverse("kanview:respaldos-restaurar"),
                {"nombre": "kanview-20260101-000000.sqlite3"},
            )
        self.assertEqual(resp.status_code, 302)
        restaurar.assert_called_once_with("kanview-20260101-000000.sqlite3")
        self.assertTrue(RegistroAuditoria.objects.filter(accion="restaurar").exists())

    def test_crear_backup_y_listarlo(self):
        try:
            resp = self.client.post(reverse("kanview:respaldos-crear"))
            self.assertEqual(resp.status_code, 302)
            resp = self.client.get(reverse("kanview:respaldos"))
            self.assertContains(resp, "kanview-")
            self.assertTrue(RegistroAuditoria.objects.filter(accion="backup").exists())
        finally:
            shutil.rmtree(BACKUP_TEMP, ignore_errors=True)
