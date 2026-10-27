"""Tabla de alumnos optimizada con filas virtualizadas."""

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
    ALTO_ENCABEZADO = 38
    ALTO_FILA = 58

    def __init__(self, parent):
        self.parent = parent
        self.seleccion_actual = None
        self.registros = []
        self.filas = {}
        self._ancho = self._ancho_total()
        self._render_pendiente = False

        self.encabezado = tb.Frame(parent, bootstyle="dark")
        self.encabezado.pack(side="top", fill="x")
        self.canvas = tk.Canvas(parent, highlightthickness=0, bg="#f8f9fa")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scroll_vertical = tb.Scrollbar(
            parent, orient="vertical", command=self._desplazar_vertical,
            bootstyle="round-primary")
        self.scroll_vertical.pack(side="right", fill="y")
        self.scroll_horizontal = tb.Scrollbar(
            parent, orient="horizontal", command=self._desplazar_horizontal,
            bootstyle="round-primary")
        self.scroll_horizontal.pack(side="bottom", fill="x")
        self.canvas.configure(
            yscrollcommand=self.scroll_vertical.set,
            xscrollcommand=self.scroll_horizontal.set)

        self.contenido = tb.Frame(self.canvas)
        self.ventana_canvas = self.canvas.create_window(
            (0, 0), window=self.contenido, anchor="nw")
        self.canvas.bind("<Configure>", self._ajustar_canvas)
        self.canvas.bind("<MouseWheel>", self._rueda_mouse)
        self.canvas.bind_all("<MouseWheel>", self._rueda_mouse, add="+")
        self.canvas.bind("<Button-4>", lambda _event: self._desplazar_vertical("scroll", -3, "units"))
        self.canvas.bind("<Button-5>", lambda _event: self._desplazar_vertical("scroll", 3, "units"))
        self._crear_encabezado()
        self._actualizar_region()

    def _ancho_total(self):
        return sum(ancho for _, _, ancho in self.COLUMNAS) + 370

    def _crear_encabezado(self):
        encabezado = self.encabezado
        encabezado.configure(width=self._ancho, height=self.ALTO_ENCABEZADO)
        encabezado.pack_propagate(False)
        for _columna, texto, ancho in self.COLUMNAS:
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

    def _ajustar_canvas(self, event):
        self._ancho = max(event.width, self._ancho_total())
        self.canvas.itemconfigure(self.ventana_canvas, width=self._ancho)
        self._actualizar_region()

    def _actualizar_region(self):
        alto = max(1, len(self.registros)) * self.ALTO_FILA
        self.contenido.configure(width=self._ancho, height=alto)
        self.canvas.configure(scrollregion=(0, 0, self._ancho, alto))
        self._programar_render()

    def _programar_render(self):
        if self._render_pendiente:
            return
        self._render_pendiente = True
        self.canvas.after_idle(self._render_visible)

    def _render_visible(self):
        self._render_pendiente = False
        arriba = self.canvas.canvasy(0)
        abajo = arriba + max(1, self.canvas.winfo_height())
        primero = max(0, int(arriba // self.ALTO_FILA) - 1)
        ultimo = min(len(self.registros), int(abajo // self.ALTO_FILA) + 2)
        visibles = {self.registros[i][0] for i in range(primero, max(primero, ultimo))}
        for iid, (fila, _botones) in list(self.filas.items()):
            if iid not in visibles:
                fila.destroy()
                del self.filas[iid]
        for posicion in range(primero, max(primero, ultimo)):
            iid, values, tags = self.registros[posicion]
            if iid in self.filas:
                self.filas[iid][0].place_configure(
                    y=posicion * self.ALTO_FILA)
                continue
            self._crear_fila(posicion, iid, values, tags)

    def _desplazar_vertical(self, *args):
        self.canvas.yview(*args)
        self._programar_render()

    def _desplazar_horizontal(self, *args):
        self.canvas.xview(*args)
        self._programar_render()

    def _rueda_mouse(self, event):
        pasos = -int(event.delta / 120) or -1
        self._desplazar_vertical("scroll", pasos, "units")

    def _seleccionar(self, iid):
        self.seleccion_actual = str(iid)
        for fila_id, (marco, _botones) in self.filas.items():
            marco.configure(bootstyle="primary" if fila_id == self.seleccion_actual else "light")
        from excel_datos import seleccionar_alumno
        seleccionar_alumno()

    def _boton_accion(self, marco, texto, estilo, comando):
        return tb.Button(marco, text=texto, bootstyle=estilo, width=3,
                         cursor="hand2", command=comando)

    def _crear_fila(self, posicion, iid, values, tags):
        con_foto = "con_foto" in tags
        fila = tb.Frame(self.contenido, bootstyle="success" if con_foto else "danger")
        fila.place(x=0, y=posicion * self.ALTO_FILA,
                   width=self._ancho, height=self.ALTO_FILA)
        for valor, (_columna, _texto, ancho) in zip(values, self.COLUMNAS):
            etiqueta = tb.Label(
                fila, text=str(valor), anchor="center", justify="center",
                width=max(8, ancho // 8), padding=(4, 8),
                bootstyle="success" if con_foto else "danger")
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
        botones.extend((
            self._boton_accion(acciones, "📷", "info-outline",
                lambda: seleccionar_y(lambda: abrir_camara_alumno(int(iid)))),
            self._boton_accion(acciones, "✏", "secondary-outline",
                lambda: seleccionar_y(abrir_editor_alumno)),
            self._boton_accion(acciones, "🖨", "success-outline",
                lambda: seleccionar_y(imprimir_alumno_seleccionado)),
            self._boton_accion(acciones, "🗑", "danger-outline",
                lambda: seleccionar_y(lambda: eliminar_alumno(int(iid)))),
        ))
        for boton in botones:
            boton.pack(side="left", padx=2, pady=12)
        self.filas[iid] = (fila, botones)

    def clear(self):
        self.registros.clear()
        self.seleccion_actual = None
        self._actualizar_region()

    def insert(self, _parent, _index, iid, values, tags=()):
        self.registros.append((str(iid), tuple(values), tuple(tags)))
        self._actualizar_region()

    def get_children(self):
        return tuple(registro[0] for registro in self.registros)

    def delete(self, iid):
        iid = str(iid)
        self.registros = [registro for registro in self.registros if registro[0] != iid]
        fila = self.filas.pop(iid, None)
        if fila:
            fila[0].destroy()
        self._actualizar_region()

    def selection(self):
        return (self.seleccion_actual,) if self.seleccion_actual is not None else ()

    def selection_set(self, iid):
        self._seleccionar(iid)

    def selection_remove(self, _selection):
        self.seleccion_actual = None
        for marco, _botones in self.filas.values():
            marco.configure(bootstyle="light")
        from excel_datos import seleccionar_alumno
        seleccionar_alumno()

    def exists(self, iid):
        return str(iid) in self.get_children()

    def see(self, iid):
        iid = str(iid)
        posiciones = {registro[0]: posicion for posicion, registro in enumerate(self.registros)}
        if iid not in posiciones:
            return
        y = posiciones[iid] * self.ALTO_FILA
        self.canvas.yview_moveto(max(0, y / max(1, self.contenido.winfo_reqheight())))
        self._programar_render()
