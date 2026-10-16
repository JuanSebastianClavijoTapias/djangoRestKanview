from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Actividades,
    Administrador,
    AnalisisFinanciero,
    Calendario,
    Catalogo,
    Cliente,
    Empleado,
    Historial,
    Inventario,
    Pedido,
    Producto,
    TareasPedido,
)


class CrudModulesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="tester", password="pass12345", is_staff=True
        )
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
            nombre="Silla", categoria="Muebles", cantidad=5, precio=100,
            descripcion="x", codigo_producto="A1B2C3",
        )
        cls.inventario = Inventario.objects.create(
            cantidad=10, id_producto=cls.producto
        )
        cls.pedido = Pedido.objects.create(
            codigo_pedido="P00001", fecha_creacion=date(2026, 10, 16),
            hora_creacion=timezone.now(), estado="activo", evidencias="",
            descripcion="x", id_cliente=cls.cliente, id_empleado=cls.empleado,
            id_producto=cls.producto,
        )
        cls.tarea = TareasPedido.objects.create(
            nombre="Cortar", descripcion="x", fecha_inicio=date(2026, 10, 16),
            fecha_fin=date(2026, 10, 17), estado="pendiente", id_pedido=cls.pedido,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _modules(self):
        """(url_name_prefix, model, create_data, update_data) para los 7 módulos nuevos."""
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
                "inventario",
                Inventario,
                {"cantidad": "15", "id_producto": self.producto.pk},
                {"cantidad": "25", "id_producto": self.producto.pk},
            ),
            (
                "catalogo",
                Catalogo,
                {"categorias": "Cueros", "id_inventario": self.inventario.pk,
                 "id_producto": self.producto.pk},
                {"categorias": "Maderas", "id_inventario": self.inventario.pk,
                 "id_producto": self.producto.pk},
            ),
            (
                "tarea",
                TareasPedido,
                {"nombre": "Cortar", "descripcion": "x", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-17", "estado": "pendiente", "id_pedido": self.pedido.pk},
                {"nombre": "Coser", "descripcion": "y", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-18", "estado": "en progreso", "id_pedido": self.pedido.pk},
            ),
            (
                "actividad",
                Actividades,
                {"nombre": "Medir", "descripcion": "x", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-16", "estado": "pendiente", "id_tarea": self.tarea.pk},
                {"nombre": "Pegar", "descripcion": "y", "fecha_inicio": "2026-10-16",
                 "fecha_fin": "2026-10-17", "estado": "completado", "id_tarea": self.tarea.pk},
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

    def test_all_list_pages_render(self):
        prefixes = [
            "cliente", "empleado", "administrador", "producto", "pedido",
            "analisis-financiero", "inventario", "catalogo", "tarea",
            "actividad", "historial", "calendario",
        ]
        for prefix in prefixes:
            url = reverse(f"kanview:{prefix}-lista")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertContains(resp, "Nuevo")

    def test_create_forms_render(self):
        for name, _model, _create, _update in self._modules():
            url = reverse(f"kanview:{name}-crear")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)

    def test_create_update_delete_flows(self):
        for name, model, create_data, update_data in self._modules():
            # Crear
            resp = self.client.post(reverse(f"kanview:{name}-crear"), create_data)
            self.assertEqual(resp.status_code, 302, f"{name} create")
            obj = model.objects.order_by("-pk").first()
            self.assertIsNotNone(obj, f"{name} created")

            # Editar
            resp = self.client.post(
                reverse(f"kanview:{name}-editar", args=[obj.pk]), update_data
            )
            self.assertEqual(resp.status_code, 302, f"{name} update")
            obj.refresh_from_db()

            # Eliminar
            resp = self.client.post(reverse(f"kanview:{name}-eliminar", args=[obj.pk]))
            self.assertEqual(resp.status_code, 302, f"{name} delete")
            self.assertFalse(model.objects.filter(pk=obj.pk).exists(), f"{name} deleted")
