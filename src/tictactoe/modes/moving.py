"""El modo **tres fichas**: cada jugador tiene solo tres fichas en el tablero.

Al poner la cuarta, desaparece la más antigua de ese jugador. Así el tablero
nunca se llena y la partida sigue hasta que alguien hace tres en raya. Para que
no pueda durar para siempre, si tras ``MAX_PLIES`` movimientos nadie ha ganado,
es empate.

**Formato del estado:** ``"<X>|<O>|<n>"``. ``<X>`` y ``<O>`` son las casillas
de cada jugador, de la más antigua a la más nueva (como mucho tres cifras), y
``<n>`` es el número de movimientos jugados. Por ejemplo, ``"40|8|3"``: X tiene
fichas en 4 (la más antigua) y 0, O tiene una en 8, y se han jugado 3
movimientos. Hace falta guardar el orden (para saber qué ficha desaparece) y el
número de movimientos (cuando los dos tienen tres fichas, el tablero ya no dice
de quién es el turno).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .. import game
from .base import EMPTY, Mark, Mode, O, State, X, line_of, rival

PIECES = 3
"""Fichas de cada jugador en el tablero."""

MAX_PLIES = 60
"""Movimientos tras los que, si nadie ha ganado, la partida es empate."""

_FORMAT = re.compile(r"([0-8]{0,3})\|([0-8]{0,3})\|(0|[1-9][0-9]*)")


def _parse(state: object) -> tuple[str, str, int]:
    """Separar y comprobar un estado. Lanza ``ValueError`` si no es válido."""
    if not isinstance(state, str):
        raise ValueError(f"el estado debe ser un str, no {type(state).__name__}")
    return _parse_text(state)


# Los bots consultan la misma posición muchas veces: se lee una vez y se recuerda.
@lru_cache(maxsize=1 << 16)
def _parse_text(state: str) -> tuple[str, str, int]:
    match = _FORMAT.fullmatch(state)
    if match is None:
        raise ValueError(f"estado mal formado: {state!r} (se espera '<X>|<O>|<movimientos>')")
    xs, os_, text = match.groups()
    plies = int(text)
    if len(set(xs + os_)) != len(xs) + len(os_):
        raise ValueError(f"estado imposible: {state!r} tiene una casilla repetida")
    expected_x = min(PIECES, (plies + 1) // 2)
    expected_o = min(PIECES, plies // 2)
    if (len(xs), len(os_)) != (expected_x, expected_o):
        raise ValueError(
            f"estado imposible: {state!r}: tras {plies} movimientos X debe tener "
            f"{expected_x} fichas y O {expected_o}"
        )
    if plies > MAX_PLIES:
        raise ValueError(f"estado imposible: {state!r} supera los {MAX_PLIES} movimientos")
    board = _board(xs, os_)
    x_line, o_line = line_of(board, X), line_of(board, O)
    if x_line and o_line:
        raise ValueError(f"estado imposible: {state!r}: los dos tienen tres en raya")
    # Solo puede tener línea quien acaba de mover (si no, la partida habría acabado antes).
    last = X if plies % 2 == 1 else O
    if (x_line and last != X) or (o_line and last != O):
        raise ValueError(f"estado imposible: {state!r}: la línea no es de quien acaba de mover")
    return xs, os_, plies


@lru_cache(maxsize=1 << 16)
def _board(xs: str, os_: str) -> str:
    board = [EMPTY] * game.CELLS
    for cell in xs:
        board[int(cell)] = X
    for cell in os_:
        board[int(cell)] = O
    return "".join(board)


class MovingMode(Mode):
    """Tres fichas por jugador: al poner la cuarta desaparece la más antigua."""

    key = "tres-fichas"
    name = "Tres fichas"
    icon = "♻️"
    summary = "Solo tres fichas: al poner la cuarta, se va la más antigua."
    rules = (
        "Con 3 fichas puestas, al poner otra se borra tu más antigua (sale marcada).",
        "Gana quien hace tres en raya.",
        f"{MAX_PLIES} movimientos sin ganador: empate.",
    )

    def initial_state(self) -> State:
        return "||0"

    def current_player(self, state: State) -> Mark:
        _, _, plies = _parse(state)
        return X if plies % 2 == 0 else O

    def cells(self, state: State) -> str:
        xs, os_, _ = _parse(state)
        return _board(xs, os_)

    def winner(self, state: State) -> Mark | None:
        board = self.cells(state)
        if line_of(board, X):
            return X
        if line_of(board, O):
            return O
        return None

    def is_terminal(self, state: State) -> bool:
        _, _, plies = _parse(state)
        return self.winner(state) is not None or plies >= MAX_PLIES

    def legal_moves(self, state: State) -> list[int]:
        if self.is_terminal(state):
            return []
        board = self.cells(state)
        return [i for i, cell in enumerate(board) if cell == EMPTY]

    def apply_move(self, state: State, move: int) -> State:
        if not self.is_legal(state, move):
            raise ValueError(f"movimiento ilegal {move!r} en {state!r}")
        xs, os_, plies = _parse(state)
        if plies % 2 == 0:
            xs = (xs + str(move))[-PIECES:]
        else:
            os_ = (os_ + str(move))[-PIECES:]
        return f"{xs}|{os_}|{plies + 1}"

    def vanishing(self, state: State) -> int | None:
        """La ficha que desaparecerá cuando mueva el jugador al que le toca, si hay."""
        if self.is_terminal(state):
            return None
        xs, os_, plies = _parse(state)
        mine = xs if plies % 2 == 0 else os_
        return int(mine[0]) if len(mine) == PIECES else None

    def highlight(self, state: State) -> list[int]:
        board = self.cells(state)
        return list(line_of(board, X) or line_of(board, O) or [])

    def extra(self, state: State) -> dict[str, Any]:
        _, _, plies = _parse(state)
        return {"vanishing": self.vanishing(state), "plies": plies, "max_plies": MAX_PLIES}

    def evaluate(self, state: State, mark: Mark) -> float:
        # Líneas con dos fichas propias y la tercera casilla libre: amenazas.
        board = self.cells(state)
        return _threats(board, mark) - _threats(board, rival(mark))


def _threats(board: str, mark: Mark) -> int:
    count = 0
    for line in game.WINNING_LINES:
        marks = [board[i] for i in line]
        if marks.count(mark) == 2 and marks.count(EMPTY) == 1:
            count += 1
    return count
