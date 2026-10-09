"""Pruebas del ejecutor de partidas (``tictactoe.match``)."""

from __future__ import annotations

import pytest

from tictactoe import game
from tictactoe.match import ERROR, ILLEGAL_MOVE, NORMAL, GameResult, play_game
from tictactoe.player import Player


class Scripted(Player):
    """Un jugador que juega una lista fija de casillas, en orden."""

    def __init__(self, moves: list[int]) -> None:
        self._moves = iter(moves)

    @classmethod
    def get_name(cls) -> str:
        return "guion"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["pruebas"]

    @classmethod
    def get_description(cls) -> str:
        return "Juega una lista de casillas fijada de antemano."

    def choose_move(self, state):
        return next(self._moves)


class FirstFree(Scripted):
    """Juega siempre en la primera casilla libre."""

    def __init__(self) -> None:
        pass

    def choose_move(self, state):
        return game.legal_moves(state)[0]


def test_x_wins_and_history_is_returned():
    # X: 4, 0, 8 (diagonal) · O: 1, 2.
    result = play_game(Scripted([4, 0, 8]), Scripted([1, 2]))
    assert result == GameResult(
        winner=game.X, moves=(4, 1, 0, 2, 8), final_state="XOO.X...X", ending=NORMAL
    )
    assert result.loser == game.O
    assert not result.is_forfeit


def test_o_wins():
    # X: 0, 1, 8 · O: 4, 2, 6 (diagonal 2-4-6).
    result = play_game(Scripted([0, 1, 8]), Scripted([4, 2, 6]))
    assert result.winner == game.O
    assert result.loser == game.X


def test_draw():
    #  X | O | X
    #  X | O | O
    #  O | X | X
    result = play_game(Scripted([0, 2, 3, 7, 8]), Scripted([1, 4, 5, 6]))
    assert result.winner is None
    assert result.loser is None
    assert result.ending == NORMAL
    assert game.is_draw(result.final_state)


def test_history_replays_to_the_final_state():
    result = play_game(FirstFree(), FirstFree())
    state = game.INITIAL_STATE
    for move in result.moves:
        state = game.apply_move(state, move)
    assert state == result.final_state
    assert game.is_terminal(state)


def test_can_start_from_a_given_position_and_turn_is_deduced():
    # En "XX..O...." le toca a O; si no bloquea en 2, X gana.
    result = play_game(Scripted([2]), Scripted([3]), state="XX..O....")
    assert result.moves == (3, 2)
    assert result.winner == game.X


def test_invalid_starting_position_raises():
    with pytest.raises(ValueError, match="no válida"):
        play_game(FirstFree(), FirstFree(), state="OO.......")


def test_starting_from_a_finished_game_returns_immediately():
    result = play_game(FirstFree(), FirstFree(), state="XXXOO....")
    assert result.moves == ()
    assert result.winner == game.X


def test_illegal_move_forfeits_and_rival_wins():
    # O intenta la casilla 4, que ocupa X.
    result = play_game(Scripted([4, 0]), Scripted([4]))
    assert result.ending == ILLEGAL_MOVE
    assert result.winner == game.X
    assert result.loser == game.O
    assert result.is_forfeit
    assert result.moves == (4,)
    assert result.final_state == "....X...."
    assert "4" in result.detail


def test_exception_forfeits_and_rival_wins():
    # X se queda sin jugadas en su guion: next() lanza StopIteration.
    result = play_game(Scripted([]), FirstFree())
    assert result.ending == ERROR
    assert result.winner == game.O
    assert "StopIteration" in result.detail
