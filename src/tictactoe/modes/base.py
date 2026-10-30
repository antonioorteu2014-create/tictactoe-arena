"""Lo que tienen en común todos los modos de juego.

Cada modo es una clase que hereda de [`Mode`][tictactoe.modes.base.Mode] y
responde a las mismas preguntas que ``tictactoe.game`` responde para el clásico:
de quién es el turno, qué movimientos son legales, cómo queda el tablero tras un
movimiento y quién ha ganado. Así la web, los bots de los modos y las pruebas
tratan a todos los modos igual.

Las decisiones de ``tictactoe.game`` se mantienen en todos los modos:

* El **estado** es siempre un ``str``: inmutable, *hashable* (sirve de clave en
  la memoria de una búsqueda) y viaja como JSON sin conversión. Cada modo explica
  su formato.
* Un **movimiento** es siempre un ``int``: la casilla donde se coloca la ficha.
* Las funciones son **puras** y la frontera es **estricta**: un estado mal
  formado o un movimiento ilegal lanzan ``ValueError``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .. import game

State = str
"""Una posición de un modo. Cada modo documenta su formato."""

Move = int
"""Un movimiento: el número de la casilla donde se coloca la ficha."""

Mark = game.Mark
X = game.X
O = game.O  # noqa: E741
EMPTY = game.EMPTY


def rival(mark: Mark) -> Mark:
    """La ficha del otro jugador."""
    return O if mark == X else X


def line_of(cells: str, mark: Mark) -> tuple[int, int, int] | None:
    """La primera línea de un tablero de 3x3 (``cells``, 9 caracteres) llena de ``mark``."""
    for line in game.WINNING_LINES:
        if all(cells[i] == mark for i in line):
            return line
    return None


class Mode(ABC):
    """Un modo de juego del tres en raya.

    Los atributos de clase describen el modo para la web y la documentación; los
    métodos son sus reglas.
    """

    key: str
    """Identificador corto, sin espacios (``"clasico"``, ``"inverso"``...)."""

    name: str
    """Nombre para mostrar."""

    icon: str
    """Un emoji que identifica el modo."""

    summary: str
    """El modo en una frase."""

    rules: tuple[str, ...]
    """Las reglas, una por elemento, para mostrarlas como lista."""

    board_size: int = 3
    """Lado de la cuadrícula que se dibuja: 3 (3x3) o 9 (9x9)."""

    humans_only: bool = False
    """``True`` si el modo es solo para personas (no admite bots)."""

    # ------------------------------------------------------------------ reglas

    @abstractmethod
    def initial_state(self) -> State:
        """La posición inicial."""

    @abstractmethod
    def current_player(self, state: State) -> Mark:
        """A quién le toca mover en ``state``."""

    @abstractmethod
    def legal_moves(self, state: State) -> list[Move]:
        """Los movimientos legales, de menor a mayor; vacía si la partida terminó."""

    @abstractmethod
    def apply_move(self, state: State, move: Move) -> State:
        """La posición tras jugar ``move``. Lanza ``ValueError`` si es ilegal."""

    @abstractmethod
    def winner(self, state: State) -> Mark | None:
        """Quién ha ganado, o ``None`` si nadie (todavía o por empate)."""

    @abstractmethod
    def is_terminal(self, state: State) -> bool:
        """``True`` si la partida ha terminado."""

    @abstractmethod
    def cells(self, state: State) -> str:
        """Las casillas que se dibujan, por filas: ``board_size ** 2`` caracteres."""

    def is_draw(self, state: State) -> bool:
        """``True`` si la partida ha terminado sin ganador."""
        return self.is_terminal(state) and self.winner(state) is None

    def is_legal(self, state: State, move: object) -> bool:
        """``True`` si ``move`` es legal en ``state``.

        Un movimiento que no es un ``int`` (``True``, ``4.0``, ``"4"``) nunca es
        legal. Un estado mal formado sí lanza ``ValueError``.
        """
        return type(move) is int and move in self.legal_moves(state)

    def highlight(self, state: State) -> list[int]:
        """Las casillas que la web resalta (la línea ganadora, si la hay)."""
        return []

    def extra(self, state: State) -> dict[str, Any]:
        """Datos propios del modo que la web necesita para dibujarlo."""
        return {}

    # ----------------------------------------------------- ayuda para los bots

    def evaluate(self, state: State, mark: Mark) -> float:
        """Lo bien que va ``mark`` en una posición no terminada (positivo: bien).

        La usan los bots de búsqueda cuando no pueden mirar hasta el final de la
        partida. Por defecto vale 0: sin opinión.
        """
        return 0.0

    # ------------------------------------------------------- para la web (JSON)

    def info(self) -> dict[str, Any]:
        """La descripción del modo: lo que no cambia de una partida a otra."""
        return {
            "key": self.key,
            "name": self.name,
            "icon": self.icon,
            "summary": self.summary,
            "rules": list(self.rules),
            "board_size": self.board_size,
            "humans_only": self.humans_only,
        }

    def describe(self, state: State) -> dict[str, Any]:
        """Todo lo que la web necesita para dibujar ``state``."""
        terminal = self.is_terminal(state)
        return {
            "mode": self.key,
            "state": state,
            "cells": self.cells(state),
            "turn": None if terminal else self.current_player(state),
            "legal": self.legal_moves(state),
            "terminal": terminal,
            "winner": self.winner(state),
            "draw": self.is_draw(state),
            "highlight": self.highlight(state),
            **self.extra(state),
        }

    def __repr__(self) -> str:
        return f"<modo {self.key}>"
