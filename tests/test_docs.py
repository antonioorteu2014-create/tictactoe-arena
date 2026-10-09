"""El bot de ejemplo de la documentación funciona de verdad.

El tutorial pide copiar un bot completo. Esta prueba extrae ese bloque de código
de las dos páginas donde aparece, comprueba que es el mismo en las dos y que pasa
el mismo examen que cualquier bot enviado. Si un cambio del proyecto rompiera el
ejemplo, fallaría aquí antes que en el ordenador de quien lo copie.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_players import contract_problems
from tictactoe.registry import CUSTOM, load_players

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "upload-a-bot"
PAGES = [DOCS / "player-api.md", DOCS / "submit-a-player.md"]


def _example(page: Path) -> str:
    """El bloque ```python de ``page`` que define el bot de ejemplo."""
    blocks = re.findall(r"```python\n(.*?)```", page.read_text(encoding="utf-8"), re.S)
    examples = [block for block in blocks if "class Oportunista(Player)" in block]
    assert len(examples) == 1, f"{page.name} debe tener un único bot de ejemplo"
    return examples[0]


@pytest.fixture
def example_cls(tmp_path):
    (tmp_path / "oportunista.py").write_text(_example(PAGES[0]), encoding="utf-8")
    manifest = tmp_path / "players.yaml"
    manifest.write_text(
        "players:\n  - file: oportunista.py\n    class: Oportunista\n", encoding="utf-8"
    )
    return load_players({CUSTOM: manifest})["oportunista"].cls


def test_the_example_is_the_same_in_both_pages():
    assert _example(PAGES[0]) == _example(PAGES[1])


def test_the_example_passes_the_style_check(tmp_path):
    # Quien lo copie tal cual debe tener el pull request en verde: el ejemplo
    # pasa el mismo `ruff check` que la integración continua.
    file = tmp_path / "oportunista.py"
    file.write_text(_example(PAGES[0]), encoding="utf-8")
    config = str(ROOT / "pyproject.toml")
    completed = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--config", config, str(file)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_the_example_passes_the_contract(example_cls):
    assert contract_problems(example_cls) == []


@pytest.mark.parametrize(
    "state, expected",
    [
        ("XX.OO....", 2),  # X gana en la casilla 2 (aunque O amenace en la 5)
        ("XO.XO....", 6),  # X gana en la columna 0-3-6
        ("XX..O....", 2),  # O debe bloquear en la casilla 2
        ("X...O...X", None),  # nada que ganar ni bloquear: cualquier casilla libre
    ],
)
def test_the_example_wins_and_blocks(example_cls, state, expected):
    move = example_cls.create(0).choose_move(state)
    if expected is None:
        assert state[move] == "."
    else:
        assert move == expected
