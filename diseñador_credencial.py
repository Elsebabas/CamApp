"""
Diseñador visual de la credencial: cargar la imagen de fondo (por separado
para frente y reverso), arrastrar los campos a su posición sobre un lienzo
con el tamaño real de la credencial, y elegir orientación horizontal o
vertical. El diseño se guarda en estado.RUTA_DISENO_JSON (posiciones como
fracciones del ancho/alto, para que sea independiente de la resolución
final de impresión).

Estructura del JSON guardado:
{
  "orientacion": "horizontal" | "vertical",
  "lados": {
    "frente":  {"fondo_path": "...", "campos": {...}},
    "reverso": {"fondo_path": "...", "campos": {...}}
  }
}
"""

import os
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import ttkbootstrap as tb
from PIL import Image, ImageTk, ImageOps

import estado
from respaldos import crear_respaldo
from utilidades import (
    obtener_valor_campo, resolver_ruta_archivo, hacer_ruta_portable,
    sanitizar_nombre_archivo,
)


def abrir_disenador_credencial():
    """Ventana para diseñar visualmente la credencial. La variable local
    `estado_diseno` (diccionario) guarda el estado del diseño en edición;
    no confundir con el módulo `estado` (estado global de la aplicación)."""

    ventana = tk.Toplevel(estado.root)
    ventana.title("Diseñador de Credencial")
    ventana.resizable(False, False)

    estado_diseno = {
        "orientacion": "horizontal",
        "lado_actual": "frente",
        "lados": {
            "frente": {"fondo_path": None, "fondo_img_tk": None, "campos": {}, "campo_seleccionado": None},
            "reverso": {"fondo_path": None, "fondo_img_tk": None, "campos": {}, "campo_seleccionado": None},
        },
    }
    alumno_preview_idx = tk.StringVar(value="")
    imagenes_preview = []

    if os.path.exists(estado.RUTA_DISENO_JSON):
        try:
            with open(estado.RUTA_DISENO_JSON, "r", encoding="utf-8") as f:
                datos_guardados = json.load(f)
            estado_diseno["orientacion"] = datos_guardados.get("orientacion", "horizontal")
            datos_lados_guardados = datos_guardados.get("lados", {})
            for lado in ("frente", "reverso"):
                datos_lado_guardado = datos_lados_guardados.get(lado, {})
                estado_diseno["lados"][lado]["fondo_path"] = datos_lado_guardado.get("fondo_path")
                estado_diseno["lados"][lado]["campos"] = datos_lado_guardado.get("campos", {})
        except Exception:
            pass

    def lado_activo():
        return estado_diseno["lados"][estado_diseno["lado_actual"]]

    frame_controles = tb.Frame(ventana, padding=10)
    frame_controles.pack(side="top", fill="x")

    frame_controles2 = tb.Frame(ventana, padding=(10, 0))
    frame_controles2.pack(side="top", fill="x")

    frame_canvas_contenedor = tb.Frame(ventana, padding=10)
    frame_canvas_contenedor.pack(side="top")

    etiqueta_lado = tb.Label(frame_canvas_contenedor, text="Editando: FRENTE",
                              font=("Segoe UI", 10, "bold"), bootstyle="primary")
    etiqueta_lado.pack(pady=(0, 5))

    canvas = tk.Canvas(frame_canvas_contenedor, bg="#dddddd", highlightthickness=1,
                        highlightbackground="#999999")
    canvas.pack()

    RADIO_NODO = 6
    TAMANO_MINIMO_CAMPO_PX = 18

    frame_propiedades = tb.Labelframe(ventana, text="Propiedades del campo seleccionado",
                                       padding=10, bootstyle="primary")
    frame_propiedades.pack(side="top", fill="x", padx=10, pady=(0, 10))

    def dimensiones_actuales_px():
        if estado_diseno["orientacion"] == "horizontal":
            ancho_cm, alto_cm = estado.ANCHO_CREDENCIAL_CM, estado.ALTO_CREDENCIAL_CM
        else:
            ancho_cm, alto_cm = estado.ALTO_CREDENCIAL_CM, estado.ANCHO_CREDENCIAL_CM
        return int(ancho_cm * estado.CM_A_PX_PREVIEW), int(alto_cm * estado.CM_A_PX_PREVIEW)

    def campo_en_posicion(x, y):
        ancho_px, alto_px = dimensiones_actuales_px()
        for nombre_campo, datos in reversed(list(lado_activo()["campos"].items())):
            x1 = datos["x_frac"] * ancho_px
            y1 = datos["y_frac"] * alto_px
            x2 = x1 + datos.get("ancho_frac", 0.3) * ancho_px
            y2 = y1 + datos.get("alto_frac", 0.08) * alto_px
            if x1 <= x <= x2 and y1 <= y <= y2:
                return nombre_campo
        return None

    def nodos_campo(nombre_campo):
        """Devuelve las cuatro esquinas del campo en coordenadas del lienzo."""
        ancho_px, alto_px = dimensiones_actuales_px()
        datos = lado_activo()["campos"][nombre_campo]
        x1 = datos["x_frac"] * ancho_px
        y1 = datos["y_frac"] * alto_px
        x2 = x1 + datos.get("ancho_frac", 0.3) * ancho_px
        y2 = y1 + datos.get("alto_frac", 0.08) * alto_px
        return {
            "nw": (x1, y1),
            "ne": (x2, y1),
            "sw": (x1, y2),
            "se": (x2, y2),
        }

    def nodo_en_posicion(x, y):
        """Detecta primero los nodos del campo seleccionado para que un clic
        en una esquina redimensione en vez de iniciar el movimiento normal."""
        nombre_campo = lado_activo()["campo_seleccionado"]
        if nombre_campo is None or nombre_campo not in lado_activo()["campos"]:
            return None
        for esquina, (nodo_x, nodo_y) in nodos_campo(nombre_campo).items():
            if abs(x - nodo_x) <= RADIO_NODO + 2 and abs(y - nodo_y) <= RADIO_NODO + 2:
                return esquina
        return None

    def dibujar_campo(nombre_campo, datos, ancho_px, alto_px):
        x = datos["x_frac"] * ancho_px
        y = datos["y_frac"] * alto_px
        w = datos.get("ancho_frac", 0.3) * ancho_px
        h = datos.get("alto_frac", 0.08) * alto_px
        color_borde = "#e74c3c" if nombre_campo == lado_activo()["campo_seleccionado"] else "#3498db"

        fila_preview = None
        if alumno_preview_idx.get() and estado.df_alumnos is not None:
            try:
                fila_preview = estado.df_alumnos.loc[int(alumno_preview_idx.get())]
            except (KeyError, TypeError, ValueError):
                fila_preview = None

        if nombre_campo == "FOTO":
            ruta_foto = resolver_ruta_archivo(
                fila_preview.get("RutaFoto", "")) if fila_preview is not None else ""
            if ruta_foto and os.path.exists(ruta_foto):
                foto = Image.open(ruta_foto).convert("RGB")
                foto = ImageOps.fit(foto, (max(1, int(w)), max(1, int(h))), Image.LANCZOS)
                foto_tk = ImageTk.PhotoImage(foto)
                imagenes_preview.append(foto_tk)
                canvas.create_image(x, y, image=foto_tk, anchor="nw", tags=(nombre_campo,))
                canvas.create_rectangle(x, y, x + w, y + h, outline=color_borde, width=2,
                                         tags=(nombre_campo,))
            else:
                canvas.create_rectangle(x, y, x + w, y + h, outline=color_borde, width=2,
                                         fill="#cccccc", stipple="gray50", tags=(nombre_campo,))
                canvas.create_text(x + w / 2, y + h / 2, text="FOTO", fill="#333333",
                                    font=("Segoe UI", 9, "bold"), tags=(nombre_campo,))
        else:
            canvas.create_rectangle(x, y, x + w, y + h, outline=color_borde, width=1,
                                     dash=(3, 2), tags=(nombre_campo,))
            tamano_pt = datos.get("tamano_pt", 10)
            estilo = "bold" if datos.get("negrita", False) else "normal"
            nombre_fuente = datos.get("fuente", "Arial")
            alineacion = datos.get("alineacion", "izquierda")

            if alineacion == "centro":
                x_texto, anchor_tk = x + w / 2, "center"
            elif alineacion == "derecha":
                x_texto, anchor_tk = x + w - 4, "e"
            else:
                x_texto, anchor_tk = x + 4, "w"

            texto_mostrado = (obtener_valor_campo(fila_preview, nombre_campo)
                              if fila_preview is not None else "{" + nombre_campo + "}")
            canvas.create_text(x_texto, y + h / 2, text=texto_mostrado,
                                fill=datos.get("color", "#000000"),
                                font=(nombre_fuente, tamano_pt, estilo),
                                anchor=anchor_tk, tags=(nombre_campo,))

        if nombre_campo == lado_activo()["campo_seleccionado"]:
            for esquina, (nodo_x, nodo_y) in nodos_campo(nombre_campo).items():
                canvas.create_rectangle(
                    nodo_x - RADIO_NODO, nodo_y - RADIO_NODO,
                    nodo_x + RADIO_NODO, nodo_y + RADIO_NODO,
                    fill="white", outline="#e74c3c", width=2,
                    tags=("nodo_redimension", f"nodo_{esquina}")
                )

    def redibujar_canvas():
        imagenes_preview.clear()
        ancho_px, alto_px = dimensiones_actuales_px()
        canvas.configure(width=ancho_px, height=alto_px)
        canvas.delete("all")

        datos_lado = lado_activo()
        etiqueta_lado.configure(text=f"Editando: {estado_diseno['lado_actual'].upper()}")

        ruta_fondo = resolver_ruta_archivo(datos_lado["fondo_path"])
        if ruta_fondo and os.path.exists(ruta_fondo):
            img = Image.open(ruta_fondo).resize((ancho_px, alto_px))
            datos_lado["fondo_img_tk"] = ImageTk.PhotoImage(img)
            canvas.create_image(0, 0, image=datos_lado["fondo_img_tk"], anchor="nw", tags="fondo")
        else:
            canvas.create_rectangle(0, 0, ancho_px, alto_px, fill="white", outline="")
            canvas.create_text(ancho_px / 2, alto_px / 2,
                                text=f"Sin plantilla de fondo cargada ({estado_diseno['lado_actual']})",
                                fill="#999999", font=("Segoe UI", 10, "italic"))

        for nombre_campo, datos in datos_lado["campos"].items():
            dibujar_campo(nombre_campo, datos, ancho_px, alto_px)

    arrastre = {
        "activo": False, "modo": None, "campo": None, "esquina": None,
        "x_prev": 0, "y_prev": 0,
        "x1_inicial": 0, "y1_inicial": 0, "x2_inicial": 0, "y2_inicial": 0,
    }

    def iniciar_arrastre(event):
        esquina = nodo_en_posicion(event.x, event.y)
        if esquina is not None:
            nombre_campo = lado_activo()["campo_seleccionado"]
            nodos = nodos_campo(nombre_campo)
            x1, y1 = nodos["nw"]
            x2, y2 = nodos["se"]
            arrastre.update({
                "activo": True, "modo": "redimensionar", "campo": nombre_campo,
                "esquina": esquina, "x_prev": event.x, "y_prev": event.y,
                "x1_inicial": x1, "y1_inicial": y1,
                "x2_inicial": x2, "y2_inicial": y2,
            })
            return

        nombre_campo = campo_en_posicion(event.x, event.y)
        if nombre_campo is None:
            return
        arrastre["activo"] = True
        arrastre["modo"] = "mover"
        arrastre["campo"] = nombre_campo
        arrastre["x_prev"] = event.x
        arrastre["y_prev"] = event.y
        seleccionar_campo(nombre_campo)

    def mover_arrastre(event):
        if not arrastre["activo"]:
            return
        nombre_campo = arrastre["campo"]

        if arrastre["modo"] == "redimensionar":
            ancho_px, alto_px = dimensiones_actuales_px()
            x1 = arrastre["x1_inicial"]
            y1 = arrastre["y1_inicial"]
            x2 = arrastre["x2_inicial"]
            y2 = arrastre["y2_inicial"]
            esquina = arrastre["esquina"]

            if "w" in esquina:
                x1 = min(max(event.x, 0), x2 - TAMANO_MINIMO_CAMPO_PX)
            else:
                x2 = max(min(event.x, ancho_px), x1 + TAMANO_MINIMO_CAMPO_PX)
            if "n" in esquina:
                y1 = min(max(event.y, 0), y2 - TAMANO_MINIMO_CAMPO_PX)
            else:
                y2 = max(min(event.y, alto_px), y1 + TAMANO_MINIMO_CAMPO_PX)

            datos = lado_activo()["campos"][nombre_campo]
            datos["x_frac"] = x1 / ancho_px
            datos["y_frac"] = y1 / alto_px
            datos["ancho_frac"] = (x2 - x1) / ancho_px
            datos["alto_frac"] = (y2 - y1) / alto_px
            redibujar_canvas()
            return

        dx = event.x - arrastre["x_prev"]
        dy = event.y - arrastre["y_prev"]
        arrastre["x_prev"] = event.x
        arrastre["y_prev"] = event.y

        ancho_px, alto_px = dimensiones_actuales_px()
        datos = lado_activo()["campos"][nombre_campo]
        ancho_frac = datos.get("ancho_frac", 0.3)
        alto_frac = datos.get("alto_frac", 0.08)
        datos["x_frac"] = min(max(datos["x_frac"] + dx / ancho_px, 0), 1 - ancho_frac)
        datos["y_frac"] = min(max(datos["y_frac"] + dy / alto_px, 0), 1 - alto_frac)
        redibujar_canvas()

    def soltar_arrastre(event):
        hubo_arrastre = arrastre["activo"]
        arrastre["activo"] = False
        arrastre["modo"] = None
        if hubo_arrastre:
            refrescar_propiedades()

    def actualizar_cursor(event):
        cursores_nodo = {
            "nw": "size_nw_se", "se": "size_nw_se",
            "ne": "size_ne_sw", "sw": "size_ne_sw",
        }
        esquina = nodo_en_posicion(event.x, event.y)
        canvas.configure(cursor=cursores_nodo.get(esquina, "arrow"))

    canvas.bind("<ButtonPress-1>", iniciar_arrastre)
    canvas.bind("<B1-Motion>", mover_arrastre)
    canvas.bind("<ButtonRelease-1>", soltar_arrastre)
    canvas.bind("<Motion>", actualizar_cursor)

    def seleccionar_campo(nombre_campo):
        lado_activo()["campo_seleccionado"] = nombre_campo
        redibujar_canvas()
        refrescar_propiedades()

    def refrescar_propiedades():
        for widget in frame_propiedades.winfo_children():
            widget.destroy()

        nombre_campo = lado_activo()["campo_seleccionado"]
        if nombre_campo is None:
            tb.Label(frame_propiedades,
                     text="Selecciona un campo en el lienzo para editar sus propiedades."
                     ).pack(anchor="w")
            return

        datos = lado_activo()["campos"][nombre_campo]
        tb.Label(frame_propiedades, text=f"Campo: {nombre_campo}",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))

        ancho_cm_credencial, alto_cm_credencial = (
            (estado.ANCHO_CREDENCIAL_CM, estado.ALTO_CREDENCIAL_CM)
            if estado_diseno["orientacion"] == "horizontal"
            else (estado.ALTO_CREDENCIAL_CM, estado.ANCHO_CREDENCIAL_CM)
        )

        # ── Tamaño (ancho/alto en cm) — aplica a cualquier campo, incluida la foto ──
        tb.Label(frame_propiedades, text="Ancho (cm):").grid(row=1, column=0, sticky="e", padx=5)
        entry_ancho = tb.Entry(frame_propiedades, width=8)
        entry_ancho.insert(0, f"{datos.get('ancho_frac', 0.3) * ancho_cm_credencial:.2f}")
        entry_ancho.grid(row=1, column=1, padx=5)

        tb.Label(frame_propiedades, text="Alto (cm):").grid(row=1, column=2, sticky="e", padx=5)
        entry_alto = tb.Entry(frame_propiedades, width=8)
        entry_alto.insert(0, f"{datos.get('alto_frac', 0.08) * alto_cm_credencial:.2f}")
        entry_alto.grid(row=1, column=3, padx=5)

        def aplicar_tamano():
            try:
                ancho_cm_campo = float(entry_ancho.get())
                alto_cm_campo = float(entry_alto.get())
            except ValueError:
                messagebox.showwarning("Valor inválido", "Ingresa números válidos.", parent=ventana)
                return
            datos["ancho_frac"] = max(0.01, min(1.0, ancho_cm_campo / ancho_cm_credencial))
            datos["alto_frac"] = max(0.01, min(1.0, alto_cm_campo / alto_cm_credencial))
            redibujar_canvas()

        tb.Button(frame_propiedades, text="Aplicar tamaño", bootstyle="secondary",
                  command=aplicar_tamano).grid(row=1, column=4, padx=8)

        if nombre_campo == "FOTO":
            def ajustar_proporcion_foto():
                try:
                    ancho_cm_campo = float(entry_ancho.get())
                except ValueError:
                    messagebox.showwarning("Valor inválido", "Ingresa un ancho válido primero.", parent=ventana)
                    return
                alto_correcto_cm = ancho_cm_campo * (estado.ALTO_RECORTE / estado.ANCHO_RECORTE)
                entry_alto.delete(0, tk.END)
                entry_alto.insert(0, f"{alto_correcto_cm:.2f}")
                aplicar_tamano()

            tb.Button(frame_propiedades, text="📐 Ajustar proporción de foto (según el ancho)",
                      bootstyle="info-outline", command=ajustar_proporcion_foto
                      ).grid(row=2, column=0, columnspan=5, pady=(8, 0), sticky="w")
        else:
            # ── Propiedades de texto: tipo de letra, tamaño, negrita, alineación ──
            tb.Label(frame_propiedades, text="Tipo de letra:").grid(row=2, column=0, sticky="e", padx=5, pady=(10, 0))
            combo_fuente = tb.Combobox(frame_propiedades, state="readonly", width=14,
                                        values=estado.FUENTES_TEXTO)
            combo_fuente.set(datos.get("fuente", "Arial"))
            combo_fuente.grid(row=2, column=1, padx=5, pady=(10, 0))

            tb.Label(frame_propiedades, text="Tamaño:").grid(row=2, column=2, sticky="e", padx=5, pady=(10, 0))
            entry_tamano = tb.Entry(frame_propiedades, width=6)
            entry_tamano.insert(0, str(datos.get("tamano_pt", 10)))
            entry_tamano.grid(row=2, column=3, padx=5, pady=(10, 0))

            var_negrita = tk.BooleanVar(value=datos.get("negrita", False))
            tb.Checkbutton(frame_propiedades, text="Negrita", variable=var_negrita,
                           bootstyle="round-toggle").grid(row=2, column=4, padx=10, pady=(10, 0))

            color_seleccionado = tk.StringVar(value=datos.get("color", "#000000"))

            def elegir_color_texto():
                _, color_hex = colorchooser.askcolor(
                    color=color_seleccionado.get(),
                    title=f"Color del campo {nombre_campo}",
                    parent=ventana,
                )
                if color_hex:
                    color_seleccionado.set(color_hex)
                    datos["color"] = color_hex
                    boton_color.configure(text=color_hex)
                    muestra_color.configure(bg=color_hex)
                    redibujar_canvas()

            tb.Label(frame_propiedades, text="Color:").grid(
                row=4, column=0, sticky="e", padx=5, pady=(8, 0))
            muestra_color = tk.Label(frame_propiedades, width=3, relief="solid", bd=1,
                                      bg=color_seleccionado.get())
            muestra_color.grid(row=4, column=1, sticky="w", padx=(5, 2), pady=(8, 0))
            boton_color = tb.Button(frame_propiedades, text=color_seleccionado.get(),
                                    bootstyle="secondary-outline", command=elegir_color_texto)
            boton_color.grid(row=4, column=2, columnspan=2, sticky="w", padx=5, pady=(8, 0))

            tb.Label(frame_propiedades, text="Alineación:").grid(row=3, column=0, sticky="e", padx=5, pady=(6, 0))
            combo_alineacion = tb.Combobox(frame_propiedades, state="readonly", width=10,
                                            values=["Izquierda", "Centro", "Derecha"])
            mapa_alineacion_a_texto = {"izquierda": "Izquierda", "centro": "Centro", "derecha": "Derecha"}
            combo_alineacion.set(mapa_alineacion_a_texto.get(datos.get("alineacion", "izquierda"), "Izquierda"))
            combo_alineacion.grid(row=3, column=1, padx=5, pady=(6, 0))

            def aplicar_texto():
                try:
                    datos["tamano_pt"] = int(entry_tamano.get())
                except ValueError:
                    pass
                datos["negrita"] = var_negrita.get()
                datos["fuente"] = combo_fuente.get()
                datos["color"] = color_seleccionado.get()
                mapa_texto_a_alineacion = {"Izquierda": "izquierda", "Centro": "centro", "Derecha": "derecha"}
                datos["alineacion"] = mapa_texto_a_alineacion.get(combo_alineacion.get(), "izquierda")
                redibujar_canvas()

            tb.Button(frame_propiedades, text="Aplicar texto", bootstyle="secondary",
                      command=aplicar_texto).grid(row=3, column=2, padx=8, pady=(6, 0))

        def quitar_campo():
            del lado_activo()["campos"][nombre_campo]
            lado_activo()["campo_seleccionado"] = None
            redibujar_canvas()
            refrescar_propiedades()

        tb.Button(frame_propiedades, text="🗑 Quitar del diseño", bootstyle="danger-outline",
                  command=quitar_campo).grid(row=5, column=0, columnspan=2, pady=(12, 0), sticky="w")

    def cargar_fondo():
        ruta = filedialog.askopenfilename(
            title=f"Selecciona la imagen de fondo ({estado_diseno['lado_actual']})",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg")]
        )
        if not ruta:
            return
        if estado.ruta_proyecto:
            carpeta_fondos = os.path.join(
                estado.ruta_proyecto, "diseno", "fondos")
            os.makedirs(carpeta_fondos, exist_ok=True)
            extension = os.path.splitext(ruta)[1].lower() or ".png"
            nombre = sanitizar_nombre_archivo(
                f"fondo_{estado_diseno['lado_actual']}") + extension
            destino = os.path.join(carpeta_fondos, nombre)
            if os.path.normcase(os.path.abspath(ruta)) != os.path.normcase(
                    os.path.abspath(destino)):
                shutil.copy2(ruta, destino)
            ruta = destino
        lado_activo()["fondo_path"] = hacer_ruta_portable(ruta)
        redibujar_canvas()

    def cambiar_orientacion():
        estado_diseno["orientacion"] = var_orientacion.get()
        redibujar_canvas()

    def cambiar_lado():
        estado_diseno["lado_actual"] = var_lado.get()
        redibujar_canvas()
        refrescar_propiedades()

    var_orientacion = tk.StringVar(value=estado_diseno["orientacion"])
    var_lado = tk.StringVar(value=estado_diseno["lado_actual"])

    tb.Button(frame_controles, text="🖼 Cargar Fondo", bootstyle="primary", cursor="hand2",
              command=cargar_fondo).pack(side="left", padx=5)

    tb.Radiobutton(frame_controles, text="Horizontal", variable=var_orientacion, value="horizontal",
                   command=cambiar_orientacion, bootstyle="toolbutton").pack(side="left", padx=(15, 2))
    tb.Radiobutton(frame_controles, text="Vertical", variable=var_orientacion, value="vertical",
                   command=cambiar_orientacion, bootstyle="toolbutton").pack(side="left", padx=2)

    tb.Radiobutton(frame_controles, text="✏️ Frente", variable=var_lado, value="frente",
                   command=cambiar_lado, bootstyle="info-toolbutton").pack(side="left", padx=(15, 2))
    tb.Radiobutton(frame_controles, text="✏️ Reverso", variable=var_lado, value="reverso",
                   command=cambiar_lado, bootstyle="info-toolbutton").pack(side="left", padx=2)

    combo_agregar_campo = tb.Combobox(frame_controles2, values=estado.CAMPOS_DISPONIBLES,
                                      state="readonly", width=18)
    combo_agregar_campo.set("Agregar campo...")
    combo_agregar_campo.pack(side="left", padx=(0, 5), pady=8)

    def agregar_campo_seleccionado():
        nombre_campo = combo_agregar_campo.get()
        campos_lado = lado_activo()["campos"]
        if nombre_campo not in estado.CAMPOS_DISPONIBLES or nombre_campo in campos_lado:
            return

        ancho_cm_credencial, alto_cm_credencial = (
            (estado.ANCHO_CREDENCIAL_CM, estado.ALTO_CREDENCIAL_CM)
            if estado_diseno["orientacion"] == "horizontal"
            else (estado.ALTO_CREDENCIAL_CM, estado.ANCHO_CREDENCIAL_CM)
        )

        if nombre_campo == "FOTO":
            # Proporción por defecto igual a la del recorte real de la foto (395x480),
            # para que no salga "estirada" si no se ajusta manualmente.
            ancho_foto_cm = 2.2
            alto_foto_cm = ancho_foto_cm * (estado.ALTO_RECORTE / estado.ANCHO_RECORTE)
            campos_lado[nombre_campo] = {
                "x_frac": 0.05, "y_frac": 0.15,
                "ancho_frac": min(1.0, ancho_foto_cm / ancho_cm_credencial),
                "alto_frac": min(1.0, alto_foto_cm / alto_cm_credencial),
            }
        else:
            campos_lado[nombre_campo] = {
                "x_frac": 0.35, "y_frac": 0.08 + 0.09 * len(campos_lado),
                "ancho_frac": 0.55, "alto_frac": 0.08,
                "tamano_pt": 10, "color": "#000000", "negrita": False,
                "fuente": "Arial", "alineacion": "izquierda"
            }
        redibujar_canvas()
        seleccionar_campo(nombre_campo)

    tb.Button(frame_controles2, text="➕ Agregar al lado actual", bootstyle="success", cursor="hand2",
              command=agregar_campo_seleccionado).pack(side="left", padx=5, pady=8)

    opciones_preview = ["Plantilla (sin datos)"]
    indices_preview = {"Plantilla (sin datos)": ""}
    if estado.df_alumnos is not None:
        for idx, fila in estado.df_alumnos.iterrows():
            etiqueta = f"{fila.get('Matricula', '')} - {fila.get('NombreCompleto', '')}"
            opciones_preview.append(etiqueta)
            indices_preview[etiqueta] = str(idx)

    tb.Label(frame_controles2, text="Vista previa:").pack(side="left", padx=(15, 3))
    combo_preview = tb.Combobox(frame_controles2, values=opciones_preview,
                                state="readonly", width=28)
    combo_preview.set(opciones_preview[0])
    combo_preview.pack(side="left", padx=3, pady=8)

    def cambiar_alumno_preview(event=None):
        alumno_preview_idx.set(indices_preview.get(combo_preview.get(), ""))
        redibujar_canvas()

    combo_preview.bind("<<ComboboxSelected>>", cambiar_alumno_preview)

    def guardar_diseno():
        datos_a_guardar = {
            "orientacion": estado_diseno["orientacion"],
            "lados": {
                "frente": {
                    "fondo_path": estado_diseno["lados"]["frente"]["fondo_path"],
                    "campos": estado_diseno["lados"]["frente"]["campos"],
                },
                "reverso": {
                    "fondo_path": estado_diseno["lados"]["reverso"]["fondo_path"],
                    "campos": estado_diseno["lados"]["reverso"]["campos"],
                },
            },
        }
        try:
            crear_respaldo(estado.RUTA_DISENO_JSON, "disenos")
            with open(estado.RUTA_DISENO_JSON, "w", encoding="utf-8") as f:
                json.dump(datos_a_guardar, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Diseño guardado",
                                 f"Diseño guardado en:\n{os.path.abspath(estado.RUTA_DISENO_JSON)}",
                                 parent=ventana)
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e), parent=ventana)

    def limpiar_diseno_completo():
        confirmar = messagebox.askyesno(
            "Limpiar diseño completo",
            "Se eliminarán las plantillas de fondo y todos los campos del "
            "frente y del reverso.\n\n"
            "Se creará una copia de seguridad antes de continuar.\n\n"
            "¿Deseas limpiar todo el diseño?",
            icon="warning",
            parent=ventana,
        )
        if not confirmar:
            return

        for lado in ("frente", "reverso"):
            datos_lado = estado_diseno["lados"][lado]
            datos_lado["fondo_path"] = None
            datos_lado["fondo_img_tk"] = None
            datos_lado["campos"] = {}
            datos_lado["campo_seleccionado"] = None

        estado_diseno["lado_actual"] = "frente"
        var_lado.set("frente")
        alumno_preview_idx.set("")
        combo_preview.set(opciones_preview[0])
        redibujar_canvas()
        refrescar_propiedades()
        guardar_diseno()

    tb.Button(frame_controles2, text="💾 Guardar Diseño", bootstyle="info", cursor="hand2",
              command=guardar_diseno).pack(side="right", padx=5, pady=8)

    tb.Button(frame_controles2, text="🧹 Limpiar Diseño", bootstyle="danger-outline",
              cursor="hand2", command=limpiar_diseno_completo
              ).pack(side="right", padx=5, pady=8)

    redibujar_canvas()
    refrescar_propiedades()
