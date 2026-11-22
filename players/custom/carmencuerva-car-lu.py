"""El jugador «car_lu»: nunca pierde y busca la partida en la que el rival tiene más
ocasiones de equivocarse, según lo que va aprendiendo de él.

Autoras: Carmen Cuerva y Lucía Argüello.

Cómo decide, en cuatro pasos:

1. **Negamax exacto.** El tres en raya es tan pequeño que se puede resolver entero.
   Con memoria, cada posición se calcula una sola vez y da su valor con juego
   perfecto (gano, empato o pierdo). Solo se consideran **jugadas seguras**: las que
   conservan ese valor. Por eso el bot **nunca pierde**.
2. **Hipótesis sobre el rival.** Cuatro maneras de jugar: al azar, oportunista (gana
   o bloquea y, si no, al azar), voraz (la misma puntuación que el bot ``voraz`` del
   proyecto: ganar, bloquear y casillas con más líneas abiertas) y perfecta.
3. **Bayes.** Al empezar, azar, voraz y perfecto pesan lo mismo y oportunista
   menos (``PRIOR_WEIGHTS``). Cada jugada del rival actualiza la
   probabilidad de cada hipótesis: ``P(tipo | jugada) ∝ P(jugada | tipo) · P(tipo)``.
4. **Expectimax con los puntos del torneo.** Entre las jugadas seguras, elige la que
   más puntos espera (ganar 1, empatar 0,5) contra la mezcla de hipótesis. Si dos
   empatan, remata antes y, si no, prefiere la que deja al rival más respuestas que
   pierden.

Lo que lo distingue: dentro del árbol, las creencias **también se actualizan** con
cada respuesta imaginada del rival, igual que lo harán en la partida real. Así el bot
planea sabiendo que, tras la próxima jugada del rival, lo conocerá mejor.
"""

from __future__ import annotations

import random
from functools import cache

from tictactoe import game
from tictactoe.bots.greedy import score_move
from tictactoe.player import Player

WIN, DRAW, LOSS = 1.0, 0.5, 0.0
"""Utilidad de cada final: los puntos que reparte el torneo."""

EPSILON = 0.05
"""Probabilidad de que el rival se salga de su modelo y juegue cualquier casilla libre.

Así ninguna hipótesis llega nunca a probabilidad 0 por una sola jugada rara."""

ROUND = 4
"""Decimales con los que se redondean las creencias para reutilizar cálculos."""


# --------------------------------------------------------------------------- #
# 1. Negamax exacto: valor de cada posición y jugadas seguras                 #
# --------------------------------------------------------------------------- #


@cache
def _value(state: game.State) -> int:
    """Valor con juego perfecto para quien mueve: 1 gana, 0 empata, -1 pierde."""
    if game.winner(state) is not None:
        return -1  # acaba de ganar el otro
    if game.EMPTY not in state:
        return 0
    return max(-_value(game.apply_move(state, m)) for m in game.legal_moves(state))


@cache
def _safe_moves(state: game.State) -> tuple[game.Move, ...]:
    """Las jugadas que conservan el valor de la posición para quien mueve."""
    best = _value(state)
    return tuple(m for m in game.legal_moves(state) if -_value(game.apply_move(state, m)) == best)


# --------------------------------------------------------------------------- #
# 2. Hipótesis sobre el rival: P(jugada | tipo)                               #
# --------------------------------------------------------------------------- #


def _other(mark: game.Mark) -> game.Mark:
    return game.O if mark == game.X else game.X


def _completes(state: game.State, cell: game.Move, mark: game.Mark) -> bool:
    return any(
        cell in line and all(state[c] == mark for c in line if c != cell)
        for line in game.WINNING_LINES
    )


def _uniform(moves) -> dict[game.Move, float]:
    return {m: 1 / len(moves) for m in moves}


def _random_model(state: game.State) -> dict[game.Move, float]:
    return _uniform(game.legal_moves(state))


def _opportunist_model(state: game.State) -> dict[game.Move, float]:
    me = game.current_player(state)
    moves = game.legal_moves(state)
    wins = [m for m in moves if _completes(state, m, me)]
    blocks = [m for m in moves if _completes(state, m, _other(me))]
    return _uniform(wins or blocks or moves)


def _greedy_model(state: game.State) -> dict[game.Move, float]:
    moves = game.legal_moves(state)
    scores = {m: score_move(state, m) for m in moves}
    best = max(scores.values())
    return _uniform([m for m in moves if scores[m] == best])


def _perfect_model(state: game.State) -> dict[game.Move, float]:
    return _uniform(_safe_moves(state))


MODELS = (_random_model, _opportunist_model, _greedy_model, _perfect_model)
NAMES = ("azar", "oportunista", "voraz", "perfecto")


