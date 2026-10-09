import os
import tempfile
import unittest

import estado
from historial import obtener_historial, registrar_impresion


class PruebasHistorial(unittest.TestCase):
    def test_registra_impresion_y_reposicion_en_csv(self):
        proyecto_anterior = estado.ruta_proyecto
        excel_anterior = estado.ruta_excel_trabajo
        with tempfile.TemporaryDirectory() as carpeta:
            estado.ruta_proyecto = carpeta
            estado.ruta_excel_trabajo = None
            fila = {"Matricula": "A-01", "NombreCompleto": "ANA LOPEZ", "Grupo": "2A"}
            registrar_impresion(fila, 3, "Solo frente", "salida.pdf", reposicion=True)
            registros = obtener_historial(indice=3)
            self.assertEqual(len(registros), 1)
            self.assertEqual(registros[0]["Matricula"], "A-01")
            self.assertEqual(registros[0]["Reposicion"], "Sí")
            self.assertTrue(os.path.isfile(os.path.join(carpeta, "historial_impresiones.csv")))
        estado.ruta_proyecto = proyecto_anterior
        estado.ruta_excel_trabajo = excel_anterior


if __name__ == "__main__":
    unittest.main()

