import os
import tempfile
import unittest

from PIL import Image, ImageDraw
import pandas as pd

from generador_credenciales import (
    _ajustar_fuente_al_campo, calcular_distribucion_hoja,
    crear_hoja_impresion, cm_a_px, generar_hojas_impresion,
)
from camara import crear_recorte_ajustado
from excel_datos import (
    determinar_ruta_excel_trabajo, construir_fila_alumno,
    normalizar_datos_alumnos,
)
from respaldos import crear_respaldo
from utilidades import (
    obtener_valor_campo, resumen_fotografias,
    inicializar_archivos_aplicacion,
)
from utilidades import resolver_ruta_archivo, hacer_ruta_portable
from proyectos import crear_proyecto, activar_proyecto, rutas_proyecto
from validacion_credenciales import validar_pre_generacion
import estado


class PruebasRespaldos(unittest.TestCase):
    def test_crea_respaldo_y_respeta_retencion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "alumnos.xlsx")
            for numero in range(5):
                with open(ruta, "w", encoding="utf-8") as archivo:
                    archivo.write(str(numero))
                crear_respaldo(ruta, "excel", max_respaldos=3)

            carpeta_respaldos = os.path.join(carpeta, "respaldos_camapp", "excel")
            respaldos = os.listdir(carpeta_respaldos)
            self.assertEqual(len(respaldos), 3)


class PruebasProyectos(unittest.TestCase):
    def tearDown(self):
        estado.ruta_proyecto = None
        estado.nombre_proyecto = None
        estado.ruta_excel_trabajo = None
        estado.FOTOS_DIR = None
        estado.RUTA_DISENO_JSON = "diseno_credencial.json"

    def test_crea_y_activa_estructura_portable(self):
        with tempfile.TemporaryDirectory() as carpeta:
            proyecto = crear_proyecto(carpeta, "Escuela Tutorial 2026")
            rutas = activar_proyecto(proyecto)
            self.assertTrue(os.path.isfile(rutas["manifiesto"]))
            self.assertTrue(os.path.isdir(rutas["fotos"]))
            self.assertTrue(os.path.isdir(rutas["fondos"]))
            self.assertTrue(os.path.isdir(rutas["pdfs"]))
            self.assertEqual(estado.nombre_proyecto, "Escuela Tutorial 2026")
            self.assertEqual(estado.ruta_excel_trabajo, rutas["excel"])

    def test_convierte_rutas_internas_a_relativas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            proyecto = crear_proyecto(carpeta, "Proyecto")
            activar_proyecto(proyecto)
            ruta_foto = os.path.join(
                rutas_proyecto(proyecto)["fotos"], "2A", "alumno.png")
            portable = hacer_ruta_portable(ruta_foto)
            self.assertEqual(portable, "fotos_alumnos/2A/alumno.png")
            self.assertEqual(
                os.path.normcase(resolver_ruta_archivo(portable)),
                os.path.normcase(os.path.normpath(ruta_foto)),
            )


