"""Pruebas de la parte Python de la web: el puente y el empaquetado.

La página (``web/app.js``) solo pregunta y dibuja; todo lo que sabe del juego se
lo responde ``web/webglue.py``. Estas pruebas ejecutan ese puente con Python
normal, sin navegador, para comprobar que responde lo correcto y que nunca deja
escapar un error hacia la página.
"""

from __future__ import annotations

import importlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def glue(monkeypatch):
    """El módulo puente, recién importado y con los bots del proyecto cargados."""
    monkeypatch.syspath_prepend(str(ROOT / "web"))
    sys.modules.pop("webglue", None)
    module = importlib.import_module("webglue")
    answer = json.loads(module.init(str(ROOT)))
    assert answer["ok"], answer
    return module


def call(function, *args):
    return json.loads(function(*args))


def test_init_lists_the_admitted_bots(glue):
    players = call(glue.players_json)["players"]
    reference = next(p for p in players if p["name"] == "aleatorio")
    assert reference["icon"] == "🎲"
    assert reference["authors"]
    assert reference["origin"] == "builtin"


def test_new_game_returns_the_empty_board(glue):
    answer = call(glue.new_game, "aleatorio", 0)
    assert answer["ok"]
    assert answer["state"] == "........."
    assert answer["turn"] == "X"
    assert answer["legal"] == list(range(9))
    assert not answer["terminal"]


def test_unknown_bot_is_an_error_not_an_exception(glue):
    answer = call(glue.new_game, "no-existe", 0)
    assert answer == {"ok": False, "error": "no existe el bot 'no-existe'"}


def test_legal_moves_come_from_the_project_rules(glue):
    # El «Resultado» de la tarea 4.2: pedir al puente los movimientos legales.
    assert call(glue.legal_moves, json.dumps("X........")) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_play_applies_the_human_move(glue):
    answer = call(glue.play, json.dumps("........."), "4")
    assert answer["ok"]
    assert answer["state"] == "....X...."
    assert answer["turn"] == "O"


@pytest.mark.parametrize("move", ["4", "9", "true", '"4"', "null"])
def test_play_rejects_illegal_moves_without_raising(glue, move):
    answer = call(glue.play, json.dumps("....X...."), move)
    assert answer["ok"] is False


def test_play_reports_the_winner_and_the_line(glue):
    answer = call(glue.play, json.dumps("XX.OO...."), "2")
    assert answer["terminal"]
    assert answer["winner"] == "X"
    assert answer["line"] == [0, 1, 2]


@pytest.mark.parametrize("state", ["nada", "OO.......", 7])
def test_invalid_positions_are_reported_not_raised(glue, state):
    assert call(glue.status, json.dumps(state))["ok"] is False
    assert call(glue.play, json.dumps(state), "0")["ok"] is False


def test_bot_plays_a_legal_move(glue):
    call(glue.new_game, "aleatorio", 3)
    answer = call(glue.bot_move, json.dumps("....X...."))
    assert answer["ok"] and not answer["forfeit"]
    assert answer["move"] in [0, 1, 2, 3, 5, 6, 7, 8]
    assert answer["state"].count("O") == 1


def test_a_full_game_through_the_bridge(glue):
    position = call(glue.new_game, "aleatorio", 1)
    while not position["terminal"]:
        if position["turn"] == "X":  # la «persona»: primera casilla libre
            position = call(glue.play, json.dumps(position["state"]), str(position["legal"][0]))
        else:
            position = call(glue.bot_move, json.dumps(position["state"]))
            assert not position["forfeit"]
    assert position["winner"] in ("X", "O", None)


class _Raises:
    def choose_move(self, state):
        raise RuntimeError("me rompo")


class _Cheats:
    def choose_move(self, state):
        return 4  # ocupada en "....X...."


class _Exits:
    def choose_move(self, state):
        raise SystemExit(1)


class _UnprintableError(Exception):
    def __str__(self):
        raise ValueError("ni siquiera se puede mostrar")


class _RaisesUnprintable:
    def choose_move(self, state):
        raise _UnprintableError


@pytest.mark.parametrize(
    "bot",
    [_Raises(), _Cheats(), _Exits(), _RaisesUnprintable()],
    ids=["lanza", "trampa", "exit", "error-raro"],
)
def test_a_broken_bot_forfeits_instead_of_breaking_the_page(glue, bot):
    glue._BOT = bot
    answer = call(glue.bot_move, json.dumps("....X...."))
    assert answer["ok"] and answer["forfeit"]
    assert answer["detail"]
    assert answer["state"] == "....X...."  # la posición no cambia


def test_bot_move_without_a_game_is_an_error(glue):
    glue._BOT = None
    assert call(glue.bot_move, json.dumps("........."))["ok"] is False


def test_bot_cannot_move_on_a_finished_game(glue):
    call(glue.new_game, "aleatorio", 0)
    assert call(glue.bot_move, json.dumps("XXXOO...."))["ok"] is False


def test_build_web_packs_the_package_bots_and_bridge(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    sys.modules.pop("build_web", None)
    build_web = importlib.import_module("build_web")

    zip_path = build_web.build(tmp_path / "py.zip")
    names = set(zipfile.ZipFile(zip_path).namelist())

    assert "webglue.py" in names
    assert "tictactoe/game.py" in names
    assert "tictactoe/registry.py" in names
    assert "players/builtin/players.yaml" in names
    assert "players/builtin/aleatorio.py" in names
    assert "players/custom/players.yaml" in names
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    assert not (tmp_path / "py").exists()  # la carpeta intermedia se borra
