"""El jugador «trampero-bayesiano»: nunca pierde y pone a cada rival la trampa que más le cuesta.

Combina las tres partes del tema de **razonamiento con incertidumbre**:

1. **Minimax (maximin).** Calcula el valor exacto de cada posición suponiendo que los dos
   juegan perfecto. Solo da por *seguras* las jugadas que conservan ese valor: jugando
   únicamente jugadas seguras, el bot **nunca pierde**, juegue como juegue el rival. Es
   aversión al riesgo: no arriesga ni una derrota por una victoria más probable.
2. **Árbol de decisión con MEU.** Entre las jugadas seguras, trata la jugada del rival como
   un **nodo de probabilidad** y elige la jugada que **maximiza la utilidad esperada**. La
   utilidad es la misma que reparte el torneo: ganar 1, empatar 0,5 y perder 0, así que el
   bot maximiza directamente los puntos que espera sacar.
3. **Inferencia bayesiana.** Las probabilidades de esos nodos salen de un modelo del rival.
   El bot no sabe contra quién juega, así que parte de cuatro hipótesis igual de probables
   (juega al azar, oportunista, voraz o perfecto) y, cada vez que ve una jugada del rival,
   actualiza la probabilidad de cada una con el teorema de Bayes::

       P(tipo | jugada) ∝ P(jugada | tipo) · P(tipo)

   La probabilidad de cada respuesta del rival es la mezcla de los cuatro modelos,
   ponderada por esas probabilidades.

Contra un rival perfecto solo se puede empatar (el tres en raya está resuelto: con juego
perfecto, empate). Los puntos se ganan contra los rivales que fallan, y para eso sirve
saber *cómo* fallan.

Decisiones comprobadas con experimentos (evaluación exacta, sumando todas las partidas
posibles contra cada tipo de rival, con X y con O):

* **Las creencias iniciales y** ``EPSILON`` se ajustaron con un **algoritmo evolutivo**
  (tema de metaheurísticas) que maximiza los puntos esperados contra azar, oportunista,
  voraz y perfecto. El óptimo es el que se usa: a priori uniforme y ``EPSILON = 0.03``.
  Creer de entrada solo en los rivales que ya están en el torneo daría +0,2 puntos allí,
  pero bajaría de 0,92 a 0,78 contra un oportunista: se descarta por sobreajuste.
* **Actualizar las creencias también dentro del árbol** (decisión bayesiana exacta) da
  exactamente el mismo resultado: la primera respuesta del rival ya lo delata casi
  siempre. Se usa la versión más sencilla.
* **Arriesgar** (MEU con cualquier jugada, no solo las seguras) tampoco suma nada: se
  mantiene la garantía de no perder nunca.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import cache

from tictactoe import game
from tictactoe.player import Player

WIN, DRAW, LOSS = 1.0, 0.5, 0.0
"""Utilidad de cada final, para el bot: los puntos que da el torneo."""

EPSILON = 0.03
"""Probabilidad de que un rival se salga de su modelo y juegue cualquier casilla.

