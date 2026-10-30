"""Pruebas de la parte Python de la web: el puente y el empaquetado.

La página (``web/app.js``) solo pregunta y dibuja; todo lo que sabe del juego se
lo responde ``web/webglue.py``. Estas pruebas ejecutan ese puente con Python
normal, sin navegador, para comprobar que responde lo correcto y que nunca deja
escapar un error hacia la página.
"""

from __future__ import annotations

import importlib
import json
import re
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


# --------------------------------------------------------------------------- #
# Los modos de juego, las preguntas y el torneo en el navegador                #
# --------------------------------------------------------------------------- #

HUMAN = {"kind": "human"}


def bot(name):
    return {"kind": "bot", "bot": name}


def test_modes_list_the_five_modes_and_their_bots(glue):
    modes = {m["key"]: m for m in call(glue.modes_json)["modes"]}
    assert list(modes) == ["clasico", "inverso", "tres-fichas", "preguntas"]
    # El clásico ofrece los bots de la plataforma (también los enviados).
    assert {"aleatorio", "voraz", "minimax"} <= {b["name"] for b in modes["clasico"]["bots"]}
    assert [b["name"] for b in modes["inverso"]["bots"]] == ["aleatorio", "voraz", "minimax"]
    assert modes["preguntas"]["humans_only"] and modes["preguntas"]["bots"] == []
    for mode in modes.values():
        assert mode["rules"] and mode["summary"]


@pytest.mark.parametrize("mode", ["clasico", "inverso", "tres-fichas"])
def test_a_full_bot_against_bot_game_in_every_mode(glue, mode):
    bots = {m["key"]: m["bots"] for m in call(glue.modes_json)["modes"]}
    fast = bots[mode][0]["name"]  # el aleatorio: rápido
    position = call(glue.mode_new_game, mode, json.dumps({"X": bot(fast), "O": bot(fast)}), 1)
    assert position["ok"] and position["mode"] == mode
    for _ in range(200):
        if position["terminal"]:
            break
        position = call(glue.mode_bot_move, json.dumps(position["state"]))
        assert position["ok"] and not position["forfeit"]
    assert position["terminal"]


def test_a_person_plays_and_the_bot_answers(glue):
    seats = json.dumps({"X": HUMAN, "O": bot("voraz")})
    position = call(glue.mode_new_game, "tres-fichas", seats, 0)
    assert position["turn"] == "X" and position["vanishing"] is None
    position = call(glue.mode_play, json.dumps(position["state"]), "4")
    assert position["turn"] == "O"
    position = call(glue.mode_bot_move, json.dumps(position["state"]))
    assert position["turn"] == "X" and position["cells"].count("O") == 1


def test_a_person_cannot_ask_the_bot_to_move_for_them(glue):
    position = call(glue.mode_new_game, "inverso", json.dumps({"X": HUMAN, "O": HUMAN}), 0)
    assert call(glue.mode_bot_move, json.dumps(position["state"]))["ok"] is False


@pytest.mark.parametrize(
    "mode, seats",
    [
        ("preguntas", {"X": HUMAN, "O": bot("aleatorio")}),  # solo personas
        ("inverso", {"X": HUMAN, "O": bot("montecarlo")}),  # no existe ese bot
        ("ultimate", {"X": HUMAN, "O": HUMAN}),  # ese modo ya no existe
        ("clasico", {"X": HUMAN, "O": bot("no-existe")}),
        ("clasico", {"X": HUMAN}),  # falta O
        ("no-existe", {"X": HUMAN, "O": HUMAN}),
    ],
)
def test_bad_games_are_errors_not_exceptions(glue, mode, seats):
    assert call(glue.mode_new_game, mode, json.dumps(seats), 0)["ok"] is False


