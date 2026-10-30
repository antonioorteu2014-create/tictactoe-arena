"""Los modos que usan el tablero clásico: el **clásico** y el **inverso**.

Los dos comparten tablero, estado y movimientos con ``tictactoe.game``: el estado
es el mismo texto de 9 casillas. Solo cambia quién gana al hacer tres en raya.
"""

from __future__ import annotations

from typing import Any

from .. import game
from .base import Mark, Mode, State, rival


class ClassicMode(Mode):
    """El tres en raya de siempre, con las reglas de ``tictactoe.game``."""

    key = "clasico"
    name = "Clásico"
    icon = "⭕"
    summary = "Tres en línea y ganas."
    rules = (
        "Empieza X. Por turnos, una ficha en una casilla libre.",
        "Gana quien hace tres en raya.",
        "Tablero lleno sin línea: empate.",
    )

    def initial_state(self) -> State:
        return game.initial_state()

    def current_player(self, state: State) -> Mark:
        return game.current_player(state)

    def legal_moves(self, state: State) -> list[int]:
        return game.legal_moves(state)

    def apply_move(self, state: State, move: int) -> State:
        return game.apply_move(state, move)

    def winner(self, state: State) -> Mark | None:
        return game.winner(state)

    def is_terminal(self, state: State) -> bool:
        return game.is_terminal(state)

    def cells(self, state: State) -> str:
        game._check_state(state)
        return state

    def highlight(self, state: State) -> list[int]:
        return list(game.winning_line(state) or [])

    def evaluate(self, state: State, mark: Mark) -> float:
        return _open_lines(state, mark) - _open_lines(state, rival(mark))


class MisereMode(ClassicMode):
    """El tres en raya **inverso** (en inglés, *misère*): pierde quien hace tres en raya.

    El tablero y los movimientos son los del clásico, y la partida también
    termina con la primera línea o con el tablero lleno. Lo único que cambia es
    el resultado: la línea la pierde quien la hace. Por eso los estados válidos
    son exactamente los mismos que en el clásico.
    """

    key = "inverso"
    name = "Inverso"
    icon = "🔄"
    summary = "Al revés: quien hace tres en raya, pierde."
    rules = (
        "Como el clásico, pero hacer tres en raya te hace perder.",
        "Tablero lleno sin línea: empate.",
    )

    def winner(self, state: State) -> Mark | None:
        made_the_line = game.winner(state)
        return None if made_the_line is None else rival(made_the_line)

    def extra(self, state: State) -> dict[str, Any]:
        # La línea resaltada es la que ha hecho perder a su autor.
        return {"losing_line": bool(game.winning_line(state))}

    def evaluate(self, state: State, mark: Mark) -> float:
        # En el inverso, tener líneas casi hechas es un peligro, no una ventaja.
        return -super().evaluate(state, mark)


def _open_lines(state: State, mark: Mark) -> int:
    """Cuántas líneas tienen fichas de ``mark`` y ninguna del rival."""
    other = rival(mark)
    count = 0
    for line in game.WINNING_LINES:
        marks = [state[i] for i in line]
        if other not in marks and mark in marks:
            count += marks.count(mark)
    return count