class PruebasValidacionCredenciales(unittest.TestCase):
    def _diseno(self, fondo):
        return {
            "orientacion": "horizontal",
            "lados": {
                "frente": {
                    "fondo_path": fondo,
                    "campos": {
                        "NombreCompleto": {
                            "x_frac": 0.1, "y_frac": 0.1,
                            "ancho_frac": 0.8, "alto_frac": 0.1,
                        },
                        "FOTO": {
                            "x_frac": 0.1, "y_frac": 0.25,
                            "ancho_frac": 0.3, "alto_frac": 0.6,
                        },
                    },
                },
                "reverso": {"fondo_path": fondo, "campos": {}},
            },
        }

    def test_aprueba_alumno_con_datos_foto_y_diseno_validos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            fondo = os.path.join(carpeta, "fondo.png")
            foto = os.path.join(carpeta, "foto.png")
            Image.new("RGB", (20, 20), "white").save(fondo)
            Image.new("RGB", (20, 20), "white").save(foto)
            df = pd.DataFrame([{
                "Matricula": "1", "NombreCompleto": "Ana Pérez",
                "Grupo": "2A", "FotoTomada": "Sí", "RutaFoto": foto,
            }])
            resultado = validar_pre_generacion(df, self._diseno(fondo))
            self.assertEqual(resultado["indices_validos"], [0])
            self.assertFalse(any(
                p["nivel"] == "Error" for p in resultado["problemas"]))

    def test_rechaza_fotografia_registrada_que_no_existe(self):
        with tempfile.TemporaryDirectory() as carpeta:
            fondo = os.path.join(carpeta, "fondo.png")
            Image.new("RGB", (20, 20), "white").save(fondo)
            df = pd.DataFrame([{
                "Matricula": "1", "NombreCompleto": "Ana Pérez",
                "Grupo": "2A", "FotoTomada": "Sí",
                "RutaFoto": os.path.join(carpeta, "ausente.png"),
            }])
            resultado = validar_pre_generacion(df, self._diseno(fondo))
            self.assertEqual(resultado["indices_validos"], [])
            self.assertTrue(any(
                p["tipo"] == "Fotografía no encontrada"
                for p in resultado["problemas"]))

    def test_bloquea_diseno_con_campo_fuera_del_lienzo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            fondo = os.path.join(carpeta, "fondo.png")
            foto = os.path.join(carpeta, "foto.png")
            Image.new("RGB", (20, 20), "white").save(fondo)
            Image.new("RGB", (20, 20), "white").save(foto)
            diseno = self._diseno(fondo)
            diseno["lados"]["frente"]["campos"]["NombreCompleto"][
                "x_frac"] = 0.9
            df = pd.DataFrame([{
                "Matricula": "1", "NombreCompleto": "Ana Pérez",
                "Grupo": "2A", "FotoTomada": "Sí", "RutaFoto": foto,
            }])
            resultado = validar_pre_generacion(df, diseno)
        self.assertTrue(resultado["error_global"])
        self.assertEqual(resultado["indices_validos"], [])

    def test_solo_frente_ignora_errores_exclusivos_del_reverso(self):
        with tempfile.TemporaryDirectory() as carpeta:
            foto = os.path.join(carpeta, "foto.png")
            Image.new("RGB", (20, 20), "white").save(foto)
            df = pd.DataFrame([{
                "Matricula": "1", "NombreCompleto": "ALUMNO PRUEBA",
                "Grupo": "1A", "FotoTomada": "Sí", "RutaFoto": foto,
            }])
            diseno = {
                "lados": {
                    "frente": {"fondo_path": "", "campos": {
                        "FOTO": {
                            "x_frac": 0.1, "y_frac": 0.1,
                            "ancho_frac": 0.3, "alto_frac": 0.5,
                        }}},
                    "reverso": {"fondo_path": "archivo_inexistente.png",
                                "campos": {}},
                }
            }
            resultado = validar_pre_generacion(
                df, diseno, lados_requeridos=("frente",))
            self.assertFalse(resultado["error_global"])
            self.assertEqual(resultado["indices_validos"], [0])

    def test_reverso_comun_no_requiere_fotografias(self):
        df = pd.DataFrame([{
            "Matricula": "1", "NombreCompleto": "ALUMNO PRUEBA",
            "Grupo": "1A", "FotoTomada": "No", "RutaFoto": "",
        }])
        diseno = {
            "lados": {
                "reverso": {"fondo_path": "", "campos": {}},
            }
        }
        resultado = validar_pre_generacion(
            df, diseno, lados_requeridos=("reverso",),
            reverso_comun=True, requerir_fotografia=False)
        self.assertFalse(resultado["error_global"])
        self.assertEqual(resultado["indices_validos"], [0])


class PruebasAjusteTexto(unittest.TestCase):
    def test_texto_largo_cabe_en_el_ancho_disponible(self):
        imagen = Image.new("RGB", (500, 100), "white")
        dibujo = ImageDraw.Draw(imagen)
        texto = "NOMBRE EXTRAORDINARIAMENTE LARGO PARA UNA CREDENCIAL"
        fuente = _ajustar_fuente_al_campo(
            dibujo, texto, "Arial", False, 60, 260, 60)
        bbox = dibujo.textbbox((0, 0), texto, font=fuente)
        self.assertLessEqual(bbox[2] - bbox[0], 252)
        self.assertLessEqual(bbox[3] - bbox[1], 56)


