"""El jugador «maximin-meu»: nunca pierde y, entre las jugadas seguras, elige la de
máxima utilidad esperada contra un rival que se puede equivocar.

Cómo decide, en tres pasos (todo son contenidos de la asignatura):

1. **Fuerza bruta + maximin.** El tres en raya solo tiene 5.478 posiciones
   posibles, así que se puede recorrer el árbol de juego completo. Con una memoria
   de posiciones ya calculadas, cada posición se evalúa una sola vez. El valor
   *maximin* de una jugada es el resultado que garantiza aunque el rival juegue
   perfecto: +1 (gano), 0 (empate) o -1 (pierdo). Solo se consideran **las
   jugadas seguras**, las de mejor valor maximin: así el bot **nunca pierde**.

2. **Modelo del rival (heurística greedy).** Un rival real se equivoca. Lo
   modelamos así: con probabilidad ``GREEDY_PROBABILITY`` juega como un jugador
   *greedy* (gana si puede, bloquea si debe y, si no, prefiere la casilla que más
   líneas abiertas tiene: centro, esquinas, lados); el resto de las veces juega
   una casilla libre al azar.

3. **MEU (máxima utilidad esperada).** Para cada jugada segura se calcula la
   utilidad esperada (+1 ganar, 0 empatar, -1 perder) recorriendo de nuevo el
   árbol completo: en los turnos del rival se promedian sus jugadas con las
   probabilidades del modelo; en los míos, se elige la jugada segura de mayor
   utilidad esperada. Se juega la jugada segura con la utilidad esperada más alta.

Contra un rival perfecto empata siempre (es lo mejor posible en el tres en raya);
contra uno que se equivoca, elige las jugadas que más ocasiones le dan de
equivocarse.
"""

from __future__ import annotations

import random

from tictactoe import game
from tictactoe.player import Player

GREEDY_PROBABILITY = 0.25
"""Probabilidad de que el rival modelado juegue como *greedy* (si no, al azar)."""

WIN, DRAW, LOSS = 1.0, 0.0, -1.0

PREFERENCE = (4, 0, 2, 6, 8, 1, 3, 5, 7)
"""Desempate final entre jugadas igual de buenas: centro, esquinas y lados."""


class MaximinMEU(Player):
    """Nunca pierde (maximin por fuerza bruta) y, entre las jugadas seguras, elige la de
    máxima utilidad esperada contra un rival modelado como greedy o aleatorio."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._maximin: dict[tuple[str, str], float] = {}
        self._expected: dict[tuple[str, str], float] = {}

    @classmethod
    def create(cls, seed: int) -> MaximinMEU:
        return cls(seed)

    @classmethod
    def get_name(cls) -> str:
        return "maximin-meu"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Cristina Colunga", "Mónica Anzola"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Nunca pierde (maximin con fuerza bruta) y, entre las jugadas seguras, elige la de "
            "máxima utilidad esperada (MEU) contra un rival que juega como greedy o al azar."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🎯"

    # ------------------------------------------------------------------ decision

    def choose_move(self, state: game.State) -> game.Move:
        me = game.current_player(state)
        safe = self._safe_moves(state, me)
        if len(safe) == 1:
            return safe[0]
        utility = {move: self._expected_value(game.apply_move(state, move), me) for move in safe}
        best = max(utility.values())
        candidates = [m for m in safe if abs(utility[m] - best) < 1e-9]
        ranked = sorted(candidates, key=PREFERENCE.index)
        top = [m for m in ranked if PREFERENCE.index(m) == PREFERENCE.index(ranked[0])]
        return top[0] if len(top) == 1 else self._rng.choice(top)

    def _safe_moves(self, state: game.State, me: str) -> list[game.Move]:
        """Moves with the best maximin value (the ones that never lose)."""
        values = {
            m: self._maximin_value(game.apply_move(state, m), me) for m in game.legal_moves(state)
        }
        best = max(values.values())
        return [m for m, v in values.items() if v == best]

    # ------------------------------------------------------------------ maximin (brute force)

    def _maximin_value(self, state: game.State, me: str) -> float:
        """Result for ``me`` if both players play perfectly from ``state``."""
        key = (state, me)
        if key in self._maximin:
            return self._maximin[key]
        if game.is_terminal(state):
            value = _utility(state, me)
        else:
            children = [
                self._maximin_value(game.apply_move(state, m), me) for m in game.legal_moves(state)
            ]
            value = max(children) if game.current_player(state) == me else min(children)
        self._maximin[key] = value
        return value

    # ------------------------------------------------------------------ expected utility (MEU)

    def _expected_value(self, state: game.State, me: str) -> float:
        """Expected utility for ``me`` if I keep playing safe-and-MEU moves and the
        rival follows the greedy/random model."""
        key = (state, me)
        if key in self._expected:
            return self._expected[key]
        if game.is_terminal(state):
            value = _utility(state, me)
        elif game.current_player(state) == me:
            value = max(
                self._expected_value(game.apply_move(state, m), me)
                for m in self._safe_moves(state, me)
            )
        else:
            value = sum(
                probability * self._expected_value(game.apply_move(state, move), me)
                for move, probability in _rival_model(state).items()
            )
        self._expected[key] = value
        return value


# ---------------------------------------------------------------------- helpers


def _utility(state: game.State, me: str) -> float:
    winner = game.winner(state)
    if winner is None:
        return DRAW
    return WIN if winner == me else LOSS


def _completes_line(state: game.State, cell: game.Move, mark: str) -> bool:
    """Would playing ``mark`` on the empty ``cell`` complete a line of three?"""
    return any(
        cell in line and all(state[c] == mark for c in line if c != cell)
        for line in game.WINNING_LINES
    )


def _open_lines(state: game.State, cell: game.Move, mark: str) -> int:
    """Lines through ``cell`` with no rival mark (still possible for ``mark``)."""
    rival = game.O if mark == game.X else game.X
    return sum(
        1 for line in game.WINNING_LINES if cell in line and all(state[c] != rival for c in line)
    )


def _greedy_moves(state: game.State) -> list[game.Move]:
    """What a greedy player would play: win, else block, else the most open lines."""
    mark = game.current_player(state)
    rival = game.O if mark == game.X else game.X
    moves = game.legal_moves(state)
    winning = [m for m in moves if _completes_line(state, m, mark)]
    if winning:
        return winning
    blocking = [m for m in moves if _completes_line(state, m, rival)]
    if blocking:
        return blocking
    best = max(_open_lines(state, m, mark) for m in moves)
    return [m for m in moves if _open_lines(state, m, mark) == best]


def _rival_model(state: game.State) -> dict[game.Move, float]:
    """Probability of each rival move: greedy with GREEDY_PROBABILITY, else uniform."""
    moves = game.legal_moves(state)
    greedy = _greedy_moves(state)
    probability = {m: (1 - GREEDY_PROBABILITY) / len(moves) for m in moves}
    for m in greedy:
        probability[m] += GREEDY_PROBABILITY / len(greedy)
    return probability
