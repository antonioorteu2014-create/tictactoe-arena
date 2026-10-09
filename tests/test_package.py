"""Pruebas de humo: el paquete está instalado y se importa correctamente.

Todavía no hay juego que probar. Esta prueba existe para que el mecanismo de
pruebas automáticas funcione desde el primer día: si el paquete deja de poder
instalarse o importarse, el pull request se pone en rojo.
"""

from __future__ import annotations

import tictactoe


def test_package_imports() -> None:
    assert tictactoe.__name__ == "tictactoe"


def test_package_exposes_version() -> None:
    assert isinstance(tictactoe.__version__, str)
    assert tictactoe.__version__ == "9.9.9"  # PRUEBA: test roto a propósito

    assert tictactoe.__version__.count(".") == 2  # formato MAYOR.MENOR.PARCHE
