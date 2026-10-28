"""Historial portable de impresiones y reposiciones por alumno."""

import csv
import os
import tempfile
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb

import estado

CAMPOS = (
    "Fecha", "Indice", "Matricula", "NombreCompleto", "Grupo",
    "Tipo", "RutaPDF", "Reposicion",
)


def eliminar_registros_alumno(matricula):
    """Quita del historial las impresiones asociadas a una matrícula."""
    ruta = ruta_historial()
    if not ruta or not os.path.isfile(ruta):
        return 0
    with open(ruta, newline="", encoding="utf-8-sig") as archivo:
        filas = list(csv.DictReader(archivo))
    restantes = [
        fila for fila in filas
        if str(fila.get("Matricula", "")) != str(matricula)
    ]
    eliminados = len(filas) - len(restantes)
    if not eliminados:
        return 0
    carpeta = os.path.dirname(ruta)
    fd, temporal = tempfile.mkstemp(
        prefix="historial_", suffix=".csv", dir=carpeta)
    os.close(fd)
    try:
        with open(temporal, "w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
            escritor.writeheader()
            escritor.writerows(restantes)
        os.replace(temporal, ruta)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)
    return eliminados


def ruta_historial():
    """Devuelve el CSV dentro del proyecto (o junto al Excel activo)."""
    base = estado.ruta_proyecto
    if not base and estado.ruta_excel_trabajo:
        base = os.path.dirname(os.path.abspath(estado.ruta_excel_trabajo))
    if not base:
        return None
    return os.path.join(base, "historial_impresiones.csv")


def registrar_impresion(fila, indice, tipo, ruta_pdf, reposicion=False):
    ruta = ruta_historial()
    if not ruta:
        return
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        if nuevo:
            escritor.writeheader()
        escritor.writerow({
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Indice": indice,
            "Matricula": str(fila.get("Matricula", "")),
            "NombreCompleto": str(fila.get("NombreCompleto", "")),
            "Grupo": str(fila.get("Grupo", "")),
            "Tipo": tipo,
            "RutaPDF": ruta_pdf or "",
            "Reposicion": "Sí" if reposicion else "No",
        })


def obtener_historial(indice=None, matricula=None):
    ruta = ruta_historial()
    if not ruta or not os.path.isfile(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8-sig") as archivo:
        filas = list(csv.DictReader(archivo))
    if indice is not None:
        filas = [fila for fila in filas if str(fila.get("Indice", "")) == str(indice)]
    if matricula is not None:
        filas = [fila for fila in filas if fila.get("Matricula", "") == str(matricula)]
    return filas


def mostrar_historial_alumno():
    if estado.df_alumnos is None or estado.alumno_actual_idx is None:
        messagebox.showwarning("Sin alumno", "Selecciona un alumno primero.")
        return
    fila = estado.df_alumnos.loc[estado.alumno_actual_idx]
    historial = obtener_historial(
        indice=estado.alumno_actual_idx, matricula=fila.get("Matricula", ""))
    ventana = tk.Toplevel(estado.root)
    ventana.title("Historial de impresiones")
    ventana.geometry("820x390")
    ventana.transient(estado.root)
    tb.Label(
        ventana,
        text=f"{fila.get('NombreCompleto', '')} · {fila.get('Matricula', '')}",
        font=("Segoe UI", 12, "bold"), bootstyle="primary",
    ).pack(anchor="w", padx=16, pady=(14, 8))
    columnas = ("fecha", "tipo", "reposicion", "archivo")
    tabla = tb.Treeview(ventana, columns=columnas, show="headings", bootstyle="primary")
    for columna, texto, ancho in (
        ("fecha", "Fecha", 155), ("tipo", "Tipo", 150),
        ("reposicion", "Reposición", 90), ("archivo", "Archivo PDF", 390),
    ):
        tabla.heading(columna, text=texto)
        tabla.column(columna, width=ancho, anchor="w")
    tabla.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    for registro in reversed(historial):
        tabla.insert("", "end", values=(
            registro.get("Fecha", ""), registro.get("Tipo", ""),
            registro.get("Reposicion", "No"), registro.get("RutaPDF", ""),
        ))
    if not historial:
        tb.Label(ventana, text="Este alumno aún no tiene impresiones registradas.",
                 bootstyle="secondary").pack(pady=(0, 10))
    tb.Button(ventana, text="Cerrar", command=ventana.destroy,
              bootstyle="secondary").pack(pady=(0, 14))

