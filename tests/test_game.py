"""Pruebas de las reglas del juego (``tictactoe.game``)."""

from __future__ import annotations

from functools import cache

import pytest

from tictactoe import game
from tictactoe.game import EMPTY, INITIAL_STATE, WINNING_LINES, O, X

# --------------------------------------------------------------------------- #
# Posición inicial y turno                                                    #
# --------------------------------------------------------------------------- #


def test_initial_state_is_empty_board():
    assert game.initial_state() == "........."
    assert game.initial_state() == INITIAL_STATE


def test_x_always_starts():
    assert game.current_player(INITIAL_STATE) == X


def test_turn_alternates():
    state = INITIAL_STATE
    expected = [X, O, X, O, X]
    for move, player in zip([0, 4, 8, 2, 6], expected, strict=True):
        assert game.current_player(state) == player
        state = game.apply_move(state, move)


# --------------------------------------------------------------------------- #
# Movimientos legales                                                         #
# --------------------------------------------------------------------------- #


def test_legal_moves_on_empty_board_are_all_cells():
    assert game.legal_moves(INITIAL_STATE) == list(range(9))


def test_legal_moves_computed_by_hand():
    #  X | . | O
    #  . | X | .
    #  . | . | O
    assert game.legal_moves("X.O.X...O") == [1, 3, 5, 6, 7]


def test_single_legal_move_left():
    #  X | O | X
    #  X | O | O
    #  O | X | .
    assert game.legal_moves("XOXXOOOX.") == [8]


def test_no_legal_moves_after_a_win_even_with_empty_cells():
    assert game.legal_moves("XXXOO....") == []


def test_no_legal_moves_on_full_board():
    assert game.legal_moves("XOXXOOOXX") == []


@pytest.mark.parametrize("move", [0, 8])
def test_corner_cells_are_legal(move):
    assert game.is_legal(INITIAL_STATE, move)


@pytest.mark.parametrize(
    "move",
    [
        -1,  # fuera del tablero, por debajo
        9,  # fuera del tablero, por encima
        True,  # bool es subclase de int: no debe colar como la casilla 1
        False,
        4.0,  # float, aunque valga lo mismo que una casilla
        "4",  # str
        None,
        [4],
        (4,),
    ],
)
def test_malformed_moves_are_illegal_and_do_not_raise(move):
    assert not game.is_legal(INITIAL_STATE, move)


def test_occupied_cell_is_illegal():
    assert not game.is_legal("....X....", 4)


def test_move_after_game_over_is_illegal():
    assert not game.is_legal("XXXOO....", 5)


# --------------------------------------------------------------------------- #
# Aplicar un movimiento                                                       #
# --------------------------------------------------------------------------- #


def test_apply_move_places_mark_of_current_player():
    after_x = game.apply_move(INITIAL_STATE, 4)
    assert after_x == "....X...."
    after_o = game.apply_move(after_x, 0)
    assert after_o == "O...X...."


def test_apply_move_does_not_change_the_original_state():
    state = "X.O.X...O"
    copy = str(state)
    new = game.apply_move(state, 1)
    assert state == copy
    assert new != state


@pytest.mark.parametrize(
    "state, move",
    [
        ("....X....", 4),  # casilla ocupada
        (INITIAL_STATE, 9),  # fuera del tablero
        (INITIAL_STATE, True),  # no es un número de casilla
        ("XXXOO....", 5),  # la partida ya terminó
        ("XOXXOOOXX", 0),  # tablero lleno
    ],
)
def test_apply_illegal_move_raises(state, move):
    with pytest.raises(ValueError, match="ilegal"):
        game.apply_move(state, move)


# --------------------------------------------------------------------------- #
# Final de la partida                                                         #
# --------------------------------------------------------------------------- #


def _won_with(player: str, line: tuple[int, int, int]) -> str:
    """Una posición real de partida donde ``player`` ganó con ``line``, y solo
    con ella."""
    for state in sorted(_reachable_states()):
        marked = {cell for cell, mark in enumerate(state) if mark == player}
        if set(line) <= marked and game.winner(state) == player:
            other_lines = [
                other for other in WINNING_LINES if other != line and set(other) <= marked
            ]
            if not other_lines:
                return state
    raise AssertionError(f"no reachable state where {player} wins only with {line}")


@pytest.mark.parametrize("line", WINNING_LINES)
@pytest.mark.parametrize("player", [X, O])
def test_every_line_wins(player, line):
    state = _won_with(player, line)
    assert game.winner(state) == player
    assert game.winning_line(state) == line
    assert game.is_terminal(state)
    assert not game.is_draw(state)


def test_game_in_progress_has_no_winner_and_is_not_terminal():
    state = "X.O.X...."
    assert game.winner(state) is None
    assert not game.is_terminal(state)
    assert not game.is_draw(state)
    assert game.winning_line(state) is None


def test_full_board_without_line_is_a_draw():
    #  X | O | X
    #  X | O | O
    #  O | X | X
    state = "XOXXOOOXX"
    assert game.winner(state) is None
    assert game.is_terminal(state)
    assert game.is_draw(state)


