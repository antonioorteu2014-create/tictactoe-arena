"""Los modos de juego: el clásico y tres variantes del tres en raya.

Todos siguen la misma interfaz, [`Mode`][tictactoe.modes.base.Mode], así que la
web y los bots de los modos los tratan igual::

    from tictactoe.modes import get_mode

    mode = get_mode("tres-fichas")
    state = mode.initial_state()
    state = mode.apply_move(state, 4)
    mode.legal_moves(state)

| Modo | Clave | Idea |
|---|---|---|
| Clásico | ``clasico`` | El de siempre (las reglas de ``tictactoe.game``). |
| Inverso | ``inverso`` | Pierde quien hace tres en raya. |
| Tres fichas | ``tres-fichas`` | Solo tres fichas por jugador; la cuarta borra la más antigua. |
| Preguntas IA | ``preguntas`` | Para poner ficha hay que acertar una pregunta de la asignatura. |

El torneo y el API ``Player`` siguen siendo del modo clásico: los modos son para
jugar en la web.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .base import Mode
from .bots import ModeBot, RandomBot, SearchBot
from .classic import ClassicMode, MisereMode
from .moving import MovingMode
from .quiz import QuizMode

MODES: dict[str, Mode] = {
    mode.key: mode for mode in (ClassicMode(), MisereMode(), MovingMode(), QuizMode())
}
"""Los modos, por clave, en el orden en que se muestran."""


def get_mode(key: str) -> Mode:
    """El modo con esa clave. Lanza ``ValueError`` si no existe."""
    try:
        return MODES[key]
    except KeyError:
        raise ValueError(f"no existe el modo {key!r}") from None


@dataclass(frozen=True)
class ModeBotSpec:
    """Un bot de un modo, tal y como se ofrece en la web."""

    name: str
    icon: str
    description: str
    create: Callable[[int], ModeBot]
    """Crea el bot a partir de una semilla."""


# Los mismos tres bots del equipo, con las mismas ideas, aplicadas a las reglas de
# cada modo (el clásico usa directamente los de la plataforma).
_RANDOM = ModeBotSpec(
    "aleatorio",
    "🎲",
    "Elige al azar entre las casillas libres.",
    lambda seed: RandomBot(seed),
)
_GREEDY = ModeBotSpec(
    "voraz",
    "🦈",
    "Gana si puede y bloquea si debe; no mira más allá de la jugada siguiente.",
    lambda seed: SearchBot(seed, depth=2),
)


def _minimax(depth: int) -> ModeBotSpec:
    return ModeBotSpec(
        "minimax",
        "🧠",
        "Minimax con poda alfa-beta: imagina las jugadas futuras de los dos.",
        lambda seed: SearchBot(seed, depth=depth),
    )


MODE_BOTS: dict[str, tuple[ModeBotSpec, ...]] = {
    # Los del clásico son los bots de la plataforma (players/): ver tictactoe.registry.
    "clasico": (),
    # El inverso es pequeño: el minimax lo ve entero (9 jugadas) y juega perfecto.
    "inverso": (_RANDOM, _GREEDY, _minimax(9)),
    # En tres fichas la partida no tiene final fijo: el minimax mira 7 jugadas.
    "tres-fichas": (_RANDOM, _GREEDY, _minimax(7)),
    # Solo para personas.
    "preguntas": (),
}
"""Los bots de cada modo (salvo el clásico, que usa los de la plataforma)."""


__all__ = [
    "MODES",
    "MODE_BOTS",
    "ClassicMode",
    "MisereMode",
    "Mode",
    "ModeBot",
    "ModeBotSpec",
    "MovingMode",
    "QuizMode",
    "RandomBot",
    "SearchBot",
    "get_mode",
]
