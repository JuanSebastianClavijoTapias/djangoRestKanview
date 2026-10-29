"""Procesos predefinidos de tapicería: tareas y actividades por tipo de producto.

Cada vez que se crea un pedido se carga automáticamente el proceso típico de
lo que se hace en el taller para ese producto (mesa, sofá, silla, restauración,
asiento de carro o de moto). Es la base de trabajo: si el cliente quiere una
tarea o una actividad más, se agrega después desde el CRUD de Tareas y
Actividades (con el pedido ya preseleccionado).

La selección es por palabras clave del nombre del producto (sin distinguir
mayúsculas ni tildes). Si el producto no coincide con ningún proceso conocido
se usa el proceso general de tapicería.
"""

import unicodedata
from datetime import timedelta

from . import historial
from .models import Actividades, TareasPedido


def _normalizar(texto):
    """Minúsculas y sin tildes, para comparar los nombres de producto."""
    sin_tildes = "".join(
        caracter for caracter in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tildes.split())


# Cada proceso: palabras clave del producto, nombre del proceso, tareas y
# actividades típicas (el trabajo común del taller para ese artículo).
PLANTILLAS = (
    {
        "claves": ("moto", "motocicleta", "motoneta", "ciclomotor", "quad", "sillin"),
        "nombre": "Tapicería de asiento de moto",
        "tareas": [
            {
                "nombre": "Desmontaje",
                "descripcion": "Retirar el sillín del chasis de la moto.",
                "actividades": [
                    {"nombre": "Retirar el sillín del chasis", "descripcion": "Soltar los tornillos o broches y separar el sillín del chasis."},
                ],
            },
            {
                "nombre": "Retiro del material viejo",
                "descripcion": "Quitar las grapas perimetrales y retirar el forro dañado.",
                "actividades": [
                    {"nombre": "Quitar grapas y forro dañado", "descripcion": "Retirar las grapas perimetrales y despegar el forro sin dañar la base."},
                ],
            },
            {
                "nombre": "Modificación y confort",
                "descripcion": "Recortar la espuma original para bajar la altura o agregar capas de gel/espuma viscoelástica para viajes largos.",
                "actividades": [
                    {"nombre": "Ajustar la espuma a la altura", "descripcion": "Recortar o agregar gel/espuma viscoelástica según lo pedido."},
                ],
            },
            {
                "nombre": "Tratamiento antihumedad",
                "descripcion": "Colocar un plástico protector sobre la espuma para evitar que absorba agua si se filtra por las costuras.",
                "actividades": [
                    {"nombre": "Colocar plástico protector", "descripcion": "Cubrir la espuma con plástico antihumedad y fijarlo."},
                ],
            },
            {
                "nombre": "Corte del vinilo sintético",
                "descripcion": "Usar telas impermeables con textura antideslizante (tipo «sintético térmico» o «grip»).",
                "actividades": [
                    {"nombre": "Cortar el vinilo impermeable", "descripcion": "Cortar el material sintético antideslizante con los patrones del sillín."},
                ],
            },
            {
                "nombre": "Confección con hilo marroquinero",
                "descripcion": "Coser con hilos de poliéster/nylon resistentes a la intemperie que no se pudran con el agua.",
                "actividades": [
                    {"nombre": "Coser con hilo marroquinero", "descripcion": "Unir las piezas con hilo de poliéster/nylon a prueba de agua."},
                ],
            },
            {
                "nombre": "Tensionado al calor y engrapado",
                "descripcion": "Usar pistola de calor para moldear la cuerina a las curvas del sillín mientras se engrapa por la cara interna de la base.",
                "actividades": [
                    {"nombre": "Moldear al calor y engrapar", "descripcion": "Tensionar la cuerina con calor en las curvas y engrapar por la cara interna."},
                ],
            },
        ],
    },
    {
        "claves": ("carro", "auto", "automovil", "vehiculo", "camioneta", "camion", "van"),
        "nombre": "Tapicería de silla/asiento de carro",
        "tareas": [
            {
                "nombre": "Desmontaje",
                "descripcion": "Retirar la silla del vehículo soltando los rieles y desconectando los sensores (cinturón o airbag).",
                "actividades": [
                    {"nombre": "Soltar rieles y desconectar sensores", "descripcion": "Desconectar los sensores del cinturón o airbag antes de manipular."},
                    {"nombre": "Retirar la silla del vehículo", "descripcion": "Soltar los rieles y sacar la silla con cuidado."},
                ],
            },
            {
                "nombre": "Desvestido",
                "descripcion": "Retirar la funda original quitando los anillos de sujeción (hog rings) de alambre.",
                "actividades": [
                    {"nombre": "Quitar anillos y funda original", "descripcion": "Retirar los hog rings de alambre y desmontar la funda pieza por pieza."},
                ],
            },
            {
                "nombre": "Reparación del cojín de espuma",
                "descripcion": "Si la espuma está cedida o rota, repararla con espuma de alta densidad y moldearla con pulidora/amoladora.",
                "actividades": [
                    {"nombre": "Reparar y moldear la espuma", "descripcion": "Rellenar los huecos con espuma de alta densidad y perfilar la forma."},
                ],
            },
            {
                "nombre": "Patronaje de alta precisión",
                "descripcion": "Desarmar la funda vieja pieza por pieza para calcar los patrones exactos en el material nuevo (cuero, vinilcuero o tela automotriz).",
                "actividades": [
                    {"nombre": "Calcar patrones de la funda vieja", "descripcion": "Usar cada pieza de la funda original como molde."},
                    {"nombre": "Cortar el material nuevo", "descripcion": "Cortar cuero, vinilcuero o tela automotriz con los patrones calzados."},
                ],
            },
            {
                "nombre": "Costura y pespunte",
                "descripcion": "Coser las piezas agregando guata o espuma delgada en el revés para dar volumen y realizar las dobles costuras decorativas.",
                "actividades": [
                    {"nombre": "Coser piezas con guata de volumen", "descripcion": "Unir las piezas con guata o espuma delgada al reverso."},
                    {"nombre": "Realizar dobles costuras decorativas", "descripcion": "Marcar el pespunte visible según el diseño original."},
                ],
            },
            {
                "nombre": "Instalación de la funda",
                "descripcion": "Calzar la funda nueva sobre la espuma y fijarla a la varilla interna con alicates y anillos de sujeción metálicos.",
                "actividades": [
                    {"nombre": "Calzar y fijar la funda nueva", "descripcion": "Moldear la funda al contorno y fijarla con anillos metálicos."},
                ],
            },
            {
                "nombre": "Reinstalación",
                "descripcion": "Montar el asiento nuevamente en el auto y verificar que los rieles corran sin problema.",
                "actividades": [
                    {"nombre": "Montar asiento y verificar rieles", "descripcion": "Volver a instalar la silla, reconectar sensores y probar los rieles."},
                ],
            },
        ],
    },
    {
        "claves": ("sofa", "sillon", "reclinable", "chaise", "daybed"),
        "nombre": "Fabricación de sofá desde cero",
        "tareas": [
            {
                "nombre": "Armado del esqueleto (estructura)",
                "descripcion": "Cortar y ensamblar el armazón de madera dura con refuerzos en las esquinas.",
                "actividades": [
                    {"nombre": "Cortar piezas del armazón", "descripcion": "Cortar la madera dura según el diseño del sofá."},
                    {"nombre": "Ensamblar y reforzar esquinas", "descripcion": "Unir el armazón con refuerzos en las esquinas para que no se hunda."},
                ],
            },
            {
                "nombre": "Cincha e hilado (suspensión)",
                "descripcion": "Tensar las cinchas elásticas o colocar los resortes en zigzag en la base del asiento y el espaldar con grapadora neumática.",
                "actividades": [
                    {"nombre": "Colocar cinchas o resortes", "descripcion": "Instalar cinchas elásticas o resortes en zigzag en asiento y espaldar."},
                    {"nombre": "Tensar y grapar la suspensión", "descripcion": "Tensar el sistema con grapadora neumática."},
                ],
            },
            {
                "nombre": "Acolchado",
                "descripcion": "Cortar las láminas de espuma (alta densidad para el asiento, más suave para el espaldar) y pegarlas al esqueleto.",
                "actividades": [
                    {"nombre": "Cortar espumas de asiento y espaldar", "descripcion": "Espuma de alta densidad para el asiento y más suave para el espaldar."},
                    {"nombre": "Pegar la espuma al esqueleto", "descripcion": "Fijar la espuma con bóxer o pegante en aerosol."},
                ],
            },
            {
                "nombre": "Patronaje y corte de tela",
                "descripcion": "Tomar medidas exactas del armazón armado y cortar los lienzos de tela (terciopelo, lino, microfibra, etc.).",
                "actividades": [
                    {"nombre": "Tomar medidas del armazón", "descripcion": "Medidas exactas sobre el armazón ya armado."},
                    {"nombre": "Cortar los lienzos de tela", "descripcion": "Cortar terciopelo, lino, microfibra u otra tela elegida."},
                ],
            },
            {
                "nombre": "Costura",
                "descripcion": "Unir las piezas en la máquina de coser industrial, añadiendo pestañas, vivos o cremalleras si los cojines son desmontables.",
                "actividades": [
                    {"nombre": "Coser las piezas de tapicería", "descripcion": "Unir los lienzos en la máquina de coser industrial."},
                    {"nombre": "Añadir pestañas, vivos o cremalleras", "descripcion": "Detalles según el diseño y cojines desmontables."},
                ],
            },
            {
                "nombre": "Tapizado y engrapado",
                "descripcion": "Estirar la tela con pinzas de tapicero fijándola por debajo del esqueleto, sin arrugas ni pliegues.",
                "actividades": [
                    {"nombre": "Estirar y fijar la tela", "descripcion": "Tensionar con pinzas de tapicero y engrapar por debajo del esqueleto."},
                ],
            },
            {
                "nombre": "Acabados",
                "descripcion": "Colocar el lienzo o tela quirúrgica en la parte inferior para tapar el armazón y fijar las patas.",
                "actividades": [
                    {"nombre": "Colocar lienzo inferior", "descripcion": "Tapar el armazón por debajo con lienzo o tela quirúrgica."},
                    {"nombre": "Fijar las patas", "descripcion": "Atornillar o encajar las patas del sofá."},
                ],
            },
        ],
    },
    {
        "claves": ("mesa", "mesita", "meson", "escritorio"),
        "nombre": "Fabricación de mesa",
        "tareas": [
            {
                "nombre": "Diseño y rectificado",
                "descripcion": "Definir medidas, estilo y tipo de madera (cedro, roble, pino, etc.).",
                "actividades": [
                    {"nombre": "Tomar medidas y definir estilo", "descripcion": "Acordar con el cliente medidas y estilo de la mesa."},
                    {"nombre": "Elegir el tipo de madera", "descripcion": "Cedro, roble, pino u otra madera según el pedido."},
                ],
            },
            {
                "nombre": "Corte y cepillado",
                "descripcion": "Cortar los listones para las patas, los faldones y la superficie superior (o el tablero).",
                "actividades": [
                    {"nombre": "Cortar patas y faldones", "descripcion": "Cortar los listones de las patas y los faldones."},
                    {"nombre": "Cortar la superficie superior", "descripcion": "Cortar el tablero o tapa de la mesa."},
                    {"nombre": "Cepillar todas las piezas", "descripcion": "Dejar cada pieza al medida y lista para el ensamble."},
                ],
            },
            {
                "nombre": "Ensamble de estructura",
                "descripcion": "Hacer espigas y escoplos (o tacos/tornillos ocultos) y unir la base con cola blanca y prensas de sargento.",
                "actividades": [
                    {"nombre": "Preparar las uniones", "descripcion": "Espigas y escoplos, tacos o tornillos ocultos según el diseño."},
                    {"nombre": "Encolar y prensar la base", "descripcion": "Unir con cola blanca para madera y prensas de sargento."},
                ],
            },
            {
                "nombre": "Lijado progresivo",
                "descripcion": "Pasar lija de grano grueso a grano fino para dejar la madera totalmente suave.",
                "actividades": [
                    {"nombre": "Lijar con grano grueso", "descripcion": "Primer lijado para igualar la superficie."},
                    {"nombre": "Lijar con grano fino", "descripcion": "Lijado final hasta dejar la madera suave."},
                ],
            },
            {
                "nombre": "Acabado y sellado",
                "descripcion": "Aplicar sellador, tinte (si se cambia el tono) y varias capas de laca o barniz (brillante, mate o satinado).",
                "actividades": [
                    {"nombre": "Aplicar sellador y tinte", "descripcion": "Sellar la madera y aplicar tinte si el cliente cambia el tono."},
                    {"nombre": "Aplicar laca o barniz", "descripcion": "Varias capas de acabado brillante, mate o satinado."},
                ],
            },
        ],
    },
    {
        "claves": ("silla", "sillita", "butaca", "poltrona", "taburete", "banqueta", "banco"),
        "nombre": "Fabricación y tapizado de sillas",
        "tareas": [
            {
                "nombre": "Ebanistería",
                "descripcion": "Ensamblar patas, travesaños y el respaldo de la silla.",
                "actividades": [
                    {"nombre": "Ensamblar patas y travesaños", "descripcion": "Armar la estructura base de la silla."},
                    {"nombre": "Montar el respaldo", "descripcion": "Fijar el respaldo al marco."},
                ],
            },
            {
                "nombre": "Tratamiento del asiento",
                "descripcion": "Si lleva base de madera aglomerada o triplex, cortar la forma a la medida del marco.",
                "actividades": [
                    {"nombre": "Cortar la base del asiento", "descripcion": "Aglomerado o triplex cortado a la medida del marco."},
                ],
            },
            {
                "nombre": "Espumado",
                "descripcion": "Pegar la espuma de alta densidad a la tabla y perfilar los bordes.",
                "actividades": [
                    {"nombre": "Pegar la espuma a la tabla", "descripcion": "Espuma de alta densidad fijada a la base."},
                    {"nombre": "Perfilar los bordes", "descripcion": "Recortar y dar forma a los bordes de la espuma."},
                ],
            },
            {
                "nombre": "Confección del vestido",
                "descripcion": "Cortar la tela o cuerina dejando sobrante para el dobladillo inferior.",
                "actividades": [
                    {"nombre": "Cortar tela o cuerina", "descripcion": "Cortar dejando sobrante para el dobladillo inferior."},
                ],
            },
            {
                "nombre": "Enfundado y tensionado",
                "descripcion": "Fijar la tela desde el centro hacia las esquinas con grapas neumáticas para mantener el patrón parejo.",
                "actividades": [
                    {"nombre": "Tensionar y engrapar la tela", "descripcion": "Fijar del centro hacia las esquinas con grapas neumáticas."},
                ],
            },
            {
                "nombre": "Montaje final",
                "descripcion": "Atornillar el asiento tapizado a la estructura y colocar deslizadores en las patas.",
                "actividades": [
                    {"nombre": "Atornillar asiento a la estructura", "descripcion": "Fijar el asiento tapizado al marco de la silla."},
                    {"nombre": "Colocar deslizadores en las patas", "descripcion": "Poner los deslizadores para proteger el piso."},
                ],
            },
        ],
    },
    {
        "claves": ("restaurar", "restauracion", "retapizar", "tapizar", "tapizado",
                   "reparar", "reparacion", "reforma", "reacondicionar", "renovar",
                   "remodelar", "usado", "usada", "viejo", "vieja", "antiguo", "antigua"),
        "nombre": "Tapicería general (restauración de muebles)",
        "tareas": [
            {
                "nombre": "Desguace (desarmado)",
                "descripcion": "Retirar la tela vieja, grapas oxidadas, cinchas vencidas y espuma desgastada sin dañar la estructura.",
                "actividades": [
                    {"nombre": "Retirar tela, grapas y espuma", "descripcion": "Desarmar sin dañar la estructura del mueble."},
                ],
            },
            {
                "nombre": "Revisión de carpintería",
                "descripcion": "Reajustar la estructura suelta, encolar uniones flojas y resanar la madera dañada.",
                "actividades": [
                    {"nombre": "Reajustar y encolar la estructura", "descripcion": "Apretar y encolar las uniones flojas."},
                    {"nombre": "Resanar la madera dañada", "descripcion": "Reparar golpes y madera picada."},
                ],
            },
            {
                "nombre": "Renovación del sistema de confort",
                "descripcion": "Reemplazar cinchas y colocar espumas totalmente nuevas.",
                "actividades": [
                    {"nombre": "Reemplazar cinchas", "descripcion": "Cambiar las cinchas vencidas por nuevas."},
                    {"nombre": "Colocar espuma nueva", "descripcion": "Renovar por completo el relleno."},
                ],
            },
            {
                "nombre": "Trazado y corte sobre tela nueva",
                "descripcion": "Usar las piezas viejas como molde (si la forma era buena) o patronear de cero.",
                "actividades": [
                    {"nombre": "Trazar patrones", "descripcion": "Usar las piezas viejas como molde o patronear de cero."},
                    {"nombre": "Cortar la tela nueva", "descripcion": "Cortar la tela elegida con los patrones."},
                ],
            },
            {
                "nombre": "Tapizado y detalles",
                "descripcion": "Volver a vestir el mueble, añadiendo capitoné (botones hundidos) o tachuelas decorativas si el diseño lo exige.",
                "actividades": [
                    {"nombre": "Tapizar el mueble", "descripcion": "Vestir el mueble con la tela nueva, bien tensionada."},
                    {"nombre": "Añadir detalles", "descripcion": "Capitoné, botones hundidos o tachuelas decorativas según el diseño."},
                ],
            },
        ],
    },
)

