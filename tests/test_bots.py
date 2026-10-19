"""Pruebas de los bots del equipo: el voraz y el minimax.

La prueba de contrato (``test_players.py``) ya comprueba que juegan movimientos
legales. Aquí se comprueba que juegan **bien**: lo que pide la guía en las tareas
3.1 y 3.2, y que el minimax juega perfecto en todas las posiciones del juego.
"""

from __future__ import annotations

import importlib
import sys
import time
from functools import cache
from pathlib import Path

import pytest

from tictactoe import game
from tictactoe.bots import evaluate, score_move
from tictactoe.match import play_game
from tictactoe.registry import load_players

ROOT = Path(__file__).resolve().parents[1]
PLAYERS = load_players()
Aleatorio = PLAYERS["aleatorio"].cls
Voraz = PLAYERS["voraz"].cls
Minimax = PLAYERS["minimax"].cls


def _results(cls_a, cls_b, games: int) -> dict[str, int]:
    """Victorias, empates y derrotas de ``cls_a`` contra ``cls_b``, en los dos sentidos."""
    tally = {"wins": 0, "draws": 0, "losses": 0}
    for seed in range(games):
        for a_is_x in (True, False):
            a, b = cls_a.create(seed), cls_b.create(seed + 10_000)
            result = play_game(a, b) if a_is_x else play_game(b, a)
            mark = game.X if a_is_x else game.O
            assert not result.is_forfeit, result.detail
            if result.winner is None:
                tally["draws"] += 1
            elif result.winner == mark:
                tally["wins"] += 1
            else:
                tally["losses"] += 1
    return tally


# --------------------------------------------------------------------------- #
# Un solucionador independiente, para comprobar al minimax                    #
# --------------------------------------------------------------------------- #


@cache
def _solve(state: str) -> int:
    """Resultado con juego perfecto para quien mueve: 1 gana, 0 empata, -1 pierde.

    Minimax sin poda, sin profundidad y sin trucos: lento pero evidente, para
    contrastar con el bot, que sí usa poda, memoria y desempates.
    """
    if game.winner(state) is not None:
        return -1  # ganó quien acaba de mover
    if game.is_draw(state):
        return 0
    return max(-_solve(game.apply_move(state, move)) for move in game.legal_moves(state))


def _perfect_moves(state: str) -> set[int]:
    best = _solve(state)
    return {m for m in game.legal_moves(state) if -_solve(game.apply_move(state, m)) == best}


def _non_terminal_positions() -> list[str]:
    seen, pending = {game.INITIAL_STATE}, [game.INITIAL_STATE]
    while pending:
        state = pending.pop()
        for move in game.legal_moves(state):
            child = game.apply_move(state, move)
            if child not in seen:
                seen.add(child)
                pending.append(child)
    return sorted(s for s in seen if not game.is_terminal(s))


# --------------------------------------------------------------------------- #
# 3.1 — El bot voraz                                                          #
# --------------------------------------------------------------------------- #


def test_greedy_takes_an_immediate_win():
    assert Voraz.create(0).choose_move("XX.OO....") == 2


def test_greedy_blocks_an_immediate_loss():
    assert Voraz.create(0).choose_move("XX..O....") == 2


def test_greedy_prefers_the_centre_on_an_empty_board():
    assert all(Voraz.create(seed).choose_move(game.INITIAL_STATE) == 4 for seed in range(5))


def test_greedy_scores_win_over_block_over_position():
    # X puede ganar en 2 y debe bloquear en 5: ganar puntúa más.
    assert score_move("XX.OO....", 2) > score_move("XX.OO....", 5)
    assert score_move("XX..O....", 2) > score_move("XX..O....", 8)  # bloquear > esquina


def test_greedy_beats_random_more_than_80_percent():
    # Resultado de la tarea 3.1: 100 partidas (50 con X y 50 con O).
    tally = _results(Voraz, Aleatorio, games=50)
    assert tally["wins"] > 80, tally


def test_evaluate_counts_open_lines():
    assert evaluate(game.INITIAL_STATE, game.X) == 0
    assert evaluate("....X....", game.X) == 4  # el centro toca 4 líneas
    assert evaluate("XX.OO....", game.X) == evaluate("XX.OO....", game.O) * -1


# --------------------------------------------------------------------------- #
# 3.2 — El bot minimax                                                        #
# --------------------------------------------------------------------------- #


def test_minimax_plays_a_perfect_move_in_every_position():
    # Las 4.520 posiciones en las que se puede mover, con X o con O: el bot elige
    # siempre una jugada perfecta (que no empeora el resultado: gana, empata o
    # pierde igual que con juego perfecto). El bot afina más que el solucionador:
    # entre jugadas que pierden todas, prefiere la que retrasa la derrota; por eso
    # sus «mejores» son un subconjunto de las perfectas, no siempre todas.
    bot = Minimax.create(0)
    positions = _non_terminal_positions()
    assert len(positions) == 4_520
    for state in positions:
        move = bot.choose_move(state)
        perfect = _perfect_moves(state)
        assert move in perfect, f"en {state!r} jugó {move}; perfectas: {sorted(perfect)}"
        assert set(bot.last_search.best_moves) <= perfect, state


