"""Pruebas de las reglas de negocio del CRUD (FBV) de Kanview.

Cubren los permisos por rol, desactivar en vez de borrar, la unicidad de correo,
los formularios construidos en las vistas (sin forms.py), el stock en Producto,
el código automático del pedido, la galería, la fecha límite, la API cerrada y
el tablero único de procesos con su estado calculado.
"""

import shutil
import tempfile
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .models import (
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Cliente,
    Empleado,
    EvidenciaPedido,
    Historial,
    Notificacion,
    Pedido,
    Producto,
    Recordatorio,
    TareasPedido,
)
from .permisos import ROL_ADMINISTRADOR, ROL_CLIENTE, ROL_TRABAJADOR

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="kanview-tests-media-")

# PNG de 1x1 transparente (válido para ImageField/Pillow).
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _grupo(nombre):
    grupo, _ = Group.objects.get_or_create(name=nombre)
    return grupo


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CrudModulesTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="tester", password="pass12345", is_staff=True
        )
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))

        cls.cliente = Cliente.objects.create(
            nombre="Juan", fecha_nacimiento=date(1990, 1, 1), documento="1",
            celular="300", direccion="Calle 1", edad=30,
        )
        cls.empleado = Empleado.objects.create(
            documento="2", nombre="Ana", cargo="tapcr", celular="301",
            direccion="Calle 2", salario=1000, edad=25,
            fecha_nacimiento=date(1995, 1, 1), tareas_realizadas=0,
        )
        cls.administrador = Administrador.objects.create(
            nombre="Admin", celular="302", documento="3"
        )
        cls.producto = Producto.objects.create(
            nombre="Silla", categoria="tela", cantidad=5, precio=100,
            descripcion="x", codigo_producto="A1B2C3",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="P00001", fecha_creacion=date(2026, 10, 16),
            hora_creacion=timezone.now(), estado="activo", evidencias="",
            descripcion="x", fecha_limite=date(2026, 10, 20),
            id_cliente=cls.cliente, id_empleado=cls.empleado,
            id_producto=cls.producto,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Cortar", descripcion="x", fecha_inicio=date(2026, 10, 16),
            fecha_fin=date(2026, 10, 17), estado="pendiente", id_pedido=cls.pedido,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _modules(self):
        """(prefijo, modelo, datos de creación, datos de edición) de los módulos CRUD."""
        return [
            (
                "analisis-financiero",
                AnalisisFinanciero,
                {"gastos": "100.00", "fuentes_ingresos": "500.00",
                 "productos_vendidos": "5", "id_administrador": self.administrador.pk},
                {"gastos": "200.00", "fuentes_ingresos": "600.00",
                 "productos_vendidos": "6", "id_administrador": self.administrador.pk},
            ),
            (
                "tarea",
                TareasPedido,
                {"nombre": "Cortar", "descripcion": "x", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-17", "estado": "pendiente", "id_pedido": self.pedido.pk,
                 "id_empleado": self.empleado.pk},
                {"nombre": "Coser", "descripcion": "y", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-18", "estado": "en progreso", "id_pedido": self.pedido.pk,
                 "id_empleado": self.empleado.pk},
            ),
            (
                "actividad",
                Actividades,
                {"nombre": "Medir", "descripcion": "x", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-16", "estado": "pendiente", "id_tarea": self.tarea.pk,
                 "id_empleado": self.empleado.pk},
                {"nombre": "Pegar", "descripcion": "y", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-17", "estado": "completado", "id_tarea": self.tarea.pk,
                 "id_empleado": self.empleado.pk},
            ),
            (
                "historial",
                Historial,
                {"hora_creacion": "10:30", "fecha_creacion": "2026-10-16",
                 "id_cliente": self.cliente.pk, "id_empleado": self.empleado.pk,
                 "id_producto": self.producto.pk},
                {"hora_creacion": "11:30", "fecha_creacion": "2026-10-16",
                 "id_cliente": self.cliente.pk, "id_empleado": self.empleado.pk,
                 "id_producto": self.producto.pk},
            ),
            (
                "calendario",
                Calendario,
                {"fecha": "2026-10-16", "anio": "2026", "mes": "10",
                 "nombre_mes": "Octubre", "dia": "16", "nombre_dia": "Viernes",
                 "id_pedido": self.pedido.pk},
                {"fecha": "2026-10-17", "anio": "2026", "mes": "10",
                 "nombre_mes": "Octubre", "dia": "17", "nombre_dia": "Sábado",
                 "id_pedido": self.pedido.pk},
            ),
        ]

    # ---- Listas y formularios ---------------------------------------------

    def test_all_list_pages_render(self):
        prefijos = [
            "cliente", "empleado", "administrador", "producto", "pedido",
            "analisis-financiero", "tarea", "actividad", "historial", "calendario",
        ]
        for prefijo in prefijos:
            url = reverse(f"kanview:{prefijo}-lista")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertContains(resp, "Estado")

    def test_los_modulos_de_inventario_y_catalogo_ya_no_existen(self):
        """Los CRUD de Inventario y Catálogo desaparecieron con sus modelos."""
        for nombre in (
            "inventario-lista", "inventario-crear", "catalogo-lista",
            "catalogo-crear", "catalogo-editar",
        ):
            with self.assertRaises(NoReverseMatch, msg=nombre):
                reverse(f"kanview:{nombre}")

    def test_create_forms_render(self):
        for nombre, _modelo, _crear, _editar in self._modules():
            url = reverse(f"kanview:{nombre}-crear")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)

    def test_formulario_de_tarea_pide_pedido_antes_de_fechas(self):
        resp = self.client.get(reverse("kanview:tarea-crear"))
        html = resp.content.decode()
        self.assertLess(html.index('name="id_pedido"'), html.index('name="fecha_inicio"'))
        self.assertContains(resp, 'id="restriccion-fechas"')
        self.assertContains(resp, '"selector": "id_pedido"')
        self.assertContains(resp, f'"desde": "{self.pedido.fecha_creacion.isoformat()}"')
        self.assertContains(resp, f'"hasta": "{self.pedido.fecha_limite.isoformat()}"')

    def test_formulario_de_actividad_pide_tarea_antes_de_fechas(self):
        resp = self.client.get(reverse("kanview:actividad-crear"))
        html = resp.content.decode()
        self.assertLess(html.index('name="id_tarea"'), html.index('name="fecha_inicio"'))
        self.assertContains(resp, '"selector": "id_tarea"')
        self.assertContains(resp, f'"desde": "{self.pedido.fecha_creacion.isoformat()}"')
        self.assertContains(resp, f'"hasta": "{self.pedido.fecha_limite.isoformat()}"')

    def test_otros_formularios_no_cargan_restriccion_de_fechas(self):
        resp = self.client.get(reverse("kanview:producto-crear"))
        self.assertNotContains(resp, 'id="restriccion-fechas"')

    # ---- Desactivar en vez de borrar --------------------------------------

    def test_create_update_desactivar_reactivar(self):
        for nombre, modelo, crear, editar in self._modules():
            resp = self.client.post(reverse(f"kanview:{nombre}-crear"), crear)
            self.assertEqual(resp.status_code, 302, f"{nombre} crear")
            obj = modelo.objects.order_by("-pk").first()
            self.assertIsNotNone(obj, f"{nombre} creado")
            self.assertTrue(obj.activo, f"{nombre} nace activo")

            resp = self.client.post(
                reverse(f"kanview:{nombre}-editar", args=[obj.pk]), editar
            )
            self.assertEqual(resp.status_code, 302, f"{nombre} editar")

            # Eliminar = desactivar: el registro sigue existiendo.
            resp = self.client.post(reverse(f"kanview:{nombre}-eliminar", args=[obj.pk]))
            self.assertEqual(resp.status_code, 302, f"{nombre} desactivar")
            obj.refresh_from_db()
            self.assertFalse(obj.activo, f"{nombre} quedó inactivo")
            self.assertTrue(
                modelo.objects.filter(pk=obj.pk).exists(), f"{nombre} no se borró"
            )

            # Reactivar lo devuelve.
            resp = self.client.post(reverse(f"kanview:{nombre}-reactivar", args=[obj.pk]))
            self.assertEqual(resp.status_code, 302, f"{nombre} reactivar")
            obj.refresh_from_db()
            self.assertTrue(obj.activo, f"{nombre} reactivado")

    # ---- Correo: único solo cuando está escrito (bug de dos sin correo) ------

    def test_dos_clientes_sin_correo_y_correo_repetido(self):
        """Dos clientes sin correo conviven; un correo repetido sí se rechaza."""
        uno = Cliente.objects.create(nombre="Sin correo 1", documento="SC-1")
        dos = Cliente.objects.create(nombre="Sin correo 2", documento="SC-2")
        self.assertEqual(uno.correo, "")
        self.assertEqual(dos.correo, "")
        self.assertTrue(Cliente.objects.filter(pk__in=[uno.pk, dos.pk]).exists())

        Cliente.objects.create(nombre="Con correo", documento="SC-3", correo="repetido@example.com")
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(
                nombre="Otro con el mismo correo", documento="SC-4",
                correo="repetido@example.com",
            )

    def test_dos_empleados_sin_correo_y_correo_repetido(self):
        """La misma regla para Empleado: vacío se repite, escrito no."""
        base = {
            "cargo": "tapcr", "celular": "300", "direccion": "Calle",
            "salario": 1000, "fecha_nacimiento": date(1990, 1, 1),
        }
        Empleado.objects.create(documento="EM-1", nombre="Sin correo 1", **base)
        Empleado.objects.create(documento="EM-2", nombre="Sin correo 2", **base)
        self.assertEqual(
            Empleado.objects.filter(documento__in=["EM-1", "EM-2"], correo="").count(), 2
        )

        Empleado.objects.create(
            documento="EM-3", nombre="Con correo", correo="trabajador@example.com", **base
        )
        with self.assertRaises(IntegrityError):
            Empleado.objects.create(
                documento="EM-4", nombre="Otro", correo="trabajador@example.com", **base
            )

    def test_crear_dos_clientes_sin_correo_desde_la_interfaz(self):
        for indice in (1, 2):
            resp = self.client.post(reverse("kanview:cliente-crear"), {
                "nombre": f"Cliente sin correo {indice}", "documento": f"900{indice}",
                "celular": "300", "direccion": "Calle", "fecha_nacimiento": "1990-01-01",
                "correo": "",
            })
            self.assertEqual(resp.status_code, 302, f"cliente {indice}")
        self.assertEqual(
            Cliente.objects.filter(documento__in=["9001", "9002"], correo="").count(), 2
        )

        # Y el correo repetido se avisa en el formulario, sin 500.
        datos = {
            "nombre": "Repetido UI", "documento": "9100",
            "celular": "300", "direccion": "Calle", "fecha_nacimiento": "1990-01-01",
            "correo": "repetido-ui@example.com",
        }
        self.assertEqual(self.client.post(reverse("kanview:cliente-crear"), datos).status_code, 302)
        resp = self.client.post(reverse("kanview:cliente-crear"), dict(datos, documento="9101"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ya existe")

    def test_el_documento_solo_acepta_numeros(self):
        resp = self.client.post(reverse("kanview:cliente-crear"), {
            "nombre": "Cliente con letras", "documento": "ABC-123",
            "celular": "300", "direccion": "Calle", "fecha_nacimiento": "1990-01-01",
            "correo": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "solo puede contener números")
        self.assertFalse(Cliente.objects.filter(nombre="Cliente con letras").exists())

        # El input del formulario también pide solo números al navegador.
        resp = self.client.get(reverse("kanview:empleado-crear"))
        self.assertContains(resp, 'data-solo-numeros="1"')
        self.assertContains(resp, 'pattern="[0-9]*"')

    def test_el_regresar_de_cada_modulo_vuelve_a_su_vista(self):
        destinos = {
            "cliente": reverse("kanview:usuarios"),
            "empleado": reverse("kanview:usuarios"),
            "administrador": reverse("kanview:usuarios"),
            "producto": reverse("kanview:catalogo"),
        }
        for nombre, destino in destinos.items():
            resp = self.client.get(reverse(f"kanview:{nombre}-lista"))
            self.assertEqual(resp.context["regresar_url"], destino, nombre)
            resp = self.client.get(reverse(f"kanview:{nombre}-crear"))
            self.assertEqual(resp.context["regresar_url"], destino, nombre)
        # Los demás módulos conservan el regreso al historial del navegador.
        resp = self.client.get(reverse("kanview:pedido-lista"))
        self.assertIsNone(resp.context["regresar_url"])

    # ---- Formularios construidos en las vistas (formas.py eliminado) --------

    def test_no_existe_el_modulo_forms(self):
        """`kanview.forms` se eliminó: los formularios viven en las vistas."""
        import importlib

        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("kanview.forms")

    def test_el_helper_de_formularios_crea_y_edita_en_cada_modulo(self):
        """Cada vista construye su ModelForm con `modelform_factory`."""
        from django.forms import ModelForm

        from . import views_crud

        casos = (
            (views_crud._form_cliente, Cliente, "SC-FORM"),
            (views_crud._form_empleado, Empleado, "EM-FORM"),
            (views_crud._form_administrador, Administrador, "AD-FORM"),
            (views_crud._form_producto, Producto, "PR-FORM"),
            (views_crud._form_calendario, Calendario, "CA-FORM"),
            (views_crud._form_tarea, TareasPedido, "TA-FORM"),
            (views_crud._form_actividad, Actividades, "AC-FORM"),
            (views_crud._form_historial, Historial, "HI-FORM"),
            (views_crud._form_analisis, AnalisisFinanciero, "AN-FORM"),
        )
        request = type("Peticion", (), {"method": "GET", "POST": {}, "FILES": {}})()
        for helper, modelo, etiqueta in casos:
            form = helper(request)
            self.assertIsInstance(form, ModelForm, etiqueta)
            self.assertEqual(form._meta.model, modelo, etiqueta)
            # En un GET no hay datos: el formulario está vacío pero es editable.
            self.assertFalse(form.is_bound, etiqueta)

        # Pedido arma su formulario aparte (añade fecha límite y quita el código).
        form = views_crud._form_pedido(request)
        self.assertIn("fecha_limite", form.fields)
        self.assertNotIn("codigo_pedido", form.fields)

    # ---- Cliente: sin edad, calculada de la fecha de nacimiento -----------

    def test_cliente_no_pide_edad_y_la_calcula(self):
        resp = self.client.get(reverse("kanview:cliente-crear"))
        self.assertNotContains(resp, 'name="edad"')

        resp = self.client.post(reverse("kanview:cliente-crear"), {
            "nombre": "Nuevo Cliente", "documento": "99", "celular": "300999",
            "direccion": "Calle 9", "fecha_nacimiento": "2000-05-10",
            "correo": "nuevo@example.com",
        })
        self.assertEqual(resp.status_code, 302)
        cliente = Cliente.objects.get(documento="99")
        hoy = timezone.localdate()
        esperada = hoy.year - 2000 - ((hoy.month, hoy.day) < (5, 10))
        self.assertEqual(cliente.edad, esperada)

    # ---- Producto: el stock vive en Producto (sin Inventario ni Catálogo) ---

    def test_producto_guarda_stock_y_categoria_en_si_mismo(self):
        resp = self.client.post(reverse("kanview:producto-crear"), {
            "nombre": "Mesa", "categoria": "madera", "codigo_producto": "Z9Y8X7",
            "cantidad": "7", "precio": "250000", "descripcion": "mesa de nogal",
        })
        self.assertEqual(resp.status_code, 302)
        producto = Producto.objects.get(codigo_producto="Z9Y8X7")
        self.assertEqual(producto.cantidad, 7)
        self.assertEqual(producto.categoria, "madera")
        # La pantalla de existencias lee del mismo producto.
        resp = self.client.get(reverse("kanview:inventario"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mesa")
        self.assertContains(resp, "Madera")

    def test_producto_rechaza_negativos(self):
        for campo, valor in (("cantidad", "-5"), ("precio", "-1000")):
            datos = {"nombre": "Silla negativa", "categoria": "tela",
                     "codigo_producto": "NEG001", "cantidad": "3",
                     "precio": "100", "descripcion": "x"}
            datos[campo] = valor
            resp = self.client.post(reverse("kanview:producto-crear"), datos)
            self.assertEqual(resp.status_code, 200, campo)
            self.assertFalse(
                Producto.objects.filter(codigo_producto="NEG001").exists(),
                f"{campo} negativo no debe guardarse",
            )

    # ---- Pedido: código automático, fecha límite y galería ----------------

    def _datos_pedido(self, **extra):
        datos = {
            "estado": "activo", "cantidad": 1, "descripcion": "silla en cuero",
            "id_cliente": self.cliente.pk, "id_empleado": self.empleado.pk,
            "id_producto": self.producto.pk,
        }
        datos.update(extra)
        return datos

    def test_fecha_limite_esta_en_el_formulario_y_se_guarda(self):
        # El campo debe existir en el formulario: antes solo se leía del POST
        # crudo, así que no había forma de meter la fecha desde la interfaz.
        resp = self.client.get(reverse("kanview:pedido-crear"))
        self.assertContains(resp, 'name="fecha_limite"')
        self.assertContains(resp, 'type="date"')
        self.assertContains(resp, "Fecha límite de entrega")

        resp = self.client.post(
            reverse("kanview:pedido-crear"),
            self._datos_pedido(fecha_limite="2026-12-31"),
        )
        self.assertEqual(resp.status_code, 302)
        pedido = Pedido.objects.order_by("-pk").first()
        self.assertEqual(pedido.codigo_pedido, "PED-0001")
        self.assertEqual(pedido.fecha_limite, date(2026, 12, 31))
        self.assertEqual(pedido.fecha_creacion, timezone.localdate())

        # El formulario no debe pedir el código ni las fechas de creación.
        resp = self.client.get(reverse("kanview:pedido-crear"))
        for campo in ("codigo_pedido", "fecha_creacion", "hora_creacion"):
            self.assertNotContains(resp, f'name="{campo}"')

        # Una fecha inválida avisa en pantalla (ya no se ignora en silencio).
        resp = self.client.post(
            reverse("kanview:pedido-crear"),
            self._datos_pedido(fecha_limite="no-es-fecha"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "fecha límite válida")

        # En edición, dejar la fecha vacía la borra.
        resp = self.client.post(
            reverse("kanview:pedido-editar", args=[pedido.pk]),
            self._datos_pedido(fecha_limite=""),
        )
        self.assertEqual(resp.status_code, 302)
        pedido.refresh_from_db()
        self.assertIsNone(pedido.fecha_limite)

    def test_desactivar_un_pedido_lo_saca_del_tablero(self):
        """Desactivar alinea ``estado`` y oculta el pedido (antes seguía visible)."""
        resp = self.client.post(reverse("kanview:pedido-eliminar", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertFalse(self.pedido.activo)
        self.assertEqual(self.pedido.estado, "inactivo")

        resp = self.client.get(reverse("kanview:pedidos-tablero"))
        self.assertNotContains(resp, self.pedido.codigo_pedido)

        resp = self.client.post(reverse("kanview:pedido-reactivar", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertTrue(self.pedido.activo)
        self.assertEqual(self.pedido.estado, "activo")

    def test_pedido_guarda_varias_imagenes(self):
        resp = self.client.post(reverse("kanview:pedido-crear"), {
            "estado": "activo", "cantidad": 1, "descripcion": "pedido con fotos",
            "id_cliente": self.cliente.pk, "id_empleado": self.empleado.pk,
            "id_producto": self.producto.pk,
            "imagenes": [
                SimpleUploadedFile("evidencia1.png", PNG_1X1, content_type="image/png"),
                SimpleUploadedFile("evidencia2.png", PNG_1X1, content_type="image/png"),
            ],
        })
        self.assertEqual(resp.status_code, 302)
        pedido = Pedido.objects.order_by("-pk").first()
        self.assertEqual(pedido.galeria.count(), 2)
        self.assertTrue(EvidenciaPedido.objects.filter(pedido=pedido).exists())

    # ---- Tarea/actividad: no pasarse de la fecha límite -------------------

    def test_tarea_respeta_fecha_limite_del_pedido(self):
        fuera = {
            "nombre": "Fuera de límite", "descripcion": "x",
            "fecha_inicio": "2026-10-16", "fecha_fin": "2026-11-30",
            "estado": "pendiente", "id_pedido": self.pedido.pk,
            "id_empleado": self.empleado.pk,
        }
        resp = self.client.post(reverse("kanview:tarea-crear"), fuera)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(TareasPedido.objects.filter(nombre="Fuera de límite").exists())

        dentro = dict(fuera, nombre="Dentro de límite", fecha_fin="2026-10-19")
        resp = self.client.post(reverse("kanview:tarea-crear"), dentro)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TareasPedido.objects.filter(nombre="Dentro de límite").exists())

    def test_tarea_no_puede_empezar_antes_del_registro_del_pedido(self):
        resp = self.client.post(reverse("kanview:tarea-crear"), {
            "nombre": "Antes del pedido", "descripcion": "x",
            "fecha_inicio": "2026-10-14", "fecha_fin": "2026-10-15",
            "estado": "pendiente", "id_pedido": self.pedido.pk,
            "id_empleado": self.empleado.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(TareasPedido.objects.filter(nombre="Antes del pedido").exists())
        self.assertContains(resp, "fecha de registro del pedido")

    def test_tarea_no_puede_terminar_antes_de_su_inicio(self):
        resp = self.client.post(reverse("kanview:tarea-crear"), {
            "nombre": "Rango invertido", "descripcion": "x",
            "fecha_inicio": "2026-10-18", "fecha_fin": "2026-10-17",
            "estado": "pendiente", "id_pedido": self.pedido.pk,
            "id_empleado": self.empleado.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(TareasPedido.objects.filter(nombre="Rango invertido").exists())
        self.assertContains(resp, "no puede ser anterior a la fecha de inicio")

    def test_actividad_respeta_las_fechas_del_pedido(self):
        fuera = {
            "nombre": "Actividad fuera", "descripcion": "x",
            "fecha_inicio": "2026-10-14", "fecha_fin": "2026-10-15",
            "estado": "pendiente", "id_tarea": self.tarea.pk,
            "id_empleado": self.empleado.pk,
        }
        resp = self.client.post(reverse("kanview:actividad-crear"), fuera)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Actividades.objects.filter(nombre="Actividad fuera").exists())
        self.assertContains(resp, "fecha de registro del pedido")

        tarde = dict(fuera, nombre="Actividad tarde", fecha_inicio="2026-10-21", fecha_fin="2026-10-22")
        resp = self.client.post(reverse("kanview:actividad-crear"), tarde)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Actividades.objects.filter(nombre="Actividad tarde").exists())

        dentro = dict(fuera, nombre="Actividad dentro", fecha_inicio="2026-10-16", fecha_fin="2026-10-17")
        resp = self.client.post(reverse("kanview:actividad-crear"), dentro)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Actividades.objects.filter(nombre="Actividad dentro").exists())

    def test_api_valida_las_fechas_de_tareas_y_actividades(self):
        invalida = {
            "nombre": "API fuera", "descripcion": "x",
            "fecha_inicio": "2026-10-14", "fecha_fin": "2026-10-15",
            "estado": "pendiente", "id_pedido": self.pedido.pk,
        }
        resp = self.client.post("/api/tareas-pedido/", invalida)
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(TareasPedido.objects.filter(nombre="API fuera").exists())

        resp = self.client.post("/api/tareas-pedido/", dict(
            invalida, nombre="API válida", fecha_inicio="2026-10-16", fecha_fin="2026-10-17",
        ))
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(TareasPedido.objects.filter(nombre="API válida").exists())

        resp = self.client.post("/api/actividades/", {
            "nombre": "API actividad fuera", "descripcion": "x",
            "fecha_inicio": "2026-10-21", "fecha_fin": "2026-10-22",
            "estado": "pendiente", "id_tarea": self.tarea.pk,
            "id_empleado": self.empleado.pk,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Actividades.objects.filter(nombre="API actividad fuera").exists())

    # ---- Roles y API ------------------------------------------------------

    def test_trabajador_no_entra_a_finanzas(self):
        trabajador = User.objects.create_user(username="obrero", password="pass12345")
        trabajador.groups.add(_grupo(ROL_TRABAJADOR))
        self.client.force_login(trabajador)

        self.assertEqual(self.client.get(reverse("kanview:finanzas")).status_code, 302)
        self.assertEqual(self.client.get(reverse("kanview:usuarios")).status_code, 302)
        self.assertEqual(self.client.get(reverse("kanview:inventario")).status_code, 200)

    def test_api_exige_sesion(self):
        self.client.logout()
        self.assertIn(self.client.get("/api/clientes/").status_code, (401, 403))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 200)

    # ---- El rol Cliente no puede leer ni escribir lo ajeno ----------------

    def _cliente_con_cuenta(self, correo="cliente.rol@kanview.com"):
        """Crea un Cliente con su cuenta de rol Cliente y devuelve (cliente, user)."""
        user = User.objects.create_user(username=correo, password="pass12345", email=correo)
        user.groups.add(_grupo(ROL_CLIENTE))
        cliente = Cliente.objects.create(
            nombre="Cliente del rol", fecha_nacimiento=date(1991, 2, 3),
            documento="CLI-ROL", celular="300", direccion="Calle rol", correo=correo,
            usuario=user,
        )
        return cliente, user

    def test_cliente_no_ve_ni_desactiva_pedidos_ajenos(self):
        cliente, user = self._cliente_con_cuenta()
        propio = Pedido.objects.create(
            codigo_pedido="PED-9001", fecha_creacion=date(2026, 10, 1),
            hora_creacion=timezone.now(), estado="activo", evidencias="",
            descripcion="propio del cliente", id_cliente=cliente,
            id_empleado=self.empleado, id_producto=self.producto,
        )
        self.client.force_login(user)

        # La lista solo muestra SUS pedidos.
        resp = self.client.get(reverse("kanview:pedido-lista"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, propio.codigo_pedido)
        self.assertNotContains(resp, self.pedido.codigo_pedido)
        # Y sin acciones de escritura (ni "Nuevo", ni "Editar", ni "Desactivar").
        self.assertNotContains(resp, "Nuevo")
        self.assertNotContains(resp, "Desactivar")

        # El tablero y el detalle de un pedido ajeno no lo muestran.
        self.assertEqual(self.client.get(reverse("kanview:pedidos-tablero")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("kanview:pedido-detalle", args=[self.pedido.pk])).status_code,
            404,
        )

        # Desactivar un pedido ajeno no hace nada.
        resp = self.client.post(reverse("kanview:pedido-eliminar", args=[self.pedido.pk]))
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertTrue(self.pedido.activo, "un Cliente no puede desactivar pedidos ajenos")

        # Tampoco puede crear pedidos.
        resp = self.client.post(reverse("kanview:pedido-crear"), self._datos_pedido())
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Pedido.objects.filter(descripcion="silla en cuero").exclude(pk=self.pedido.pk).exists())

    def test_cliente_no_puede_ver_ni_crear_productos(self):
        _cliente, user = self._cliente_con_cuenta()
        self.client.force_login(user)

        self.assertEqual(self.client.get(reverse("kanview:producto-crear")).status_code, 302)
        datos = {
            "nombre": "Producto del cliente", "categoria": "tela",
            "codigo_producto": "CLI001", "cantidad": "3", "precio": "100",
            "descripcion": "no debería crearse",
        }
        resp = self.client.post(reverse("kanview:producto-crear"), datos)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Producto.objects.filter(codigo_producto="CLI001").exists())

        # La gestión de productos queda cerrada; el catálogo sí lo ve (solo
        # lectura) para pedir desde él.
        self.assertEqual(self.client.get(reverse("kanview:producto-lista")).status_code, 302)
        self.assertEqual(self.client.get(reverse("kanview:catalogo")).status_code, 200)

    def test_api_rechaza_al_rol_cliente(self):
        _cliente, user = self._cliente_con_cuenta()
        self.client.force_login(user)

        # Un Cliente no entra a los recursos de gestión ni a los de otros módulos.
        self.assertEqual(self.client.get("/api/clientes/").status_code, 403)
        # El catálogo de productos es de solo lectura para el Cliente.
        self.assertEqual(self.client.get("/api/productos/").status_code, 200)
        self.assertEqual(self.client.post("/api/productos/", {}).status_code, 403)
        self.assertEqual(self.client.get("/api/pedidos/").status_code, 200)
        self.assertEqual(self.client.post("/api/pedidos/", {}).status_code, 403)
        # Los módulos que no le tocan quedan cerrados también para escritura.
        # (Inventario y Catálogo ya no existen como recursos de la API.)
        self.assertEqual(self.client.get("/api/inventarios/").status_code, 404)
        self.assertEqual(self.client.get("/api/catalogos/").status_code, 404)
        self.assertEqual(self.client.get("/api/analisis-financieros/").status_code, 403)

        # El administrador sí, y el DELETE de la API ya no borra: desactiva.
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 200)
        resp = self.client.delete(f"/api/clientes/{self.cliente.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.activo)
        self.assertTrue(Cliente.objects.filter(pk=self.cliente.pk).exists())

    # ---- Archivos de la galería: allow-list, tope y contenido -------------

    def test_archivo_html_se_rechaza_con_mensaje(self):
        adjunto = SimpleUploadedFile(
            "ataque.html", b"<script>alert(1)</script>", content_type="text/html"
        )
        resp = self.client.post(
            reverse("kanview:pedido-crear"), self._datos_pedido(imagenes=adjunto)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "no es una imagen permitida")
        self.assertFalse(Pedido.objects.filter(descripcion="silla en cuero").exists())
        self.assertFalse(EvidenciaPedido.objects.exists())

    def test_archivo_mayor_a_5mb_se_rechaza_con_mensaje(self):
        grande = SimpleUploadedFile(
            "grande.png", b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 1),
            content_type="image/png",
        )
        resp = self.client.post(
            reverse("kanview:pedido-crear"), self._datos_pedido(imagenes=grande)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "pesa más de 5 MB")
        self.assertFalse(EvidenciaPedido.objects.exists())

    def test_archivo_con_content_type_falso_se_rechaza(self):
        falso = SimpleUploadedFile(
            "foto.png", b"<script>alert(1)</script>", content_type="text/html"
        )
        resp = self.client.post(
            reverse("kanview:pedido-crear"), self._datos_pedido(imagenes=falso)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "no parece una imagen válida")
        self.assertFalse(EvidenciaPedido.objects.exists())

    def test_mas_de_cinco_imagenes_se_rechaza(self):
        adjuntos = [
            SimpleUploadedFile(f"evidencia{i}.png", PNG_1X1, content_type="image/png")
            for i in range(6)
        ]
        resp = self.client.post(
            reverse("kanview:pedido-crear"), self._datos_pedido(imagenes=adjuntos)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "máximo 5 imágenes")
        self.assertFalse(EvidenciaPedido.objects.exists())

    def test_si_una_imagen_falla_no_se_guarda_ninguna(self):
        """Un PNG válido junto a un .html: no se guarda nada (ni pedido ni imagen)."""
        adjuntos = [
            SimpleUploadedFile("buena.png", PNG_1X1, content_type="image/png"),
            SimpleUploadedFile("mala.html", b"<script>alert(1)</script>", content_type="text/html"),
        ]
        resp = self.client.post(
            reverse("kanview:pedido-crear"), self._datos_pedido(imagenes=adjuntos)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "no es una imagen permitida")
        self.assertFalse(Pedido.objects.filter(descripcion="silla en cuero").exists())
        self.assertFalse(EvidenciaPedido.objects.exists())

    # ---- Sidebar filtrado por rol y Configuración sin el correo real ------

    def test_sidebar_de_las_listas_crud_se_filtra_por_rol(self):
        trabajador = User.objects.create_user(username="obrero.sidebar", password="pass12345")
        trabajador.groups.add(_grupo(ROL_TRABAJADOR))
        self.client.force_login(trabajador)

        resp = self.client.get(reverse("kanview:pedido-lista"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        sidebar = html[html.index("<aside"):html.index("</aside>")]
        self.assertIn("Procesos", sidebar)
        self.assertNotIn("Finanzas", sidebar)
        self.assertNotIn("Usuarios", sidebar)

    def test_configuracion_no_publica_el_correo_de_envio(self):
        resp = self.client.get(reverse("kanview:configuracion"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, settings.CORREO_CONTACTO)
        if settings.EMAIL_HOST_USER:
            self.assertNotContains(resp, settings.EMAIL_HOST_USER)
        self.assertNotContains(resp, settings.EMAIL_HOST)

    def test_paginas_del_modulo_usuarios_renderizan(self):
        for url in (
            reverse("kanview:usuarios"),
            reverse("kanview:usuario-ver", args=["cliente", self.cliente.pk]),
            reverse("kanview:usuario-ver", args=["trabajador", self.empleado.pk]),
        ):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)

    # ---- Cuentas: no se puede apropiar de la cuenta de otra persona -------

    def test_acceso_no_reescribe_la_cuenta_de_otro(self):
        trabajador = User.objects.create_user(
            username="obrero@kanview.com", password="pass12345",
            email="obrero@kanview.com", last_name="Permanece",
        )
        trabajador.groups.add(_grupo(ROL_TRABAJADOR))
        # Un Cliente nuevo que pretende el correo del trabajador.
        intruso = Cliente.objects.create(
            nombre="Intruso", documento="INT-1", correo="otro@kanview.com",
        )

        resp = self.client.post(
            reverse("kanview:usuario-acceso", args=["cliente", intruso.pk]),
            {"correo": "obrero@kanview.com", "rol": ROL_CLIENTE, "clave": ""},
        )
        self.assertEqual(resp.status_code, 302)

        trabajador.refresh_from_db()
        intruso.refresh_from_db()
        self.assertIsNone(intruso.usuario, "no debe quedarse con una cuenta ajena")
        self.assertEqual(trabajador.last_name, "Permanece")
        self.assertEqual(
            list(trabajador.groups.values_list("name", flat=True)), [ROL_TRABAJADOR]
        )
        self.assertEqual(
            User.objects.filter(username="obrero@kanview.com").count(), 1,
            "no se debe crear un duplicado de la cuenta ajena",
        )

    def test_acceso_crea_y_enlaza_la_cuenta_propia(self):
        empleado = Empleado.objects.create(
            documento="TRB-1", nombre="Trabajador Nuevo", cargo="tapcr",
            celular="301", direccion="Calle 3", salario=1000,
            fecha_nacimiento=date(1990, 1, 1),
        )
        resp = self.client.post(
            reverse("kanview:usuario-acceso", args=["trabajador", empleado.pk]),
            {"correo": "nuevo.trabajador@kanview.com", "rol": ROL_TRABAJADOR, "clave": ""},
        )
        self.assertEqual(resp.status_code, 302)
        empleado.refresh_from_db()
        self.assertIsNotNone(empleado.usuario)
        self.assertEqual(empleado.correo, "nuevo.trabajador@kanview.com")
        self.assertEqual(empleado.usuario.username, "nuevo.trabajador@kanview.com")
        self.assertEqual(
            list(empleado.usuario.groups.values_list("name", flat=True)), [ROL_TRABAJADOR]
        )

        # Volver a guardar el acceso no duplica la cuenta (idempotente).
        resp = self.client.post(
            reverse("kanview:usuario-acceso", args=["trabajador", empleado.pk]),
            {"correo": "nuevo.trabajador@kanview.com", "rol": ROL_TRABAJADOR, "clave": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            User.objects.filter(username="nuevo.trabajador@kanview.com").count(), 1
        )


# ---- Tanda de UI: dinero con puntos de miles ---------------------------------


class DineroConSeparadorTestCase(TestCase):
    """Los cuatro campos de dinero aceptan puntos de miles y comas decimales.

    Cubre la normalización que va en las VISTAS (`kanview/formato.py`) y cómo se
    imprimen los montos con puntos cada tres dígitos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="dinero", password="pass12345", is_staff=True
        )
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.administrador = Administrador.objects.create(
            nombre="Admin Dinero", celular="300000000", documento="DIN-1"
        )
        cls.cliente = Cliente.objects.create(nombre="Cliente Dinero", documento="DIN-2")
        cls.empleado = Empleado.objects.create(
            documento="DIN-3", nombre="Empleado Dinero", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000, fecha_nacimiento=date(1990, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)

    # ---- el helper de lectura -------------------------------------------------

    def test_normalizar_monto_acepta_puntos_y_comas(self):
        from .formato import normalizar_monto

        casos = {
            "250000": "250000",
            "250.000": "250000",          # puntos de miles
            "1.250.000": "1250000",
            "10.000.000": "10000000",
            "250,50": "250.50",           # coma decimal
            "250.000,50": "250000.50",    # las dos cosas
            "250.50": "250.50",           # punto decimal del navegador
            "$ 1.250.000": "1250000",     # con el signo de pesos
            "": "",
        }
        for crudo, esperado in casos.items():
            self.assertEqual(normalizar_monto(crudo), esperado, crudo)

    def test_normalizar_monto_rechaza_lo_que_no_es_numero(self):
        from .formato import normalizar_monto

        for crudo in ("abc", "1.23.456", "250.", "no-es-un-precio"):
            with self.assertRaises(ValueError, msg=crudo):
                normalizar_monto(crudo)

    # ---- producto -------------------------------------------------------------

    def _datos_producto(self, precio, codigo="DIN001"):
        return {
            "nombre": "Mesa de nogal", "categoria": "madera", "codigo_producto": codigo,
            "cantidad": "3", "precio": precio, "descripcion": "prueba de dinero",
        }

    def test_producto_guarda_precio_con_puntos_de_miles(self):
        # Cada caso usa su propio código: el producto genera Inventario y
        # Catálogo (FK en PROTECT) y no se puede borrar para reutilizar el código.
        for indice, (precio, esperado) in enumerate((
            ("250.000", "250000.00"),
            ("1.250.000", "1250000.00"),
            ("250000", "250000.00"),
        )):
            codigo = f"DIN00{indice + 4}"
            resp = self.client.post(
                reverse("kanview:producto-crear"), self._datos_producto(precio, codigo=codigo)
            )
            self.assertEqual(resp.status_code, 302, precio)
            producto = Producto.objects.get(codigo_producto=codigo)
            self.assertEqual(str(producto.precio), esperado, precio)

    def test_producto_guarda_precio_con_coma_decimal(self):
        resp = self.client.post(
            reverse("kanview:producto-crear"), self._datos_producto("250.000,50", codigo="DIN002")
        )
        self.assertEqual(resp.status_code, 302)
        producto = Producto.objects.get(codigo_producto="DIN002")
        self.assertEqual(str(producto.precio), "250000.50")

        resp = self.client.post(
            reverse("kanview:producto-crear"), self._datos_producto("250,50", codigo="DIN003")
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(str(Producto.objects.get(codigo_producto="DIN003").precio), "250.50")

    def test_precio_invalido_avisa_en_espanol(self):
        resp = self.client.post(
            reverse("kanview:producto-crear"), self._datos_producto("no-es-un-precio", codigo="DINBAD")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "no es un número válido")
        self.assertContains(resp, "1.250.000")  # el ejemplo que se le muestra
        self.assertFalse(Producto.objects.filter(codigo_producto="DINBAD").exists())

    def test_el_precio_se_imprime_con_puntos_en_la_lista(self):
        self.client.post(reverse("kanview:producto-crear"), self._datos_producto("1250000", codigo="DINLST"))
        resp = self.client.get(reverse("kanview:producto-lista"))
        self.assertContains(resp, "1.250.000")
        self.assertNotContains(resp, "1250000.00")

    def test_el_campo_de_precio_es_texto_para_poder_mostrar_los_puntos(self):
        import re

        resp = self.client.get(reverse("kanview:producto-crear"))
        html = resp.content.decode()
        etiqueta = re.search(r"<input[^>]*name=\"precio\"[^>]*>", html)
        self.assertIsNotNone(etiqueta, "el formulario debe traer el campo precio")
        self.assertIn('type="text"', etiqueta.group(0))
        self.assertIn('inputmode="decimal"', etiqueta.group(0))
        # La cantidad sigue siendo numérica: no es dinero.
        cantidad = re.search(r"<input[^>]*name=\"cantidad\"[^>]*>", html)
        self.assertIn('type="number"', cantidad.group(0))

    # ---- empleado y análisis financiero --------------------------------------

    def test_crear_empleado_no_pide_edad_ni_tareas_realizadas(self):
        resp = self.client.get(reverse("kanview:empleado-crear"))
        self.assertNotContains(resp, 'name="edad"')
        self.assertNotContains(resp, 'name="tareas_realizadas"')

        resp = self.client.post(reverse("kanview:empleado-crear"), {
            "nombre": "Sin edad", "documento": "9876201", "cargo": "tapcr",
            "celular": "300", "direccion": "Calle", "salario": "1000000",
            "fecha_nacimiento": "1995-01-01",
        })
        self.assertEqual(resp.status_code, 302)
        empleado = Empleado.objects.get(documento="9876201")
        self.assertEqual(empleado.tareas_realizadas, 0)

    def test_salario_acepta_puntos_de_miles(self):
        resp = self.client.post(reverse("kanview:empleado-crear"), {
            "nombre": "Tapicero", "documento": "9876202", "cargo": "tapcr", "celular": "301",
            "direccion": "Calle 4", "salario": "2.500.000", "edad": "30",
            "fecha_nacimiento": "1995-01-01", "tareas_realizadas": "0",
        })
        self.assertEqual(resp.status_code, 302)
        empleado = Empleado.objects.get(documento="9876202")
        self.assertEqual(str(empleado.salario), "2500000.00")

        resp = self.client.get(reverse("kanview:empleado-lista"))
        self.assertContains(resp, "2.500.000")

    def test_analisis_financiero_acepta_puntos_de_miles(self):
        resp = self.client.post(reverse("kanview:analisis-financiero-crear"), {
            "gastos": "1.250.000", "fuentes_ingresos": "2.000.000,50",
            "productos_vendidos": "12", "id_administrador": self.administrador.pk,
        })
        self.assertEqual(resp.status_code, 302)
        registro = AnalisisFinanciero.objects.order_by("-pk").first()
        self.assertEqual(str(registro.gastos), "1250000.00")
        self.assertEqual(str(registro.fuentes_ingresos), "2000000.50")

        resp = self.client.get(reverse("kanview:analisis-financiero-lista"))
        self.assertContains(resp, "1.250.000")
        self.assertContains(resp, "2.000.000")  # 2.000.000,50 se muestra sin centavos


# ---- Tanda de UI: sidebar, calendario, tareas, textos y accesibilidad --------


class TandaUiTestCase(TestCase):
    """Puntos A3-A6 y B1-B4 de la tanda de UI."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="ui.tanda", password="pass12345", is_staff=True
        )
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.cliente = Cliente.objects.create(nombre="Cliente UI", documento="UI-1")
        cls.empleado = Empleado.objects.create(
            documento="UI-2", nombre="Empleado UI", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000, fecha_nacimiento=date(1990, 1, 1),
            tareas_realizadas=0,
        )
        cls.producto = Producto.objects.create(
            nombre="Producto UI", categoria="tela", cantidad=2, precio=1000,
            descripcion="x", codigo_producto="UI0001",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="UI0001", fecha_creacion=date(2026, 10, 5), hora_creacion=timezone.now(),
            estado="activo", evidencias="", descripcion="pedido UI",
            fecha_limite=date(2026, 12, 31),
            id_cliente=cls.cliente, id_empleado=cls.empleado, id_producto=cls.producto,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Tarea UI", descripcion="cortar la tela", fecha_inicio=date(2026, 10, 6),
            fecha_fin=date(2026, 10, 9), estado="pendiente", id_pedido=cls.pedido,
            id_empleado=cls.empleado,
        )
        cls.actividad = Actividades.objects.create(
            nombre="Actividad UI", descripcion="medir", fecha_inicio=date(2026, 10, 6),
            fecha_fin=date(2026, 10, 7), estado="en progreso", id_tarea=cls.tarea,
            id_empleado=cls.empleado,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _sidebar(self, resp):
        html = resp.content.decode()
        return html[html.index("<aside"):html.index("</aside>")]

    # ---- A5 / A6: el menú -----------------------------------------------------

    def test_el_sidebar_lleva_a_productos_y_catalogo_sin_inventario(self):
        resp = self.client.get(reverse("kanview:dashboard"))
        sidebar = self._sidebar(resp)
        self.assertIn(reverse("kanview:producto-lista"), sidebar)
        self.assertIn(reverse("kanview:catalogo"), sidebar)
        self.assertLess(sidebar.index(">Productos<"), sidebar.index(">Catálogo<"))
        # Inventario ya no es módulo del menú (su pantalla sigue existiendo).
        self.assertNotIn(">Inventario<", sidebar)

        # El enlace responde 200 con sesión iniciada.
        self.assertEqual(self.client.get(reverse("kanview:producto-lista")).status_code, 200)

    def test_productos_marca_solo_productos_como_activo(self):
        def bloque(sidebar, etiqueta):
            return next(
                parte for parte in sidebar.split("<li data-seccion=")[1:]
                if f">{etiqueta}<" in parte
            )

        sidebar = self._sidebar(self.client.get(reverse("kanview:producto-lista")))
        self.assertIn("bg-[#004f4f]", bloque(sidebar, "Productos"))
        self.assertNotIn("bg-[#004f4f]", bloque(sidebar, "Catálogo"))

        sidebar = self._sidebar(self.client.get(reverse("kanview:catalogo")))
        self.assertIn("bg-[#004f4f]", bloque(sidebar, "Catálogo"))
        self.assertNotIn("bg-[#004f4f]", bloque(sidebar, "Productos"))

    def test_el_sidebar_tiene_mensajeria(self):
        sidebar = self._sidebar(self.client.get(reverse("kanview:dashboard")))
        self.assertIn(">Mensajería<", sidebar)
        self.assertIn(reverse("kanview:mensajeria"), sidebar)
        self.assertEqual(self.client.get(reverse("kanview:mensajeria")).status_code, 200)

    def test_el_sidebar_tiene_procesos_y_tareas(self):
        resp = self.client.get(reverse("kanview:dashboard"))
        sidebar = self._sidebar(resp)
        self.assertIn(">Procesos<", sidebar)
        self.assertIn(reverse("kanview:pedidos-tablero"), sidebar)
        self.assertIn(">Tareas<", sidebar)
        self.assertIn(reverse("kanview:tareas"), sidebar)

    def test_tareas_muestra_el_listado_de_tareas(self):
        resp = self.client.get(reverse("kanview:tareas"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tareas")
        self.assertContains(resp, reverse("kanview:tarea-crear"))
        self.assertContains(resp, "Tarea UI")

    def test_el_sidebar_ya_no_tiene_configuracion(self):
        resp = self.client.get(reverse("kanview:dashboard"))
        sidebar = self._sidebar(resp)
        self.assertNotIn("Configuración", sidebar)
        self.assertNotIn(reverse("kanview:configuracion"), sidebar)
        # La ruta sigue funcionando: solo se quitó el botón del menú.
        self.assertEqual(self.client.get(reverse("kanview:configuracion")).status_code, 200)

    def test_un_trabajador_ve_productos_en_el_sidebar(self):
        trabajador = User.objects.create_user(username="obrero.ui", password="pass12345")
        trabajador.groups.add(_grupo(ROL_TRABAJADOR))
        self.client.force_login(trabajador)

        resp = self.client.get(reverse("kanview:pedido-lista"))
        sidebar = self._sidebar(resp)
        self.assertIn("Productos", sidebar)
        self.assertNotIn("Finanzas", sidebar)

    # ---- B3: textos en inglés -------------------------------------------------

    def test_no_quedan_textos_en_ingles(self):
        for url in (reverse("kanview:dashboard"), reverse("kanview:producto-crear")):
            resp = self.client.get(url)
            self.assertNotContains(resp, "Manufacturing Pro")
            self.assertNotContains(resp, "- Select an option -")
        resp = self.client.get(reverse("kanview:dashboard"))
        self.assertContains(resp, "Gestión de taller")

    def test_los_selects_de_fk_dicen_selecciona_una_opcion(self):
        resp = self.client.get(reverse("kanview:pedido-crear"))
        self.assertEqual(resp.content.decode().count("Selecciona una opción"), 3)
        resp = self.client.get(reverse("kanview:actividad-crear"))
        self.assertContains(resp, "Selecciona una opción")

    # ---- A3: fecha de entrega en el calendario -------------------------------

    def test_el_calendario_muestra_la_fecha_de_entrega_del_pedido(self):
        Calendario.objects.create(
            fecha=date(2026, 10, 5), anio=2026, mes=10, nombre_mes="Octubre",
            dia=5, nombre_dia="Lunes", id_pedido=self.pedido,
        )
        resp = self.client.get(reverse("kanview:calendario"), {"mes": "2026-10"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Entrega: 31/12/2026")
        # Y se distingue de la fecha del registro de calendario.
        self.assertContains(resp, "Registro del calendario")

    def test_el_calendario_avisa_cuando_no_hay_fecha_limite(self):
        self.pedido.fecha_limite = None
        self.pedido.save(update_fields=["fecha_limite"])
        Calendario.objects.create(
            fecha=date(2026, 10, 5), anio=2026, mes=10, nombre_mes="Octubre",
            dia=5, nombre_dia="Lunes", id_pedido=self.pedido,
        )
        resp = self.client.get(reverse("kanview:calendario"), {"mes": "2026-10"})
        self.assertContains(resp, "Sin fecha límite")

    # ---- Kanban único: modal de detalle de la actividad ----------------------

    def test_las_tareas_del_tablero_abren_su_modal_de_actividades(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()

        # La tarea de la tarjeta abre el modal de sus actividades.
        self.assertIn('aria-haspopup="dialog"', html)
        self.assertIn(f'data-tarea-detalle="tarea-{self.tarea.pk}"', html)
        self.assertIn("abrirTarea(event, this)", html)
        self.assertIn('id="modal-tarea"', html)
        self.assertIn('id="datos-tareas"', html)
        self.assertIn('id="modal-tarea-grupos"', html)
        self.assertIn("Pendientes", html)
        self.assertIn("En progreso", html)
        self.assertIn("Completadas", html)
        self.assertIn('"Actividad UI"', html)
        self.assertIn('"Empleado UI"', html)
        self.assertIn('"Tapicero"', html)

        # El modal de actividad sigue disponible para cambiar el estado.
        self.assertIn('id="datos-detalle"', html)
        self.assertIn('id="form-estado-actividad"', html)
        self.assertIn('name="estado"', html)

    def test_la_tarjeta_muestra_las_tareas_y_su_responsable(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"))
        html = resp.content.decode()
        cuerpo = html[html.index("</header>"):]
        self.assertIn("Tarea UI", cuerpo)
        self.assertIn("Empleado UI", cuerpo)
        self.assertIn("Tapicero", cuerpo)
        self.assertIn("0/1 actividades", cuerpo)
        self.assertIn(f'data-tarea-detalle="tarea-{self.tarea.pk}"', cuerpo)
        self.assertIn('data-columna="en proceso"', html)

    # ---- B4: los menores ------------------------------------------------------

    def test_la_lista_de_pedidos_no_repite_la_columna_estado(self):
        resp = self.client.get(reverse("kanview:pedido-lista"))
        html = resp.content.decode()
        self.assertEqual(html.count(">Estado</th>"), 1)

    def test_cero_tareas_realizadas_se_muestra_como_cero(self):
        import re

        resp = self.client.get(
            reverse("kanview:usuario-ver", args=["trabajador", self.empleado.pk])
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        valor = re.search(r"Tareas realizadas</dt>.*?<dd[^>]*>([^<]*)</dd>", html, re.S)
        self.assertIsNotNone(valor, "la ficha debe mostrar «Tareas realizadas»")
        self.assertEqual(valor.group(1).strip(), "0")

    def test_los_buscadores_tienen_aria_label(self):
        for url in (reverse("kanview:clientes"), reverse("kanview:inventario"),
                    reverse("kanview:pedidos-tablero")):
            self.assertContains(self.client.get(url), 'aria-label="Buscar')

    def test_el_logo_local_existe_y_reemplaza_a_la_imagen_rota(self):
        from django.contrib.staticfiles import finders

        self.assertIsNotNone(finders.find("kanview/img/logo-kanview-icono.png"))
        for url in (reverse("kanview:dashboard"), reverse("kanview:clientes")):
            resp = self.client.get(url)
            self.assertNotContains(resp, "lh3.googleusercontent.com/aida/AEtjO1")
            self.assertContains(resp, "Logo de Kanview")

    # ---- Una sola configuración de Tailwind para todas las pantallas -------

    def test_la_configuracion_de_tailwind_es_una_sola_y_canonica(self):
        plantillas = settings.BASE_DIR / "kanview" / "templates" / "kanview"
        pantallas = [
            ruta for ruta in plantillas.glob("*.html") if ruta.name != "_tailwind_config.html"
        ]
        inline = [
            ruta.name for ruta in pantallas
            if '<script id="tailwind-config">' in ruta.read_text(encoding="utf-8")
        ]
        self.assertEqual(inline, [], f"configuración de Tailwind duplicada en {inline}")

        canonica = (plantillas / "_tailwind_config.html").read_text(encoding="utf-8")
        # Los valores de la paleta y de las fuentes no se tocaron.
        for token in ('"surface": "#fbf9f8"', '"primary": "#006565"', '"background": "#fbf9f8"',
                      '"label-md": ["14px"', '"headline-md": ["24px"'):
            self.assertIn(token, canonica)

        # Todas las pantallas (y la base del CRUD, que hereda el Panel) la incluyen.
        for obligada in ("crud_base.html", "pedidos_tablero.html", "catalogo.html", "calendario.html",
                         "login.html"):
            texto = (plantillas / obligada).read_text(encoding="utf-8")
            self.assertIn('{% include "kanview/_tailwind_config.html" %}', texto, obligada)

        # Y ninguna vuelve a forzar el fondo gris por CSS.
        for ruta in pantallas:
            self.assertNotIn("#F5F5F5 !important", ruta.read_text(encoding="utf-8"), ruta.name)

    def test_todos_los_modulos_cargan_poppins(self):
        for url in (
            reverse("kanview:dashboard"),
            reverse("kanview:catalogo"),
            reverse("kanview:auditoria"),
            reverse("kanview:finanzas"),
            reverse("kanview:login"),
        ):
            html = self.client.get(url).content.decode()
            self.assertIn("family=Poppins", html, url)
            self.assertNotIn("family=Inter", html, url)

    def test_el_panel_y_el_tablero_renderizan_la_misma_configuracion(self):
        for url in (reverse("kanview:dashboard"), reverse("kanview:pedidos-tablero")):
            html = self.client.get(url).content.decode()
            self.assertEqual(html.count('id="tailwind-config"'), 1, url)
            self.assertNotIn("#F5F5F5 !important", html, url)
        self.assertContains(self.client.get(reverse("kanview:dashboard")), "bg-surface")

    # ---- B1: en móvil el contenido no se sale de la pantalla -----------------

    def test_el_sidebar_se_oculta_en_movil_en_las_plantillas(self):
        for archivo in ("_sidebar.html", "crud_base.html", "pedidos_tablero.html"):
            ruta = settings.BASE_DIR / "kanview" / "templates" / "kanview" / archivo
            texto = ruta.read_text(encoding="utf-8")
            self.assertNotIn("md:ml-64", texto, archivo)
        sidebar = (settings.BASE_DIR / "kanview" / "templates" / "kanview" / "_sidebar.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("hidden lg:flex", sidebar)


class NotificacionesTestCase(TestCase):
    """Campana del header: avisos calculados de datos reales (helper único)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="avisos.admin", password="pass12345")
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.cliente = Cliente.objects.create(nombre="Cliente Avisos", documento="AV-1")
        cls.empleado = Empleado.objects.create(
            documento="AV-2", nombre="Empleado Avisos", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000,
        )
        cls.producto = Producto.objects.create(
            nombre="Tela Avisos", categoria="tela", cantidad=2, precio=1000,
            descripcion="x", codigo_producto="AV0001",
        )
        hoy = timezone.localdate()

        # Pedido activo con la fecha límite vencida y sin evidencias cargadas.
        cls.pedido_vencido = Pedido.objects.create(
            codigo_pedido="AV-0001", fecha_creacion=hoy, hora_creacion=timezone.now(),
            fecha_limite=hoy - timedelta(days=2), estado="activo", evidencias="",
            descripcion="pedido vencido", id_cliente=cls.cliente,
            id_empleado=cls.empleado, id_producto=cls.producto,
        )
        # Tarea vencida y sin completar.
        cls.tarea = TareasPedido.objects.create(
            nombre="Tarea vencida", descripcion="cortar", fecha_inicio=hoy - timedelta(days=9),
            fecha_fin=hoy - timedelta(days=1), estado="pendiente", id_pedido=cls.pedido_vencido,
        )
        # Producto por debajo del umbral de stock bajo (cantidad 2, que está
        # por debajo de UMBRAL_STOCK_BAJO: el pedido de arriba no descuenta
        # inventario porque aún no está aprobado).

    def setUp(self):
        self.client.force_login(self.user)

    def test_el_helper_genera_los_cuatro_tipos_de_aviso(self):
        from .notificaciones import notificaciones

        datos = notificaciones(self.user)
        self.assertEqual(datos["total"], 4, datos)
        textos = " ".join(aviso["texto"] for aviso in datos["avisos"])
        self.assertIn("Tarea vencida", textos)          # tarea vencida
        self.assertIn("AV-0001", textos)                # pedido pasado de fecha
        self.assertIn("no tiene evidencias", textos)    # pedido sin galería
        self.assertIn("Stock bajo", textos)             # producto en umbral
        for aviso in datos["avisos"]:
            self.assertTrue(aviso["url"].startswith("/"), aviso)

    def test_la_campana_muestra_el_contador_y_los_avisos(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"))
        html = resp.content.decode()
        self.assertIn('id="contador-avisos"', html)
        self.assertIn(">4<", html)
        self.assertIn("Avisos del taller", html)
        self.assertIn("Tarea vencida", html)
        self.assertIn('id="panel-avisos"', html)
        self.assertIn('aria-expanded="false"', html)

    def test_sin_avisos_no_hay_contador_ni_lista(self):
        from .notificaciones import notificaciones

        TareasPedido.objects.all().delete()
        Pedido.objects.all().delete()
        Producto.objects.update(cantidad=250)

        datos = notificaciones(self.user)
        self.assertEqual(datos, {"total": 0, "avisos": []})

        html = self.client.get(reverse("kanview:pedidos-tablero")).content.decode()
        self.assertNotIn('id="contador-avisos"', html)
        self.assertIn("No tienes notificaciones.", html)

    def test_un_cliente_solo_ve_los_avisos_de_sus_pedidos(self):
        from .notificaciones import notificaciones

        cliente_user = User.objects.create_user(
            username="avisos.cliente", password="pass12345", email="cliente.avisos@example.com"
        )
        cliente_user.groups.add(_grupo(ROL_CLIENTE))
        self.cliente.correo = "cliente.avisos@example.com"
        self.cliente.save(update_fields=["correo"])

        datos = notificaciones(cliente_user)
        textos = " ".join(aviso["texto"] for aviso in datos["avisos"])
        self.assertIn("AV-0001", textos)
        # No se le avisa del taller (tareas ni inventario).
        self.assertNotIn("Tarea vencida", textos)
        self.assertNotIn("Stock bajo", textos)


class BusquedaHeaderTestCase(TestCase):
    """Buscador del header: `?q=` resuelto en el servidor, con y sin resultados."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="busca.admin", password="pass12345")
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.cliente = Cliente.objects.create(nombre="Cliente Busca", documento="BU-1")
        cls.empleado = Empleado.objects.create(
            documento="BU-2", nombre="Empleado Busca", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000,
        )
        cls.producto_uno = Producto.objects.create(
            nombre="Tela Lino", categoria="tela", cantidad=30, precio=1000,
            descripcion="x", codigo_producto="BU0001",
        )
        cls.producto_dos = Producto.objects.create(
            nombre="Madera Roble", categoria="madera", cantidad=40, precio=2000,
            descripcion="x", codigo_producto="BU0002",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="BU-0001", fecha_creacion=date(2026, 10, 5),
            hora_creacion=timezone.now(), fecha_limite=date(2026, 12, 31),
            estado="activo", evidencias="", descripcion="pedido busca",
            id_cliente=cls.cliente, id_empleado=cls.empleado, id_producto=cls.producto_uno,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Cortar lino", descripcion="corte inicial",
            fecha_inicio=date(2026, 10, 6), fecha_fin=date(2026, 10, 9),
            estado="pendiente", id_pedido=cls.pedido, id_empleado=cls.empleado,
        )
        cls.otra_tarea = TareasPedido.objects.create(
            nombre="Lijar madera", descripcion="lijado",
            fecha_inicio=date(2026, 10, 6), fecha_fin=date(2026, 10, 9),
            estado="pendiente", id_pedido=cls.pedido,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _cuerpo(self, resp):
        """HTML sin el header: la campana puede nombrar registros del taller."""
        html = resp.content.decode()
        return html[html.index("</header>"):]

    # ---- Tablero de procesos --------------------------------------------------

    def test_el_tablero_filtra_por_cliente_producto_y_trabajador(self):
        for termino in ("Cliente Busca", "Tela Lino", "Empleado Busca"):
            resp = self.client.get(reverse("kanview:pedidos-tablero"), {"q": termino})
            cuerpo = self._cuerpo(resp)
            self.assertIn("BU-0001", cuerpo, termino)
            self.assertIn("Buscando en procesos", resp.content.decode(), termino)
            self.assertIn("Quitar filtro", resp.content.decode(), termino)

    def test_el_tablero_sin_resultados_avisa_en_espanol(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"), {"q": "zzzz"})
        cuerpo = self._cuerpo(resp)
        self.assertNotIn("BU-0001", cuerpo)
        self.assertIn("Ningún pedido coincide con «zzzz»", cuerpo)

    def test_el_tablero_filtra_por_codigo_de_pedido(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"), {"q": "BU-0001"})
        self.assertIn("BU-0001", self._cuerpo(resp))

    # ---- Existencias (la pantalla lee de Producto) ----------------------------

    def test_inventario_filtra_por_producto_y_por_codigo(self):
        resp = self.client.get(reverse("kanview:inventario"), {"q": "Lino"})
        cuerpo = self._cuerpo(resp)
        self.assertIn("Tela Lino", cuerpo)
        self.assertNotIn("Madera Roble", cuerpo)

        resp = self.client.get(reverse("kanview:inventario"), {"q": "BU0002"})
        cuerpo = self._cuerpo(resp)
        self.assertIn("Madera Roble", cuerpo)
        self.assertNotIn("Tela Lino", cuerpo)

    def test_inventario_sin_resultados_avisa_en_espanol(self):
        resp = self.client.get(reverse("kanview:inventario"), {"q": "zzzz"})
        cuerpo = self._cuerpo(resp)
        self.assertNotIn("Tela Lino", cuerpo)
        self.assertIn("No hay productos que coincidan con «zzzz»", cuerpo)

    # ---- Listas del CRUD (mismo header, `crud_base.html`) ---------------------

    def test_las_listas_del_crud_tambien_filtran(self):
        resp = self.client.get(reverse("kanview:cliente-lista"), {"q": "Busca"})
        self.assertContains(resp, "Cliente Busca")
        resp = self.client.get(reverse("kanview:cliente-lista"), {"q": "zzzz"})
        self.assertContains(resp, "No hay registros que coincidan con «zzzz»")


class PedidosVistaTestCase(TestCase):
    """Conmutador Kanban / Lista de /pedidos/ (enlaces GET, mismo queryset)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="vista.admin", password="pass12345")
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.cliente = Cliente.objects.create(nombre="Cliente Vista", documento="VI-1")
        cls.empleado = Empleado.objects.create(
            documento="VI-2", nombre="Empleado Vista", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000,
        )
        cls.producto = Producto.objects.create(
            nombre="Silla Vista", categoria="madera", cantidad=30, precio=1000,
            descripcion="x", codigo_producto="VI0001",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="VI-0001", fecha_creacion=date(2026, 10, 5),
            hora_creacion=timezone.now(), fecha_limite=date(2026, 11, 15),
            estado="activo", evidencias="", descripcion="pedido vista",
            id_cliente=cls.cliente, id_empleado=cls.empleado, id_producto=cls.producto,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _boton(self, html, ident):
        import re

        return re.search(r'<a[^>]*id="%s"[^>]*>' % ident, html).group(0)

    def test_por_defecto_muestra_el_tablero(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"))
        html = resp.content.decode()
        self.assertNotIn('id="tabla-pedidos"', html)
        self.assertIn('aria-pressed="true"', self._boton(html, "vista-kanban"))

    def test_vista_lista_muestra_la_tabla_y_marca_el_boton(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"), {"vista": "lista"})
        html = resp.content.decode()
        self.assertIn('id="tabla-pedidos"', html)
        self.assertIn("VI-0001", html)
        self.assertIn("Cliente Vista", html)
        self.assertIn("Silla Vista", html)
        self.assertIn("15/11/2026", html)
        lista = self._boton(html, "vista-lista")
        self.assertIn('aria-pressed="true"', lista)
        self.assertIn('aria-pressed="false"', self._boton(html, "vista-kanban"))
        # El enlace a Kanban existe y conserva el resto de la query.
        self.assertIn("vista=kanban", html)

    def test_la_lista_respeta_el_buscador_del_header(self):
        resp = self.client.get(
            reverse("kanview:pedidos-tablero"), {"vista": "lista", "q": "zzzz"}
        )
        html = resp.content.decode()
        cuerpo = html[html.index("</header>"):]
        self.assertNotIn("VI-0001", cuerpo)
        self.assertIn("Ningún pedido coincide con «zzzz»", cuerpo)
        # El conmutador conserva q al cambiar de vista.
        self.assertIn("q=zzzz", html)

    def test_vista_desconocida_cae_en_el_tablero(self):
        resp = self.client.get(reverse("kanview:pedidos-tablero"), {"vista": "otra"})
        html = resp.content.decode()
        self.assertNotIn('id="tabla-pedidos"', html)
        self.assertIn('aria-pressed="true"', self._boton(html, "vista-kanban"))


class EstadoTareaTestCase(TestCase):
    """Cambio de estado de tareas/actividades desde el tablero (POST-only)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="estado.admin", password="pass12345")
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.cliente = Cliente.objects.create(nombre="Cliente Estado", documento="ES-1")
        cls.empleado = Empleado.objects.create(
            documento="ES-2", nombre="Empleado Estado", cargo="tapcr", celular="300",
            direccion="Calle", salario=1000,
        )
        cls.producto = Producto.objects.create(
            nombre="Tela Estado", categoria="tela", cantidad=30, precio=1000,
            descripcion="x", codigo_producto="ES0001",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="ES-0001", fecha_creacion=date(2026, 10, 5),
            hora_creacion=timezone.now(), estado="activo", evidencias="",
            descripcion="pedido estado", id_cliente=cls.cliente,
            id_empleado=cls.empleado, id_producto=cls.producto,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Tarea Estado", descripcion="x", fecha_inicio=date(2026, 10, 6),
            fecha_fin=date(2026, 10, 30), estado="pendiente", id_pedido=cls.pedido,
            id_empleado=cls.empleado,
        )
        cls.actividad = Actividades.objects.create(
            nombre="Actividad Estado", descripcion="x", fecha_inicio=date(2026, 10, 6),
            fecha_fin=date(2026, 10, 30), estado="pendiente", id_tarea=cls.tarea,
            id_empleado=cls.empleado,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_el_modal_trae_el_control_de_estado(self):
        html = self.client.get(reverse("kanview:pedidos-tablero")).content.decode()
        self.assertIn('id="form-estado-actividad"', html)
        self.assertIn('id="modal-detalle-nuevo-estado"', html)
        self.assertIn('name="estado"', html)
        self.assertIn("csrfmiddlewaretoken", html)
        self.assertIn(f'"url_estado": "/tareas/actividad/{self.actividad.pk}/estado/"', html)

    def test_cambia_el_estado_y_vuelve_al_tablero_con_la_query(self):
        resp = self.client.post(
            reverse("kanview:actividad-estado", args=[self.actividad.pk]) + "?q=estado",
            {"estado": "en progreso"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("q=estado", resp["Location"])
        self.assertIn("/pedidos/", resp["Location"])
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, "en progreso")

        html = self.client.get(reverse("kanview:pedidos-tablero")).content.decode()
        self.assertIn("pasó a «En progreso»", html)
        # El pedido se movió de columna al cambiar su estado calculado.
        self.assertIn("ES-0001", html)

    def test_rechaza_un_estado_invalido_sin_cambiar_nada(self):
        resp = self.client.post(
            reverse("kanview:actividad-estado", args=[self.actividad.pk]),
            {"estado": "volando"},
        )
        self.assertEqual(resp.status_code, 302)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, "pendiente")

        html = self.client.get(reverse("kanview:pedidos-tablero")).content.decode()
        self.assertIn("no es válido", html)

    def test_el_cambio_es_solo_por_post(self):
        resp = self.client.get(reverse("kanview:actividad-estado", args=[self.actividad.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_la_tarea_no_se_cierra_con_actividades_pendientes(self):
        resp = self.client.post(
            reverse("kanview:tarea-estado", args=[self.tarea.pk]),
            {"estado": "completado"},
        )
        self.assertEqual(resp.status_code, 302)
        self.tarea.refresh_from_db()
        self.assertEqual(self.tarea.estado, "pendiente")

    def test_la_tarea_se_cierra_con_todas_las_actividades_completadas(self):
        self.actividad.estado = "completado"
        self.actividad.save(update_fields=["estado"])
        resp = self.client.post(
            reverse("kanview:tarea-estado", args=[self.tarea.pk]),
            {"estado": "completado"},
        )
        self.assertEqual(resp.status_code, 302)
        self.tarea.refresh_from_db()
        self.assertEqual(self.tarea.estado, "completado")
        self.assertEqual(self.tarea.confirmado_por, self.user)

    def test_un_estado_invalido_de_tarea_tampoco_cambia(self):
        self.client.post(
            reverse("kanview:tarea-estado", args=[self.tarea.pk]),
            {"estado": "otro"},
        )
        self.tarea.refresh_from_db()
        self.assertEqual(self.tarea.estado, "pendiente")


class EstadoDelPedidoTestCase(TestCase):
    """`estado_del_pedido` (función pura) en sus cuatro casos."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = Cliente.objects.create(nombre="Cliente Kanban", documento="KB-1")
        cls.empleado = Empleado.objects.create(
            documento="KB-2", nombre="Empleado Kanban", cargo="costr", celular="300",
            direccion="Calle", salario=1000,
        )
        cls.producto = Producto.objects.create(
            nombre="Producto Kanban", categoria="tela", cantidad=10, precio=1000,
            descripcion="x", codigo_producto="KB0001",
        )

    def _pedido(self, codigo):
        return Pedido.objects.create(
            codigo_pedido=codigo, fecha_creacion=date(2026, 10, 5),
            hora_creacion=timezone.now(), estado="activo", evidencias="",
            descripcion="pedido kanban", id_cliente=self.cliente,
            id_empleado=self.empleado, id_producto=self.producto,
        )

    def _tarea(self, pedido, nombre="Tarea"):
        return TareasPedido.objects.create(
            nombre=nombre, descripcion="x", fecha_inicio=date(2026, 10, 6),
            fecha_fin=date(2026, 10, 9), estado="pendiente", id_pedido=pedido,
        )

    def _actividad(self, tarea, estado, nombre="Actividad"):
        return Actividades.objects.create(
            nombre=nombre, descripcion="x", fecha_inicio=date(2026, 10, 6),
            fecha_fin=date(2026, 10, 7), estado=estado, id_tarea=tarea,
            id_empleado=self.empleado,
        )

    def test_sin_actividades_es_pendiente(self):
        from .views_pedidos import estado_del_pedido

        pedido = self._pedido("KB-0001")
        self._tarea(pedido)
        self.assertEqual(estado_del_pedido(pedido), "pendiente")

    def test_todas_completadas_es_completado(self):
        from .views_pedidos import estado_del_pedido

        pedido = self._pedido("KB-0002")
        tarea = self._tarea(pedido)
        self._actividad(tarea, "completado", "Una")
        self._actividad(tarea, "completado", "Otra")
        self.assertEqual(estado_del_pedido(pedido), "completado")

    def test_alguna_en_progreso_es_en_proceso(self):
        from .views_pedidos import estado_del_pedido

        pedido = self._pedido("KB-0003")
        tarea = self._tarea(pedido)
        self._actividad(tarea, "en progreso", "Una")
        self._actividad(tarea, "pendiente", "Otra")
        self.assertEqual(estado_del_pedido(pedido), "en proceso")

    def test_todas_pendientes_es_pendiente(self):
        from .views_pedidos import estado_del_pedido

        pedido = self._pedido("KB-0004")
        tarea = self._tarea(pedido)
        self._actividad(tarea, "pendiente", "Una")
        self._actividad(tarea, "pendiente", "Otra")
        self.assertEqual(estado_del_pedido(pedido), "pendiente")

    def test_el_tablero_agrupa_por_estado_calculado(self):
        from . import views_pedidos

        vencido = self._pedido("KB-0005")
        listo = self._pedido("KB-0006")
        tarea_vencida = self._tarea(vencido, "Tarea A")
        tarea_lista = self._tarea(listo, "Tarea B")
        self._actividad(tarea_vencida, "en progreso", "Act A")
        self._actividad(tarea_lista, "completado", "Act B")

        self.assertEqual(views_pedidos.estado_del_pedido(vencido), "en proceso")
        self.assertEqual(views_pedidos.estado_del_pedido(listo), "completado")


class MigracionExistenciasTestCase(TransactionTestCase):
    """La migración de datos conserva en Producto.cantidad el stock de Inventario."""

    migrate_from = [("kanview", "0008_alter_cliente_correo_and_more")]
    migrate_to = [("kanview", "0010_remove_inventario_id_producto_delete_catalogo_and_more")]

    def _migrar(self, destino):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(destino)
        return ejecutor.loader.project_state(destino).apps

    def test_el_stock_mayor_sobrevive_al_borrar_inventario(self):
        apps_viejas = self._migrar(self.migrate_from)
        Producto = apps_viejas.get_model("kanview", "Producto")
        Inventario = apps_viejas.get_model("kanview", "Inventario")

        # Producto con 5 en su campo y 9 en la línea de inventario.
        producto = Producto.objects.create(
            nombre="Sofá migrado", categoria="tela", cantidad=5, precio=1000,
            descripcion="x", codigo_producto="MIG001",
        )
        Inventario.objects.create(cantidad=9, id_producto_id=producto.pk)

        apps_nuevas = self._migrar(self.migrate_to)
        ProductoNuevo = apps_nuevas.get_model("kanview", "Producto")
        self.assertEqual(ProductoNuevo.objects.get(pk=producto.pk).cantidad, 9)

        # Se vuelve a la última migración para no dejar el esquema a medias.
        self._migrar([("kanview", "0011_actividades_id_empleado_tareaspedido_id_empleado")])


class LoginTestCase(TestCase):
    """El login acepta el correo o el username de la cuenta."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="admin_kanview",
            email="admin@kanview.test",
            password="ClaveSegura123",
            is_staff=True,
            is_superuser=True,
        )

    def _login(self, identificador, clave="ClaveSegura123"):
        return self.client.post(
            reverse("kanview:login"),
            {"username": identificador, "password": clave},
        )

    def test_inicia_sesion_con_el_correo(self):
        respuesta = self._login("admin@kanview.test")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.user.pk
        )

    def test_inicia_sesion_con_el_username(self):
        respuesta = self._login("admin_kanview")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.user.pk
        )

    def test_correo_ambiguo_no_autentica(self):
        User.objects.create_user(
            username="otro_admin",
            email="admin@kanview.test",
            password="ClaveSegura123",
        )
        respuesta = self._login("admin@kanview.test")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_clave_incorrecta_no_autentica(self):
        respuesta = self._login("admin@kanview.test", "clave-equivocada")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class CalendarioEventosTestCase(TestCase):
    """Crear eventos personales y recordatorios desde el calendario."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="calendario.admin", password="pass12345", is_staff=True
        )
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))

    def setUp(self):
        self.client.force_login(self.user)

    def test_el_modal_precarga_la_fecha_seleccionada(self):
        resp = self.client.get(reverse("kanview:calendario"), {"mes": "2026-10"})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="modalFecha"', html)
        self.assertIn('name="fecha"', html)
        self.assertIn('value="pedido"', html)
        self.assertIn('id="form-evento"', html)
        self.assertIn('id="form-pedido"', html)

    def test_crear_evento_personal_desde_el_modal(self):
        fecha = date.today() + timedelta(days=5)
        resp = self.client.post(
            reverse("kanview:calendario-evento-crear"),
            {
                "tipo": "evento",
                "fecha": fecha.isoformat(),
                "titulo": "Reunión de producción",
                "descripcion": "Revisar avances",
                "hora_inicio": "09:00",
                "hora_limite": "10:00",
                "recordatorio": "1",
                "minutos_recordatorio": "30",
            },
        )
        self.assertEqual(resp.status_code, 302)
        evento = Calendario.objects.get(titulo="Reunión de producción")
        self.assertEqual(evento.fecha, fecha)
        self.assertTrue(evento.recordatorio)
        self.assertEqual(evento.minutos_recordatorio, 30)
        self.assertTrue(evento.recordatorios.exists())

    def test_el_evento_personal_aparece_en_el_calendario(self):
        fecha = date.today() + timedelta(days=5)
        Calendario.objects.create(
            fecha=fecha,
            anio=fecha.year,
            mes=fecha.month,
            nombre_mes="Octubre",
            dia=fecha.day,
            nombre_dia="Jueves",
            titulo="Reunión de producción",
            hora_inicio="09:00:00",
            usuario=self.user,
        )
        resp = self.client.get(reverse("kanview:calendario"), {"mes": f"{fecha.year}-{fecha.month:02d}"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reunión de producción")

    def test_no_permite_evento_en_fecha_pasada(self):
        fecha = date.today() - timedelta(days=5)
        resp = self.client.post(
            reverse("kanview:calendario-evento-crear"),
            {
                "tipo": "evento",
                "fecha": fecha.isoformat(),
                "titulo": "Evento pasado",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Calendario.objects.filter(titulo="Evento pasado").exists())

    def test_el_recordatorio_llega_a_notificaciones(self):
        from django.utils import timezone
        from datetime import datetime, timedelta

        fecha = date.today() + timedelta(days=5)
        evento = Calendario.objects.create(
            fecha=fecha,
            anio=fecha.year,
            mes=fecha.month,
            nombre_mes="Octubre",
            dia=fecha.day,
            nombre_dia="Jueves",
            titulo="Reunión de producción",
            hora_inicio="09:00:00",
            recordatorio=True,
            minutos_recordatorio=30,
            usuario=self.user,
        )
        Recordatorio.objects.create(
            calendario=evento,
            fecha_hora=timezone.now() - timedelta(minutes=5),
        )
        self.client.get(reverse("kanview:dashboard"))
        notif = Notificacion.objects.filter(usuario=self.user, tipo="calendario").first()
        self.assertIsNotNone(notif)
        self.assertIn("Reunión de producción", notif.mensaje)


class ReglasDelTallerTestCase(TestCase):
    """Reglas de negocio señaladas en la revisión del proyecto.

    - El trabajador mueve las tarjetas (solo las de SUS procesos) y en el módulo
      Actividades no ve las tareas de sus compañeros.
    - No se permiten pedidos con fecha límite en días anteriores.
    - El precio del pedido se toma del inventario.
    - El inventario se disminuye al aprobar el pedido (y se devuelve al
      desactivarlo o rechazarlo).
    - Un proceso solo se marca completado si ya se realizaron sus tareas, y al
      finalizar queda en el histórico (con su factura reflejada en Finanzas).
    - Al desactivar un cliente no se muestran sus pedidos anteriores.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="reglas.admin", password="pass12345", is_staff=True
        )
        cls.admin.groups.add(_grupo(ROL_ADMINISTRADOR))

        cls.trabajador_user = User.objects.create_user(
            username="reglas.trabajador", password="pass12345"
        )
        cls.trabajador_user.groups.add(_grupo(ROL_TRABAJADOR))
        cls.empleado = Empleado.objects.create(
            documento="RT-1", nombre="Taller Uno", cargo="tapcr", celular="300",
            direccion="Calle 1", salario=1000, usuario=cls.trabajador_user,
        )
        cls.companero = Empleado.objects.create(
            documento="RT-2", nombre="Taller Dos", cargo="costur", celular="301",
            direccion="Calle 2", salario=1000,
        )

        cls.cliente = Cliente.objects.create(
            nombre="Cliente Reglas", documento="RT-3", correo="reglas.cliente@example.com",
        )
        cls.cliente_user = User.objects.create_user(
            username="reglas.cliente", password="pass12345",
            email="reglas.cliente@example.com",
        )
        cls.cliente_user.groups.add(_grupo(ROL_CLIENTE))

        cls.producto = Producto.objects.create(
            nombre="Cuero Reglas", categoria="tela", cantidad=10, precio=250000,
            descripcion="x", codigo_producto="RT0001",
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="RT-0001", fecha_creacion=timezone.localdate(),
            hora_creacion=timezone.now(), fecha_limite=timezone.localdate() + timedelta(days=5),
            descripcion="pedido propio", id_cliente=cls.cliente,
            id_empleado=cls.empleado, id_producto=cls.producto, cantidad=2,
        )
        cls.pedido_ajeno = Pedido.objects.create(
            codigo_pedido="RT-0002", fecha_creacion=timezone.localdate(),
            hora_creacion=timezone.now(), fecha_limite=timezone.localdate() + timedelta(days=5),
            descripcion="pedido del compañero", id_cliente=cls.cliente,
            id_empleado=cls.companero, id_producto=cls.producto, cantidad=1,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Tarea propia", descripcion="x",
            fecha_inicio=timezone.localdate(), fecha_fin=timezone.localdate() + timedelta(days=1),
            id_pedido=cls.pedido, id_empleado=cls.empleado,
        )
        cls.actividad_propia = Actividades.objects.create(
            nombre="Actividad propia", descripcion="x",
            fecha_inicio=timezone.localdate(), fecha_fin=timezone.localdate() + timedelta(days=1),
            id_tarea=cls.tarea, id_empleado=cls.empleado,
        )
        cls.tarea_ajena = TareasPedido.objects.create(
            nombre="Tarea ajena", descripcion="x",
            fecha_inicio=timezone.localdate(), fecha_fin=timezone.localdate() + timedelta(days=1),
            id_pedido=cls.pedido_ajeno, id_empleado=cls.companero,
        )
        cls.actividad_ajena = Actividades.objects.create(
            nombre="Actividad ajena", descripcion="x",
            fecha_inicio=timezone.localdate(), fecha_fin=timezone.localdate() + timedelta(days=1),
            id_tarea=cls.tarea_ajena, id_empleado=cls.companero,
        )

    def _datos(self, **extra):
        datos = {
            "estado": "activo", "cantidad": 1, "descripcion": "pedido de prueba",
            "id_cliente": self.cliente.pk, "id_empleado": self.empleado.pk,
            "id_producto": self.producto.pk,
            "fecha_limite": (timezone.localdate() + timedelta(days=5)).isoformat(),
        }
        datos.update(extra)
        return datos

    # ---- Fechas límite ----------------------------------------------------

    def test_no_se_permite_un_pedido_con_fecha_limite_en_dias_anteriores(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("kanview:pedido-crear"),
            self._datos(fecha_limite=(timezone.localdate() - timedelta(days=1)).isoformat()),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Pedido.objects.filter(descripcion="pedido de prueba").exists())
        self.assertContains(resp, "no puede ser anterior a hoy")

        # En edición tampoco se acepta retroceder la fecha límite.
        resp = self.client.post(
            reverse("kanview:pedido-editar", args=[self.pedido.pk]),
            self._datos(fecha_limite=(timezone.localdate() - timedelta(days=3)).isoformat()),
        )
        self.assertEqual(resp.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(
            self.pedido.fecha_limite, timezone.localdate() + timedelta(days=5)
        )

    # ---- Precio del inventario -------------------------------------------

    def test_el_precio_del_pedido_se_toma_del_inventario(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("kanview:pedido-crear"))
        self.assertContains(resp, "Precio unitario (del inventario)")
        self.assertContains(resp, 'data-precio="250000')

        self.client.force_login(self.cliente_user)
        resp = self.client.get(reverse("kanview:pedido-cliente-crear"))
        self.assertContains(resp, "Precio unitario (del inventario)")
        self.assertContains(resp, 'data-precio="250000')

    # ---- Inventario ------------------------------------------------------

    def test_el_inventario_se_descuenta_al_aprobar_y_no_al_crear(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("kanview:pedido-crear"), self._datos())
        self.assertEqual(resp.status_code, 302)
        nuevo = Pedido.objects.get(descripcion="pedido de prueba")
        self.assertEqual(nuevo.estado_aprobacion, "pendiente")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad, 10, "crear el pedido no descuenta inventario")

        # Al aprobar sí se disminuye el inventario.
        resp = self.client.post(
            reverse("kanview:pedido-aprobar", args=[nuevo.pk]),
            {"empleado": self.empleado.pk},
        )
        self.assertEqual(resp.status_code, 302)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad, 9)

        # Desactivar el pedido devuelve las unidades al inventario.
        self.client.post(reverse("kanview:pedido-eliminar", args=[nuevo.pk]))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad, 10)

    def test_no_se_aprueba_un_pedido_sin_stock_suficiente(self):
        sin_stock = Pedido.objects.create(
            codigo_pedido="RT-0003", fecha_creacion=timezone.localdate(),
            hora_creacion=timezone.now(), fecha_limite=timezone.localdate() + timedelta(days=5),
            descripcion="pedido enorme", id_cliente=self.cliente,
            id_empleado=self.empleado, id_producto=self.producto, cantidad=50,
        )
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("kanview:pedido-aprobar", args=[sin_stock.pk]),
            {"empleado": self.empleado.pk}, follow=True,
        )
        sin_stock.refresh_from_db()
        self.assertEqual(sin_stock.estado_aprobacion, "pendiente")
        self.assertContains(resp, "No hay suficientes unidades disponibles")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad, 10)

    # ---- Mover tarjetas --------------------------------------------------

    def test_el_trabajador_mueve_solo_las_tarjetas_de_sus_procesos(self):
        self.client.force_login(self.trabajador_user)
        resp = self.client.post(
            reverse("kanview:pedido-estado", args=[self.pedido.pk]),
            {"estado": "en proceso"},
        )
        self.assertEqual(resp.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_kanban, "en proceso")

        # El proceso de su compañero no lo puede mover.
        resp = self.client.post(
            reverse("kanview:pedido-estado", args=[self.pedido_ajeno.pk]),
            {"estado": "en proceso"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_el_cliente_no_mueve_tarjetas(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.post(
            reverse("kanview:pedido-estado", args=[self.pedido.pk]),
            {"estado": "en proceso"},
        )
        self.assertEqual(resp.status_code, 403)

    # ---- Módulo Actividades ----------------------------------------------

    def test_el_trabajador_solo_ve_sus_actividades(self):
        self.client.force_login(self.trabajador_user)
        resp = self.client.get(reverse("kanview:actividades"))
        self.assertContains(resp, "Actividad propia")
        self.assertNotContains(resp, "Actividad ajena")
        self.assertNotContains(resp, "Taller Dos")

        # El administrador sí ve todas.
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("kanview:actividades"))
        self.assertContains(resp, "Actividad propia")
        self.assertContains(resp, "Actividad ajena")

    def test_el_trabajador_no_cambia_actividades_de_sus_companeros(self):
        self.client.force_login(self.trabajador_user)
        resp = self.client.post(
            reverse("kanview:actividad-estado", args=[self.actividad_ajena.pk]),
            {"estado": "en progreso"},
        )
        # La vista responde con un aviso y redirección (el cambio no se aplica).
        self.assertEqual(resp.status_code, 302)
        self.actividad_ajena.refresh_from_db()
        self.assertEqual(self.actividad_ajena.estado, "pendiente")

    # ---- Finalización e histórico ----------------------------------------

    def test_completar_el_proceso_exige_las_tareas_realizadas(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("kanview:pedido-estado", args=[self.pedido.pk]),
            {"estado": "completado"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("tarea", resp.json()["error"].lower())

        # Con la tarea y su actividad realizadas, el proceso queda en el
        # histórico y su pago se refleja en Finanzas (amarrado al pedido).
        self.actividad_propia.estado = "completado"
        self.actividad_propia.save(update_fields=["estado"])
        self.tarea.estado = "completado"
        self.tarea.save(update_fields=["estado"])
        resp = self.client.post(
            reverse("kanview:pedido-estado", args=[self.pedido.pk]),
            {"estado": "completado"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            Historial.objects.filter(id_pedido=self.pedido, accion="pedido_completado").exists()
        )
        pago = AnalisisFinanciero.objects.filter(id_pedido=self.pedido).first()
        self.assertIsNotNone(pago)
        self.assertEqual(pago.fuentes_ingresos, self.pedido.factura.total)

        # Y el cliente lo ve en su histórico (log de pedidos completados).
        self.client.force_login(self.cliente_user)
        resp = self.client.get(reverse("kanview:historico"))
        self.assertContains(resp, "RT-0001")
        self.assertContains(resp, "pedido_completado".replace("_", " ").capitalize())

    # ---- Cliente desactivado ---------------------------------------------

    def test_desactivar_un_cliente_oculta_sus_pedidos(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("kanview:cliente-eliminar", args=[self.cliente.pk]))
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get(reverse("kanview:pedidos-tablero"))
        codigos = [tarjeta["codigo"] for tarjeta in resp.context["tarjetas"]]
        self.assertNotIn("RT-0001", codigos)
        self.assertNotIn("RT-0002", codigos)

        self.assertEqual(
            self.client.get(reverse("kanview:pedido-detalle", args=[self.pedido.pk])).status_code,
            404,
        )
        resp = self.client.get("/api/pedidos/")
        self.assertNotIn("RT-0001", resp.content.decode())


class ProcesoPredefinidoTestCase(TestCase):
    """Al crear un pedido se carga su proceso típico de tapicería.

    Cada producto recibe sus tareas y actividades comunes (mesa, sofá, silla,
    restauración, carro, moto o proceso general) y sobre esa base se pueden
    agregar tareas o actividades extra desde el CRUD.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="proceso.admin", password="pass12345", is_staff=True
        )
        cls.user.groups.add(_grupo(ROL_ADMINISTRADOR))
        cls.cliente = Cliente.objects.create(
            nombre="Cliente Proceso", documento="PR-1",
            correo="proceso.cliente@example.com",
        )
        cls.cliente_user = User.objects.create_user(
            username="proceso.cliente", password="pass12345",
            email="proceso.cliente@example.com",
        )
        cls.cliente_user.groups.add(_grupo(ROL_CLIENTE))
        cls.empleado = Empleado.objects.create(
            documento="PR-2", nombre="Trabajador Proceso", cargo="tapcr",
            celular="300", direccion="Calle", salario=1000,
        )
        cls.mesa = Producto.objects.create(
            nombre="Mesa de comedor", categoria="madera", cantidad=5,
            precio=500000, codigo_producto="PR0001",
        )

    def _datos(self, **extra):
        datos = {
            "estado": "activo", "cantidad": 1, "descripcion": "pedido de proceso",
            "id_cliente": self.cliente.pk, "id_empleado": self.empleado.pk,
            "id_producto": self.mesa.pk,
            "fecha_limite": (timezone.localdate() + timedelta(days=10)).isoformat(),
        }
        datos.update(extra)
        return datos

    def test_crear_un_pedido_carga_su_proceso_tipico(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("kanview:pedido-crear"), self._datos())
        self.assertEqual(resp.status_code, 302)
        pedido = Pedido.objects.get(descripcion="pedido de proceso")
        nombres = list(pedido.tareaspedido_set.values_list("nombre", flat=True))
        self.assertIn("Diseño y rectificado", nombres)
        self.assertIn("Corte y cepillado", nombres)
        self.assertIn("Lijado progresivo", nombres)
        self.assertIn("Acabado y sellado", nombres)
        self.assertTrue(Actividades.objects.filter(id_tarea__id_pedido=pedido).exists())
        # Las fechas del trabajo quedan dentro de la ventana del pedido.
        for tarea in pedido.tareaspedido_set.all():
            self.assertGreaterEqual(tarea.fecha_inicio, pedido.fecha_creacion)
            self.assertLessEqual(tarea.fecha_fin, pedido.fecha_limite)

    def test_el_cliente_tambien_recibe_el_proceso_de_su_pedido(self):
        Producto.objects.create(
            nombre="Sofá de terciopelo", categoria="tela", cantidad=3,
            precio=2000000, codigo_producto="PR0002",
        )
        sofa = Producto.objects.get(codigo_producto="PR0002")
        self.client.force_login(self.cliente_user)
        resp = self.client.post(reverse("kanview:pedido-cliente-crear"), {
            "id_producto": sofa.pk, "cantidad": "1", "descripcion": "sofa nuevo",
        })
        self.assertEqual(resp.status_code, 302)
        pedido = Pedido.objects.get(descripcion="sofa nuevo")
        nombres = list(pedido.tareaspedido_set.values_list("nombre", flat=True))
        self.assertIn("Cincha e hilado (suspensión)", nombres)
        self.assertIn("Tapizado y engrapado", nombres)

    def test_cada_producto_recibe_su_proceso(self):
        from .plantillas_proceso import plantilla_para

        casos = {
            "Mesa de comedor": "Fabricación de mesa",
            "Sofá de terciopelo": "Fabricación de sofá desde cero",
            "Silla de comedor": "Fabricación y tapizado de sillas",
            "Sillón reclinable": "Fabricación de sofá desde cero",
            "Mueble usado para retapizar": "Tapicería general (restauración de muebles)",
            "Asiento de carro": "Tapicería de silla/asiento de carro",
            "Sillín de moto": "Tapicería de asiento de moto",
            "Alfombra persa": "Proceso general de tapicería",
        }
        for producto, esperado in casos.items():
            self.assertEqual(plantilla_para(producto)["nombre"], esperado, producto)

    def test_se_pueden_agregar_tareas_y_actividades_extra_desde_el_crud(self):
        self.client.force_login(self.user)
        self.client.post(reverse("kanview:pedido-crear"), self._datos())
        pedido = Pedido.objects.get(descripcion="pedido de proceso")
        base = pedido.tareaspedido_set.count()
        self.assertGreater(base, 0)

        # Una tarea extra (lo que pida el cliente) se agrega desde el CRUD.
        resp = self.client.post(reverse("kanview:tarea-crear"), {
            "nombre": "Tarea extra pedida por el cliente",
            "descripcion": "adicional al proceso típico",
            "fecha_inicio": timezone.localdate().isoformat(),
            "fecha_fin": (timezone.localdate() + timedelta(days=2)).isoformat(),
            "estado": "pendiente",
            "id_pedido": pedido.pk,
            "id_empleado": self.empleado.pk,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(pedido.tareaspedido_set.count(), base + 1)

        # Los formularios llegan con el pedido/tarea preseleccionados.
        resp = self.client.get(reverse("kanview:tarea-crear"), {"pedido": pedido.pk})
        self.assertEqual(resp.context["form"].initial.get("id_pedido"), pedido.pk)
        tarea_extra = TareasPedido.objects.get(nombre="Tarea extra pedida por el cliente")
        resp = self.client.get(reverse("kanview:actividad-crear"), {"tarea": tarea_extra.pk})
        self.assertEqual(resp.context["form"].initial.get("id_tarea"), tarea_extra.pk)
