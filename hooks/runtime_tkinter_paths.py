"""Configura las rutas Tcl/Tk dentro del ejecutable congelado."""

import os
import sys


if getattr(sys, "frozen", False):
    directorio_temporal = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    os.environ.setdefault(
        "TCL_LIBRARY", os.path.join(directorio_temporal, "tcl"))
    os.environ.setdefault(
        "TK_LIBRARY", os.path.join(directorio_temporal, "tk"))
