"""Tic-Tac-Toe Arena — el tres en raya como librería de Python instalable.

En este paquete viven las reglas del juego, y vivirán el API de jugadores para
los bots y el torneo, de modo que las pruebas, la web y el bot de cualquiera lo
importen igual::

    from tictactoe import game

    state = game.initial_state()        # "........."
    state = game.apply_move(state, 4)   # X en el centro: "....X...."

Contenido:

* :mod:`tictactoe.game` — las reglas, como funciones puras.
* :mod:`tictactoe.cli` — partida entre dos personas en la terminal
  (comando ``tictactoe-play``). No se importa aquí: el paquete es silencioso.
"""

from __future__ import annotations

from . import game

__all__ = ["game", "__version__"]
__version__ = "0.1.0"
