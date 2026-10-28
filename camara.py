"""
Funciones de la cámara: iniciar/detener, recorte centrado, guía visual con
silueta de referencia, detección de foto borrosa, y guardado de la foto
(que a su vez actualiza el Excel y avanza al siguiente alumno pendiente).
"""

import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
import cv2
import imutils
from PIL import Image, ImageTk, ImageEnhance

import estado
from utilidades import (
    sanitizar_nombre_archivo, calcular_nitidez, hacer_ruta_portable, notificar,
)
from excel_datos import guardar_excel, actualizar_lista, seleccionar_siguiente_pendiente


def video_camara():
    if estado.video is not None and estado.video.isOpened():
        notificar("La cámara ya está activa", "info")
        return

    estado.video = cv2.VideoCapture(estado.camera_index)
    if not estado.video.isOpened():
        messagebox.showerror(
            "Error de cámara",
            "No se pudo abrir la cámara. Verifica que esté conectada y que no "
            "esté en uso por otro programa."
        )
        estado.video = None
        notificar("No se pudo iniciar la cámara", "danger")
        return
    if estado.boton_iniciar_camara is not None:
        estado.boton_iniciar_camara.configure(state="disabled")
    if estado.boton_tomar_foto is not None:
        estado.boton_tomar_foto.configure(state="normal")
    if estado.boton_detener_camara is not None:
        estado.boton_detener_camara.configure(state="normal")
    # La fotografía y la cámara comparten el mismo espacio. Al iniciar la
    # cámara se oculta toda la vista previa para que el video pueda crecer.
    if estado.frame_info_alumno is not None:
        estado.frame_info_alumno.pack_forget()
    if estado.etiqueta_video is not None:
        estado.etiqueta_video.pack(
            side="top", fill="both", expand=True, padx=5, pady=5)
    notificar(f"Cámara {estado.camera_index} iniciada", "success")
    iniciar()


def abrir_configuracion_camara():
    ventana = tk.Toplevel(estado.root)
    ventana.title("Configurar Cámara")
    ventana.resizable(False, False)
    ventana.transient(estado.root)
    ventana.grab_set()

    tb.Label(
        ventana, text="Configuración de cámara",
        font=("Segoe UI", 12, "bold")
    ).grid(row=0, column=0, columnspan=2, padx=20, pady=(18, 12))

    tb.Label(ventana, text="Dispositivo:").grid(
        row=1, column=0, sticky="e", padx=6, pady=6)
    combo_indice = tb.Combobox(
        ventana, values=[str(i) for i in range(6)],
        state="readonly", width=10)
    combo_indice.set(str(estado.camera_index))
    combo_indice.grid(row=1, column=1, sticky="w", padx=6, pady=6)

    var_espejo = tk.BooleanVar(value=estado.espejo_camara)
    tb.Checkbutton(
        ventana,
        text="Reflejar horizontalmente la vista y la fotografía",
        variable=var_espejo, bootstyle="round-toggle"
    ).grid(row=2, column=0, columnspan=2, padx=20, pady=8)

    def aplicar():
        nuevo_indice = int(combo_indice.get())
        reiniciar = nuevo_indice != estado.camera_index
        if reiniciar:
            detener_video()
        estado.camera_index = nuevo_indice
        estado.espejo_camara = var_espejo.get()
        ventana.destroy()
        if reiniciar:
            messagebox.showinfo(
                "Cámara actualizada",
                "La cámara cambió. Pulsa 'Iniciar Cámara' para utilizarla.")

    frame_botones = tb.Frame(ventana)
    frame_botones.grid(row=3, column=0, columnspan=2, pady=(10, 18))
    tb.Button(
        frame_botones, text="Aplicar", bootstyle="success",
        command=aplicar
    ).pack(side="left", padx=6)
    tb.Button(
        frame_botones, text="Cancelar", bootstyle="secondary",
        command=ventana.destroy
    ).pack(side="left", padx=6)