#: Proceso por defecto para productos que no coinciden con ningún proceso.
PLANTILLA_GENERAL = {
    "nombre": "Proceso general de tapicería",
    "tareas": [
        {
            "nombre": "Diseño y medidas",
            "descripcion": "Definir medidas, materiales y estilo con el cliente.",
            "actividades": [
                {"nombre": "Tomar medidas y confirmar diseño", "descripcion": "Acordar medidas, materiales y estilo."},
            ],
        },
        {
            "nombre": "Corte de materiales",
            "descripcion": "Cortar la estructura, el relleno y la tela según los patrones.",
            "actividades": [
                {"nombre": "Cortar estructura y relleno", "descripcion": "Preparar la base y la espuma."},
                {"nombre": "Cortar la tela", "descripcion": "Cortar la tela elegida con los patrones."},
            ],
        },
        {
            "nombre": "Confección y armado",
            "descripcion": "Ensamblar la estructura y preparar el confort (espuma y suspensión).",
            "actividades": [
                {"nombre": "Armar la estructura", "descripcion": "Ensamblar y reforzar la base."},
                {"nombre": "Colocar espuma y suspensión", "descripcion": "Instalar el relleno y el sistema de confort."},
            ],
        },
        {
            "nombre": "Tapizado",
            "descripcion": "Vestir la pieza con la tela elegida, bien tensionada y sin arrugas.",
            "actividades": [
                {"nombre": "Tapizar y tensionar la tela", "descripcion": "Fijar la tela sin arrugas ni pliegues."},
            ],
        },
        {
            "nombre": "Acabados y entrega",
            "descripcion": "Revisar detalles, limpiar la pieza y entregarla.",
            "actividades": [
                {"nombre": "Revisión final y limpieza", "descripcion": "Revisar acabados, limpiar y dejar lista la entrega."},
            ],
        },
    ],
}