@cache
def _likelihoods(state: game.State) -> tuple[dict[game.Move, float], ...]:
    """``P(jugada | tipo)`` para cada tipo, con el margen ``EPSILON``."""
    moves = game.legal_moves(state)
    result = []
    for model in MODELS:
        dist = model(state)
        result.append({m: (1 - EPSILON) * dist.get(m, 0.0) + EPSILON / len(moves) for m in moves})
    return tuple(result)


def _update(beliefs: tuple[float, ...], state: game.State, move: game.Move) -> tuple[float, ...]:
    """Bayes: las creencias tras ver al rival jugar ``move`` en ``state``."""
    likelihood = _likelihoods(state)
    posterior = [p * lk[move] for p, lk in zip(beliefs, likelihood, strict=True)]
    total = sum(posterior)
    return tuple(round(p / total, ROUND) for p in posterior)


PRIOR_WEIGHTS = (1.0, 0.1, 1.0, 1.0)
"""Creencias iniciales (azar, oportunista, voraz, perfecto), antes de normalizar.

Se eligieron con una evaluación exacta (todas las partidas posibles, con X y con O):
con creencias uniformes el bot abre con un lado y gana siempre al voraz con X, pero
saca 0,962 puntos por partida contra el azar; bajando el peso del oportunista sube a
0,971 sin perder nada contra el voraz (0,75: con O nadie puede ganarle)."""

PRIOR = tuple(round(w / sum(PRIOR_WEIGHTS), ROUND) for w in PRIOR_WEIGHTS)


# --------------------------------------------------------------------------- #
# 3 y 4. Expectimax con creencias que se actualizan dentro del árbol          #
# --------------------------------------------------------------------------- #


@cache
def _expected(state: game.State, me: game.Mark, beliefs: tuple[float, ...]) -> float:
    """Puntos esperados por ``me`` desde ``state`` jugando solo jugadas seguras."""
    winner = game.winner(state)
    if winner is not None:
        return WIN if winner == me else LOSS
    if game.EMPTY not in state:
        return DRAW
    if game.current_player(state) == me:
        return max(_expected(game.apply_move(state, m), me, beliefs) for m in _safe_moves(state))
    likelihood = _likelihoods(state)
    total = 0.0
    for reply in game.legal_moves(state):
        p = sum(b * lk[reply] for b, lk in zip(beliefs, likelihood, strict=True))
        after = game.apply_move(state, reply)
        total += p * _expected(after, me, _update(beliefs, state, reply))
    return total


def _losing_replies(state: game.State) -> int:
    """Cuántas respuestas del rival, desde ``state``, le dejan perdido."""
    if game.is_terminal(state):
        return 0
    return sum(1 for m in game.legal_moves(state) if _value(game.apply_move(state, m)) == 1)


# --------------------------------------------------------------------------- #
# El jugador                                                                  #
# --------------------------------------------------------------------------- #


class CarLu(Player):
    """Nunca pierde y, con Bayes, elige la jugada segura que más puntos espera."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._beliefs = PRIOR
        self._last: game.State | None = None  # el tablero tras nuestra última jugada

    @classmethod
    def create(cls, seed: int) -> CarLu:
        return cls(seed)

    @classmethod
    def get_name(cls) -> str:
        return "car_lu"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Carmen Cuerva", "Lucía Argüello"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Nunca pierde (negamax exacto). Deduce con Bayes si el rival juega al azar, "
            "como oportunista, como voraz o perfecto, y elige la jugada segura que más "
            "puntos espera, contando con que lo conocerá mejor tras cada respuesta."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🏴‍☠️"

    def choose_move(self, state: game.State) -> game.Move:
        me = game.current_player(state)
        self._observe(state)
        safe = _safe_moves(state)

        def rank(move: game.Move) -> tuple[float, bool, int]:
            after = game.apply_move(state, move)
            return (
                round(_expected(after, me, self._beliefs), 9),
                game.winner(after) == me,
                _losing_replies(after),
            )

        ranks = {m: rank(m) for m in safe}
        best = max(ranks.values())
        move = self._rng.choice([m for m in safe if ranks[m] == best])
        self._last = game.apply_move(state, move)
        return move

    def _observe(self, state: game.State) -> None:
        """Ver qué jugó el rival desde nuestra última jugada y actualizar las creencias."""
        before = self._last
        if before is None or _single_move(before, state) is None:
            # Partida nueva (o posición sin historia): se empieza de cero.
            self._beliefs = PRIOR
            before = game.INITIAL_STATE
        move = _single_move(before, state)
        if move is not None:
            self._beliefs = _update(self._beliefs, before, move)


def _single_move(before: game.State, after: game.State) -> game.Move | None:
    """La casilla que lleva de ``before`` a ``after`` en una jugada legal, o ``None``."""
    changed = [i for i in range(game.CELLS) if before[i] != after[i]]
    if len(changed) != 1 or not game.is_legal(before, changed[0]):
        return None
    return changed[0] if game.apply_move(before, changed[0]) == after else None