def iniciar():
    if estado.video is None:
        return
    ret, frame = estado.video.read()
    if ret:
        if estado.espejo_camara:
            frame = cv2.flip(frame, 1)
        frame = imutils.resize(frame, width=950)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Se mide el widget real donde se dibuja el video. Medir el panel
        # completo hacía que el frame resultara más grande que su etiqueta y
        # se recortara al mostrarlo.
        ancho_panel = estado.etiqueta_video.winfo_width() or estado.root.winfo_width()
        alto_panel = estado.etiqueta_video.winfo_height() or estado.root.winfo_height()
        alto_maximo = max(180, min(560, alto_panel - 12))
        ancho_maximo = max(320, min(950, ancho_panel - 12))
        alto_frame, ancho_frame = frame.shape[:2]
        escala_preview = min(
            1.0, ancho_maximo / ancho_frame, alto_maximo / alto_frame)
        if escala_preview < 1.0:
            frame = cv2.resize(
                frame,
                (int(ancho_frame * escala_preview),
                 int(alto_frame * escala_preview)),
                interpolation=cv2.INTER_AREA,
            )
        frame_con_guia = dibujar_guia_recorte(
            frame,
            ancho_recorte=max(1, int(estado.ANCHO_RECORTE * escala_preview)),
            alto_recorte=max(1, int(estado.ALTO_RECORTE * escala_preview)),
        )
        img = Image.fromarray(frame_con_guia)
        img_tk = ImageTk.PhotoImage(img)
        estado.etiqueta_video.configure(image=img_tk)
        estado.etiqueta_video.image = img_tk
        estado.etiqueta_video.after(10, iniciar)
    else:
        messagebox.showerror(
            "Error de cámara",
            "Se perdió la señal de la cámara. Intenta iniciarla de nuevo."
        )
        detener_video()


def detener_video():
    if estado.video is not None:
        estado.video.release()
        estado.video = None
    estado.etiqueta_video.configure(image="")
    estado.etiqueta_video.image = None
    if estado.boton_iniciar_camara is not None:
        estado.boton_iniciar_camara.configure(state="normal")
    if estado.boton_tomar_foto is not None:
        estado.boton_tomar_foto.configure(state="disabled")
    if estado.boton_detener_camara is not None:
        estado.boton_detener_camara.configure(state="disabled")
    if estado.frame_info_alumno is not None and estado.etiqueta_video is not None:
        estado.etiqueta_video.pack_forget()
        estado.frame_info_alumno.pack(
            fill="both", expand=True, pady=(4, 2))
    notificar("Cámara detenida", "info")


def cerrar_ventana():
    detener_video()
    estado.root.destroy()


