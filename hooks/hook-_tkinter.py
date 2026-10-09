"""Incluye Tcl/Tk explícitamente cuando la autodetección de PyInstaller falla."""

import os
import sys


directorio_tcl = os.path.join(sys.base_prefix, "tcl")
tcl = os.path.join(directorio_tcl, "tcl8.6")
tk = os.path.join(directorio_tcl, "tk8.6")
modulos_tcl = os.path.join(directorio_tcl, "tcl8")

datas = []
if os.path.isdir(tcl):
    datas.append((tcl, "tcl"))
if os.path.isdir(tk):
    datas.append((tk, "tk"))
if os.path.isdir(modulos_tcl):
    datas.append((modulos_tcl, "tcl8"))
