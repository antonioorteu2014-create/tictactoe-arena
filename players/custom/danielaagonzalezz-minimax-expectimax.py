"""El jugador «minimax-expectimax»: nunca pierde y aprovecha los fallos del rival.

Idea en dos capas:

1. **Minimax (con poda por caché).** Calcula el valor exacto de cada posición. El bot solo
   juega jugadas *seguras*, las que conservan ese valor, así que **nunca pierde**: contra
   un rival perfecto, empata.
2. **Expectimax contra un modelo de humano.** Entre las jugadas seguras elige la que da
   más puntos esperados (ganar 1, empatar 0,5) suponiendo que el rival juega como una
   persona: casi siempre ve una victoria inmediata y casi siempre tapa una amenaza
   simple, pero a menudo no ve venir una **doble amenaza** (un *tenedor*) y, cuando no
   hay nada urgente, prefiere el centro y las esquinas sin calcular más allá.

Así el bot no se limita a empatar: monta las posiciones en las que es más fácil que el
rival caiga en un tenedor (por ejemplo, abrir en esquina con X) y, si cae, lo remata.
"""

from __future__ import annotations

import random
from functools import cache

from tictactoe import game
from tictactoe.player import Player

WIN, DRAW, LOSS = 1.0, 0.5, 0.0
"""Utilidad de cada final para el bot: los puntos que reparte el torneo."""

SEES_WIN = 0.95
"""Probabilidad de que el humano vea que puede ganar en una jugada."""

SEES_BLOCK = 0.9
"""Probabilidad de que el humano tape una amenaza (si hay una sola)."""

TASTE_POWER = 2
"""Cuánto prefiere el humano, sin nada urgente, las casillas con más líneas abiertas.

El peso de una casilla es ``(1 + líneas abiertas) ** TASTE_POWER``: centro > esquinas >
lados en un tablero vacío, y las casillas que ya no sirven para nada casi no se juegan."""

LOOKAHEAD = 0.35
"""Probabilidad de que el humano, sin nada urgente, juegue una jugada óptima (minimax)."""


# --------------------------------------------------------------------------- #
# Minimax: valor exacto y jugadas seguras                                     #
# --------------------------------------------------------------------------- #


@cache
def _value(state: game.State) -> int:
    """Valor minimax de ``state`` para quien mueve: 1 gana, 0 empata, -1 pierde."""
    if game.winner(state) is not None:
        return -1  # acaba de ganar el que movió antes
    if game.EMPTY not in state:
        return 0
    return max(-_value(game.apply_move(state, m)) for m in game.legal_moves(state))


@cache
def _safe_moves(state: game.State) -> tuple[game.Move, ...]:
    """Jugadas que conservan el valor minimax para quien mueve."""
    best = _value(state)
    return tuple(m for m in game.legal_moves(state) if -_value(game.apply_move(state, m)) == best)


# --------------------------------------------------------------------------- #
# Modelo del humano: P(jugada | posición)                                     #
# --------------------------------------------------------------------------- #


def _other(mark: str) -> str:
    return game.O if mark == game.X else game.X


def _completes(state: game.State, cell: game.Move, mark: str) -> bool:
    """¿Poner ``mark`` en la casilla libre ``cell`` completa una línea?"""
    return any(
        cell in line and all(state[c] == mark for c in line if c != cell)
        for line in game.WINNING_LINES
    )


def _weighted(
    state: game.State, moves: list[game.Move] | tuple[game.Move, ...]
) -> dict[game.Move, float]:
    """Repartir la probabilidad entre ``moves`` según las líneas que abre cada una."""
    rival = _other(game.current_player(state))
    taste = {
        m: (
            1
            + sum(
                1
                for line in game.WINNING_LINES
                if m in line and all(state[c] != rival for c in line)
            )
        )
        ** TASTE_POWER
        for m in moves
    }
    total = sum(taste.values())
    return {m: t / total for m, t in taste.items()}


def _add(dist: dict[game.Move, float], part: dict[game.Move, float], weight: float) -> None:
    for move, p in part.items():
        dist[move] = dist.get(move, 0.0) + weight * p


@cache
def _human(state: game.State) -> dict[game.Move, float]:
    """Distribución de la jugada de un humano razonable en ``state``."""
    me = game.current_player(state)
    moves = game.legal_moves(state)
    wins = [m for m in moves if _completes(state, m, me)]
    blocks = [m for m in moves if _completes(state, m, _other(me))]
    calm = _weighted(state, moves)  # jugar «a ojo», sin calcular

    dist: dict[game.Move, float] = {}
    if wins:
        _add(dist, _weighted(state, wins), SEES_WIN)
        _add(dist, calm, 1 - SEES_WIN)
    elif len(blocks) == 1:
        _add(dist, {blocks[0]: 1.0}, SEES_BLOCK)
        _add(dist, calm, 1 - SEES_BLOCK)
    elif blocks:  # le han hecho un tenedor: tapa una al azar, pierde igual
        _add(dist, _weighted(state, blocks), SEES_BLOCK)
        _add(dist, calm, 1 - SEES_BLOCK)
    else:
        _add(dist, _weighted(state, _safe_moves(state)), LOOKAHEAD)
        _add(dist, calm, 1 - LOOKAHEAD)
    return dist


# --------------------------------------------------------------------------- #
# El jugador                                                                  #
# --------------------------------------------------------------------------- #


@cache
def _expected(state: game.State, me: str) -> float:
    """Puntos esperados de ``state`` para ``me`` si solo juega jugadas seguras."""
    winner = game.winner(state)
    if winner is not None:
        return WIN if winner == me else LOSS
    if game.EMPTY not in state:
        return DRAW
    if game.current_player(state) == me:
        return max(_expected(game.apply_move(state, m), me) for m in _safe_moves(state))
    return sum(p * _expected(game.apply_move(state, m), me) for m, p in _human(state).items())


class MinimaxExpectimax(Player):
    """Minimax para no perder nunca y expectimax contra un modelo de humano para ganar."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    @classmethod
    def create(cls, seed: int) -> MinimaxExpectimax:
        return cls(seed)

    @classmethod
    def get_name(cls) -> str:
        return "minimax-expectimax"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Daniela González", "Marcos González"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Nunca pierde (minimax) y, entre las jugadas seguras, elige la que más puntos "
            "espera, buscando que el rival caiga en una doble amenaza."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🎯"

    def choose_move(self, state: game.State) -> game.Move:
        me = game.current_player(state)
        scores = {m: _expected(game.apply_move(state, m), me) for m in _safe_moves(state)}
        best = max(scores.values())
        candidates = [m for m, s in scores.items() if s >= best - 1e-9]
        # A igualdad de puntos, rematar ya antes que alargar la partida.
        finishing = [m for m in candidates if game.winner(game.apply_move(state, m)) == me]
        return self._rng.choice(finishing or candidates)
