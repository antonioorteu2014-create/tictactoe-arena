"""Pruebas del torneo por eliminatorias (el cuadro que se juega en la web)."""

from __future__ import annotations

import pytest

from tictactoe import game
from tictactoe.knockout import (
    BY_BYE,
    BY_DRAW,
    BY_GAMES,
    GAMES_PER_TIE,
    SUDDEN_DEATH,
    Knockout,
    round_name,
)
from tictactoe.player import Player
from tictactoe.registry import load_players

PLAYERS = load_players()
FACTORIES = {name: p.cls.create for name, p in PLAYERS.items()}


class _FirstFree(Player):
    """Juega siempre en la primera casilla libre: dos iguales empatan o gana X."""

    @classmethod
    def get_name(cls):
        return "primera"

    @classmethod
    def get_authors(cls):
        return ["pruebas"]

    @classmethod
    def get_description(cls):
        return "primera casilla libre"

    @classmethod
    def create(cls, seed):
        return cls()

    def choose_move(self, state):
        return game.legal_moves(state)[0]


class _Broken(_FirstFree):
    def choose_move(self, state):
        raise RuntimeError("me rompo")


def run(knockout):
    events = []
    while (event := knockout.step()) is not None:
        events.append(event)
    return events


def test_round_names():
    assert [round_name(n) for n in (1, 2, 4, 8, 16)] == [
        "Final",
        "Semifinales",
        "Cuartos de final",
        "Octavos de final",
        "Ronda de 32",
    ]


@pytest.mark.parametrize("count, rounds", [(2, 1), (3, 2), (4, 2), (5, 3), (8, 3)])
def test_the_bracket_has_the_right_size_and_byes(count, rounds):
    names = [f"bot{i}" for i in range(count)]
    factories = {name: _FirstFree.create for name in names}
    knockout = Knockout(factories, names, seed=1)
    assert len(knockout.rounds) == rounds
    first = knockout.rounds[0]
    byes = [t for t in first if t.decided_by == BY_BYE]
    assert len(byes) == 2**rounds - count
    assert sorted(n for t in first for n in (t.a, t.b) if n) == sorted(names)


def test_a_full_tournament_has_one_champion_and_everyone_else_loses_once():
    names = list(FACTORIES)
    knockout = Knockout(FACTORIES, names, seed=3)
    events = run(knockout)
    assert knockout.done and knockout.champion in names
    assert events[-1]["champion"] == knockout.champion
    eliminated = [
        (t.b if t.winner == t.a else t.a)
        for ties in knockout.rounds
        for t in ties
        if t.decided_by != BY_BYE
    ]
    assert sorted(eliminated + [knockout.champion]) == sorted(names)
    assert knockout.step() is None  # terminado: no hay más partidas


def test_each_tie_plays_both_colours_and_moves_are_recorded():
    knockout = Knockout(FACTORIES, ["voraz", "minimax"], seed=0)
    first = knockout.step()["game"]
    second = knockout.step()["game"]
    assert (first["x"], first["o"]) == (second["o"], second["x"])
    replay = game.initial_state()
    for move in first["moves"]:
        replay = game.apply_move(replay, move)
    assert game.is_terminal(replay)


def test_two_perfect_bots_go_to_sudden_death_and_then_a_draw():
    # Dos minimax empatan siempre: se resuelve por sorteo tras la muerte súbita.
    factories = {"a": FACTORIES["minimax"], "b": FACTORIES["minimax"]}
    knockout = Knockout(factories, ["a", "b"], seed=5)
    run(knockout)
    tie = knockout.rounds[0][0]
    assert len(tie.games) == GAMES_PER_TIE + SUDDEN_DEATH
    assert tie.decided_by == BY_DRAW
    assert knockout.champion in ("a", "b")


def test_minimax_knocks_out_random_in_two_games():
    knockout = Knockout(FACTORIES, ["aleatorio", "minimax"], seed=2)
    run(knockout)
    tie = knockout.rounds[0][0]
    assert knockout.champion == "minimax"
    assert tie.decided_by in (BY_GAMES, "muerte súbita")


def test_a_broken_bot_loses_without_breaking_the_tournament():
    factories = {"rompe": _Broken.create, "voraz": FACTORIES["voraz"]}
    knockout = Knockout(factories, ["rompe", "voraz"], seed=0)
    events = run(knockout)
    assert knockout.champion == "voraz"
    assert all(e["game"]["ending"] == "error" for e in events if "rompe" in e["game"]["x"])


def test_a_bot_that_cannot_be_created_loses():
    def boom(seed):
        raise RuntimeError("no arranco")

    knockout = Knockout({"boom": boom, "voraz": FACTORIES["voraz"]}, ["boom", "voraz"], seed=0)
    run(knockout)
    assert knockout.champion == "voraz"
    assert "no se pudo crear" in knockout.rounds[0][0].games[0]["detail"]


def test_same_seed_same_tournament():
    def summary(seed):
        knockout = Knockout(FACTORIES, list(FACTORIES), seed)
        run(knockout)
        return knockout.to_json()

    assert summary(11) == summary(11)


@pytest.mark.parametrize("names", [[], ["voraz"], ["voraz", "voraz"], ["voraz", "nadie"]])
def test_bad_brackets_raise(names):
    with pytest.raises(ValueError):
        Knockout(FACTORIES, names, seed=0)


def test_json_has_what_the_page_draws():
    knockout = Knockout(FACTORIES, list(FACTORIES), seed=0)
    knockout.step()
    data = knockout.to_json()
    assert set(data) == {"rounds", "champion", "done"}
    tie = data["rounds"][0]["ties"][0]
    assert set(tie) == {"a", "b", "score", "games", "winner", "decided_by"}
