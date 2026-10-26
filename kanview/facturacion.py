"""Generación y envío de facturas en PDF."""

from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.db import IntegrityError, transaction
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .correo import enviar_correo
from .formato import moneda_cop
from .models import Factura


def _siguiente_numero():
    mayor = 0
    for numero in Factura.objects.values_list("numero", flat=True):
        if numero and numero.upper().startswith("FAC-"):
            try:
                mayor = max(mayor, int(numero[4:]))
            except ValueError:
                continue
    return f"FAC-{mayor + 1:04d}"


def crear_factura(pedido, usuario=None):
    """Crea (o devuelve) la factura del pedido con los datos congelados."""
    try:
        return pedido.factura, False
    except Factura.DoesNotExist:
        pass

    precio = Decimal(pedido.id_producto.precio)
    cantidad = Decimal(pedido.cantidad or 1)
    subtotal = (precio * cantidad).quantize(Decimal("0.01"))
    iva_porcentaje = Decimal(str(getattr(settings, "FACTURA_IVA", 0) or 0))
    iva_valor = (subtotal * iva_porcentaje / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = (subtotal + iva_valor).quantize(Decimal("0.01"))

    for _ in range(5):
        try:
            with transaction.atomic():
                factura = Factura.objects.create(
                    pedido=pedido,
                    numero=_siguiente_numero(),
                    cliente_nombre=pedido.id_cliente.nombre,
                    cliente_documento=pedido.id_cliente.documento or "",
                    cliente_correo=pedido.id_cliente.correo or "",
                    cliente_direccion=pedido.id_cliente.direccion or "",
                    producto_nombre=pedido.id_producto.nombre,
                    cantidad=pedido.cantidad or 1,
                    precio_unitario=precio,
                    subtotal=subtotal,
                    iva_porcentaje=iva_porcentaje,
                    iva_valor=iva_valor,
                    total=total,
                    creado_por=usuario if getattr(usuario, "is_authenticated", False) else None,
                )
                return factura, True
        except IntegrityError:
            # Si otro proceso creó la factura del mismo pedido, se devuelve.
            try:
                return pedido.factura, False
            except Factura.DoesNotExist:
                continue
    raise IntegrityError("No se pudo asignar un número único a la factura.")


def generar_pdf(factura):
    """Devuelve el PDF de la factura como ``BytesIO``."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Factura {factura.numero}",
        author=getattr(settings, "EMPRESA_NOMBRE", "Kanview"),
    )
    estilos = getSampleStyleSheet()
    titulo = estilos["Title"]
    normal = estilos["Normal"]
    pequeno = estilos["BodyText"].clone("pequeno")
    pequeno.fontSize = 9
    pequeno.leading = 12

    fecha_limite = (
        factura.pedido.fecha_limite.strftime("%d/%m/%Y")
        if factura.pedido.fecha_limite
        else "Sin fecha"
    )
    elementos = [
        Paragraph(escape(getattr(settings, "EMPRESA_NOMBRE", "Kanview")), titulo),
        Paragraph(
            f"NIT: {escape(getattr(settings, 'EMPRESA_NIT', ''))}<br/>"
            f"{escape(getattr(settings, 'EMPRESA_DIRECCION', ''))}<br/>"
            f"Tel: {escape(getattr(settings, 'EMPRESA_TELEFONO', ''))} · "
            f"{escape(getattr(settings, 'EMPRESA_CORREO', ''))}",
            pequeno,
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Factura {factura.numero}</b>", estilos["Heading2"]),
        Paragraph(
            f"Pedido: {escape(factura.pedido.codigo_pedido)}<br/>"
            f"Fecha del pedido: {factura.pedido.fecha_creacion:%d/%m/%Y}<br/>"
            f"Fecha límite: {fecha_limite}<br/>"
            f"Fecha de emisión: {factura.fecha_emision:%d/%m/%Y %H:%M}<br/>"
            f"Estado del pedido: {factura.pedido.get_estado_aprobacion_display()}<br/>"
            f"Responsable: {escape(factura.pedido.id_empleado.nombre if factura.pedido.id_empleado else 'Sin asignar')}",
            normal,
        ),
        Spacer(1, 0.5 * cm),
        Paragraph("<b>Cliente</b>", estilos["Heading3"]),
        Paragraph(
            f"{escape(factura.cliente_nombre)}<br/>"
            f"Documento: {escape(factura.cliente_documento or 'Sin documento')}<br/>"
            f"Correo: {escape(factura.cliente_correo or 'Sin correo')}<br/>"
            f"Dirección: {escape(factura.cliente_direccion or 'Sin dirección')}",
            normal,
        ),
        Spacer(1, 0.6 * cm),
    ]

    datos = [
        ["Producto", "Cantidad", "Precio unitario", "Subtotal"],
        [
            escape(factura.producto_nombre),
            str(factura.cantidad),
            f"$ {moneda_cop(factura.precio_unitario)}",
            f"$ {moneda_cop(factura.subtotal)}",
        ],
    ]
    tabla = Table(datos, colWidths=[7.2 * cm, 2.2 * cm, 3.3 * cm, 3.3 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#006565")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4c4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f7")]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 0.5 * cm))

    totales = Table(
        [
            ["Subtotal", f"$ {moneda_cop(factura.subtotal)}"],
            [f"IVA ({factura.iva_porcentaje}%)", f"$ {moneda_cop(factura.iva_valor)}"],
            ["Total", f"$ {moneda_cop(factura.total)}"],
        ],
        colWidths=[12 * cm, 4 * cm],
    )
    totales.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#006565")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elementos.extend([totales, Spacer(1, 0.8 * cm)])
    elementos.append(
        Paragraph(
            "Factura generada por Kanview. "
            f"Pedido: {factura.pedido.codigo_pedido} · "
            f"Descripción: {escape(factura.pedido.descripcion)}",
            pequeno,
        )
    )
    documento.build(elementos)
    buffer.seek(0)
    return buffer


def enviar_factura(factura):
    """Envía el PDF al correo del cliente. Devuelve True si salió el correo."""
    if not factura.cliente_correo:
        return False
    pdf = generar_pdf(factura)
    return enviar_correo(
        f"Kanview · Factura {factura.numero}",
        f"Hola {factura.cliente_nombre},\n\n"
        f"Adjuntamos la factura {factura.numero} del pedido "
        f"{factura.pedido.codigo_pedido}.\n\nGracias por confiar en Kanview.",
        [factura.cliente_correo],
        adjuntos=[(f"factura-{factura.numero}.pdf", pdf.getvalue(), "application/pdf")],
    )
