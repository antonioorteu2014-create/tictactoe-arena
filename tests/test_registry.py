"""Pruebas del registro de jugadores (``tictactoe.registry``).

Cada prueba escribe una lista de admitidos y sus bots en una carpeta temporal, para
comprobar que el registro acepta lo correcto y rechaza con un mensaje claro todo lo
demás.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tictactoe.registry import (
    BUILTIN,
    CUSTOM,
    DEFAULT_MANIFESTS,
    ManifestError,
    load_players,
)

GOOD_BOT = '''
from tictactoe import game
from tictactoe.player import Player


class {cls}(Player):
    @classmethod
    def get_name(cls):
        return {name!r}

    @classmethod
    def get_authors(cls):
        return {authors!r}

    @classmethod
    def get_description(cls):
        return "Juega en la primera casilla libre."

    def choose_move(self, state):
        return game.legal_moves(state)[0]
'''


def _bot(folder: Path, file: str, cls: str = "Bot", name: str = "bot", authors=("Ana",)):
    (folder / file).write_text(
        GOOD_BOT.format(cls=cls, name=name, authors=list(authors)), encoding="utf-8"
    )


def _manifest(folder: Path, body: str) -> Path:
    path = folder / "players.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_project_builtin_manifest_loads_the_reference_player():
    # Solo la lista del equipo: un bot enviado roto ya lo señala test_players.py.
    players = load_players({BUILTIN: DEFAULT_MANIFESTS[BUILTIN]})
    assert players["aleatorio"].origin == BUILTIN
    assert set(DEFAULT_MANIFESTS) == {BUILTIN, CUSTOM}


def test_loads_a_valid_player(tmp_path):
    _bot(tmp_path, "primera.py", cls="Primera", name="primera")
    manifest = _manifest(tmp_path, "players:\n  - file: primera.py\n    class: Primera\n")
    players = load_players({CUSTOM: manifest})
    admitted = players["primera"]
    assert admitted.origin == CUSTOM
    assert admitted.cls.__name__ == "Primera"
    assert admitted.cls.create(0).choose_move(".........") == 0


@pytest.mark.parametrize("body", ["players: []\n", "players:\n"])
def test_empty_manifest_admits_nobody(tmp_path, body):
    assert load_players({CUSTOM: _manifest(tmp_path, body)}) == {}


def test_duplicate_names_are_rejected(tmp_path):
    builtin = tmp_path / "builtin"
    custom = tmp_path / "custom"
    builtin.mkdir()
    custom.mkdir()
    _bot(builtin, "a.py", cls="A", name="repetido")
    _bot(custom, "b.py", cls="B", name="repetido")
    manifests = {
        BUILTIN: _manifest(builtin, "players:\n  - file: a.py\n    class: A\n"),
        CUSTOM: _manifest(custom, "players:\n  - file: b.py\n    class: B\n"),
    }
    with pytest.raises(ManifestError, match="repetido"):
        load_players(manifests)


@pytest.mark.parametrize(
    "body, message",
    [
        ("otra_cosa: 1\n", "clave 'players'"),
        ("players: hola\n", "debe ser una lista"),
        ("players:\n  - file: bot.py\n", "exactamente 'file' y 'class'"),
        ("players:\n  - file: ''\n    class: Bot\n", "'file' está vacío"),
        ("players:\n  - file: bot.py\n    class: 3\n", "'class' debe ser un texto, no int"),
        ("players:\n  - file: ../bot.py\n    class: Bot\n", "sin rutas"),
        ("players:\n  - file: /tmp/bot.py\n    class: Bot\n", "sin rutas"),
        ("players:\n  - file: sub/bot.py\n    class: Bot\n", "sin rutas"),
        ("players:\n  - file: bot.txt\n    class: Bot\n", "archivo .py"),
        ("players:\n  - file: no_existe.py\n    class: Bot\n", "no existe el archivo"),
        ("players:\n  - file: bot.py\n    class: Otra\n", "no define una clase 'Otra'"),
        ("players: [\n", "no es un YAML válido"),
    ],
)
def test_malformed_manifests_are_rejected(tmp_path, body, message):
    _bot(tmp_path, "bot.py")
    with pytest.raises(ManifestError, match=message):
        load_players({CUSTOM: _manifest(tmp_path, body)})


def test_missing_manifest_is_rejected(tmp_path):
    with pytest.raises(ManifestError, match="no existe la lista"):
        load_players({CUSTOM: tmp_path / "players.yaml"})


def test_a_class_that_is_not_a_player_is_rejected(tmp_path):
    (tmp_path / "bot.py").write_text("class Bot:\n    pass\n", encoding="utf-8")
    manifest = _manifest(tmp_path, "players:\n  - file: bot.py\n    class: Bot\n")
    with pytest.raises(ManifestError, match="herede de tictactoe.player.Player"):
        load_players({CUSTOM: manifest})


def test_an_incomplete_player_is_rejected(tmp_path):
    (tmp_path / "bot.py").write_text(
        "from tictactoe.player import Player\n\n"
        "class Bot(Player):\n"
        "    @classmethod\n"
        "    def get_name(cls):\n"
        "        return 'bot'\n",
        encoding="utf-8",
    )
    manifest = _manifest(tmp_path, "players:\n  - file: bot.py\n    class: Bot\n")
    with pytest.raises(ManifestError, match="no implementa: choose_move"):
        load_players({CUSTOM: manifest})


def test_duplicate_names_differing_only_in_case_are_rejected(tmp_path):
    _bot(tmp_path, "a.py", cls="A", name="bot")
    _bot(tmp_path, "b.py", cls="B", name="Bot")
    body = "players:\n  - file: a.py\n    class: A\n  - file: b.py\n    class: B\n"
    with pytest.raises(ManifestError, match="repetido"):
        load_players({CUSTOM: _manifest(tmp_path, body)})


def test_identity_method_that_raises_is_reported_clearly(tmp_path):
    # El error típico de principiante: olvidar @classmethod en get_name.
    (tmp_path / "bot.py").write_text(
        GOOD_BOT.format(cls="Bot", name="bot", authors=["Ana"]).replace(
            "    @classmethod\n    def get_name(cls):", "    def get_name(self):"
        ),
        encoding="utf-8",
    )
    manifest = _manifest(tmp_path, "players:\n  - file: bot.py\n    class: Bot\n")
    with pytest.raises(ManifestError, match=r"get_name\(\) lanzó TypeError.*@classmethod"):
        load_players({CUSTOM: manifest})


def test_a_file_that_calls_exit_on_import_is_rejected(tmp_path):
    (tmp_path / "bot.py").write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    manifest = _manifest(tmp_path, "players:\n  - file: bot.py\n    class: Bot\n")
    with pytest.raises(ManifestError, match="error al importar"):
        load_players({CUSTOM: manifest})


def test_a_file_that_fails_to_import_is_rejected(tmp_path):
    (tmp_path / "bot.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    manifest = _manifest(tmp_path, "players:\n  - file: bot.py\n    class: Bot\n")
    with pytest.raises(ManifestError, match="error al importar"):
        load_players({CUSTOM: manifest})


@pytest.mark.parametrize(
    "name, authors, message",
    [
        ("", ["Ana"], "get_name"),
        ("  con espacios  ", ["Ana"], "get_name"),
        ("mi bot", ["Ana"], "sin espacios"),
        ("x" * 41, ["Ana"], "de 1 a 40"),
        ("bot", [], "get_authors"),
        ("bot", [""], "get_authors"),
    ],
)
def test_invalid_identity_is_rejected(tmp_path, name, authors, message):
    _bot(tmp_path, "bot.py", name=name, authors=authors)
    manifest = _manifest(tmp_path, "players:\n  - file: bot.py\n    class: Bot\n")
    with pytest.raises(ManifestError, match=message):
        load_players({CUSTOM: manifest})
