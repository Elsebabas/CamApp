"""
Estado compartido de la aplicación.

Este módulo concentra las variables globales (mutables) y constantes que
necesitan compartir los demás módulos: cámara, datos de Excel, y el
diseñador de credencial.

IMPORTANTE para quien edite estos módulos: los demás archivos deben hacer
`import estado` y acceder como `estado.variable`, nunca
`from estado import variable`. Con `from...import`, cada módulo se queda
con su propia copia del valor en el momento del import y los cambios ya
no se reflejan entre módulos — hay que asignar siempre sobre el atributo
del módulo (`estado.df_alumnos = ...`), no sobre un nombre local.

Las referencias a widgets de Tkinter (root, tree, combo_grupo, etc.) también
viven aquí; main.py las asigna justo después de crear cada widget.
"""

import os

# ─── Referencias a widgets (asignadas por main.py al construir la ventana) ───
root = None
tree = None
frame_contenido = None
tabla_alumnos = None
combo_grupo = None
combo_estado_foto = None
entry_buscar = None
etiqueta_excel = None
etiqueta_alumno = None
etiqueta_foto = None
etiqueta_video = None
etiqueta_proyecto = None
etiqueta_estado = None
etiqueta_progreso = None
barra_progreso = None
boton_iniciar_camara = None
boton_tomar_foto = None
boton_detener_camara = None
boton_imprimir_credencial = None
boton_cargar_foto = None
boton_historial = None
id_notificacion_pendiente = None

# ─── Proyecto activo ─────────────────────────────────────────────────────────
ruta_proyecto = None
nombre_proyecto = None

# ─── Estado de la cámara ─────────────────────────────────────────────────────
video = None
camera_index = 0
espejo_camara = False
ventana_foto_activa = None    # Referencia a la ventana de preview de foto abierta (o None)
ventana_camara = None         # Ventana independiente de cámara del alumno activo

# ─── Estado de los datos de alumnos ──────────────────────────────────────────
df_alumnos = None             # DataFrame con los datos del Excel cargado
ruta_excel_trabajo = None     # Ruta donde se va guardando el progreso (copia)
FOTOS_DIR = None              # Carpeta donde se guardan las fotos
alumno_actual_idx = None      # Índice (en df_alumnos) del alumno seleccionado
id_busqueda_pendiente = None  # Id del root.after() programado para el buscador (debounce)

# ─── Constantes de la foto / recorte ─────────────────────────────────────────
ANCHO_RECORTE = 395    # Ancho final de la foto de credencial
ALTO_RECORTE = 480     # Alto final de la foto de credencial
UMBRAL_BORROSO = 30    # Varianza del Laplaciano por debajo de la cual se considera borrosa

# ─── Excel de alumnos ─────────────────────────────────────────────────────────
COLUMNAS_REQUERIDAS = [
    "Matricula", "Nombre", "Apellido Paterno", "Apellido Materno",
    "CURP", "Grupo", "Turno", "Especialidad", "Semestre", "Generacion"
]

# ─── Diseñador de credencial ──────────────────────────────────────────────────
CAMPOS_DISPONIBLES = [
    "NombreCompleto", "Nombre", "Apellidos", "Apellido Paterno", "Apellido Materno",
    "Matricula", "CURP", "Grupo", "Turno", "Especialidad", "Semestre",
    "Generacion", "FOTO"
]
ANCHO_CREDENCIAL_CM = 8.5
ALTO_CREDENCIAL_CM = 5.5
CM_A_PX_PREVIEW = 70   # escala de edición en pantalla (no es la resolución final de impresión)
DIRECTORIO_APLICACION = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CamApp")
RUTA_DISENO_JSON = os.path.join(
    DIRECTORIO_APLICACION, "diseno_credencial.json")

FUENTES_TEXTO = [
    "Arial", "Gill Sans MT", "Calibri", "Times New Roman", "Georgia",
    "Verdana", "Segoe UI", "Tahoma", "Century Gothic", "Trebuchet MS"
]
