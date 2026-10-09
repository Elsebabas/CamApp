"""
Funciones auxiliares sin estado propio: sanitizar nombres de archivo,
calcular nitidez de una imagen (detección de foto borrosa), y activar
DPI awareness en Windows. No dependen de ningún otro módulo del programa.
"""

import re
import unicodedata
import ctypes
import cv2
import numpy as np
import os
import sys
import shutil
import estado


def ruta_recurso(nombre):
    """Resuelve recursos tanto en código fuente como dentro de PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


def inicializar_archivos_aplicacion():
    """Prepara archivos editables en una carpeta escribible del usuario."""
    os.makedirs(estado.DIRECTORIO_APLICACION, exist_ok=True)
    plantilla = ruta_recurso("diseno_credencial.json")
    if (not os.path.exists(estado.RUTA_DISENO_JSON)
            and os.path.isfile(plantilla)):
        shutil.copy2(plantilla, estado.RUTA_DISENO_JSON)


def resumen_fotografias(df):
    """Devuelve total, fotografías realizadas, pendientes y porcentaje."""
    if df is None or len(df) == 0:
        return 0, 0, 0, 0
    total = len(df)
    con_foto = int((df["FotoTomada"] == "Sí").sum())
    pendientes = total - con_foto
    porcentaje = round((con_foto / total) * 100)
    return total, con_foto, pendientes, porcentaje


def actualizar_indicadores():
    """Refresca el avance general sin depender de que la ventana ya exista."""
    total, con_foto, pendientes, porcentaje = resumen_fotografias(
        estado.df_alumnos)
    if estado.etiqueta_progreso is not None:
        estado.etiqueta_progreso.configure(
            text=(
                f"Fotografías: {con_foto}/{total} · {pendientes} pendientes"
                if total else "Sin alumnos cargados"
            ),
            bootstyle="success" if total and not pendientes else "secondary",
        )
    if estado.barra_progreso is not None:
        estado.barra_progreso.configure(value=porcentaje)


def notificar(mensaje, tipo="info", duracion=4500):
    """Muestra un estado breve y no intrusivo en la ventana principal."""
    if estado.etiqueta_estado is None or estado.root is None:
        return
    estilos = {
        "info": ("ℹ", "secondary"),
        "success": ("✓", "success"),
        "warning": ("⚠", "warning"),
        "danger": ("✕", "danger"),
    }
    icono, estilo = estilos.get(tipo, estilos["info"])
    estado.etiqueta_estado.configure(
        text=f"{icono}  {mensaje}", bootstyle=estilo)
    if estado.id_notificacion_pendiente is not None:
        try:
            estado.root.after_cancel(estado.id_notificacion_pendiente)
        except Exception:
            pass
    estado.id_notificacion_pendiente = estado.root.after(
        duracion, lambda: estado.etiqueta_estado.configure(
            text="Listo", bootstyle="secondary"))


def sanitizar_nombre_archivo(texto):
    """Convierte un texto en un nombre de archivo seguro (sin acentos, espacios ni símbolos)."""
    texto = str(texto).strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'[^A-Za-z0-9]+', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    return texto


def obtener_valor_campo(fila, nombre_campo):
    """Obtiene un valor imprimible y reconstruye campos calculados cuando un
    archivo de trabajo antiguo todavía no los contiene."""

    def texto_limpio(valor):
        if valor is None:
            return ""
        try:
            if valor != valor:  # NaN de pandas/numpy
                return ""
        except Exception:
            pass
        return str(valor).strip()

    valor = texto_limpio(fila.get(nombre_campo, ""))
    if nombre_campo == "Apellidos" and not valor:
        valor = " ".join(filter(None, (
            texto_limpio(fila.get("Apellido Paterno", "")),
            texto_limpio(fila.get("Apellido Materno", "")),
        )))
    return valor


def resolver_ruta_archivo(ruta):
    """Convierte una ruta portable del proyecto en una ruta utilizable."""
    if not ruta:
        return ""
    ruta = str(ruta)
    if os.path.isabs(ruta) or not estado.ruta_proyecto:
        return os.path.normpath(ruta)
    return os.path.normpath(os.path.join(estado.ruta_proyecto, ruta))


def hacer_ruta_portable(ruta):
    """Guarda como relativa cualquier ruta contenida dentro del proyecto."""
    if not ruta:
        return ""
    ruta_absoluta = os.path.abspath(ruta)
    if not estado.ruta_proyecto:
        return ruta_absoluta.replace("\\", "/")
    try:
        ruta_relativa = os.path.relpath(ruta_absoluta, estado.ruta_proyecto)
    except ValueError:
        return ruta_absoluta.replace("\\", "/")
    if ruta_relativa == ".." or ruta_relativa.startswith(".." + os.sep):
        return ruta_absoluta.replace("\\", "/")
    return ruta_relativa.replace("\\", "/")


def calcular_nitidez(imagen_pil):
    """Calcula la varianza del Laplaciano de la imagen: entre más bajo el valor,
    más borrosa se considera la foto. Se usa como aviso antes de guardar."""
    imagen_gris = cv2.cvtColor(np.array(imagen_pil), cv2.COLOR_RGB2GRAY)
    return cv2.Laplacian(imagen_gris, cv2.CV_64F).var()


def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"Error setting DPI awareness: {e}")
