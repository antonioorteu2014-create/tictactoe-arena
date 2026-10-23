"""El torneo: la liguilla, la clasificación en JSON y sobrevivir a bots malos.

Los bots rotos se escriben como archivos de verdad y se admiten con su propia
lista, igual que llegaría un bot enviado por pull request: cada partida carga a
sus jugadores en un proceso aparte, a partir de las listas de admitidos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from tictactoe import tournament
from tictactoe.registry import BUILTIN, CUSTOM, DEFAULT_MANIFESTS

#: Límite por movimiento en estas pruebas: corto, para que el bot que se cuelga
#: no las haga lentas, y holgado para los demás (que mueven en milisegundos).
LIMIT = 0.5

_HEADER = """\
import os
import sys
import time

from tictactoe import game
from tictactoe.player import Player


class _Base(Player):
    @classmethod
    def get_name(cls):
        return cls.__name__.lower()

    @classmethod
    def get_authors(cls):
        return ["pruebas"]

    @classmethod
    def get_description(cls):
        return "Bot de las pruebas del torneo."
"""

BOTS = {
    "Primera": "return game.legal_moves(state)[0]",
    "LanzaError": "raise RuntimeError('me he roto')",
    "Tramposo": "return 0",
    "Dormilon": "time.sleep(60)",
    "SeCae": "os._exit(3)",
}


@pytest.fixture
def broken_manifests(tmp_path):
    """Una lista con un bot correcto y cuatro rotos, cada uno de una forma."""
    source = _HEADER
    for name, body in BOTS.items():
        source += f"\n\nclass {name}(_Base):\n    def choose_move(self, state):\n        {body}\n"
    (tmp_path / "bots.py").write_text(source, encoding="utf-8")
    entries = "".join(f"  - file: bots.py\n    class: {name}\n" for name in BOTS)
    manifest = tmp_path / "players.yaml"
    manifest.write_text("players:\n" + entries, encoding="utf-8")
    return {CUSTOM: manifest}


@pytest.fixture(scope="module")
def builtin_result():
    """Un torneo pequeño con los bots del proyecto (se juega una vez por módulo)."""
    return tournament.run_tournament(
        manifests={BUILTIN: DEFAULT_MANIFESTS[BUILTIN]}, games_per_pairing=3, seed=0
    )


# --------------------------------------------------------------------------- #
# La liguilla                                                                 #
# --------------------------------------------------------------------------- #


def test_everyone_plays_everyone_in_both_orders(builtin_result):
    names = {s.name for s in builtin_result.standings}
    pairs = {(g.x, g.o) for g in builtin_result.games}
    assert pairs == {(a, b) for a in names for b in names if a != b}
    assert len(builtin_result.games) == len(pairs) * 3
    # Cada bot juega 3 partidas con X y 3 con O contra cada rival.
    assert {s.played for s in builtin_result.standings} == {2 * 3 * (len(names) - 1)}


def test_the_table_adds_up(builtin_result):
    for s in builtin_result.standings:
        assert s.wins + s.draws + s.losses == s.played
    assert sum(s.wins for s in builtin_result.standings) == sum(
        s.losses for s in builtin_result.standings
    )


def test_minimax_never_loses_and_random_is_last(builtin_result):
    # Quién queda primero entre minimax y voraz depende de cuánto le saquen al
    # aleatorio; lo que no depende de nada es que el minimax no pierde.
    by_name = {s.name: s for s in builtin_result.standings}
    assert by_name["minimax"].losses == 0
    assert builtin_result.standings[-1].name == "aleatorio"


def test_same_seed_same_tournament(builtin_result):
    again = tournament.run_tournament(
        manifests={BUILTIN: DEFAULT_MANIFESTS[BUILTIN]}, games_per_pairing=3, seed=0
    )
    assert again.games == builtin_result.games


def test_games_per_pairing_must_be_positive():
    with pytest.raises(ValueError):
        tournament.run_tournament(games_per_pairing=0)


# --------------------------------------------------------------------------- #
# Sobrevivir a un jugador malo (requisito 4.1)                                #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("bot", "ending", "words"),
    [
        ("lanzaerror", "error", "RuntimeError"),
        ("tramposo", "illegal_move", "ilegal"),
        ("dormilon", tournament.TIMEOUT, "tardó"),
        ("secae", tournament.CRASH, "caer"),
    ],
)
def test_a_broken_bot_loses_with_its_reason(broken_manifests, bot, ending, words):
    record = tournament.play_isolated(
        "primera", bot, seed=1, manifests=broken_manifests, move_time_limit=LIMIT
    )
    assert record.winner == "primera"
    assert record.loser == bot
    assert record.ending == ending
    assert record.detail.startswith("O ")  # el culpable es quien llevaba O
    assert words in record.detail


def test_the_tournament_survives_every_broken_bot(broken_manifests):
    result = tournament.run_tournament(
        manifests=broken_manifests, games_per_pairing=1, seed=0, move_time_limit=LIMIT
    )
    by_name = {s.name: s for s in result.standings}
    # La tabla está completa: nadie se quedó sin jugar sus 8 partidas.
    assert {s.played for s in result.standings} == {8}
    # El bot correcto gana todo; los rotos solo pierden las partidas en las que
    # les tocó mover (contra otro roto, pierde el primero que falla).
    assert result.standings[0].name == "primera"
    assert by_name["primera"].wins == 8
    for name in ("lanzaerror", "tramposo", "dormilon", "secae"):
        assert by_name[name].forfeits == by_name[name].losses > 0


# --------------------------------------------------------------------------- #
# La clasificación en un archivo                                              #
# --------------------------------------------------------------------------- #


def test_leaderboard_json_has_what_the_web_needs(builtin_result):
    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    data = tournament.to_json(builtin_result, now=now)
    assert data["schema_version"] == tournament.SCHEMA_VERSION
    assert data["generated_at"] == "2026-10-18T12:00:00+00:00"
    assert data["settings"]["games_per_pairing"] == 3
    first = data["standings"][0]
    for key in ("rank", "name", "icon", "authors", "description", "points", "forfeits"):
        assert key in first
    assert [row["rank"] for row in data["standings"]][0] == 1
    assert len(data["games"]) == len(builtin_result.games)


def test_equal_points_share_the_rank():
    result = tournament.TournamentResult(
        standings=[
            tournament.Standing("a", "🤖", ["x"], "", "custom", played=2, wins=1, losses=1),
            tournament.Standing("b", "🤖", ["x"], "", "custom", played=2, wins=1, losses=1),
            tournament.Standing("c", "🤖", ["x"], "", "custom", played=2, draws=1, losses=1),
        ],
        games=[],
    )
    assert [row["rank"] for row in tournament.to_json(result)["standings"]] == [1, 1, 3]


def test_the_command_writes_the_file(tmp_path, capsys, monkeypatch):
    out = tmp_path / "results" / "leaderboard.json"
    monkeypatch.setattr(tournament, "DEFAULT_MANIFESTS", {BUILTIN: DEFAULT_MANIFESTS[BUILTIN]})
    assert tournament.main(["--games", "1", "--output", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert {row["name"] for row in data["standings"]} == {"aleatorio", "voraz", "minimax"}
    assert "minimax" in capsys.readouterr().out


def test_the_leaderboard_follows_the_web_format(builtin_result):
    # El formato lo fija el marcador de la web (tests/test_leaderboard_web.py,
    # acordado en la issue #10): el torneo tiene que escribir algo que la web pinte.
    from test_leaderboard_web import leaderboard_problems

    assert leaderboard_problems(tournament.to_json(builtin_result)) == []
