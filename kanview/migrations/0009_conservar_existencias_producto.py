"""Migración de DATOS: conserva en ``Producto.cantidad`` las existencias reales.

Antes de borrar las tablas ``Inventario`` y ``Catalogo`` (que duplicaban el
stock), cada línea de Inventario se compara con su producto: si el inventario
tenía más unidades se queda ese valor mayor en ``Producto.cantidad`` para no
perder existencias. Es idempotente: volver a correrla no cambia nada.
"""

from django.db import migrations


def conservar_existencias(apps, schema_editor):
    Inventario = apps.get_model("kanview", "Inventario")
    Producto = apps.get_model("kanview", "Producto")

    for linea in Inventario.objects.all().order_by("pk"):
        producto = Producto.objects.filter(pk=linea.id_producto_id).first()
        if producto is None:
            continue
        if (linea.cantidad or 0) > (producto.cantidad or 0):
            Producto.objects.filter(pk=producto.pk).update(cantidad=linea.cantidad)


class Migration(migrations.Migration):

    dependencies = [
        ("kanview", "0008_alter_cliente_correo_and_more"),
    ]

    operations = [
        migrations.RunPython(conservar_existencias, migrations.RunPython.noop),
    ]
