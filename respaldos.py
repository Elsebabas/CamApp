"""Copias de seguridad automáticas de los archivos de trabajo de CamApp."""

import os
import shutil
from datetime import datetime

import estado


MAX_RESPALDOS_POR_ARCHIVO = 20


def crear_respaldo(ruta_archivo, categoria, max_respaldos=MAX_RESPALDOS_POR_ARCHIVO):
    """Copia la versión existente antes de sobrescribirla y conserva solamente
    los respaldos más recientes de ese archivo. Devuelve la ruta creada o None."""
    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        return None

    ruta_absoluta = os.path.abspath(ruta_archivo)
    carpeta_base = os.path.dirname(ruta_absoluta)
    carpeta_respaldos = (
        os.path.join(estado.ruta_proyecto, "respaldos_camapp", categoria)
        if estado.ruta_proyecto
        else os.path.join(carpeta_base, "respaldos_camapp", categoria)
    )
    os.makedirs(carpeta_respaldos, exist_ok=True)

    nombre, extension = os.path.splitext(os.path.basename(ruta_absoluta))
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ruta_respaldo = os.path.join(
        carpeta_respaldos, f"{nombre}_{marca_tiempo}{extension}")
    shutil.copy2(ruta_absoluta, ruta_respaldo)

    prefijo = f"{nombre}_"
    respaldos = sorted(
        (
            os.path.join(carpeta_respaldos, archivo)
            for archivo in os.listdir(carpeta_respaldos)
            if archivo.startswith(prefijo) and archivo.endswith(extension)
        ),
        key=os.path.getmtime,
        reverse=True,
    )
    for respaldo_antiguo in respaldos[max_respaldos:]:
        try:
            os.remove(respaldo_antiguo)
        except OSError:
            pass

    return ruta_respaldo