def test_minimax_delays_a_loss_it_cannot_avoid():
    # En ".....O.XX" (le toca a O) pierde haga lo que haga: si bloquea en 6, X le
    # hace una doble amenaza. Aun así bloquea, para alargar la partida y obligar
    # al rival a encontrar la doble amenaza.
    assert _solve(".....O.XX") == -1
    bot = Minimax.create(0)
    assert bot.choose_move(".....O.XX") == 6
    assert bot.last_search.score < 0


@pytest.mark.parametrize("bot_is_x", [True, False], ids=["con X", "con O"])
def test_minimax_never_loses_whatever_the_opponent_does(bot_is_x):
    # Recorre todas las respuestas posibles del rival a cada jugada del bot.
    bot_mark = game.X if bot_is_x else game.O
    games = 0

    def explore(state: str) -> None:
        nonlocal games
        if game.is_terminal(state):
            games += 1
            assert game.winner(state) != (game.O if bot_is_x else game.X), state
            return
        if game.current_player(state) == bot_mark:
            explore(game.apply_move(state, Minimax.create(0).choose_move(state)))
        else:
            for move in game.legal_moves(state):
                explore(game.apply_move(state, move))

    explore(game.INITIAL_STATE)
    assert games > 0


def test_minimax_beats_greedy_and_never_loses():
    # Resultado de la tarea 3.2: el bot de búsqueda gana al avaricioso.
    tally = _results(Minimax, Voraz, games=50)
    assert tally["losses"] == 0, tally
    assert tally["wins"] > 0, tally


def test_minimax_answers_in_under_a_second_in_the_hardest_position():
    # El tablero vacío, sin nada en memoria, es la búsqueda más grande.
    game._check_board.cache_clear()
    game._first_line.cache_clear()
    bot = Minimax.create(0)
    started = time.perf_counter()
    bot.choose_move(game.INITIAL_STATE)
    assert time.perf_counter() - started < 1.0


def test_minimax_reports_its_reasoning():
    bot = Minimax.create(0)
    move = bot.choose_move("XX.OO....")
    info = bot.last_search
    assert info.move == move == 2
    assert info.score > 1_000  # victoria asegurada
    assert info.best_moves == (2,)
    assert info.nodes > 0 and info.seconds >= 0
    assert info.depth == 9


def test_minimax_with_limited_depth_still_plays_legal_moves():
    class Shallow(Minimax):
        @classmethod
        def create(cls, seed):
            return cls(seed, depth=1)

    bot = Shallow.create(0)
    assert bot.choose_move("XX.OO....") == 2  # una jugada basta para ver la victoria
    for state in _non_terminal_positions()[:300]:
        assert game.is_legal(state, bot.choose_move(state))


def test_minimax_respects_a_limited_depth_everywhere():
    # Con profundidad 1, ni siquiera el cálculo de trampas busca más allá: no
    # quedan en la memoria búsquedas con profundidad negativa (sin límite).
    bot = Minimax(0, depth=1)
    bot.choose_move(game.INITIAL_STATE)
    assert all(depth >= 0 for _, depth in bot._memory)
    deeper = Minimax(0, depth=2)
    deeper.choose_move(game.INITIAL_STATE)
    assert bot.last_search.nodes < deeper.last_search.nodes


@pytest.mark.parametrize("depth", [0, 10, -1])
def test_minimax_rejects_an_invalid_depth(depth):
    with pytest.raises(ValueError, match="depth"):
        Minimax(0, depth=depth)


# --------------------------------------------------------------------------- #
# 3.3 — La medición                                                           #
# --------------------------------------------------------------------------- #


def _benchmark_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        sys.modules.pop("benchmark", None)
        return importlib.import_module("benchmark")
    finally:
        sys.path.remove(str(ROOT / "scripts"))


def test_benchmark_is_reproducible(capsys):
    benchmark = _benchmark_module()
    tables = []
    for _ in range(2):
        assert benchmark.main(["--games", "5", "--seed", "3", "aleatorio", "voraz"]) == 0
        output = capsys.readouterr().out
        tables.append(output.split("| Bot | Jugadas medidas")[0])  # sin los tiempos
    assert tables[0] == tables[1]
    assert "| voraz | aleatorio |" in tables[0]


def test_benchmark_rejects_unknown_bots():
    with pytest.raises(SystemExit):
        _benchmark_module().main(["no-existe", "voraz"])