def recortar_tamano_infantil(imagen):
    """Recorta la imagen centrada, calculando la posición según el centro real
    del frame en vez de usar coordenadas fijas que asumían una resolución de
    cámara específica."""
    ancho_img, alto_img = imagen.size

    x1 = max(0, (ancho_img - estado.ANCHO_RECORTE) // 2)
    y1 = max(0, (alto_img - estado.ALTO_RECORTE) // 2)
    x2 = min(ancho_img, x1 + estado.ANCHO_RECORTE)
    y2 = min(alto_img, y1 + estado.ALTO_RECORTE)

    return imagen.crop((x1, y1, x2, y2))


def crear_recorte_ajustado(imagen, zoom=1.0, offset_x=0, offset_y=0,
                           brillo=1.0, contraste=1.0):
    """Genera el recorte final permitiendo acercar y desplazar la imagen."""
    ancho_objetivo = estado.ANCHO_RECORTE
    alto_objetivo = estado.ALTO_RECORTE
    ancho_original, alto_original = imagen.size

    escala_base = max(
        ancho_objetivo / ancho_original,
        alto_objetivo / alto_original,
    )
    escala = escala_base * max(1.0, float(zoom))
    ancho_escalado = max(ancho_objetivo, int(round(ancho_original * escala)))
    alto_escalado = max(alto_objetivo, int(round(alto_original * escala)))
    imagen_escalada = imagen.resize(
        (ancho_escalado, alto_escalado), Image.LANCZOS)

    izquierda_centrada = (ancho_escalado - ancho_objetivo) / 2
    superior_centrada = (alto_escalado - alto_objetivo) / 2
    izquierda = int(round(izquierda_centrada - float(offset_x)))
    superior = int(round(superior_centrada - float(offset_y)))
    izquierda = min(max(izquierda, 0), ancho_escalado - ancho_objetivo)
    superior = min(max(superior, 0), alto_escalado - alto_objetivo)

    recorte = imagen_escalada.crop((
        izquierda,
        superior,
        izquierda + ancho_objetivo,
        superior + alto_objetivo,
    ))
    if float(brillo) != 1.0:
        recorte = ImageEnhance.Brightness(recorte).enhance(float(brillo))
    if float(contraste) != 1.0:
        recorte = ImageEnhance.Contrast(recorte).enhance(float(contraste))
    return recorte


def dibujar_guia_recorte(frame_rgb, ancho_recorte=None, alto_recorte=None):
    """Dibuja sobre el frame completo (en vivo) un recuadro semitransparente
    que marca exactamente el área que 'recortar_tamano_infantil' va a capturar,
    oscureciendo todo lo que queda fuera de ese recuadro, más una silueta de
    referencia (cabeza y hombros) para ayudar a encuadrar al alumno."""
    alto_img, ancho_img = frame_rgb.shape[:2]
    ancho_recorte = ancho_recorte or estado.ANCHO_RECORTE
    alto_recorte = alto_recorte or estado.ALTO_RECORTE

    x1 = max(0, (ancho_img - ancho_recorte) // 2)
    y1 = max(0, (alto_img - alto_recorte) // 2)
    x2 = min(ancho_img, x1 + ancho_recorte)
    y2 = min(alto_img, y1 + alto_recorte)

    overlay = frame_rgb.copy()
    overlay[:, :] = 0                      # oscurece todo el frame
    overlay[y1:y2, x1:x2] = frame_rgb[y1:y2, x1:x2]  # restaura el área del recorte

    frame_con_guia = cv2.addWeighted(overlay, 0.55, frame_rgb, 0.45, 0)
    cv2.rectangle(frame_con_guia, (x1, y1), (x2, y2), (50, 220, 120), 2)

    # ── Silueta de referencia: cabeza (óvalo) + hombros (arco) ──
    ancho_recorte_real = x2 - x1
    alto_recorte_real = y2 - y1
    centro_x = (x1 + x2) // 2
    color_silueta = (255, 255, 255)
    grosor = 2

    centro_cabeza = (centro_x, y1 + int(alto_recorte_real * 0.32))
    eje_cabeza = (int(ancho_recorte_real * 0.27), int(alto_recorte_real * 0.28))
    cv2.ellipse(frame_con_guia, centro_cabeza, eje_cabeza, 0, 0, 360, color_silueta, grosor)

    centro_hombros = (centro_x, y1 + int(alto_recorte_real * 1.05))
    eje_hombros = (int(ancho_recorte_real * 0.42), int(alto_recorte_real * 0.30))
    cv2.ellipse(frame_con_guia, centro_hombros, eje_hombros, 0, 180, 360, color_silueta, grosor)

    texto = "Alinea el rostro dentro del ovalo"
    cv2.putText(frame_con_guia, texto, (x1 + 8, y2 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_silueta, 1, cv2.LINE_AA)

    return frame_con_guia


def tomar_foto():
    if estado.ventana_foto_activa is not None:
        return  # ya hay una foto en preview, evita abrir una segunda

    if estado.video is None or not estado.video.isOpened():
        messagebox.showwarning("Cámara no iniciada", "Primero da clic en 'Iniciar Cámara'.")
        return

    if estado.df_alumnos is None:
        messagebox.showwarning("Sin Excel", "Primero carga el Excel de alumnos.")
        return

    if estado.alumno_actual_idx is None:
        messagebox.showwarning("Falta el alumno", "Selecciona un alumno de la lista antes de tomar la foto.")
        return

    ret, frame = estado.video.read()
    if not ret:
        messagebox.showerror("Error de cámara", "No se pudo capturar el frame actual.")
        return

    if estado.espejo_camara:
        frame = cv2.flip(frame, 1)
    frame = imutils.resize(frame, width=950)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame)

    abrir_editor_fotografia(img)


def cargar_foto_archivo():
    """Carga una fotografía existente y la pasa por el mismo editor/recorte."""
    if estado.ventana_foto_activa is not None:
        return
    if estado.df_alumnos is None:
        messagebox.showwarning("Sin Excel", "Primero carga el Excel de alumnos.")
        return
    if estado.alumno_actual_idx is None:
        messagebox.showwarning("Falta el alumno", "Selecciona un alumno de la lista primero.")
        return
    ruta = filedialog.askopenfilename(
        title="Seleccionar fotografía del alumno",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp"),
                   ("Todos los archivos", "*.*")],
        parent=estado.root,
    )
    if not ruta:
        return
    try:
        with Image.open(ruta) as imagen:
            imagen = imagen.convert("RGB")
            abrir_editor_fotografia(imagen.copy())
    except Exception as error:
        messagebox.showerror("No se pudo abrir la fotografía", str(error))


def abrir_editor_fotografia(img):
    """Abre el editor común para una captura de cámara o un archivo."""
    if estado.alumno_actual_idx is None or estado.df_alumnos is None:
        return

    fila = estado.df_alumnos.loc[estado.alumno_actual_idx]

    ventana_foto = tk.Toplevel(estado.root)
    ventana_foto.title("Ajustar Fotografía")
    ventana_foto.resizable(False, False)
    estado.ventana_foto_activa = ventana_foto

    def cerrar_preview():
        estado.ventana_foto_activa = None
        ventana_foto.destroy()

    tb.Label(
        ventana_foto, text=f"{fila['NombreCompleto']} — {fila['Matricula']}",
        font=("Segoe UI", 11, "bold")
    ).pack(padx=18, pady=(15, 8))

    frame_editor = tb.Frame(ventana_foto)
    frame_editor.pack(padx=18, pady=5)
    canvas = tk.Canvas(
        frame_editor, width=estado.ANCHO_RECORTE,
        height=estado.ALTO_RECORTE, bg="black",
        highlightthickness=2, highlightbackground="#32bea6",
        cursor="fleur")
    canvas.grid(row=0, column=0, rowspan=8, padx=(0, 18))

    var_zoom = tk.DoubleVar(value=1.0)
    var_brillo = tk.DoubleVar(value=1.0)
    var_contraste = tk.DoubleVar(value=1.0)
    ajuste = {"offset_x": 0.0, "offset_y": 0.0, "x_prev": 0, "y_prev": 0}

    def recorte_actual():
        return crear_recorte_ajustado(
            img, var_zoom.get(), ajuste["offset_x"], ajuste["offset_y"],
            var_brillo.get(), var_contraste.get())

    def redibujar(*_):
        recorte = recorte_actual()
        imagen_tk = ImageTk.PhotoImage(recorte)
        canvas.delete("all")
        canvas.create_image(0, 0, image=imagen_tk, anchor="nw")
        canvas.image = imagen_tk

    def actualizar_nitidez(*_):
        nitidez = calcular_nitidez(recorte_actual())
        if nitidez < estado.UMBRAL_BORROSO:
            etiqueta_nitidez.configure(
                text=f"⚠ Posible desenfoque ({nitidez:.0f})",
                bootstyle="danger")
        else:
            etiqueta_nitidez.configure(
                text=f"✓ Nitidez aceptable ({nitidez:.0f})",
                bootstyle="success")

    def iniciar_movimiento(event):
        ajuste["x_prev"] = event.x
        ajuste["y_prev"] = event.y

    def mover_imagen(event):
        ajuste["offset_x"] += event.x - ajuste["x_prev"]
        ajuste["offset_y"] += event.y - ajuste["y_prev"]
        ajuste["x_prev"] = event.x
        ajuste["y_prev"] = event.y
        redibujar()

    def terminar_movimiento(event):
        actualizar_nitidez()

    canvas.bind("<ButtonPress-1>", iniciar_movimiento)
    canvas.bind("<B1-Motion>", mover_imagen)
    canvas.bind("<ButtonRelease-1>", terminar_movimiento)

    tb.Label(frame_editor, text="Arrastra la imagen para encuadrar",
             font=("Segoe UI", 9, "italic"), bootstyle="secondary"
             ).grid(row=0, column=1, sticky="w", pady=(0, 12))

    def agregar_control(fila_control, texto, variable, desde, hasta):
        tb.Label(frame_editor, text=texto).grid(
            row=fila_control, column=1, sticky="w")
        control = tb.Scale(
            frame_editor, variable=variable, from_=desde, to=hasta,
            length=240, command=lambda valor: redibujar())
        control.grid(row=fila_control + 1, column=1, sticky="ew", pady=(0, 12))
        control.bind("<ButtonRelease-1>", actualizar_nitidez)

    agregar_control(1, "Zoom", var_zoom, 1.0, 3.0)
    agregar_control(3, "Brillo", var_brillo, 0.5, 1.5)
    agregar_control(5, "Contraste", var_contraste, 0.5, 1.5)

    etiqueta_nitidez = tb.Label(
        frame_editor, text="", font=("Segoe UI", 9, "bold"))
    etiqueta_nitidez.grid(row=7, column=1, sticky="w", pady=(4, 0))

    def restablecer():
        var_zoom.set(1.0)
        var_brillo.set(1.0)
        var_contraste.set(1.0)
        ajuste["offset_x"] = 0.0
        ajuste["offset_y"] = 0.0
        redibujar()
        actualizar_nitidez()

    def confirmar_guardado():
        recorte = recorte_actual()
        foto_borrosa = calcular_nitidez(recorte) < estado.UMBRAL_BORROSO
        guardar_foto(recorte, ventana_foto, foto_borrosa)

    frame_btns = tb.Frame(ventana_foto)
    frame_btns.pack(pady=(10, 16))
    tb.Button(
        frame_btns, text="Restablecer", bootstyle="secondary-outline",
        cursor="hand2", command=restablecer, width=13
    ).grid(row=0, column=0, padx=6, ipady=5)
    tb.Button(
        frame_btns, text="Guardar", bootstyle="success", cursor="hand2",
        command=confirmar_guardado, width=13
    ).grid(row=0, column=1, padx=6, ipady=5)
    tb.Button(
        frame_btns, text="Repetir Fotografía", bootstyle="danger",
        cursor="hand2", command=cerrar_preview, width=16
    ).grid(row=0, column=2, padx=6, ipady=5)

    ventana_foto.protocol("WM_DELETE_WINDOW", cerrar_preview)
    ventana_foto.bind('<Return>', lambda e: confirmar_guardado())
    ventana_foto.bind('<Escape>', lambda e: cerrar_preview())
    redibujar()
    actualizar_nitidez()
    ventana_foto.focus_set()


def guardar_foto(img_recortada, ventana_foto=None, foto_borrosa=False):
    if estado.alumno_actual_idx is None or estado.df_alumnos is None:
        messagebox.showerror("Error", "No hay un alumno seleccionado.")
        return

    if foto_borrosa:
        if not messagebox.askyesno(
                "Foto borrosa",
                "Esta foto parece estar borrosa.\n¿Deseas guardarla de todas formas?",
                parent=ventana_foto):
            return

    fila = estado.df_alumnos.loc[estado.alumno_actual_idx]
    nombre_archivo = sanitizar_nombre_archivo(f"{fila['NombreCompleto']}_{fila['Matricula']}") + ".png"

    carpeta_grupo = os.path.join(estado.FOTOS_DIR, sanitizar_nombre_archivo(fila["Grupo"]))
    os.makedirs(carpeta_grupo, exist_ok=True)  # por si el grupo no existía al cargar el Excel
    ruta_foto = os.path.join(carpeta_grupo, nombre_archivo)

    if os.path.exists(ruta_foto):
        if not messagebox.askyesno(
                "Ya existe una foto",
                f"Ya existe una foto para {fila['NombreCompleto']}.\n¿Deseas reemplazarla?",
                parent=ventana_foto):
            return

    img_recortada.save(ruta_foto)

    estado.df_alumnos.at[
        estado.alumno_actual_idx, "RutaFoto"] = hacer_ruta_portable(ruta_foto)
    estado.df_alumnos.at[estado.alumno_actual_idx, "FotoTomada"] = "Sí"
    estado.df_alumnos.at[estado.alumno_actual_idx, "FechaCaptura"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    idx_recien_guardado = estado.alumno_actual_idx

    guardar_excel(mostrar_aviso=False)
    actualizar_lista()

    notificar(
        f"Fotografía de {fila['NombreCompleto']} guardada", "success")

    seleccionar_siguiente_pendiente(idx_recien_guardado)

    estado.ventana_foto_activa = None
    if ventana_foto is not None:
        ventana_foto.destroy()
