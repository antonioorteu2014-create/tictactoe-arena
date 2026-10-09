"""El jugador ``aleatorio``: el bot de referencia.

Elige al azar entre los movimientos legales. No tiene ninguna estrategia, y por
eso sirve de vara de medir: cualquier bot que se precie tiene que ganarle.

Está escrito como lo escribiría alguien de fuera del equipo: solo importa el API
público (:mod:`tictactoe.game` y :class:`tictactoe.player.Player`). Sirve también
de plantilla para el tutorial «Subir un bot».
"""

from __future__ import annotations

import random

from tictactoe import game
from tictactoe.player import Player


class Aleatorio(Player):
    """Juega en una casilla libre cualquiera, elegida al azar."""

    def __init__(self, seed: int = 0) -> None:
        # Un generador propio, sembrado: con la misma semilla, las mismas jugadas.
        # No se usa el `random` global para no depender de lo que hagan otros.
        self._rng = random.Random(seed)

    @classmethod
    def create(cls, seed: int) -> Aleatorio:
        return cls(seed)

    @classmethod
    def get_name(cls) -> str:
        return "aleatorio"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Antonio Orteu", "Álvaro Domingo", "María Sanz"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Elige al azar entre las casillas libres. No tiene estrategia: es la "
            "referencia que cualquier otro bot debe superar."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🎲"

    def choose_move(self, state: game.State) -> game.Move:
        return self._rng.choice(game.legal_moves(state))
