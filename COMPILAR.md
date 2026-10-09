# Compilar CamApp para Windows

## Preparación

Instala Python 3.12 e Inno Setup 6. Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Ejecutable e instalador

```powershell
.\build_installer.ps1
```

El script ejecuta las pruebas, genera `installer_artifacts\CamApp.exe` y
después crea:

```text
installer_artifacts\CamApp-Setup-1.0.0.exe
```

Los diseños usados sin un proyecto se guardan en `%LOCALAPPDATA%\CamApp`.
Los proyectos conservan sus diseños, fotografías, Excel y PDFs dentro de su
propia carpeta portable.