def plantilla_para(nombre_producto):
    """Proceso típico del producto según su nombre (por palabras clave)."""
    texto = _normalizar(nombre_producto)
    for plantilla in PLANTILLAS:
        if any(clave in texto for clave in plantilla["claves"]):
            return plantilla
    return PLANTILLA_GENERAL


def _tramos(inicio, fin, cantidad):
    """Reparte el rango [inicio, fin] en ``cantidad`` tramos consecutivos."""
    if cantidad <= 0:
        return []
    if fin < inicio:
        fin = inicio
    dias = (fin - inicio).days
    return [
        (
            inicio + timedelta(days=(dias * i) // cantidad),
            inicio + timedelta(days=(dias * (i + 1)) // cantidad),
        )
        for i in range(cantidad)
    ]


def _ventana_del_pedido(pedido):
    """Fechas válidas para el trabajo: de la creación a la fecha límite."""
    inicio = pedido.fecha_creacion
    fin = pedido.fecha_limite or (inicio + timedelta(days=30))
    return inicio, fin


def crear_proceso_predefinido(pedido):
    """Carga las tareas y actividades típicas del producto en un pedido nuevo.

    Devuelve ``(tareas, actividades)`` creadas. No toca pedidos que ya tienen
    tareas: lo predefinido es la base y desde el CRUD se agregan las tareas o
    actividades extra que el cliente pida.
    """
    if pedido is None or not pedido.id_producto_id:
        return 0, 0
    if pedido.tareaspedido_set.filter(activo=True).exists():
        return 0, 0

    plantilla = plantilla_para(pedido.id_producto.nombre)
    inicio, fin = _ventana_del_pedido(pedido)
    total_tareas = 0
    total_actividades = 0

    for tarea_datos, (desde, hasta) in zip(plantilla["tareas"], _tramos(inicio, fin, len(plantilla["tareas"]))):
        tarea = TareasPedido.objects.create(
            nombre=tarea_datos["nombre"][:100],
            descripcion=tarea_datos["descripcion"],
            fecha_inicio=desde,
            fecha_fin=hasta,
            estado="pendiente",
            id_pedido=pedido,
            id_empleado=pedido.id_empleado,
        )
        total_tareas += 1
        actividades = tarea_datos["actividades"]
        for actividad_datos, (a_desde, a_hasta) in zip(actividades, _tramos(desde, hasta, len(actividades))):
            Actividades.objects.create(
                nombre=actividad_datos["nombre"][:50],
                descripcion=actividad_datos["descripcion"],
                fecha_inicio=a_desde,
                fecha_fin=a_hasta,
                estado="pendiente",
                id_tarea=tarea,
                id_empleado=pedido.id_empleado,
            )
            total_actividades += 1

    historial.registrar(
        pedido,
        "proceso_predefinido",
        f"Proceso «{plantilla['nombre']}» cargado automáticamente: "
        f"{total_tareas} tareas y {total_actividades} actividades. "
        "Las tareas o actividades extra se agregan desde el CRUD.",
    )
    return total_tareas, total_actividades
