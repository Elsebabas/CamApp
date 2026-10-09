# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datos = [('diseno_credencial.json', '.')]
datos += collect_data_files('ttkbootstrap')
imports_ocultos = collect_submodules('ttkbootstrap')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datos,
    hiddenimports=imports_ocultos,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/runtime_tkinter_paths.py'],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CamApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
    version='version_info.txt',
)
