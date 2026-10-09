# CamApp

Aplicación de escritorio para capturar fotografías de alumnos y generar credenciales escolares listas para imprimir.

CamApp está desarrollada para Windows con Python, Tkinter/ttkbootstrap, OpenCV, Pillow y pandas.

## Funciones principales

- Crear y abrir proyectos portables.
- Descargar y cargar la plantilla de alumnos en Excel.
- Agregar y editar alumnos manualmente.
- Normalizar los datos de alumnos en mayúsculas.
- Capturar fotografías desde la cámara web.
- Ajustar el recorte, zoom, desplazamiento y brillo de la fotografía.
- Diseñar el frente y reverso de la credencial mediante un editor visual.
- Cambiar posición, tamaño, fuente y color de los campos.
- Generar credenciales de todos los alumnos, por grupo o de un alumno seleccionado.
- Exportar solo frente, frente y reverso, o solo detrás.
- Generar archivos PDF identificados por matrícula y nombre del alumno.
- Crear respaldos automáticos del Excel.
- Validar datos, fotografías y diseños antes de generar credenciales.
- Generar un instalador para Windows.

## Requisitos

- Windows 10 u 11.
- Python 3.12 para ejecutar desde código fuente.
- Cámara web para capturar fotografías.

## Ejecutar desde código fuente

Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python main.py
```

También puedes ejecutar el proyecto desde VS Code usando el intérprete:

```text
venv\Scripts\python.exe
```

## Ejecutar pruebas

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Generar el ejecutable y el instalador

Es necesario tener Inno Setup 6 instalado. Después ejecuta:

```powershell
.\build_installer.ps1
```

Los archivos generados se guardan en:

```text
installer_artifacts\CamApp.exe
installer_artifacts\CamApp-Setup-1.0.0.exe
```

## Estructura de un proyecto creado

Cada proyecto puede conservar sus archivos de trabajo de forma portable:

```text
ProyectoCamApp/
├── alumnos.xlsx
├── fotos_alumnos/
├── fondos_credencial/
├── pdfs/
└── manifiesto.json
```

## Flujo recomendado

1. Crear o abrir un proyecto.
2. Descargar la plantilla Excel.
3. Capturar o cargar los datos de los alumnos.
4. Diseñar la credencial.
5. Tomar las fotografías.
6. Revisar la validación previa.
7. Generar las credenciales completas, por grupo o individualmente.
8. Revisar los PDF almacenados en la carpeta `pdfs`.

## Ramas de trabajo

- `main`: versión estable.
- `develop`: desarrollo y pruebas de nuevas funciones.

## Licencia

Proyecto privado para la gestión de credenciales escolares.
