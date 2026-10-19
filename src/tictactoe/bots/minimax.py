"""El bot minimax: busca entre las jugadas futuras con poda alfa-beta.

Cómo decide, en una frase: para cada jugada posible imagina la partida hacia
delante, suponiendo que **los dos juegan lo mejor posible**, y elige la jugada con
el mejor resultado garantizado.

Las piezas, tal como las pide la guía (tarea 3.2):

* **Valor de las posiciones terminales.** Ganar vale ``WIN_SCORE`` más el número
  de casillas que quedan libres (así prefiere ganar *antes*); perder, lo mismo en
  negativo (así, si va a perder, retrasa la derrota); el empate vale 0.
* **Evaluación de las no terminales.** Si llega al límite de profundidad sin que la
  partida termine, usa [`tictactoe.bots.greedy.evaluate()`][tictactoe.bots.greedy.evaluate], la misma idea que el
  bot voraz: líneas abiertas con una o dos fichas propias, menos las del rival.
* **Límite de profundidad.** ``depth`` es cuántos movimientos (de los dos
  jugadores) mira hacia delante. Por defecto 9: en el tres en raya caben todas las
  jugadas restantes, así que con 9 juega **perfecto**. Con menos juega peor, y
  sirve para medir qué aporta mirar más lejos.

Se implementa como *negamax*: el valor de una posición para quien mueve es el
opuesto del valor de la mejor respuesta del rival. Es el mismo minimax, escrito
con una sola función en lugar de dos (una que maximiza y otra que minimiza).

**Poda alfa-beta.** Mientras busca, recuerda lo mejor que ya tiene garantizado
cada jugador (``alpha`` y ``beta``). En cuanto una rama demuestra que el rival
nunca le dejaría llegar a ella, deja de mirarla. El resultado es idéntico al de
minimax sin poda, pero examinando muchas menos posiciones. Ayuda mirar primero las
jugadas que suelen ser buenas (centro, esquinas y lados, por ese orden).

**Memoria de posiciones (tabla de transposición).** Muchas posiciones se
alcanzan por caminos distintos (X en 0 y luego en 4 es lo mismo que X en 4 y
luego en 0). El bot guarda el valor de cada posición que ya ha calculado, junto
con si es exacto o solo un límite (por culpa de la poda), y no la vuelve a buscar.
La memoria dura toda la partida, así que a partir del segundo movimiento casi todo
está ya calculado.

**Desempate: poner trampas.** En la raíz calcula el valor exacto de *cada*
jugada. Si varias empatan en el mejor valor (por ejemplo, todas llevan al empate
contra un rival perfecto), elige la que **más probable hace que el rival se
equivoque**. Para estimarlo imagina primero un rival *corto de vista*, como un
novato o el bot voraz: si puede ganar en una jugada, gana; si tiene que bloquear,
bloquea; y si no, elige al azar. La trampa buena es la que ese rival no ve venir,
típicamente una jugada que prepara una doble amenaza. Si varias jugadas empatan
también en eso, prefiere la que más probable hace perder a un rival que juega
completamente al azar. Contra un rival perfecto da igual, pero contra uno que
puede fallar le da más ocasiones de hacerlo. Si aun así
empatan, decide la puntuación del bot voraz
([`score_move()`][tictactoe.bots.greedy.score_move]) y, por último, el azar con un
generador sembrado. Nunca deja de jugar perfecto: solo cambia *cuál* de las
jugadas perfectas elige.
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from .. import game
from ..player import Player
from .greedy import evaluate, score_move

WIN_SCORE = 1_000
"""Valor de una victoria (antes de sumar las casillas libres). Es mucho mayor que
cualquier valor de [`evaluate()`][tictactoe.bots.greedy.evaluate] (como mucho 80), para
que una victoria segura cuente siempre más que una buena posición."""

_EXACT, _LOWER, _UPPER = 0, 1, 2
"""Qué es un valor guardado en la memoria: exacto, o solo un mínimo o un máximo
del valor real (cuando la poda cortó la búsqueda antes de terminar)."""

MOVE_ORDER = (4, 0, 2, 6, 8, 1, 3, 5, 7)
"""Orden en que se prueban las jugadas: centro, esquinas y lados. Mirar antes las
jugadas buenas hace que la poda alfa-beta corte antes."""


@dataclass(frozen=True)
class SearchInfo:
    """Qué pensó el bot en su última jugada.

    Attributes:
        move: la casilla elegida.
        score: su valor. Mayor o igual que ``WIN_SCORE``: victoria asegurada;
            menor o igual que ``-WIN_SCORE``: derrota asegurada si el rival no
            falla; ``0`` con la profundidad completa: empate con juego perfecto.
        best_moves: todas las casillas que empataban en ese mejor valor (antes
            de desempatar con la puntuación del voraz).
        depth: la profundidad de búsqueda usada.
        nodes: cuántas posiciones examinó.
        seconds: cuánto tardó.
    """

    move: game.Move
    score: int
    best_moves: tuple[game.Move, ...]
    depth: int
    nodes: int
    seconds: float


class MinimaxBot(Player):
    """Minimax con poda alfa-beta y límite de profundidad.

    Es una estrategia: le falta la identidad (nombre, autores, descripción), que la
    pone el archivo de ``players/builtin/`` que la admite.

    Args:
        seed: semilla del generador que desempata entre jugadas igual de buenas.
        depth: cuántos movimientos mira hacia delante (de 1 a 9; 9 = perfecto).
    """

    def __init__(self, seed: int = 0, depth: int = 9) -> None:
        if not 1 <= depth <= game.CELLS:
            raise ValueError(f"depth debe estar entre 1 y {game.CELLS}, no {depth}")
        self._rng = random.Random(seed)
        self.depth = depth
        self.last_search: SearchInfo | None = None
        self._nodes = 0
        # (posición, profundidad) -> (valor, tipo de valor)
        self._memory: dict[tuple[game.State, int], tuple[float, int]] = {}

    @classmethod
    def create(cls, seed: int) -> MinimaxBot:
        return cls(seed)

    def choose_move(self, state: game.State) -> game.Move:
        started = time.perf_counter()
        self._nodes = 0
        moves = _ordered(game.legal_moves(state))

        # En la raíz, valor exacto de cada jugada (ventana completa, sin podar
        # entre ellas) para poder desempatar entre todas las mejores.
        values = {
            move: -self._negamax(game.apply_move(state, move), self.depth - 1, -math.inf, math.inf)
            for move in moves
        }
        best = max(values.values())
        best_moves = tuple(move for move in moves if values[move] == best)
        # Entre las jugadas perfectas, la que más trampas pone; después, la que
        # mejor puntúa el voraz; y por último, al azar.
        hints = {}
        for move in best_moves:
            after = game.apply_move(state, move)
            hints[move] = (
                self._trap_ratio(after, _shortsighted_replies),
                self._trap_ratio(after, game.legal_moves),
                score_move(state, move),
            )
        top = max(hints.values())
        move = self._rng.choice([m for m in best_moves if hints[m] == top])

        self.last_search = SearchInfo(
            move=move,
            score=int(best),
            best_moves=best_moves,
            depth=self.depth,
            nodes=self._nodes,
            seconds=time.perf_counter() - started,
        )
        return move

    def _trap_ratio(
        self, state: game.State, candidates: Callable[[game.State], list[game.Move]]
    ) -> float:
        """Probabilidad de que el rival pierda desde ``state`` si elige al azar entre
        ``candidates(state)``.

        ``state`` es la posición tras nuestra jugada: le toca al rival. Una
        respuesta «le lleva a perder» si, tras ella, nosotros tenemos la victoria
        asegurada dentro de la profundidad de búsqueda.
        """
        if game.is_terminal(state):
            return 0.0
        replies = candidates(state)
        losing = 0
        for reply in replies:
            after = game.apply_move(state, reply)
            # `after` es nuestro turno: su valor para nosotros.
            if self._negamax(after, self.depth - 2, -math.inf, math.inf) >= WIN_SCORE:
                losing += 1
        return losing / len(replies)

    def _negamax(self, state: game.State, depth: int, alpha: float, beta: float) -> float:
        """Valor de ``state`` para el jugador al que le toca mover."""
        self._nodes += 1
        winner = game.winner(state)
        if winner is not None:
            # Quien acaba de mover ha ganado: para quien mueve ahora es una derrota.
            # Cuantas más casillas libres, antes llegó y peor es.
            return -(WIN_SCORE + state.count(game.EMPTY))
        if game.EMPTY not in state:
            return 0  # empate
        if depth <= 0:  # <= y no ==: el cálculo de trampas puede pedir profundidad -1
            return evaluate(state, game.current_player(state))

        # Mirar más movimientos de los que quedan es lo mismo que mirar los que
        # quedan: así la memoria sirve igual en la jugada siguiente.
        depth = min(depth, state.count(game.EMPTY))
        remembered = self._memory.get((state, depth))
        if remembered is not None:
            value, kind = remembered
            if kind == _EXACT:
                return value
            if kind == _LOWER:
                alpha = max(alpha, value)
            else:
                beta = min(beta, value)
            if alpha >= beta:
                return value

        original_alpha = alpha
        best = -math.inf
        for move in _ordered(game.legal_moves(state)):
            value = -self._negamax(game.apply_move(state, move), depth - 1, -beta, -alpha)
            best = max(best, value)
            alpha = max(alpha, value)
            if alpha >= beta:
                break  # poda: el rival nunca dejaría llegar a esta rama

        if best <= original_alpha:
            kind = _UPPER  # todo fue peor que lo ya garantizado: solo es un máximo
        elif best >= beta:
            kind = _LOWER  # se podó: el valor real puede ser aún mayor
        else:
            kind = _EXACT
        self._memory[(state, depth)] = (best, kind)
        return best


def _completes(state: game.State, cell: game.Move, mark: game.Mark) -> bool:
    """¿Poner ``mark`` en la casilla libre ``cell`` completa una línea de tres?"""
    return any(
        cell in line and all(state[c] == mark for c in line if c != cell)
        for line in game.WINNING_LINES
    )


def _shortsighted_replies(state: game.State) -> list[game.Move]:
    """Las jugadas que consideraría un rival corto de vista en ``state``.

    Si puede ganar ya, solo esas; si no, si tiene que bloquear, solo los
    bloqueos; si no, todas.
    """
    me = game.current_player(state)
    rival = game.O if me == game.X else game.X
    moves = game.legal_moves(state)
    winning = [m for m in moves if _completes(state, m, me)]
    if winning:
        return winning
    blocking = [m for m in moves if _completes(state, m, rival)]
    return blocking or moves


def _ordered(moves: list[game.Move]) -> list[game.Move]:
    """``moves`` en el orden de [`MOVE_ORDER`][tictactoe.bots.minimax.MOVE_ORDER]."""
    return sorted(moves, key=MOVE_ORDER.index)