def test_illegal_moves_in_a_mode_are_rejected(glue):
    position = call(glue.mode_new_game, "tres-fichas", json.dumps({"X": HUMAN, "O": HUMAN}), 0)
    position = call(glue.mode_play, json.dumps(position["state"]), "4")
    assert call(glue.mode_play, json.dumps(position["state"]), "4")["ok"] is False


def test_a_broken_bot_forfeits_in_any_mode(glue):
    call(glue.mode_new_game, "inverso", json.dumps({"X": bot("aleatorio"), "O": HUMAN}), 0)
    glue._SEATS["X"] = _Raises()
    answer = call(glue.mode_bot_move, json.dumps("........."))
    assert answer["ok"] and answer["forfeit"] and answer["forfeit_by"] == "X"


def test_the_quiz_never_sends_the_answer_before_answering(glue):
    question = call(glue.quiz_question, 3, "[]")["question"]
    assert set(question) == {"id", "tema", "pregunta", "opciones"}
    again = call(glue.quiz_question, 3, json.dumps([question["id"]]))["question"]
    assert again["id"] != question["id"]


def test_the_quiz_answer_places_or_passes(glue):
    call(glue.mode_new_game, "preguntas", json.dumps({"X": HUMAN, "O": HUMAN}), 0)
    question = call(glue.quiz_question, 3, "[]")["question"]
    answers = [
        call(glue.quiz_answer, json.dumps(".........|X"), 4, question["id"], c) for c in range(4)
    ]
    right = [a for a in answers if a["correct"]]
    wrong = [a for a in answers if not a["correct"]]
    assert len(right) == 1 and len(wrong) == 3
    assert right[0]["cells"] == "....X...." and right[0]["turn"] == "O"
    assert right[0]["explanation"]
    for answer in wrong:
        # Fallada: pasa el turno y no se revela nada (la pregunta sigue en juego).
        assert answer["cells"] == "........." and answer["turn"] == "O"
        assert answer["correct_choice"] is None and answer["explanation"] is None
    assert call(glue.quiz_answer, json.dumps(".........|X"), 4, "nada", 0)["ok"] is False
    assert call(glue.quiz_topics)["topics"]


def test_the_browser_knockout_plays_until_a_champion(glue):
    answer = call(glue.knockout_start, json.dumps(["aleatorio", "voraz", "minimax"]), 7)
    assert answer["ok"] and answer["event"] is None
    assert [r["name"] for r in answer["bracket"]["rounds"]] == ["Semifinales", "Final"]
    for _ in range(50):
        answer = call(glue.knockout_step)
        if answer["bracket"]["done"]:
            break
        assert answer["event"]["game"]["moves"]
    assert answer["bracket"]["champion"] in ("aleatorio", "voraz", "minimax")
    assert call(glue.knockout_step)["event"] is None


@pytest.mark.parametrize(
    "names", [["aleatorio"], ["aleatorio", "aleatorio"], ["aleatorio", "nadie"], "x"]
)
def test_bad_knockouts_are_errors(glue, names):
    assert call(glue.knockout_start, json.dumps(names), 0)["ok"] is False


def test_build_web_packs_the_modes_and_the_questions(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    sys.modules.pop("build_web", None)
    build_web = importlib.import_module("build_web")
    names = set(zipfile.ZipFile(build_web.build(tmp_path / "py.zip")).namelist())
    assert "tictactoe/modes/moving.py" in names
    assert "tictactoe/modes/preguntas.json" in names


def test_every_page_script_is_loaded_and_writes_no_html():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    scripts = (
        "engine.js",
        "app.js",
        "fighters.js",
        "play.js",
        "league.js",
        "botrank.js",
        "arena.js",
    )
    for script in (*scripts, "leaderboard.js"):
        assert re.search(rf'<script src="{re.escape(script)}(\?v=\d+)?"></script>', html)
        source = (ROOT / "web" / script).read_text(encoding="utf-8")
        # Los nombres los escribe cualquiera: siempre como texto, nunca como HTML.
        assert "innerHTML" not in source and "insertAdjacentHTML" not in source
