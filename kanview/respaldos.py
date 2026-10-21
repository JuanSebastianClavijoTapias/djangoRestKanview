"""Copias de seguridad y restauración de la base SQLite."""

import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connections

PREFIJO = "kanview-"
EXTENSION = ".sqlite3"


def _directorio():
    directorio = Path(settings.BACKUP_DIR)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def _es_sqlite():
    return connections["default"].settings_dict.get("ENGINE", "").endswith("sqlite3")


def _ruta_segura(nombre):
    directorio = _directorio().resolve()
    ruta = (directorio / Path(nombre).name).resolve()
    if ruta.parent != directorio or not ruta.name.endswith(EXTENSION):
        raise ValueError("Nombre de copia de seguridad no válido.")
    return ruta


def listar_respaldos():
    """Lista de copias disponibles, de la más reciente a la más antigua."""
    if not _directorio().exists():
        return []
    rutas = sorted(_directorio().glob(f"{PREFIJO}*{EXTENSION}"), reverse=True)
    return [
        {
            "nombre": ruta.name,
            "ruta": str(ruta),
            "tamano": ruta.stat().st_size,
            "fecha": datetime.fromtimestamp(ruta.stat().st_mtime),
        }
        for ruta in rutas
    ]


def _aplicar_retencion():
    retencion = max(1, int(getattr(settings, "BACKUP_RETENCION", 10)))
    for respaldo in listar_respaldos()[retencion:]:
        try:
            Path(respaldo["ruta"]).unlink()
        except OSError:
            pass


def crear_respaldo():
    """Copia consistente de la BD usando la API de backup de SQLite."""
    if not _es_sqlite():
        raise ValueError("Las copias de seguridad solo están disponibles para SQLite.")
    conexion_origen = connections["default"].connection
    if conexion_origen is None:
        connections["default"].ensure_connection()
        conexion_origen = connections["default"].connection
    destino = _directorio() / f"{PREFIJO}{datetime.now():%Y%m%d-%H%M%S}{EXTENSION}"
    temporal = destino.with_suffix(".tmp")
    nombre = str(connections["default"].settings_dict.get("NAME", ""))
    if nombre == ":memory:" or nombre.startswith("file:"):
        # En pruebas la BD vive en memoria y backup() puede bloquearse con la
        # transacción abierta; serialize() entrega una copia consistente.
        if hasattr(conexion_origen, "serialize"):
            temporal.write_bytes(conexion_origen.serialize())
        else:  # Python 3.10: volcado SQL de la base en memoria.
            with sqlite3.connect(temporal) as conexion_destino:
                for sentencia in conexion_origen.iterdump():
                    conexion_destino.execute(sentencia)
    else:
        with sqlite3.connect(temporal) as conexion_destino:
            conexion_origen.backup(conexion_destino)
    temporal.replace(destino)
    try:
        destino.chmod(0o600)
    except OSError:
        pass
    _aplicar_retencion()
    return destino


def restaurar_respaldo(nombre):
    """Restaura una copia existente y devuelve el respaldo de seguridad previo."""
    if not _es_sqlite():
        raise ValueError("La restauración solo está disponible para SQLite.")
    origen = _ruta_segura(nombre)
    if not origen.exists():
        raise FileNotFoundError("La copia de seguridad no existe.")

    with sqlite3.connect(origen) as conexion:
        if conexion.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("La copia de seguridad está dañada.")

    seguridad = crear_respaldo()
    conexion_destino = connections["default"].connection
    if conexion_destino is None:
        connections["default"].ensure_connection()
        conexion_destino = connections["default"].connection
    with sqlite3.connect(origen) as conexion_origen:
        conexion_origen.backup(conexion_destino)
    connections.close_all()
    return seguridad
