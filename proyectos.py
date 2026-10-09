"""Creación, apertura y activación de proyectos portables de CamApp."""

import json
import os
from datetime import datetime

import estado
from utilidades import sanitizar_nombre_archivo


ARCHIVO_MANIFIESTO = "proyecto_camapp.json"
VERSION_PROYECTO = 1


def rutas_proyecto(carpeta):
    carpeta = os.path.abspath(carpeta)
    return {
        "raiz": carpeta,
        "manifiesto": os.path.join(carpeta, ARCHIVO_MANIFIESTO),
        "datos": os.path.join(carpeta, "datos"),
        "excel": os.path.join(carpeta, "datos", "alumnos_con_fotos.xlsx"),
        "fotos": os.path.join(carpeta, "fotos_alumnos"),
        "diseno": os.path.join(carpeta, "diseno"),
        "diseno_json": os.path.join(carpeta, "diseno", "diseno_credencial.json"),
        "fondos": os.path.join(carpeta, "diseno", "fondos"),
        "pdfs": os.path.join(carpeta, "pdfs"),
        "respaldos": os.path.join(carpeta, "respaldos_camapp"),
        "historial": os.path.join(carpeta, "historial_impresiones.csv"),
    }


def crear_proyecto(carpeta_padre, nombre):
    nombre_limpio = nombre.strip()
    if not nombre_limpio:
        raise ValueError("El nombre del proyecto no puede estar vacío.")

    nombre_carpeta = sanitizar_nombre_archivo(nombre_limpio) or "Proyecto_CamApp"
    carpeta = os.path.join(os.path.abspath(carpeta_padre), nombre_carpeta)
    if os.path.exists(carpeta) and os.listdir(carpeta):
        raise FileExistsError(
            f"La carpeta del proyecto ya existe y no está vacía:\n{carpeta}")

    rutas = rutas_proyecto(carpeta)
    for clave in ("raiz", "datos", "fotos", "diseno", "fondos", "pdfs", "respaldos"):
        os.makedirs(rutas[clave], exist_ok=True)

    manifiesto = {
        "version": VERSION_PROYECTO,
        "nombre": nombre_limpio,
        "creado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "excel": "datos/alumnos_con_fotos.xlsx",
        "diseno": "diseno/diseno_credencial.json",
    }
    with open(rutas["manifiesto"], "w", encoding="utf-8") as archivo:
        json.dump(manifiesto, archivo, ensure_ascii=False, indent=2)
    return carpeta


def leer_proyecto(carpeta):
    rutas = rutas_proyecto(carpeta)
    if not os.path.isfile(rutas["manifiesto"]):
        raise FileNotFoundError(
            "La carpeta seleccionada no contiene un proyecto de CamApp.")
    with open(rutas["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)
    if not manifiesto.get("nombre"):
        raise ValueError("El manifiesto del proyecto no contiene un nombre válido.")
    return manifiesto, rutas


def activar_proyecto(carpeta):
    manifiesto, rutas = leer_proyecto(carpeta)
    estado.ruta_proyecto = rutas["raiz"]
    estado.nombre_proyecto = manifiesto["nombre"]
    estado.ruta_excel_trabajo = rutas["excel"]
    estado.FOTOS_DIR = rutas["fotos"]
    estado.RUTA_DISENO_JSON = rutas["diseno_json"]
    for clave in ("datos", "fotos", "diseno", "fondos", "pdfs", "respaldos"):
        os.makedirs(rutas[clave], exist_ok=True)
    return rutas
