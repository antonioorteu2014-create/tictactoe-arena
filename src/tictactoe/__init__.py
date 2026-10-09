"""Tic-Tac-Toe Arena — el tres en raya como librería de Python instalable.

En este paquete viven las reglas del juego, el API de jugadores para los bots y
el ejecutor de partidas, de modo que las pruebas, la web, el torneo y el bot de
cualquiera los importen igual::

    from tictactoe import game

    state = game.initial_state()        # "........."
    state = game.apply_move(state, 4)   # X en el centro: "....X...."

Contenido:

* ``tictactoe.game`` — las reglas, como funciones puras.
* ``tictactoe.player`` — ``Player``, la interfaz que implementa cada bot.
* ``tictactoe.match`` — ``play_game``, que juega una partida entre dos jugadores.
* ``tictactoe.registry`` — ``load_players``, que carga los bots admitidos en
  ``players/*/players.yaml``.
* ``tictactoe.cli`` — partida entre dos personas en la terminal (comando
  ``tictactoe-play``). No se importa aquí: el paquete es silencioso.
"""

from __future__ import annotations

from . import game, match, player, registry
from .match import GameResult, play_game
from .player import Player

__all__ = [
    "game",
    "match",
    "player",
    "registry",
    "GameResult",
    "Player",
    "play_game",
    "__version__",
]
__version__ = "0.1.0"
