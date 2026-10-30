"""Los bots de los modos de juego.

Los bots del modo clásico son los de la plataforma (``players/``), escritos con
el API ``Player`` y enfrentados en el torneo. Los de este módulo sirven para
**cualquier modo**: reciben el modo y la posición y eligen un movimiento usando
solo las reglas del propio modo (``legal_moves``, ``apply_move``...). Son las
mismas ideas que los bots del equipo del modo clásico:

* [`RandomBot`][tictactoe.modes.bots.RandomBot] — juega al azar.
* [`SearchBot`][tictactoe.modes.bots.SearchBot] — minimax (negamax) con poda
  alfa-beta y memoria, hasta una profundidad. Si no llega al final de la
  partida, valora la posición con ``Mode.evaluate``. Con profundidad 9 en un
  tablero de 3x3 ve la partida entera y juega perfecto (el **minimax**). Con
  profundidad 2 solo ve si puede ganar ya o si el rival le gana en la siguiente:
  es la idea del **voraz** (ganar si puede, bloquear si debe).
"""

from __future__ import annotations

import math
import random

from .base import Mark, Mode, State, rival

WIN = 1000.0
"""Valor de una victoria segura en la búsqueda (más los movimientos que sobran)."""


class ModeBot:
    """Un bot para los modos de juego. Cada bot elige con ``choose_move``."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def choose_move(self, mode: Mode, state: State) -> int:  # pragma: no cover - interfaz
        raise NotImplementedError


class RandomBot(ModeBot):
    """Elige al azar entre los movimientos legales."""

    def choose_move(self, mode: Mode, state: State) -> int:
        return self.rng.choice(mode.legal_moves(state))


class SearchBot(ModeBot):
    """Minimax (negamax) con poda alfa-beta y memoria, hasta ``depth`` movimientos.

    Valora cada posición desde el punto de vista de quien mueve: ganar vale
    ``WIN`` más lo pronto que se gana (para preferir ganar antes y perder
    tarde); el empate vale 0; y una posición sin terminar a la que ya no llega
    la búsqueda vale lo que diga ``Mode.evaluate``. Entre jugadas igual de
    buenas elige al azar, para no jugar siempre la misma partida.
    """

    def __init__(self, seed: int = 0, depth: int = 9) -> None:
        super().__init__(seed)
        if depth < 1:
            raise ValueError(f"depth debe ser al menos 1, no {depth}")
        self.depth = depth
        self.nodes = 0

    def choose_move(self, mode: Mode, state: State) -> int:
        moves = mode.legal_moves(state)
        if not moves:
            raise ValueError("no hay movimientos: la partida ha terminado")
        self.nodes = 0
        memory: dict[tuple[State, int], tuple[float, int]] = {}
        # En la raíz, ventana completa para cada jugada: así se conoce el valor
        # exacto de todas y se puede elegir al azar entre las empatadas.
        scores = {
            move: -self._negamax(
                mode, mode.apply_move(state, move), self.depth - 1, -math.inf, math.inf, memory
            )
            for move in moves
        }
        best = max(scores.values())
        return self.rng.choice([m for m, s in scores.items() if s == best])

    def _negamax(
        self,
        mode: Mode,
        state: State,
        depth: int,
        alpha: float,
        beta: float,
        memory: dict[tuple[State, int], tuple[float, int]],
    ) -> float:
        """El valor de ``state`` para quien mueve, buscando ``depth`` jugadas.

        La memoria guarda, junto al valor, si es exacto o solo una cota (cuando
        la poda cortó la búsqueda), para no reutilizar una cota como si fuera
        exacta.
        """
        key = (state, depth)
        if key in memory:
            value, flag = memory[key]
            if flag == _EXACT:
                return value
            if flag == _LOWER:
                alpha = max(alpha, value)
            else:
                beta = min(beta, value)
            if alpha >= beta:
                return value
        self.nodes += 1
        original_alpha = alpha
        if mode.is_terminal(state):
            winner = mode.winner(state)
            if winner is None:
                value = 0.0
            else:
                value = (WIN + depth) if winner == mode_player(mode, state) else -(WIN + depth)
            memory[key] = (value, _EXACT)
            return value
        if depth <= 0:
            value = mode.evaluate(state, mode.current_player(state))
            memory[key] = (value, _EXACT)
            return value

        value = -math.inf
        for move in mode.legal_moves(state):
            child = -self._negamax(
                mode, mode.apply_move(state, move), depth - 1, -beta, -alpha, memory
            )
            value = max(value, child)
            alpha = max(alpha, value)
            if alpha >= beta:
                break  # el rival nunca dejaría llegar aquí: no hace falta mirar más
        if value <= original_alpha:
            flag = _UPPER
        elif value >= beta:
            flag = _LOWER
        else:
            flag = _EXACT
        memory[key] = (value, flag)
        return value


_EXACT, _LOWER, _UPPER = 0, 1, 2


def mode_player(mode: Mode, state: State) -> Mark:
    """A quién le «tocaría» en ``state`` aunque la partida haya terminado.

    En una posición terminada no hay turno, pero la búsqueda necesita saber
    desde el punto de vista de quién la valora: el siguiente que movería.
    """
    try:
        return mode.current_player(state)
    except ValueError:  # pragma: no cover - ningún modo lo lanza hoy
        return rival(mode.winner(state) or "X")
