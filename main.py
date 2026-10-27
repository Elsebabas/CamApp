"""
Captura de Fotografías para Credenciales Escolares — punto de entrada.

Construye la ventana principal y conecta los módulos: estado (estado
compartido), utilidades, excel_datos (Excel/lista/editor de alumno), camara
(captura de fotos), y diseñador_credencial (diseño visual de la credencial).

Ejecutar este archivo para iniciar la aplicación:  python main.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import ttkbootstrap as tb
import os

import estado
from utilidades import (
    set_dpi_awareness, actualizar_indicadores, notificar,
    inicializar_archivos_aplicacion,
)
from excel_datos import (
    cargar_excel, guardar_excel, descargar_plantilla_excel,
    actualizar_lista, actualizar_lista_debounced,
    seleccionar_alumno, abrir_editor_alumno, abrir_agregar_alumno,
    actualizar_etiqueta_excel, actualizar_etiqueta_alumno,
)
from camara import (
    video_camara, tomar_foto, cargar_foto_archivo, detener_video, cerrar_ventana,
    abrir_configuracion_camara,
)
from historial import mostrar_historial_alumno
from diseñador_credencial import abrir_disenador_credencial
from generador_credenciales import (
    abrir_generador_credenciales, imprimir_alumno_seleccionado,
)
from proyectos import crear_proyecto, activar_proyecto


# ─── Ventana principal ────────────────────────────────────────────────────────
inicializar_archivos_aplicacion()
estado.root = tb.Window(themename="minty")
estado.root.title("Captura de Fotografías - Credenciales Escolares")
estado.root.state("zoomed")
set_dpi_awareness()

# Barra tipo "hero" con el nombre de la app
frame_hero = tb.Frame(estado.root, bootstyle="primary")
frame_hero.pack(side="top", fill="x")
tb.Label(frame_hero, text="📸  Captura de Fotografías — Credenciales Escolares",
         bootstyle="inverse-primary", font=("Segoe UI", 16, "bold")
         ).pack(side="left", padx=20, pady=14)

# Barras superiores: proyecto y herramientas de trabajo
frame_proyectos = tb.Frame(estado.root, padding=(15, 8), bootstyle="light")
frame_proyectos.pack(side="top", fill="x")

frame_superior = tb.Frame(estado.root, padding=(15, 7))
frame_superior.pack(side="top", fill="x")

def limpiar_datos_actuales():
    estado.df_alumnos = None
    estado.alumno_actual_idx = None
    if estado.boton_imprimir_credencial:
        estado.boton_imprimir_credencial.configure(state="disabled")
    if estado.boton_cargar_foto:
        estado.boton_cargar_foto.configure(state="disabled")
    if estado.boton_historial:
        estado.boton_historial.configure(state="disabled")
    for item in estado.tree.get_children() if estado.tree else []:
        estado.tree.delete(item)
    if estado.combo_grupo:
        estado.combo_grupo["values"] = ["Todos"]
        estado.combo_grupo.set("Todos")
    if estado.combo_estado_foto:
        estado.combo_estado_foto.set("Todos")
    for combo in (estado.combo_especialidad, estado.combo_turno):
        if combo:
            combo["values"] = ["Todos"]
            combo.set("Todos")
    if estado.entry_buscar:
        estado.entry_buscar.delete(0, tk.END)
    actualizar_indicadores()


def reflejar_proyecto_activo():
    texto = (
        f"📁 Proyecto: {estado.nombre_proyecto}"
        if estado.nombre_proyecto else "Sin proyecto activo"
    )
    estado.etiqueta_proyecto.configure(text=texto)


def nuevo_proyecto():
    carpeta_padre = filedialog.askdirectory(
        title="Selecciona dónde crear el proyecto")
    if not carpeta_padre:
        return
    nombre = simpledialog.askstring(
        "Nuevo proyecto", "Nombre del proyecto:", parent=estado.root)
    if not nombre:
        return
    try:
        carpeta = crear_proyecto(carpeta_padre, nombre)
        activar_proyecto(carpeta)
        limpiar_datos_actuales()
        reflejar_proyecto_activo()
        actualizar_etiqueta_excel()
        actualizar_etiqueta_alumno()
        messagebox.showinfo(
            "Proyecto creado",
            f"Proyecto creado correctamente en:\n{carpeta}\n\n"
            "Ahora puedes cargar un Excel o agregar un alumno manualmente.")
        notificar(f"Proyecto «{estado.nombre_proyecto}» creado", "success")
    except Exception as error:
        messagebox.showerror("No se pudo crear el proyecto", str(error))


def abrir_proyecto():
    carpeta = filedialog.askdirectory(
        title="Selecciona una carpeta de proyecto CamApp")
    if not carpeta:
        return
    try:
        rutas = activar_proyecto(carpeta)
        limpiar_datos_actuales()
        reflejar_proyecto_activo()
        if os.path.isfile(rutas["excel"]):
            cargar_excel(ruta_forzada=rutas["excel"], preguntar_progreso=False)
        else:
            actualizar_etiqueta_excel()
            actualizar_etiqueta_alumno()
        messagebox.showinfo(
            "Proyecto abierto",
            f"Proyecto activo: {estado.nombre_proyecto}")
        notificar(f"Proyecto «{estado.nombre_proyecto}» abierto", "success")
    except Exception as error:
        messagebox.showerror("No se pudo abrir el proyecto", str(error))


tb.Button(frame_proyectos, text="🗂 Nuevo Proyecto", bootstyle="dark",
          cursor="hand2", command=nuevo_proyecto
          ).pack(side="left", padx=5, ipady=4)

tb.Button(frame_proyectos, text="📁 Abrir Proyecto", bootstyle="dark-outline",
          cursor="hand2", command=abrir_proyecto
          ).pack(side="left", padx=5, ipady=4)

estado.etiqueta_proyecto = tb.Label(
    frame_proyectos, text="Sin proyecto activo", bootstyle="secondary",
    font=("Segoe UI", 10, "bold"))
estado.etiqueta_proyecto.pack(side="left", padx=(20, 5))

tb.Button(frame_superior, text="📄 Plantilla Excel", bootstyle="info",
          cursor="hand2", command=descargar_plantilla_excel
          ).pack(side="left", padx=5, ipady=4)

tb.Button(frame_superior, text="📂 Cargar Excel", bootstyle="primary",
          cursor="hand2", command=cargar_excel).pack(side="left", padx=5, ipady=4)

tb.Button(frame_superior, text="➕ Agregar Alumno", bootstyle="primary-outline",
          cursor="hand2", command=abrir_agregar_alumno
          ).pack(side="left", padx=5, ipady=4)

tb.Button(frame_superior, text="💾 Guardar Excel", bootstyle="success",
          cursor="hand2", command=lambda: guardar_excel(mostrar_aviso=True)
          ).pack(side="left", padx=5, ipady=4)

tb.Button(frame_superior, text="🪪 Diseñador de Credencial", bootstyle="secondary",
          cursor="hand2", command=abrir_disenador_credencial
          ).pack(side="left", padx=5, ipady=4)

tb.Button(frame_superior, text="🖨️ Generar Credenciales", bootstyle="dark",
          cursor="hand2", command=abrir_generador_credenciales
          ).pack(side="left", padx=5, ipady=4)

estado.etiqueta_excel = tb.Label(frame_superior, text="Ningún archivo cargado",
                                  bootstyle="secondary", font=("Segoe UI", 10, "italic"),
                                  anchor="e")
estado.etiqueta_excel.pack(side="right", fill="x", expand=True, padx=(20, 5))

# Barra de estado: se empaqueta antes del contenido expandible para reservar
# siempre su espacio en pantallas de menor altura.
frame_estado = tb.Frame(estado.root, padding=(18, 7), bootstyle="light")
frame_estado.pack(side="bottom", fill="x")
estado.etiqueta_estado = tb.Label(
    frame_estado, text="Listo", bootstyle="secondary",
    font=("Segoe UI", 9))
estado.etiqueta_estado.pack(side="left")
estado.etiqueta_progreso = tb.Label(
    frame_estado, text="Sin alumnos cargados", bootstyle="secondary",
    font=("Segoe UI", 9, "bold"))
estado.etiqueta_progreso.pack(side="right", padx=(12, 0))
estado.barra_progreso = tb.Progressbar(
    frame_estado, length=170, maximum=100, value=0,
    bootstyle="success-striped")
estado.barra_progreso.pack(side="right")
actualizar_indicadores()

# Contenedor principal (paneles lado a lado)
frame_contenido = tb.Frame(estado.root, padding=(15, 5))
frame_contenido.pack(side="top", fill="both", expand=True)
frame_contenido.grid_columnconfigure(0, weight=1, uniform="paneles")
frame_contenido.grid_columnconfigure(1, weight=1, uniform="paneles")
frame_contenido.grid_rowconfigure(0, weight=1)

# Panel izquierdo: alumnos
frame_izquierdo = tb.Labelframe(frame_contenido, text="Alumnos", bootstyle="primary", padding=12)
frame_izquierdo.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

frame_filtros = tb.Frame(frame_izquierdo)
frame_filtros.pack(fill="x", pady=5)
for columna in range(3):
    frame_filtros.grid_columnconfigure(columna, weight=1)

def crear_filtro_superior(texto, fila, columna, control):
    bloque = tb.Frame(frame_filtros)
    bloque.grid(row=fila, column=columna, sticky="ew", padx=4, pady=2)
    tb.Label(bloque, text=texto).pack(anchor="w")
    control.pack(fill="x")
    return control

estado.combo_grupo = crear_filtro_superior(
    "Grupo", 0, 0,
    tb.Combobox(frame_filtros, state="readonly", width=12, values=["Todos"]))
estado.combo_grupo.set("Todos")
estado.combo_grupo.bind("<<ComboboxSelected>>", actualizar_lista)

estado.combo_estado_foto = crear_filtro_superior(
    "Foto", 0, 1,
    tb.Combobox(frame_filtros, state="readonly", width=12,
                values=["Todos", "Con foto", "Sin foto"]))
estado.combo_estado_foto.set("Todos")
estado.combo_estado_foto.bind("<<ComboboxSelected>>", actualizar_lista)

estado.combo_turno = crear_filtro_superior(
    "Turno", 0, 2,
    tb.Combobox(frame_filtros, state="readonly", width=12, values=["Todos"]))
estado.combo_turno.set("Todos")
estado.combo_turno.bind("<<ComboboxSelected>>", actualizar_lista)

estado.combo_especialidad = crear_filtro_superior(
    "Especialidad", 1, 0,
    tb.Combobox(frame_filtros, state="readonly", width=20, values=["Todos"]))
estado.combo_especialidad.set("Todos")
estado.combo_especialidad.bind("<<ComboboxSelected>>", actualizar_lista)

estado.entry_buscar = crear_filtro_superior(
    "Buscar", 1, 1,
    tb.Entry(frame_filtros, width=16))
estado.entry_buscar.bind("<KeyRelease>", actualizar_lista_debounced)

frame_tree = tb.Frame(frame_izquierdo)
frame_tree.pack(fill="both", expand=True, pady=5)

columnas = (
    "nombre", "apellido_paterno", "apellido_materno", "matricula",
    "especialidad", "grupo", "turno", "generacion", "semestre", "foto",
)
estado.tree = tb.Treeview(
    frame_tree, columns=columnas, show="headings", height=26,
    bootstyle="primary")
encabezados = {
    "nombre": "Nombre", "apellido_paterno": "A. Paterno",
    "apellido_materno": "A. Materno", "matricula": "Matrícula",
    "especialidad": "Especialidad", "grupo": "Grupo", "turno": "Turno",
    "generacion": "Generación", "semestre": "Semestre", "foto": "Foto",
}
anchos = {
    "nombre": 150, "apellido_paterno": 130,
    "apellido_materno": 130, "matricula": 125, "especialidad": 150,
    "grupo": 70, "turno": 95, "generacion": 100, "semestre": 75,
    "foto": 90,
}
for columna in columnas:
    estado.tree.heading(columna, text=encabezados[columna])
    estado.tree.column(columna, width=anchos[columna], minwidth=anchos[columna],
                      stretch=False, anchor="center")
estado.tree.tag_configure("con_foto", foreground="#2e8b57")
estado.tree.tag_configure("sin_foto", foreground="#c0392b")
estado.tree.pack(side="top", fill="both", expand=True)
estado.tree.bind("<<TreeviewSelect>>", seleccionar_alumno)

scrollbar_tree = tb.Scrollbar(frame_tree, orient="vertical", command=estado.tree.yview,
                               bootstyle="round-primary")
estado.tree.configure(yscrollcommand=scrollbar_tree.set)
scrollbar_tree.pack(side="right", fill="y")
scrollbar_horizontal = tb.Scrollbar(
    frame_tree, orient="horizontal", command=estado.tree.xview,
    bootstyle="round-primary")
estado.tree.configure(xscrollcommand=scrollbar_horizontal.set)
scrollbar_horizontal.pack(side="bottom", fill="x")

# Panel derecho: cámara
frame_derecho = tb.Labelframe(frame_contenido, text="Cámara", bootstyle="primary", padding=12)
frame_derecho.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

frame_info_alumno = tb.Frame(frame_derecho)
frame_info_alumno.pack(fill="x", pady=(5, 2))

estado.etiqueta_alumno = tb.Label(
    frame_info_alumno, text="Sin alumno seleccionado",
    font=("Segoe UI", 12, "bold"), anchor="center", justify="center")
estado.etiqueta_alumno.pack(fill="x", padx=8)

estado.etiqueta_foto = tk.Label(
    frame_info_alumno, text="Sin fotografía", bg="#f8f9fa",
    fg="#6c757d", anchor="center", justify="center",
    padx=8, pady=8)
estado.etiqueta_foto.pack(pady=(5, 8))

frame_acciones_alumno = tb.Frame(frame_derecho)
frame_acciones_alumno.pack(pady=(2, 8))

tb.Button(frame_acciones_alumno, text="✏️ Editar Datos", bootstyle="secondary-outline",
          cursor="hand2", command=abrir_editor_alumno, width=18
          ).pack(side="left", padx=5, ipady=4)

estado.boton_imprimir_credencial = tb.Button(
    frame_acciones_alumno, text="🖨️ Imprimir credencial",
    bootstyle="success-outline", cursor="hand2",
    command=imprimir_alumno_seleccionado, state="disabled", width=22)
estado.boton_imprimir_credencial.pack(side="left", padx=5, ipady=4)

estado.boton_cargar_foto = tb.Button(
    frame_acciones_alumno, text="📂 Cargar fotografía",
    bootstyle="info-outline", cursor="hand2",
    command=cargar_foto_archivo, state="disabled", width=20)
estado.boton_cargar_foto.pack(side="left", padx=5, ipady=4)

estado.boton_historial = tb.Button(
    frame_acciones_alumno, text="🧾 Historial",
    bootstyle="warning-outline", cursor="hand2",
    command=mostrar_historial_alumno, state="disabled", width=14)
estado.boton_historial.pack(side="left", padx=5, ipady=4)

# Los controles se empaquetan desde abajo antes que el video para reservar
# siempre su espacio, incluso en pantallas de menor altura.
tb.Button(frame_derecho, text="Cerrar Programa", bootstyle="danger",
          cursor="hand2", command=cerrar_ventana, width=18
          ).pack(side="bottom", pady=(8, 12), ipady=4)

frame_botones_camara = tb.Frame(frame_derecho)
frame_botones_camara.pack(side="bottom", pady=(8, 10))

estado.boton_iniciar_camara = tb.Button(
    frame_botones_camara, text="▶ Iniciar Cámara", bootstyle="success",
    cursor="hand2", command=video_camara, width=15)
estado.boton_iniciar_camara.grid(row=0, column=0, padx=8, ipady=8)

estado.boton_tomar_foto = tb.Button(
    frame_botones_camara, text="📷 Tomar Fotografía", bootstyle="primary",
    cursor="hand2", command=tomar_foto, width=15, state="disabled")
estado.boton_tomar_foto.grid(row=0, column=1, padx=8, ipady=8)

estado.boton_detener_camara = tb.Button(
    frame_botones_camara, text="■ Detener Cámara", bootstyle="warning",
    cursor="hand2", command=detener_video, width=15, state="disabled")
estado.boton_detener_camara.grid(row=0, column=2, padx=8, ipady=8)

tb.Button(
    frame_botones_camara, text="⚙ Configurar Cámara",
    bootstyle="secondary-outline", cursor="hand2",
    command=abrir_configuracion_camara, width=18
).grid(row=1, column=0, columnspan=3, pady=(12, 0), ipady=4)

estado.etiqueta_video = tk.Label(frame_derecho, bg="black")
estado.etiqueta_video.pack(side="top", pady=5)


def manejar_tecla_espacio(event):
    """Permite tomar la foto con la barra espaciadora, salvo que el foco esté
    en un campo de texto (por ejemplo el buscador) donde el espacio debe
    escribirse normalmente."""
    widget_enfocado = estado.root.focus_get()
    if isinstance(widget_enfocado, (tk.Entry, ttk.Entry)):
        return
    tomar_foto()


estado.root.bind_all('<space>', manejar_tecla_espacio)
estado.root.protocol("WM_DELETE_WINDOW", cerrar_ventana)
estado.root.mainloop()
