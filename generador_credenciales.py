"""
Generador de credenciales en PDF: lee el diseño guardado por el Diseñador de
Credencial (frente + reverso) y los datos del Excel de alumnos, y renderiza
cada credencial en alta resolución (300 DPI) como un PDF de 2 páginas
(página 1 = frente, página 2 = reverso), guardado en una subcarpeta por
grupo — listo para mandar a imprimir.

Solo genera credencial para alumnos que ya tienen foto tomada (FotoTomada
== "Sí"); los demás se cuentan como omitidos y se informa al final.
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from PIL import Image, ImageDraw, ImageFont, ImageOps

import estado
from utilidades import (
    sanitizar_nombre_archivo, obtener_valor_campo, resolver_ruta_archivo,
)
from validacion_credenciales import validar_pre_generacion

RESOLUCION_IMPRESION_DPI = 300


def nombre_pdf_alumno(fila):
    """Construye un nombre identificable para un PDF de un solo alumno."""
    matricula = sanitizar_nombre_archivo(str(fila.get("Matricula", "")).strip())
    nombre = sanitizar_nombre_archivo(
        str(fila.get("NombreCompleto", "")).strip())
    partes = [parte for parte in (matricula, nombre) if parte]
    return "_".join(partes) or "Credencial_sin_identificar"
TAMANOS_PAPEL_CM = {
    "Carta": (21.59, 27.94),
    "A4": (21.0, 29.7),
}

# Mapeo de nombre de fuente (elegido en el diseñador) -> archivos .ttf típicos de Windows
FUENTES_DISPONIBLES = {
    "Arial": ("arial.ttf", "arialbd.ttf"),
    "Gill Sans MT": ("GIL.TTF", "GILB.TTF"),
    "Calibri": ("calibri.ttf", "calibrib.ttf"),
    "Times New Roman": ("times.ttf", "timesbd.ttf"),
    "Georgia": ("georgia.ttf", "georgiab.ttf"),
    "Verdana": ("verdana.ttf", "verdanab.ttf"),
    "Segoe UI": ("segoeui.ttf", "segoeuib.ttf"),
    "Tahoma": ("tahoma.ttf", "tahomabd.ttf"),
    "Century Gothic": ("GOTHIC.TTF", "GOTHICB.TTF"),
    "Trebuchet MS": ("trebuc.ttf", "trebucbd.ttf"),
}


def cm_a_px(cm, dpi=RESOLUCION_IMPRESION_DPI):
    return int(round(cm / 2.54 * dpi))


def calcular_distribucion_hoja(
        papel="Carta", orientacion="Vertical", ancho_credencial_cm=8.5,
        alto_credencial_cm=5.5, margen_cm=1.0, separacion_cm=0.3):
    """Calcula una cuadrícula válida y devuelve sus medidas en centímetros."""
    ancho_papel, alto_papel = TAMANOS_PAPEL_CM[papel]
    if orientacion == "Horizontal":
        ancho_papel, alto_papel = alto_papel, ancho_papel
    ancho_util = ancho_papel - (2 * margen_cm)
    alto_util = alto_papel - (2 * margen_cm)
    columnas = int((ancho_util + separacion_cm) //
                   (ancho_credencial_cm + separacion_cm))
    filas = int((alto_util + separacion_cm) //
                (alto_credencial_cm + separacion_cm))
    return {
        "ancho_papel_cm": ancho_papel,
        "alto_papel_cm": alto_papel,
        "columnas": max(0, columnas),
        "filas": max(0, filas),
        "por_hoja": max(0, columnas) * max(0, filas),
        "margen_cm": margen_cm,
        "separacion_cm": separacion_cm,
    }


def crear_hoja_impresion(imagenes, distribucion, marcas_corte=False,
                         reflejar_columnas=False, dpi=RESOLUCION_IMPRESION_DPI):
    """Coloca credenciales ya renderizadas en una hoja blanca."""
    ancho_pagina = cm_a_px(distribucion["ancho_papel_cm"], dpi)
    alto_pagina = cm_a_px(distribucion["alto_papel_cm"], dpi)
    hoja = Image.new("RGB", (ancho_pagina, alto_pagina), "white")
    dibujo = ImageDraw.Draw(hoja)
    margen = cm_a_px(distribucion["margen_cm"], dpi)
    separacion = cm_a_px(distribucion["separacion_cm"], dpi)
    columnas = distribucion["columnas"]
    ancho_credencial, alto_credencial = imagenes[0].size if imagenes else (0, 0)
    largo_marca = cm_a_px(0.25, dpi)

    for posicion, imagen in enumerate(imagenes):
        fila = posicion // columnas
        columna = posicion % columnas
        if reflejar_columnas:
            columna = columnas - 1 - columna
        x = margen + columna * (ancho_credencial + separacion)
        y = margen + fila * (alto_credencial + separacion)
        hoja.paste(imagen, (x, y))
        if marcas_corte:
            color = "#555555"
            dibujo.line((x - largo_marca, y, x, y), fill=color, width=1)
            dibujo.line((x, y - largo_marca, x, y), fill=color, width=1)
            dibujo.line(
                (x + ancho_credencial, y - largo_marca,
                 x + ancho_credencial, y), fill=color, width=1)
            dibujo.line(
                (x + ancho_credencial, y,
                 x + ancho_credencial + largo_marca, y), fill=color, width=1)
            dibujo.line(
                (x - largo_marca, y + alto_credencial,
                 x, y + alto_credencial), fill=color, width=1)
            dibujo.line(
                (x, y + alto_credencial,
                 x, y + alto_credencial + largo_marca), fill=color, width=1)
            dibujo.line(
                (x + ancho_credencial, y + alto_credencial,
                 x + ancho_credencial + largo_marca,
                 y + alto_credencial), fill=color, width=1)
            dibujo.line(
                (x + ancho_credencial, y + alto_credencial,
                 x + ancho_credencial,
                 y + alto_credencial + largo_marca), fill=color, width=1)
    return hoja


def _obtener_fuente(nombre_fuente, negrita, tamano_px):
    """Busca la fuente elegida en el diseñador (Windows primero, ya que es el
    entorno de destino de la app). Si no la encuentra, intenta con Arial: y si
    tampoco, usa un respaldo multiplataforma o la fuente embebida de PIL."""
    directorio_fuentes_windows = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")

    archivos = FUENTES_DISPONIBLES.get(nombre_fuente, FUENTES_DISPONIBLES["Arial"])
    nombre_archivo = archivos[1] if negrita else archivos[0]
    ruta = os.path.join(directorio_fuentes_windows, nombre_archivo)
    if os.path.exists(ruta):
        try:
            return ImageFont.truetype(ruta, tamano_px)
        except Exception:
            pass

    if nombre_fuente != "Arial":
        archivos_arial = FUENTES_DISPONIBLES["Arial"]
        nombre_arial = archivos_arial[1] if negrita else archivos_arial[0]
        ruta_arial = os.path.join(directorio_fuentes_windows, nombre_arial)
        if os.path.exists(ruta_arial):
            try:
                return ImageFont.truetype(ruta_arial, tamano_px)
            except Exception:
                pass

    # Respaldo multiplataforma (por si el programa corre en otro sistema operativo)
    rutas_respaldo = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrita
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if negrita
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for ruta in rutas_respaldo:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tamano_px)
            except Exception:
                continue

    for nombre in [nombre_archivo, "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]:
        try:
            return ImageFont.truetype(nombre, tamano_px)
        except Exception:
            continue

    try:
        return ImageFont.load_default(size=tamano_px)
    except TypeError:
        # Pillow < 10.1 no acepta 'size' en load_default
        return ImageFont.load_default()


def _ajustar_fuente_al_campo(dibujo, texto, nombre_fuente, negrita,
                             tamano_px_inicial, ancho_disponible, alto_disponible):
    """Reduce la fuente solo cuando el texto real no cabe en su campo."""
    tamano_px = max(6, tamano_px_inicial)
    ancho_limite = max(1, ancho_disponible - 8)
    alto_limite = max(1, alto_disponible - 4)

    while tamano_px > 6:
        fuente = _obtener_fuente(nombre_fuente, negrita, tamano_px)
        bbox = dibujo.textbbox((0, 0), texto, font=fuente)
        if bbox[2] - bbox[0] <= ancho_limite and bbox[3] - bbox[1] <= alto_limite:
            return fuente
        tamano_px -= 1
    return _obtener_fuente(nombre_fuente, negrita, 6)


def renderizar_lado(datos_lado, fila_alumno, ancho_px, alto_px):
    """Renderiza un lado (frente o reverso) de la credencial para un alumno
    y devuelve una imagen PIL en alta resolución."""
    fondo_path = resolver_ruta_archivo(datos_lado.get("fondo_path"))
    if fondo_path and os.path.exists(fondo_path):
        imagen = Image.open(fondo_path).convert("RGB").resize((ancho_px, alto_px))
    else:
        imagen = Image.new("RGB", (ancho_px, alto_px), "white")

    dibujo = ImageDraw.Draw(imagen)

    for nombre_campo, datos_campo in datos_lado.get("campos", {}).items():
        x = int(datos_campo["x_frac"] * ancho_px)
        y = int(datos_campo["y_frac"] * alto_px)
        w = int(datos_campo.get("ancho_frac", 0.3) * ancho_px)
        h = int(datos_campo.get("alto_frac", 0.08) * alto_px)

        if nombre_campo == "FOTO":
            ruta_foto = resolver_ruta_archivo(fila_alumno.get("RutaFoto", ""))
            if ruta_foto and os.path.exists(ruta_foto):
                foto = Image.open(ruta_foto).convert("RGB")
                foto = ImageOps.fit(foto, (max(w, 1), max(h, 1)), Image.LANCZOS)
                imagen.paste(foto, (x, y))
            else:
                dibujo.rectangle([x, y, x + w, y + h], outline="gray", width=2)
        else:
            valor = obtener_valor_campo(fila_alumno, nombre_campo)
            tamano_pt = datos_campo.get("tamano_pt", 10)
            tamano_px_final = max(6, int(tamano_pt * RESOLUCION_IMPRESION_DPI / 72))
            nombre_fuente = datos_campo.get("fuente", "Arial")
            negrita = datos_campo.get("negrita", False)
            fuente = _ajustar_fuente_al_campo(
                dibujo, valor, nombre_fuente, negrita, tamano_px_final, w, h)
            color = datos_campo.get("color", "#000000")
            alineacion = datos_campo.get("alineacion", "izquierda")

            if alineacion == "centro":
                pos_x, anchor_pil = x + w / 2, "mm"
            elif alineacion == "derecha":
                pos_x, anchor_pil = x + w - 4, "rm"
            else:
                pos_x, anchor_pil = x + 4, "lm"

            dibujo.text((pos_x, y + h / 2), valor, font=fuente, fill=color, anchor=anchor_pil)

    return imagen


def generar_hojas_impresion(
        df, datos_frente, datos_reverso, ancho_px, alto_px,
        carpeta_salida, opciones):
    """Genera un PDF multipágina con credenciales distribuidas en hojas."""
    nombre_grupo = sanitizar_nombre_archivo(
        opciones.get("grupo", "Todos")) or "Todos"

    if opciones["lados"] == "Solo detrás":
        datos_comunes = dict(datos_reverso)
        datos_comunes["campos"] = {}
        reverso = renderizar_lado(
            datos_comunes, {}, ancho_px, alto_px)
        ruta_pdf = os.path.join(
            carpeta_salida, f"Reverso_Comun_{nombre_grupo}.pdf")
        reverso.save(
            ruta_pdf, "PDF", resolution=RESOLUCION_IMPRESION_DPI)
        return 1, [], ruta_pdf

    registros = []
    errores = []
    for idx, fila in df.iterrows():
        if fila.get("FotoTomada") != "Sí":
            continue
        try:
            frente = renderizar_lado(
                datos_frente, fila, ancho_px, alto_px)
            registros.append((fila, frente))
        except Exception as error:
            errores.append(f"{fila.get('NombreCompleto', idx)}: {error}")

    if not registros:
        return 0, errores, None

    if len(registros) == 1:
        ruta_pdf = os.path.join(
            carpeta_salida, f"{nombre_pdf_alumno(registros[0][0])}.pdf")
    else:
        ruta_pdf = os.path.join(
            carpeta_salida, f"Frentes_{nombre_grupo}.pdf")

    # En Solo frente cada página conserva exactamente el tamaño físico de la
    # credencial. No se aplica papel, margen, separación ni marcas de corte.
    if opciones["lados"] == "Solo frente":
        paginas = [frente for _, frente in registros]
        paginas[0].save(
            ruta_pdf, "PDF", resolution=RESOLUCION_IMPRESION_DPI,
            save_all=True, append_images=paginas[1:])
        return len(registros), errores, ruta_pdf

    distribucion = calcular_distribucion_hoja(
        papel=opciones["papel"],
        orientacion=opciones["orientacion_papel"],
        ancho_credencial_cm=ancho_px / RESOLUCION_IMPRESION_DPI * 2.54,
        alto_credencial_cm=alto_px / RESOLUCION_IMPRESION_DPI * 2.54,
        margen_cm=opciones["margen_cm"],
        separacion_cm=opciones["separacion_cm"],
    )
    if distribucion["por_hoja"] < 1:
        raise ValueError(
            "La credencial no cabe con los márgenes y separación elegidos.")

    paginas = []
    por_hoja = distribucion["por_hoja"]
    incluir_reverso = opciones["lados"] == "Frente y reverso"
    reverso_comun = None
    if incluir_reverso and opciones["reverso_comun"]:
        datos_comunes = dict(datos_reverso)
        datos_comunes["campos"] = {}
        reverso_comun = renderizar_lado(
            datos_comunes, {}, ancho_px, alto_px)

    for inicio in range(0, len(registros), por_hoja):
        lote = registros[inicio:inicio + por_hoja]
        frentes = [frente for _, frente in lote]
        paginas.append(crear_hoja_impresion(
            frentes, distribucion, opciones["marcas_corte"]))
        if incluir_reverso:
            reversos = [
                reverso_comun.copy() if reverso_comun is not None
                else renderizar_lado(
                    datos_reverso, fila, ancho_px, alto_px)
                for fila, _ in lote
            ]
            # El espejo horizontal alinea ambas caras al imprimir por borde largo.
            paginas.append(crear_hoja_impresion(
                reversos, distribucion, opciones["marcas_corte"],
                reflejar_columnas=True))

    paginas[0].save(
        ruta_pdf, "PDF", resolution=RESOLUCION_IMPRESION_DPI,
        save_all=True, append_images=paginas[1:])
    return len(registros), errores, ruta_pdf


def generar_credenciales(carpeta_salida=None, solo_grupo="Todos",
                         indices_permitidos=None, diseno_precargado=None,
                         opciones_impresion=None):
    """Genera un PDF (frente+reverso) por cada alumno con foto ya tomada."""
    if estado.df_alumnos is None:
        messagebox.showwarning("Sin datos", "Primero carga el Excel de alumnos.")
        return

    if not os.path.exists(estado.RUTA_DISENO_JSON):
        messagebox.showwarning(
            "Sin diseño",
            "Primero diseña y guarda la credencial en '🪪 Diseñador de Credencial'."
        )
        return

    if diseno_precargado is None:
        try:
            with open(estado.RUTA_DISENO_JSON, "r", encoding="utf-8") as f:
                diseno = json.load(f)
        except Exception as e:
            messagebox.showerror("Error al leer el diseño", str(e))
            return
    else:
        diseno = diseno_precargado

    orientacion = diseno.get("orientacion", "horizontal")
    lados = diseno.get("lados", {})
    datos_frente = lados.get("frente", {})
    datos_reverso = lados.get("reverso", {})

    if orientacion == "horizontal":
        ancho_cm, alto_cm = estado.ANCHO_CREDENCIAL_CM, estado.ALTO_CREDENCIAL_CM
    else:
        ancho_cm, alto_cm = estado.ALTO_CREDENCIAL_CM, estado.ANCHO_CREDENCIAL_CM

    ancho_px = cm_a_px(ancho_cm)
    alto_px = cm_a_px(alto_cm)

    if carpeta_salida is None:
        carpeta_salida = (
            os.path.join(estado.ruta_proyecto, "pdfs")
            if estado.ruta_proyecto
            else filedialog.askdirectory(
                title="Selecciona la carpeta donde guardar las credenciales")
        )
        if not carpeta_salida:
            return
    os.makedirs(carpeta_salida, exist_ok=True)

    df = estado.df_alumnos
    if solo_grupo and solo_grupo != "Todos":
        df = df[df["Grupo"] == solo_grupo]
    if indices_permitidos is not None:
        df = df[df.index.isin(indices_permitidos)]

    generadas = 0
    saltadas = 0
    errores = []

    if opciones_impresion is not None:
        opciones_impresion = dict(opciones_impresion)
        opciones_impresion["grupo"] = solo_grupo
        try:
            generadas, errores, ruta_pdf = generar_hojas_impresion(
                df, datos_frente, datos_reverso, ancho_px, alto_px,
                carpeta_salida, opciones_impresion)
        except Exception as error:
            messagebox.showerror(
                "No se pudieron generar las hojas", str(error))
            return
        saltadas = int((df["FotoTomada"] != "Sí").sum())
        mensaje = (
            f"Credenciales incluidas: {generadas}\n"
            f"Alumnos sin foto (omitidos): {saltadas}\n"
            f"Archivo: {ruta_pdf or 'No generado'}"
        )
        if errores:
            mensaje += "\n\nErrores en:\n" + "\n".join(errores[:5])
        messagebox.showinfo("Hojas de impresión generadas", mensaje)
        return

    for idx, fila in df.iterrows():
        if fila.get("FotoTomada") != "Sí":
            saltadas += 1
            continue

        try:
            imagen_frente = renderizar_lado(datos_frente, fila, ancho_px, alto_px)
            imagen_reverso = renderizar_lado(datos_reverso, fila, ancho_px, alto_px)

            carpeta_grupo = os.path.join(carpeta_salida, sanitizar_nombre_archivo(fila["Grupo"]))
            os.makedirs(carpeta_grupo, exist_ok=True)

            nombre_archivo = nombre_pdf_alumno(fila) + ".pdf"
            ruta_pdf = os.path.join(carpeta_grupo, nombre_archivo)

            imagen_frente.save(
                ruta_pdf, "PDF", resolution=RESOLUCION_IMPRESION_DPI,
                save_all=True, append_images=[imagen_reverso]
            )
            generadas += 1
        except Exception as e:
            errores.append(f"{fila.get('NombreCompleto', idx)}: {e}")

    mensaje = (
        f"Credenciales generadas: {generadas}\n"
        f"Alumnos sin foto (omitidos): {saltadas}\n"
        f"Carpeta: {carpeta_salida}"
    )
    if errores:
        mensaje += "\n\nErrores en:\n" + "\n".join(errores[:5])
        if len(errores) > 5:
            mensaje += f"\n... y {len(errores) - 5} más."

    messagebox.showinfo("Generación completa", mensaje)


def imprimir_alumno_seleccionado():
    """Abre el generador limitado al alumno seleccionado en la tabla."""
    if estado.df_alumnos is None or estado.alumno_actual_idx is None:
        messagebox.showwarning(
            "Sin alumno seleccionado",
            "Selecciona un alumno antes de imprimir su credencial.",
        )
        return
    abrir_generador_credenciales([estado.alumno_actual_idx])


def abrir_generador_credenciales(indices_iniciales=None):
    """Permite exportar frentes, credenciales individuales o reverso común."""
    if estado.df_alumnos is None:
        messagebox.showwarning("Sin datos", "Primero carga el Excel de alumnos.")
        return

    ventana = tk.Toplevel(estado.root)
    ventana.title("Generar Credenciales")
    ventana.resizable(False, False)

    tb.Label(ventana, text="Generar credenciales en PDF",
             font=("Segoe UI", 12, "bold")).pack(padx=20, pady=(20, 5))
    indices_iniciales = list(indices_iniciales or [])
    es_impresion_individual = len(indices_iniciales) == 1
    alumno_individual = None
    if es_impresion_individual:
        idx = indices_iniciales[0]
        if idx not in estado.df_alumnos.index:
            messagebox.showwarning(
                "Alumno no disponible",
                "El alumno seleccionado ya no está disponible.",
                parent=ventana,
            )
            ventana.destroy()
            return
        alumno_individual = estado.df_alumnos.loc[idx]

    tb.Label(
        ventana,
        text=(
            f"Imprimir únicamente a: {alumno_individual['NombreCompleto']}"
            if es_impresion_individual
            else "Elige qué parte de las credenciales necesitas imprimir."
        ),
             font=("Segoe UI", 9), bootstyle="secondary", justify="center"
             ).pack(padx=20, pady=(0, 10))

    frame_opciones = tb.Frame(ventana)
    frame_opciones.pack(padx=20, pady=10)

    tb.Label(frame_opciones, text="Grupo:").grid(row=0, column=0, sticky="e", padx=5)
    grupos = sorted([g for g in estado.df_alumnos["Grupo"].unique().tolist() if g])
    combo_grupo_gen = tb.Combobox(frame_opciones, values=["Todos"] + grupos,
                                  state="readonly", width=15)
    combo_grupo_gen.set(
        str(alumno_individual["Grupo"]) if es_impresion_individual else "Todos")
    combo_grupo_gen.grid(row=0, column=1, padx=5)
    if es_impresion_individual:
        combo_grupo_gen.configure(state="disabled")

    var_modo = tk.StringVar(
        value="Credenciales individuales"
        if es_impresion_individual else "Solo frente")
    tb.Label(frame_opciones, text="Salida:").grid(
        row=1, column=0, sticky="e", padx=5, pady=(12, 2))
    combo_modo = tb.Combobox(
        frame_opciones,
        values=["Solo frente", "Credenciales individuales", "Solo detrás"],
        textvariable=var_modo, state="readonly", width=22)
    combo_modo.grid(row=1, column=1, padx=5, pady=(12, 2))

    frame_impresion = tb.Labelframe(
        ventana, text="Configuración de hoja", padding=12,
        bootstyle="primary")

    var_papel = tk.StringVar(value="Carta")
    var_orientacion = tk.StringVar(value="Vertical")
    var_lados = tk.StringVar(value="Frente y reverso")
    var_margen = tk.StringVar(value="1.0")
    var_separacion = tk.StringVar(value="0.3")
    var_marcas = tk.BooleanVar(value=True)
    var_reverso_comun = tk.BooleanVar(value=False)
    etiqueta_capacidad = tb.Label(
        frame_impresion, text="", bootstyle="info",
        font=("Segoe UI", 9, "bold"))

    controles = [
        ("Papel:", tb.Combobox(
            frame_impresion, values=["Carta", "A4"],
            textvariable=var_papel, state="readonly", width=16)),
        ("Orientación:", tb.Combobox(
            frame_impresion, values=["Vertical", "Horizontal"],
            textvariable=var_orientacion, state="readonly", width=16)),
        ("Contenido:", tb.Combobox(
            frame_impresion, values=["Solo frente", "Frente y reverso"],
            textvariable=var_lados, state="readonly", width=16)),
        ("Margen (cm):", tb.Entry(
            frame_impresion, textvariable=var_margen, width=18)),
        ("Separación (cm):", tb.Entry(
            frame_impresion, textvariable=var_separacion, width=18)),
    ]
    for numero, (texto, control) in enumerate(controles):
        tb.Label(frame_impresion, text=texto).grid(
            row=numero, column=0, sticky="e", padx=5, pady=4)
        control.grid(row=numero, column=1, sticky="w", padx=5, pady=4)

    check_marcas = tb.Checkbutton(
        frame_impresion, text="Agregar marcas de corte",
        variable=var_marcas, bootstyle="round-toggle")
    check_marcas.grid(
        row=5, column=0, columnspan=2, sticky="w",
        padx=5, pady=(8, 3))
    check_reverso = tb.Checkbutton(
        frame_impresion,
        text="Usar reverso común (solo fondo, sin datos del alumno)",
        variable=var_reverso_comun, bootstyle="round-toggle")
    check_reverso.grid(
        row=6, column=0, columnspan=2, sticky="w", padx=5, pady=3)
    etiqueta_capacidad.grid(
        row=7, column=0, columnspan=2, pady=(10, 0))

    def numero_decimal(variable):
        return float(variable.get().strip().replace(",", "."))

    def actualizar_capacidad(*_):
        if var_lados.get() == "Solo frente":
            etiqueta_capacidad.configure(
                text="Una credencial por página · tamaño final 8.5 × 5.5 cm",
                bootstyle="success")
            return
        try:
            orientacion_diseno = "horizontal"
            if os.path.isfile(estado.RUTA_DISENO_JSON):
                with open(
                        estado.RUTA_DISENO_JSON, "r",
                        encoding="utf-8") as archivo:
                    orientacion_diseno = json.load(archivo).get(
                        "orientacion", "horizontal")
            ancho_cm, alto_cm = (
                (estado.ANCHO_CREDENCIAL_CM, estado.ALTO_CREDENCIAL_CM)
                if orientacion_diseno == "horizontal"
                else (estado.ALTO_CREDENCIAL_CM, estado.ANCHO_CREDENCIAL_CM)
            )
            distribucion = calcular_distribucion_hoja(
                var_papel.get(), var_orientacion.get(), ancho_cm, alto_cm,
                numero_decimal(var_margen), numero_decimal(var_separacion))
            etiqueta_capacidad.configure(
                text=(
                    f"Distribución: {distribucion['columnas']} × "
                    f"{distribucion['filas']} = "
                    f"{distribucion['por_hoja']} por hoja"
                ),
                bootstyle=(
                    "success" if distribucion["por_hoja"] else "danger"),
            )
        except (ValueError, KeyError):
            etiqueta_capacidad.configure(
                text="Revisa margen y separación", bootstyle="danger")

    def actualizar_modo(*_):
        frame_impresion.pack_forget()

    def actualizar_opciones_reverso(*_):
        solo_frente = var_lados.get() == "Solo frente"
        estado_check = "disabled" if solo_frente else "normal"
        check_reverso.configure(state=estado_check)
        controles[0][1].configure(
            state="disabled" if solo_frente else "readonly")
        controles[1][1].configure(
            state="disabled" if solo_frente else "readonly")
        controles[3][1].configure(
            state="disabled" if solo_frente else "normal")
        controles[4][1].configure(
            state="disabled" if solo_frente else "normal")
        check_marcas.configure(
            state="disabled" if solo_frente else "normal")
        if solo_frente:
            var_reverso_comun.set(False)
        actualizar_capacidad()

    combo_modo.bind("<<ComboboxSelected>>", actualizar_modo)
    for variable in (
            var_papel, var_orientacion, var_margen, var_separacion):
        variable.trace_add("write", actualizar_capacidad)
    var_lados.trace_add("write", actualizar_opciones_reverso)

    def iniciar_generacion():
        grupo_sel = combo_grupo_gen.get()
        opciones_impresion = None
        if var_modo.get() in ("Solo frente", "Solo detrás"):
            opciones_impresion = {
                "papel": "Carta",
                "orientacion_papel": "Vertical",
                "lados": var_modo.get(),
                "margen_cm": 1.0,
                "separacion_cm": 0.3,
                "marcas_corte": False,
                "reverso_comun": var_modo.get() == "Solo detrás",
            }
        if not os.path.isfile(estado.RUTA_DISENO_JSON):
            messagebox.showwarning(
                "Sin diseño",
                "Primero diseña y guarda la credencial.",
                parent=ventana,
            )
            return
        try:
            with open(estado.RUTA_DISENO_JSON, "r", encoding="utf-8") as archivo:
                diseno = json.load(archivo)
        except Exception as error:
            messagebox.showerror(
                "Error al leer el diseño", str(error), parent=ventana)
            return

        lados_requeridos = ("frente", "reverso")
        reverso_comun = False
        if opciones_impresion:
            if opciones_impresion["lados"] == "Solo frente":
                lados_requeridos = ("frente",)
            elif opciones_impresion["lados"] == "Solo detrás":
                lados_requeridos = ("reverso",)
            reverso_comun = opciones_impresion["reverso_comun"]
        df_validacion = estado.df_alumnos
        grupo_validacion = grupo_sel
        if es_impresion_individual:
            df_validacion = estado.df_alumnos.loc[indices_iniciales]
            grupo_validacion = "Todos"
        resultado = validar_pre_generacion(
            df_validacion, diseno, grupo_validacion,
            lados_requeridos=lados_requeridos,
            reverso_comun=reverso_comun,
            requerir_fotografia=(
                not opciones_impresion
                or opciones_impresion["lados"] != "Solo detrás"))
        ventana.destroy()
        mostrar_resultados_validacion(
            resultado, grupo_sel, diseno, opciones_impresion)

    tb.Button(ventana, text="🖨️ Generar", bootstyle="success", cursor="hand2",
              command=iniciar_generacion).pack(pady=(10, 20), ipady=6)


def mostrar_resultados_validacion(
        resultado, grupo, diseno, opciones_impresion=None):
    ventana = tk.Toplevel(estado.root)
    ventana.title("Validación previa de credenciales")
    ventana.geometry("980x560")
    ventana.minsize(820, 460)

    problemas = resultado["problemas"]
    errores = sum(1 for item in problemas if item["nivel"] == "Error")
    avisos = sum(1 for item in problemas if item["nivel"] == "Aviso")
    listas = len(resultado["indices_validos"])

    tb.Label(
        ventana, text="Revisión antes de generar",
        font=("Segoe UI", 14, "bold"), bootstyle="primary"
    ).pack(anchor="w", padx=18, pady=(16, 4))
    tb.Label(
        ventana,
        text=(
            f"Alumnos revisados: {resultado['total']}   |   "
            f"Listos: {listas}   |   Errores: {errores}   |   Avisos: {avisos}"
        ),
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w", padx=18, pady=(0, 12))

    frame_tabla = tb.Frame(ventana)
    frame_tabla.pack(fill="both", expand=True, padx=18)
    columnas = ("nivel", "alumno", "tipo", "detalle")
    tabla = tb.Treeview(
        frame_tabla, columns=columnas, show="headings", bootstyle="primary")
    tabla.heading("nivel", text="Nivel")
    tabla.heading("alumno", text="Alumno")
    tabla.heading("tipo", text="Problema")
    tabla.heading("detalle", text="Detalle")
    tabla.column("nivel", width=70, stretch=False)
    tabla.column("alumno", width=210)
    tabla.column("tipo", width=180)
    tabla.column("detalle", width=450)
    tabla.tag_configure("Error", foreground="#c0392b")
    tabla.tag_configure("Aviso", foreground="#b9770e")
    tabla.pack(side="left", fill="both", expand=True)
    scroll = tb.Scrollbar(frame_tabla, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")

    mapa_problemas = {}
    for numero, problema in enumerate(problemas):
        iid = str(numero)
        mapa_problemas[iid] = problema
        tabla.insert("", "end", iid=iid, values=(
            problema["nivel"], problema["alumno"],
            problema["tipo"], problema["detalle"],
        ), tags=(problema["nivel"],))

    if not problemas:
        tabla.insert("", "end", values=(
            "OK", "Todos", "Sin problemas",
            "Todas las credenciales seleccionadas están listas para generar."))

    def localizar_alumno():
        seleccion = tabla.selection()
        if not seleccion:
            return
        problema = mapa_problemas.get(seleccion[0])
        if not problema or problema["idx"] is None:
            messagebox.showinfo(
                "Problema del diseño",
                "Este problema debe corregirse en el Diseñador de Credencial.",
                parent=ventana,
            )
            return
        from excel_datos import actualizar_lista, seleccionar_alumno
        estado.combo_grupo.set("Todos")
        estado.entry_buscar.delete(0, tk.END)
        actualizar_lista()
        iid_alumno = str(problema["idx"])
        if estado.tree.exists(iid_alumno):
            estado.tree.selection_set(iid_alumno)
            estado.tree.see(iid_alumno)
            seleccionar_alumno()
            ventana.destroy()

    def continuar_generacion():
        if not resultado["indices_validos"]:
            messagebox.showwarning(
                "No hay credenciales listas",
                "Corrige los errores antes de generar.",
                parent=ventana,
            )
            return
        ventana.destroy()
        generar_credenciales(
            solo_grupo=grupo,
            indices_permitidos=resultado["indices_validos"],
            diseno_precargado=diseno,
            opciones_impresion=opciones_impresion,
        )

    frame_botones = tb.Frame(ventana)
    frame_botones.pack(fill="x", padx=18, pady=16)
    tb.Button(
        frame_botones, text="Ir al Alumno", bootstyle="info-outline",
        command=localizar_alumno
    ).pack(side="left", padx=5)
    tb.Button(
        frame_botones, text="Cerrar y Corregir", bootstyle="secondary",
        command=ventana.destroy
    ).pack(side="right", padx=5)
    boton_generar = tb.Button(
        frame_botones,
        text=(
            "Generar reverso común"
            if opciones_impresion
            and opciones_impresion["lados"] == "Solo detrás"
            else f"Generar PDF con {listas} frente(s)"
            if opciones_impresion
            else f"Generar {listas} Credencial(es)"
        ),
        bootstyle="success", command=continuar_generacion)
    boton_generar.pack(side="right", padx=5)
    if not resultado["indices_validos"]:
        boton_generar.configure(state="disabled")