class PruebasHojasImpresion(unittest.TestCase):
    def test_carta_vertical_admite_ocho_credenciales_horizontales(self):
        distribucion = calcular_distribucion_hoja(
            papel="Carta", orientacion="Vertical",
            ancho_credencial_cm=8.5, alto_credencial_cm=5.5,
            margen_cm=1.0, separacion_cm=0.3)
        self.assertEqual(distribucion["columnas"], 2)
        self.assertEqual(distribucion["filas"], 4)
        self.assertEqual(distribucion["por_hoja"], 8)

    def test_crea_hoja_con_tamano_fisico_solicitado(self):
        dpi = 30
        distribucion = calcular_distribucion_hoja(
            papel="A4", orientacion="Horizontal",
            ancho_credencial_cm=8.5, alto_credencial_cm=5.5)
        credencial = Image.new(
            "RGB", (cm_a_px(8.5, dpi), cm_a_px(5.5, dpi)), "red")
        hoja = crear_hoja_impresion(
            [credencial], distribucion, dpi=dpi)
        self.assertEqual(hoja.size, (
            cm_a_px(29.7, dpi), cm_a_px(21.0, dpi)))

    def test_reverso_refleja_columnas_para_impresion_duplex(self):
        dpi = 30
        distribucion = calcular_distribucion_hoja(
            papel="Carta", orientacion="Vertical",
            ancho_credencial_cm=8.5, alto_credencial_cm=5.5)
        credencial = Image.new(
            "RGB", (cm_a_px(8.5, dpi), cm_a_px(5.5, dpi)), "blue")
        hoja = crear_hoja_impresion(
            [credencial], distribucion, reflejar_columnas=True, dpi=dpi)
        margen = cm_a_px(1.0, dpi)
        separacion = cm_a_px(0.3, dpi)
        x_reflejada = margen + credencial.width + separacion
        self.assertEqual(hoja.getpixel((x_reflejada, margen)), (0, 0, 255))
        self.assertEqual(hoja.getpixel((margen, margen)), (255, 255, 255))

    def test_pdf_duplex_contiene_frente_y_reverso(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as carpeta:
            df = pd.DataFrame([{
                "NombreCompleto": "ALUMNO PRUEBA",
                "Matricula": "1", "Grupo": "1A", "FotoTomada": "Sí",
            }])
            opciones = {
                "papel": "Carta", "orientacion_papel": "Vertical",
                "lados": "Frente y reverso", "margen_cm": 1.0,
                "separacion_cm": 0.3, "marcas_corte": True,
                "reverso_comun": True, "grupo": "Todos",
            }
            generadas, errores, ruta = generar_hojas_impresion(
                df, {}, {}, cm_a_px(8.5), cm_a_px(5.5),
                carpeta, opciones)
            self.assertEqual(generadas, 1)
            self.assertEqual(errores, [])
            self.assertTrue(os.path.isfile(ruta))
            self.assertEqual(len(PdfReader(ruta).pages), 2)

    def test_solo_frente_genera_una_pagina_por_credencial(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as carpeta:
            df = pd.DataFrame([{
                "NombreCompleto": f"ALUMNO {numero}",
                "Matricula": str(numero), "Grupo": "2A",
                "FotoTomada": "Sí",
            } for numero in range(10)])
            opciones = {
                "papel": "Carta", "orientacion_papel": "Vertical",
                "lados": "Solo frente", "margen_cm": 1.0,
                "separacion_cm": 0.3, "marcas_corte": True,
                "reverso_comun": False, "grupo": "2A",
            }
            generadas, errores, ruta = generar_hojas_impresion(
                df, {}, {}, cm_a_px(8.5), cm_a_px(5.5),
                carpeta, opciones)
            lector = PdfReader(ruta)
            self.assertEqual(generadas, 10)
            self.assertEqual(errores, [])
            self.assertEqual(len(lector.pages), 10)
            pagina = lector.pages[0]
            self.assertAlmostEqual(
                float(pagina.mediabox.width), 8.5 / 2.54 * 72, delta=1)
            self.assertAlmostEqual(
                float(pagina.mediabox.height), 5.5 / 2.54 * 72, delta=1)

    def test_solo_detras_genera_un_unico_reverso_comun(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as carpeta:
            df = pd.DataFrame([{
                "NombreCompleto": f"ALUMNO {numero}",
                "Matricula": str(numero), "Grupo": "2A",
                "FotoTomada": "No",
            } for numero in range(10)])
            opciones = {"lados": "Solo detrás", "grupo": "2A"}
            generadas, errores, ruta = generar_hojas_impresion(
                df, {}, {}, cm_a_px(8.5), cm_a_px(5.5),
                carpeta, opciones)
            self.assertEqual(generadas, 1)
            self.assertEqual(errores, [])
            self.assertEqual(len(PdfReader(ruta).pages), 1)


class PruebasEditorFotografia(unittest.TestCase):
    def test_recorte_siempre_conserva_tamano_final(self):
        imagen = Image.new("RGB", (1280, 720), "gray")
        recorte = crear_recorte_ajustado(
            imagen, zoom=2.2, offset_x=120, offset_y=-80)
        self.assertEqual(recorte.size, (estado.ANCHO_RECORTE, estado.ALTO_RECORTE))

    def test_desplazamiento_cambia_el_encuadre(self):
        imagen = Image.new("RGB", (800, 600), "red")
        ImageDraw.Draw(imagen).rectangle((400, 0, 799, 599), fill="blue")
        izquierda = crear_recorte_ajustado(imagen, zoom=1.5, offset_x=-120)
        derecha = crear_recorte_ajustado(imagen, zoom=1.5, offset_x=120)
        self.assertNotEqual(izquierda.tobytes(), derecha.tobytes())

    def test_control_de_brillo_modifica_la_imagen(self):
        imagen = Image.new("RGB", (800, 600), (100, 100, 100))
        normal = crear_recorte_ajustado(imagen, brillo=1.0)
        brillante = crear_recorte_ajustado(imagen, brillo=1.4)
        self.assertGreater(brillante.getpixel((10, 10))[0],
                           normal.getpixel((10, 10))[0])


class PruebasIndicadoresInterfaz(unittest.TestCase):
    def test_resumen_de_avance_fotografico(self):
        datos = pd.DataFrame({
            "FotoTomada": ["Sí", "No", "Sí", ""],
        })
        self.assertEqual(resumen_fotografias(datos), (4, 2, 2, 50))

    def test_resumen_sin_alumnos(self):
        self.assertEqual(resumen_fotografias(None), (0, 0, 0, 0))


class PruebasArchivosAplicacion(unittest.TestCase):
    def test_inicializa_diseno_en_carpeta_escribible(self):
        import utilidades
        with tempfile.TemporaryDirectory() as carpeta:
            plantilla = os.path.join(carpeta, "plantilla.json")
            destino = os.path.join(carpeta, "datos", "diseno.json")
            with open(plantilla, "w", encoding="utf-8") as archivo:
                archivo.write('{"version": 1}')

            directorio_anterior = estado.DIRECTORIO_APLICACION
            ruta_anterior = estado.RUTA_DISENO_JSON
            resolver_anterior = utilidades.ruta_recurso
            try:
                estado.DIRECTORIO_APLICACION = os.path.dirname(destino)
                estado.RUTA_DISENO_JSON = destino
                utilidades.ruta_recurso = lambda nombre: plantilla
                inicializar_archivos_aplicacion()
                self.assertTrue(os.path.isfile(destino))
                with open(destino, "r", encoding="utf-8") as archivo:
                    self.assertEqual(archivo.read(), '{"version": 1}')
            finally:
                estado.DIRECTORIO_APLICACION = directorio_anterior
                estado.RUTA_DISENO_JSON = ruta_anterior
                utilidades.ruta_recurso = resolver_anterior


class PruebasArchivosDeTrabajo(unittest.TestCase):
    def test_agrega_sufijo_solo_al_archivo_original(self):
        ruta, es_trabajo = determinar_ruta_excel_trabajo("C:/datos/alumnos.xlsx")
        self.assertEqual(ruta, "C:/datos/alumnos_con_fotos.xlsx")
        self.assertFalse(es_trabajo)

    def test_convierte_original_xls_a_trabajo_xlsx(self):
        ruta, es_trabajo = determinar_ruta_excel_trabajo("C:/datos/alumnos.xls")
        self.assertEqual(ruta, "C:/datos/alumnos_con_fotos.xlsx")
        self.assertFalse(es_trabajo)

    def test_no_duplica_sufijo_en_archivo_de_trabajo(self):
        ruta, es_trabajo = determinar_ruta_excel_trabajo(
            "C:/datos/alumnos_con_fotos.xlsx")
        self.assertEqual(ruta, "C:/datos/alumnos_con_fotos.xlsx")
        self.assertTrue(es_trabajo)

    def test_reconoce_sufijo_sin_importar_mayusculas(self):
        ruta, es_trabajo = determinar_ruta_excel_trabajo(
            "C:/datos/ALUMNOS_CON_FOTOS.XLSX")
        self.assertEqual(ruta, "C:/datos/ALUMNOS_CON_FOTOS.XLSX")
        self.assertTrue(es_trabajo)


class PruebasCamposCalculados(unittest.TestCase):
    def test_reconstruye_apellidos_en_archivo_antiguo(self):
        fila = {"Apellido Paterno": "Pérez", "Apellido Materno": "López"}
        self.assertEqual(obtener_valor_campo(fila, "Apellidos"), "Pérez López")

    def test_construye_fila_manual_con_campos_calculados(self):
        fila = construir_fila_alumno({
            "Matricula": " 2026001 ",
            "Nombre": " Ana ",
            "Apellido Paterno": " Pérez ",
            "Apellido Materno": " López ",
            "CURP": " PELA080101MYNRPNA1 ",
            "Grupo": " 2A ",
        })
        self.assertEqual(fila["Matricula"], "2026001")
        self.assertEqual(fila["Apellidos"], "PÉREZ LÓPEZ")
        self.assertEqual(fila["NombreCompleto"], "ANA PÉREZ LÓPEZ")
        self.assertEqual(fila["FotoTomada"], "No")
        self.assertEqual(fila["RutaFoto"], "")

    def test_alta_manual_convierte_datos_a_mayusculas(self):
        fila = construir_fila_alumno({
            "Matricula": " ab-102 ",
            "Nombre": "  María josé ",
            "Apellido Paterno": "de la cruz",
            "Apellido Materno": "Núñez",
            "CURP": "nucm010101mxxrrra1",
            "Grupo": "2 a",
            "Turno": "Matutino",
        })
        self.assertEqual(fila["Matricula"], "AB-102")
        self.assertEqual(fila["Nombre"], "MARÍA JOSÉ")
        self.assertEqual(fila["Apellido Paterno"], "DE LA CRUZ")
        self.assertEqual(fila["Apellido Materno"], "NÚÑEZ")
        self.assertEqual(fila["CURP"], "NUCM010101MXXRRRA1")
        self.assertEqual(fila["Grupo"], "2 A")
        self.assertEqual(fila["Turno"], "MATUTINO")

    def test_excel_importado_convierte_columnas_requeridas(self):
        datos = {
            columna: ["dato mixto"] for columna in estado.COLUMNAS_REQUERIDAS
        }
        df = normalizar_datos_alumnos(pd.DataFrame(datos))
        for columna in estado.COLUMNAS_REQUERIDAS:
            self.assertEqual(df.at[0, columna], "DATO MIXTO")

    def test_respeta_apellidos_ya_calculados(self):
        fila = {
            "Apellidos": "Pérez López",
            "Apellido Paterno": "Otro",
            "Apellido Materno": "Nombre",
        }
        self.assertEqual(obtener_valor_campo(fila, "Apellidos"), "Pérez López")


if __name__ == "__main__":
    unittest.main()