Evita que una sola jugada inesperada descarte para siempre una hipótesis (su probabilidad
nunca llega a 0) y que el bot dé por imposible una respuesta del rival."""


# --------------------------------------------------------------------------- #
# Minimax: valor exacto de cada posición y jugadas seguras                    #
# --------------------------------------------------------------------------- #


@cache
def _value(state: game.State) -> int:
    """Valor minimax de ``state`` para quien mueve: 1 gana, 0 empata y -1 pierde."""
    if game.winner(state) is not None:
        return -1  # ha ganado quien acaba de mover
    if game.EMPTY not in state:
        return 0
    return max(-_value(game.apply_move(state, m)) for m in game.legal_moves(state))


@cache
def _safe_moves(state: game.State) -> tuple[game.Move, ...]:
    """Las jugadas que conservan el valor minimax de ``state`` para quien mueve."""
    best = _value(state)
    return tuple(m for m in game.legal_moves(state) if -_value(game.apply_move(state, m)) == best)


# --------------------------------------------------------------------------- #
# Modelos del rival: P(jugada | tipo de rival)                                #
# --------------------------------------------------------------------------- #


def _rival(mark: game.Mark) -> game.Mark:
    return game.O if mark == game.X else game.X


def _completes(state: game.State, cell: game.Move, mark: game.Mark) -> bool:
    """¿Poner ``mark`` en la casilla libre ``cell`` completa una línea de tres?"""
    return any(
        cell in line and all(state[c] == mark for c in line if c != cell)
        for line in game.WINNING_LINES
    )


def _uniform(moves: list[game.Move] | tuple[game.Move, ...]) -> dict[game.Move, float]:
    return {m: 1 / len(moves) for m in moves}


def _random_model(state: game.State) -> dict[game.Move, float]:
    """Juega cualquier casilla libre."""
    return _uniform(game.legal_moves(state))


def _opportunist_model(state: game.State) -> dict[game.Move, float]:
    """Gana si puede, bloquea si debe y, si no, juega al azar."""
    me = game.current_player(state)
    moves = game.legal_moves(state)
    wins = [m for m in moves if _completes(state, m, me)]
    blocks = [m for m in moves if _completes(state, m, _rival(me))]
    return _uniform(wins or blocks or moves)


def _greedy_model(state: game.State) -> dict[game.Move, float]:
    """Gana, bloquea y, si no, prefiere las casillas con más líneas abiertas (centro, esquinas)."""
    me = game.current_player(state)
    rival = _rival(me)

    def score(cell: game.Move) -> int:
        open_lines = sum(
            1
            for line in game.WINNING_LINES
            if cell in line and all(state[c] != rival for c in line)
        )
        return 100 * _completes(state, cell, me) + 10 * _completes(state, cell, rival) + open_lines

    moves = game.legal_moves(state)
    best = max(score(m) for m in moves)
    return _uniform([m for m in moves if score(m) == best])


def _perfect_model(state: game.State) -> dict[game.Move, float]:
    """Juega cualquiera de las jugadas óptimas según minimax."""
    return _uniform(_safe_moves(state))


MODELS = {
    "azar": _random_model,
    "oportunista": _opportunist_model,
    "voraz": _greedy_model,
    "perfecto": _perfect_model,
}
"""Las hipótesis sobre cómo juega el rival."""


@cache
def _likelihoods(state: game.State) -> dict[str, dict[game.Move, float]]:
    """``P(jugada | tipo)`` en ``state`` para cada tipo, con el margen ``EPSILON``."""
    moves = game.legal_moves(state)
    result = {}
    for name, model in MODELS.items():
        dist = model(state)
        result[name] = {m: (1 - EPSILON) * dist.get(m, 0.0) + EPSILON / len(moves) for m in moves}
    return result


# --------------------------------------------------------------------------- #
# El jugador                                                                  #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Decision:
    """Qué pensó el bot en su última jugada (para depurar y para explicarlo).

    Attributes:
        move: la casilla elegida.
        beliefs: probabilidad de cada tipo de rival en ese momento.
        expected: utilidad esperada de cada jugada segura (de 0 a 1).
    """

    move: game.Move
    beliefs: dict[str, float]
    expected: dict[game.Move, float]


class TramperoBayesiano(Player):
    """Minimax para no perder, MEU para elegir la trampa y Bayes para conocer al rival."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._beliefs = self._prior()
        self._last: game.State | None = None  # el tablero que dejamos tras nuestra jugada
        self.last_decision: Decision | None = None

    @classmethod
    def create(cls, seed: int) -> TramperoBayesiano:
        return cls(seed)

    @classmethod
    def get_name(cls) -> str:
        return "trampero-bayesiano"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Marcos Felgueroso"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Nunca pierde (minimax) y, entre las jugadas seguras, elige la que más puntos "
            "espera sacar (MEU), según lo que deduce con Bayes de cómo juega el rival."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🪤"

    def choose_move(self, state: game.State) -> game.Move:
        me = game.current_player(state)
        self._observe(state)

        mix = self._beliefs
        memo: dict[game.State, float] = {}
        expected = {
            m: self._expected(game.apply_move(state, m), me, mix, memo)
            for m in _safe_moves(state)
        }
        best = max(expected.values())
        candidates = [m for m, u in expected.items() if u >= best - 1e-9]
        # A igual utilidad esperada, rematar ya antes que alargar una victoria segura.
        finishing = [m for m in candidates if game.winner(game.apply_move(state, m)) == me]
        move = self._rng.choice(finishing or candidates)

        self._last = game.apply_move(state, move)
        self.last_decision = Decision(move, dict(mix), expected)
        return move

    # -- Bayes ------------------------------------------------------------ #

    @staticmethod
    def _prior() -> dict[str, float]:
        return {name: 1 / len(MODELS) for name in MODELS}

    def _observe(self, state: game.State) -> None:
        """Deducir la última jugada del rival y actualizar las creencias con Bayes."""
        if state == game.INITIAL_STATE:  # empezamos nosotros una partida nueva
            self._beliefs, self._last = self._prior(), None
            return
        before = self._last if self._last is not None else game.INITIAL_STATE
        move = _single_move(before, state)
        if move is None:  # no viene de nuestra jugada anterior: otra partida
            self._beliefs, before = self._prior(), game.INITIAL_STATE
            move = _single_move(before, state)
            if move is None:  # posición suelta sin historia: no hay nada que aprender
                return
        likelihood = _likelihoods(before)
        posterior = {name: p * likelihood[name][move] for name, p in self._beliefs.items()}
        total = sum(posterior.values())
        self._beliefs = {name: p / total for name, p in posterior.items()}

    # -- Árbol de decisión (MEU) -------------------------------------------- #

    def _expected(
        self,
        state: game.State,
        me: game.Mark,
        beliefs: dict[str, float],
        memo: dict[game.State, float],
    ) -> float:
        """Utilidad esperada de ``state`` para ``me`` si sigue jugando solo jugadas seguras.

        En los nodos de decisión (le toca a ``me``) toma el máximo; en los nodos de
        probabilidad (le toca al rival) toma la media ponderada por la mezcla de modelos.
        """
        if state in memo:
            return memo[state]
        winner = game.winner(state)
        if winner is not None:
            value = WIN if winner == me else LOSS
        elif game.EMPTY not in state:
            value = DRAW
        elif game.current_player(state) == me:
            value = max(
                self._expected(game.apply_move(state, m), me, beliefs, memo)
                for m in _safe_moves(state)
            )
        else:
            likelihood = _likelihoods(state)
            value = sum(
                sum(p * likelihood[name][reply] for name, p in beliefs.items())
                * self._expected(game.apply_move(state, reply), me, beliefs, memo)
                for reply in game.legal_moves(state)
            )
        memo[state] = value
        return value


def _single_move(before: game.State, after: game.State) -> game.Move | None:
    """La casilla que lleva de ``before`` a ``after`` en una jugada legal, o ``None``."""
    changed = [i for i in range(game.CELLS) if before[i] != after[i]]
    if len(changed) != 1 or not game.is_legal(before, changed[0]):
        return None
    return changed[0] if game.apply_move(before, changed[0]) == after else None