def test_win_on_the_last_cell_is_a_win_not_a_draw():
    #  X | O | X        X | O | X
    #  O | X | O   ->   O | X | O
    #  O | X | .        O | X | X   (X completa la diagonal 0-4-8)
    state = game.apply_move("XOXOXOOX.", 8)
    assert EMPTY not in state
    assert game.winner(state) == X
    assert not game.is_draw(state)


def test_double_line_with_one_move_is_a_valid_win():
    #  X | X | .        X | X | X
    #  O | X | O   ->   O | X | O   (X completa la fila 0-1-2 y la diagonal 2-4-6)
    #  X | O | O        X | O | O
    state = game.apply_move("XX.OXOXOO", 2)
    assert game.is_valid_state(state)
    assert game.winner(state) == X
    assert game.winning_line(state) == (0, 1, 2)


def test_scripted_game_ends_with_expected_winner():
    # X: 4, 0, 8 ... X hace la diagonal 0-4-8. O: 1, 2.
    state = INITIAL_STATE
    for move in [4, 1, 0, 2, 8]:
        assert not game.is_terminal(state)
        state = game.apply_move(state, move)
    assert state == "XOO.X...X"
    assert game.winner(state) == X
    assert game.is_terminal(state)


# --------------------------------------------------------------------------- #
# Estados mal formados o imposibles                                           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "state, reason",
    [
        (None, "str"),
        (["X"] * 9, "str"),  # una lista no es un estado, aunque tenga 9 casillas
        ("", "9 casillas"),
        ("X........X", "9 casillas"),
        ("x........", "solo puede contener"),  # minúscula
        ("0........", "solo puede contener"),  # cero en vez de O
        ("X O......", "solo puede contener"),  # espacio en vez de punto
        ("O........", "siempre empieza X"),  # O no puede mover primero
        ("XX.......", "siempre empieza X"),  # X no puede mover dos veces
        ("XXXOOO...", "los dos jugadores"),
        ("XXXOO.O..", "después de ganar X"),  # O movió tras perder
        ("OOOXX.X.X", "después de ganar O"),  # X movió tras perder
    ],
)
def test_invalid_states_are_rejected(state, reason):
    assert not game.is_valid_state(state)
    with pytest.raises(ValueError, match=reason):
        game.legal_moves(state)


@pytest.mark.parametrize(
    "function",
    [
        game.current_player,
        game.legal_moves,
        game.winner,
        game.winning_line,
        game.is_terminal,
        game.is_draw,
    ],
)
def test_every_query_validates_the_state(function):
    with pytest.raises(ValueError):
        function("not a board")


def test_is_legal_validates_the_state():
    with pytest.raises(ValueError):
        game.is_legal("not a board", 0)


# --------------------------------------------------------------------------- #
# El juego completo, comprobado contra cifras conocidas                       #
# --------------------------------------------------------------------------- #


@cache
def _count_games(state: str) -> tuple[int, int, int]:
    """Contar (victorias de X, victorias de O, empates) en todas las partidas
    que pueden seguir desde ``state``."""
    if game.is_terminal(state):
        result = game.winner(state)
        return (int(result == X), int(result == O), int(result is None))
    totals = [0, 0, 0]
    for move in game.legal_moves(state):
        for i, count in enumerate(_count_games(game.apply_move(state, move))):
            totals[i] += count
    return (totals[0], totals[1], totals[2])


@cache
def _reachable_states() -> frozenset[str]:
    """Todas las posiciones alcanzables desde el tablero vacío jugando legalmente."""
    seen = {INITIAL_STATE}
    pending = [INITIAL_STATE]
    while pending:
        state = pending.pop()
        for move in game.legal_moves(state):
            child = game.apply_move(state, move)
            if child not in seen:
                seen.add(child)
                pending.append(child)
    return frozenset(seen)


def test_number_of_complete_games_matches_known_totals():
    # Cifras conocidas del tres en raya: 255.168 partidas distintas, de las que
    # X gana 131.184, O gana 77.904 y 46.080 terminan en empate. Una sola regla
    # mal implementada (un empate mal detectado, una partida que sigue tras un
    # tres en raya…) cambiaría estos números.
    x_wins, o_wins, draws = _count_games(INITIAL_STATE)
    assert (x_wins, o_wins, draws) == (131_184, 77_904, 46_080)
    assert x_wins + o_wins + draws == 255_168


def test_number_of_reachable_positions_matches_known_total():
    # Hay exactamente 5.478 posiciones legales alcanzables, contando la inicial.
    states = _reachable_states()
    assert len(states) == 5_478
    assert all(game.is_valid_state(state) for state in states)


def test_every_game_ends_within_nine_moves():
    # Ninguna posición alcanzable tiene más de 9 fichas, y todas las que tienen 9
    # son terminales: la partida nunca se queda sin movimientos sin haber acabado.
    for state in _reachable_states():
        marks = 9 - state.count(EMPTY)
        assert marks <= 9
        if marks == 9:
            assert game.is_terminal(state)
        if not game.is_terminal(state):
            assert game.legal_moves(state)
