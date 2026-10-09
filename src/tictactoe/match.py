"""El ejecutor de partidas: juega una partida completa entre dos jugadores.

[`play_game()`][tictactoe.match.play_game] es la frontera entre el código del
proyecto y el de un bot del que no sabemos nada. Por eso:

* **Valida cada movimiento antes de aplicarlo**, con
  [`is_legal()`][tictactoe.game.is_legal], la única definición de «movimiento
  legal» del proyecto.
* **Nunca se rompe por culpa de un jugador.** Si un jugador lanza una excepción
  (incluido un ``exit()`` olvidado), o devuelve un movimiento ilegal o algo que no
  es un ``int``, **pierde la partida** (abandono) y el resultado explica por qué.
  Es lo que pide el requisito 4.1: un bot que falla pierde, pero no rompe el
  torneo.
* **No sabe quién juega.** Recibe dos objetos con un método ``choose_move`` y nada
  más: ni nombres, ni niveles, ni torneos. Por eso la web y el torneo lo
  reutilizan sin modificarlo.
* **No necesita copiar el estado.** El estado es un ``str`` inmutable: un jugador
  no puede modificar el tablero que recibe.

Lo que todavía **no** controla es el tiempo: un bot que se queda pensando para
siempre bloquearía la partida. Tampoco puede protegerse de un bot escrito a
propósito para hacer daño dentro del mismo programa. Ambas cosas son del torneo
(paso 5 de la guía), que ejecutará cada partida en un proceso aparte y con un
plazo. Ctrl+C (``KeyboardInterrupt``) no se trata como abandono: sigue sirviendo
para detener el programa.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import game
from .player import Player

NORMAL = "normal"
"""La partida terminó por las reglas: tres en raya o tablero lleno."""

ILLEGAL_MOVE = "illegal_move"
"""Un jugador devolvió un movimiento ilegal (o algo que no es un movimiento) y perdió."""

ERROR = "error"
"""Un jugador lanzó una excepción al elegir su movimiento y perdió."""


@dataclass(frozen=True)
class GameResult:
    """El resultado de una partida.

    Attributes:
        winner: ``"X"``, ``"O"`` o ``None`` si hubo empate.
        moves: los movimientos jugados, en orden, desde la posición inicial.
        final_state: la posición en la que terminó la partida.
        ending: cómo terminó: [`NORMAL`][tictactoe.match.NORMAL],
            [`ILLEGAL_MOVE`][tictactoe.match.ILLEGAL_MOVE] o
            [`ERROR`][tictactoe.match.ERROR].
        detail: en un abandono, qué hizo mal el jugador que perdió; si no, ``""``.
    """

    winner: game.Mark | None
    moves: tuple[game.Move, ...]
    final_state: game.State
    ending: str = NORMAL
    detail: str = ""

    @property
    def loser(self) -> game.Mark | None:
        """El jugador que perdió, o ``None`` si hubo empate."""
        if self.winner is None:
            return None
        return game.O if self.winner == game.X else game.X

    @property
    def is_forfeit(self) -> bool:
        """``True`` si la partida terminó porque un jugador hizo algo no permitido."""
        return self.ending != NORMAL


def _describe(obj: object) -> str:
    """``repr(obj)`` sin riesgo: lo que devuelve un bot podría fallar incluso al mostrarlo."""
    try:
        return repr(obj)
    except Exception:
        return f"<{type(obj).__name__}>"


def play_game(
    player_x: Player,
    player_o: Player,
    state: game.State | None = None,
) -> GameResult:
    """Jugar una partida completa entre ``player_x`` y ``player_o``.

    Args:
        player_x: el jugador que mueve con X.
        player_o: el jugador que mueve con O.
        state: posición desde la que empezar. Por defecto, el tablero vacío. A
            quién le toca se deduce de la propia posición.

    Returns:
        El [`GameResult`][tictactoe.match.GameResult]: ganador, movimientos y forma en que terminó.

    Raises:
        ValueError: si ``state`` no es una posición válida. Es un error de quien
            llama, no de los jugadores, así que no se trata como abandono.
    """
    if state is None:
        state = game.initial_state()
    if not game.is_valid_state(state):
        raise ValueError(f"posición inicial no válida: {state!r}")

    players = {game.X: player_x, game.O: player_o}
    moves: list[game.Move] = []

    while not game.is_terminal(state):
        mark = game.current_player(state)
        rival = game.O if mark == game.X else game.X
        try:
            move = players[mark].choose_move(state)
        except (Exception, SystemExit, GeneratorExit) as exc:  # abandono, no caída
            return GameResult(
                winner=rival,
                moves=tuple(moves),
                final_state=state,
                ending=ERROR,
                detail=f"{mark} lanzó {type(exc).__name__}: {_describe(exc)}",
            )
        # is_legal solo acepta un int de Python exacto: un bool, un float o un
        # objeto que «se parece» a un int no llegan nunca a apply_move.
        if not game.is_legal(state, move):
            return GameResult(
                winner=rival,
                moves=tuple(moves),
                final_state=state,
                ending=ILLEGAL_MOVE,
                detail=f"{mark} devolvió el movimiento ilegal {_describe(move)}",
            )
        state = game.apply_move(state, move)
        moves.append(move)

    return GameResult(winner=game.winner(state), moves=tuple(moves), final_state=state)
