"""Reglas de validación previas a generar credenciales."""

import os

import estado
from utilidades import obtener_valor_campo, resolver_ruta_archivo


def _problema(nivel, tipo, detalle, idx=None, alumno="Diseño"):
    return {
        "nivel": nivel,
        "tipo": tipo,
        "detalle": detalle,
        "idx": idx,
        "alumno": alumno,
    }


def validar_pre_generacion(
        df, diseno, solo_grupo="Todos", lados_requeridos=None,
        reverso_comun=False, requerir_fotografia=True):
    """Devuelve problemas y los índices que pueden generarse con seguridad."""
    problemas = []
    lados = diseno.get("lados", {})
    campos_usados = set()
    error_global = False

    if lados_requeridos is None:
        lados_requeridos = ("frente", "reverso")

    for lado in lados_requeridos:
        datos_lado = lados.get(lado, {})
        fondo_guardado = datos_lado.get("fondo_path", "")
        fondo = resolver_ruta_archivo(fondo_guardado)
        campos = datos_lado.get("campos", {})
        if lado == "reverso" and reverso_comun:
            campos = {}

        if not fondo_guardado:
            problemas.append(_problema(
                "Aviso", "Fondo no configurado",
                f"El {lado} se generará con fondo blanco."))
        elif not os.path.isfile(fondo):
            problemas.append(_problema(
                "Error", "Fondo no encontrado",
                f"No se encontró el fondo del {lado}: {fondo_guardado}"))
            error_global = True

        if not campos and not (lado == "reverso" and reverso_comun):
            problemas.append(_problema(
                "Aviso", "Lado vacío",
                f"El {lado} no contiene fotografía ni campos de texto."))

        for nombre, datos in campos.items():
            if nombre != "FOTO":
                campos_usados.add(nombre)
            try:
                x = float(datos.get("x_frac", 0))
                y = float(datos.get("y_frac", 0))
                ancho = float(datos.get("ancho_frac", 0))
                alto = float(datos.get("alto_frac", 0))
                geometria_invalida = (
                    ancho <= 0 or alto <= 0 or x < 0 or y < 0
                    or x + ancho > 1.000001 or y + alto > 1.000001
                )
            except (TypeError, ValueError):
                geometria_invalida = True
            if geometria_invalida:
                problemas.append(_problema(
                    "Error", "Campo fuera del diseño",
                    f"El campo {nombre} del {lado} tiene posición o tamaño inválido."))
                error_global = True

    df_revisar = df
    if solo_grupo and solo_grupo != "Todos":
        df_revisar = df[df["Grupo"] == solo_grupo]

    indices_validos = []
    for idx, fila in df_revisar.iterrows():
        alumno = obtener_valor_campo(fila, "NombreCompleto") or f"Fila {idx + 2}"
        errores_alumno = False

        for campo in ("Matricula", "NombreCompleto", "Grupo"):
            if not obtener_valor_campo(fila, campo):
                problemas.append(_problema(
                    "Error", "Dato obligatorio vacío",
                    f"Falta el campo {campo}.", idx, alumno))
                errores_alumno = True

        if requerir_fotografia and fila.get("FotoTomada", "") != "Sí":
            problemas.append(_problema(
                "Error", "Fotografía pendiente",
                "El alumno todavía no tiene fotografía.", idx, alumno))
            errores_alumno = True
        elif requerir_fotografia:
            ruta_foto = resolver_ruta_archivo(fila.get("RutaFoto", ""))
            if not ruta_foto or not os.path.isfile(ruta_foto):
                problemas.append(_problema(
                    "Error", "Fotografía no encontrada",
                    "La fotografía registrada no existe en el disco.", idx, alumno))
                errores_alumno = True

        for campo in sorted(campos_usados):
            if not obtener_valor_campo(fila, campo):
                problemas.append(_problema(
                    "Aviso", "Campo del diseño vacío",
                    f"El diseño usa {campo}, pero el alumno no tiene ese dato.",
                    idx, alumno))

        if not errores_alumno and not error_global:
            indices_validos.append(idx)

    return {
        "problemas": problemas,
        "indices_validos": indices_validos,
        "total": len(df_revisar),
        "error_global": error_global,
    }
