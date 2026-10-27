"""Tabla visual de alumnos con acciones por fila.

Se usa una fila de widgets en lugar de un Treeview para poder colocar botones
reales (cámara, edición, impresión y eliminación) dentro de cada registro.
"""

import tkinter as tk
import ttkbootstrap as tb


class TablaAlumnos:
    COLUMNAS = (
        ("matricula", "Matrícula", 125),
        ("nombre", "Nombre", 150),
        ("apellido_paterno", "A. Paterno", 130),
        ("apellido_materno", "A. Materno", 130),
        ("especialidad", "Especialidad", 150),
        ("grupo", "Grupo", 70),
        ("turno", "Turno", 95),
        ("generacion", "Generación", 100),
        ("semestre", "Semestre", 75),
        ("foto", "Foto", 90),
    )

    def __init__(self, parent):
        self.parent = parent
        self.seleccion_actual = None
        self.filas = {}

        self.canvas = tk.Canvas(parent, highlightthickness=0, bg="#f8f9fa")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scroll_vertical = tb.Scrollbar(
            parent, orient="vertical", command=self.canvas.yview,
            bootstyle="round-primary")
        self.scroll_vertical.pack(side="right", fill="y")
        self.scroll_horizontal = tb.Scrollbar(
            parent, orient="horizontal", command=self.canvas.xview,
            bootstyle="round-primary")
        self.scroll_horizontal.pack(side="bottom", fill="x")
        self.canvas.configure(
            yscrollcommand=self.scroll_vertical.set,
            xscrollcommand=self.scroll_horizontal.set)

        self.contenido = tb.Frame(self.canvas)
        self.ventana_canvas = self.canvas.create_window(
            (0, 0), window=self.contenido, anchor="nw")
        self.contenido.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))
        self.canvas.bind(
            "<Configure>", self._ajustar_ancho_minimo)
        self._crear_encabezado()

    def _ajustar_ancho_minimo(self, event):
        ancho = max(event.width, self._ancho_total())
        self.canvas.itemconfigure(self.ventana_canvas, width=ancho)

    def _ancho_total(self):
        return sum(ancho for _, _, ancho in self.COLUMNAS) + 370

    def _crear_encabezado(self):
        encabezado = tb.Frame(self.contenido, bootstyle="dark")
        encabezado.grid(row=0, column=0, sticky="ew")
        for columna, texto, ancho in self.COLUMNAS:
            tb.Label(
                encabezado, text=texto, bootstyle="inverse-dark",
                font=("Segoe UI", 9, "bold"), anchor="center",
                width=max(8, ancho // 8), padding=(4, 8),
            ).pack(side="left", fill="y")
        tb.Label(
            encabezado, text="Acciones", bootstyle="inverse-dark",
            font=("Segoe UI", 9, "bold"), anchor="center",
            width=38, padding=(4, 8),
        ).pack(side="left", fill="y")

    def _seleccionar(self, iid):
        self.seleccion_actual = str(iid)
        for fila_id, (marco, _botones) in self.filas.items():
            marco.configure(bootstyle="primary" if fila_id == self.seleccion_actual else "light")
        from excel_datos import seleccionar_alumno
        seleccionar_alumno()

    def _boton_accion(self, marco, texto, estilo, comando):
        return tb.Button(
            marco, text=texto, bootstyle=estilo, width=3,
            cursor="hand2", command=comando)

    def clear(self):
        for marco, _ in self.filas.values():
            marco.destroy()
        self.filas.clear()
        self.seleccion_actual = None

    def insert(self, _parent, _index, iid, values, tags=()):
        iid = str(iid)
        fila = tb.Frame(
            self.contenido,
            bootstyle="success" if "con_foto" in tags else "danger")
        fila.grid(row=len(self.filas) + 1, column=0, sticky="ew")
        fila.grid_propagate(False)
        fila.configure(height=58)

        for posicion, (_columna, _texto, ancho) in enumerate(self.COLUMNAS):
            valor = str(values[posicion]) if posicion < len(values) else ""
            etiqueta = tb.Label(
                fila, text=valor, anchor="center", justify="center",
                width=max(8, ancho // 8), padding=(4, 8),
                bootstyle="success" if "con_foto" in tags else "danger")
            etiqueta.pack(side="left", fill="y")
            etiqueta.bind("<Button-1>", lambda _event, idx=iid: self._seleccionar(idx))

        acciones = tb.Frame(fila)
        acciones.pack(side="left", fill="y", padx=4)
        botones = []

        def seleccionar_y(comando):
            self._seleccionar(iid)
            comando()

        from camara import abrir_camara_alumno
        from excel_datos import abrir_editor_alumno, eliminar_alumno
        from generador_credenciales import imprimir_alumno_seleccionado
        botones.append(self._boton_accion(
            acciones, "📷", "info-outline",
            lambda: seleccionar_y(lambda: abrir_camara_alumno(int(iid)))))
        botones.append(self._boton_accion(
            acciones, "✏", "secondary-outline",
            lambda: seleccionar_y(abrir_editor_alumno)))
        botones.append(self._boton_accion(
            acciones, "🖨", "success-outline",
            lambda: seleccionar_y(imprimir_alumno_seleccionado)))
        botones.append(self._boton_accion(
            acciones, "🗑", "danger-outline",
            lambda: seleccionar_y(lambda: eliminar_alumno(int(iid)))))
        for boton in botones:
            boton.pack(side="left", padx=2, pady=12)
        self.filas[iid] = (fila, botones)

    def get_children(self):
        return tuple(self.filas.keys())

    def delete(self, iid):
        iid = str(iid)
        fila = self.filas.pop(iid, None)
        if fila:
            fila[0].destroy()

    def selection(self):
        return (self.seleccion_actual,) if self.seleccion_actual is not None else ()

    def selection_set(self, iid):
        self.seleccion_actual = str(iid)
        self._seleccionar(iid)

    def selection_remove(self, _selection):
        self.seleccion_actual = None
        for marco, _botones in self.filas.values():
            marco.configure(bootstyle="light")
        # Mantiene sincronizados los botones y el índice activo cuando una
        # acción del flujo cambia la selección programáticamente.
        from excel_datos import seleccionar_alumno
        seleccionar_alumno()

    def exists(self, iid):
        return str(iid) in self.filas

    def see(self, _iid):
        return None

