"""El bot voraz: puntúa cada jugada posible con reglas sencillas y juega la mejor.

No mira hacia delante: solo se pregunta qué tal es *esta* jugada. Las reglas, de
más a menos importante:

1. **Ganar ya** si una jugada completa un tres en raya.
2. **Bloquear** si el rival completaría un tres en raya en esa casilla.
3. Si no hay nada urgente, preferir las casillas que **más líneas abiertas**
   tocan: el centro (4 líneas), luego las esquinas (3) y por último los lados (2).

A propósito, **no** tiene en cuenta las dobles amenazas (dos líneas a falta de una
ficha a la vez, de las que el rival solo puede bloquear una): verlas venir exige
mirar jugadas hacia delante, y eso es justo lo que hace el bot minimax. Es su
punto débil, y por eso el minimax le gana.

Los empates se deshacen al azar con un generador propio sembrado, así que con la
misma semilla el bot juega siempre igual.

La misma idea, puntuar lo bien colocado que está cada jugador, es la función
[`evaluate()`][tictactoe.bots.greedy.evaluate] que usa el bot minimax cuando no puede buscar hasta el final.
"""

from __future__ import annotations

import random

from .. import game
from ..player import Player

#: Pesos de cada regla. Cada nivel supera a todos los inferiores juntos, para que
#: una regla más importante decida siempre antes que cualquier combinación de las
#: de abajo (como mucho hay 4 líneas abiertas por casilla).
WIN = 10_000
BLOCK = 1_000
OPEN_LINE = 1


def _rival(mark: game.Mark) -> game.Mark:
    return game.O if mark == game.X else game.X


def _completes(state: game.State, cell: game.Move, mark: game.Mark) -> bool:
    """¿Poner ``mark`` en la casilla libre ``cell`` completa una línea de tres?"""
    return any(
        cell in line and all(state[c] == mark for c in line if c != cell)
        for line in game.WINNING_LINES
    )


def _open_lines(state: game.State, cell: game.Move, mark: game.Mark) -> int:
    """Cuántas líneas que pasan por ``cell`` siguen libres de fichas del rival."""
    rival = _rival(mark)
    return sum(
        1 for line in game.WINNING_LINES if cell in line and all(state[c] != rival for c in line)
    )


def score_move(state: game.State, cell: game.Move) -> int:
    """Puntuación voraz de jugar en ``cell`` en la posición ``state``.

    Cuanto más alta, mejor para el jugador al que le toca. Solo tiene sentido para
    una casilla libre de una partida sin terminar.
    """
    me = game.current_player(state)
    rival = _rival(me)
    score = 0
    if _completes(state, cell, me):
        score += WIN
    if _completes(state, cell, rival):
        score += BLOCK
    score += OPEN_LINE * _open_lines(state, cell, me)
    return score


def evaluate(state: game.State, mark: game.Mark) -> int:
    """Lo bien colocado que está ``mark`` en ``state``, sin buscar hacia delante.

    Suma, por cada línea que solo tiene fichas de ``mark``, 1 punto si tiene una
    ficha y 10 si tiene dos; y resta lo mismo por las líneas que solo tienen fichas
    del rival. Una línea con fichas de los dos ya no puede ganarla nadie y no cuenta.
    Es la evaluación que usa el bot minimax en las posiciones que no puede buscar
    hasta el final.
    """
    rival = _rival(mark)
    value = 0
    for line in game.WINNING_LINES:
        marks = [state[c] for c in line]
        mine, theirs = marks.count(mark), marks.count(rival)
        if theirs == 0 and mine:
            value += 10 if mine == 2 else 1
        elif mine == 0 and theirs:
            value -= 10 if theirs == 2 else 1
    return value


class GreedyBot(Player):
    """Juega la jugada con mejor [`score_move()`][tictactoe.bots.greedy.score_move]; empates al azar.

    Es una estrategia: le falta la identidad (nombre, autores, descripción), que la
    pone el archivo de ``players/builtin/`` que la admite.
    """

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    @classmethod
    def create(cls, seed: int) -> GreedyBot:
        return cls(seed)

    def choose_move(self, state: game.State) -> game.Move:
        scored = [(score_move(state, cell), cell) for cell in game.legal_moves(state)]
        best = max(score for score, _ in scored)
        return self._rng.choice([cell for score, cell in scored if score == best])
