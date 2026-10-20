"""El marcador de la web y el formato de la clasificación.

El torneo escribe ``leaderboard.json`` y la página (``web/leaderboard.js``) lo
lee. Solo se entienden si usan el mismo formato, el acordado en la issue #10.
``leaderboard_problems()`` es ese acuerdo escrito en código, como
``contract_problems`` lo es para los bots: el torneo puede importarla para
comprobar que el archivo que genera es válido.

La página no se puede ejecutar sin navegador. Aquí se comprueba que está bien
conectada y que respeta las dos reglas que importan: no usar una copia vieja del
archivo y no escribir como HTML lo que viene de los bots.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
EXAMPLE = Path(__file__).parent / "data" / "leaderboard_example.json"

SCHEMA_VERSION = 1
COUNTS = ("rank", "played", "wins", "draws", "losses", "forfeits")


def _is_count(value: object) -> bool:
    # bool es un int en Python, pero True no es un número de partidas.
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_points(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def leaderboard_problems(data: object) -> list[str]:
    """Los problemas de una clasificación, o una lista vacía si es válida."""
    if not isinstance(data, dict):
        return ["la clasificación debe ser un objeto JSON"]

    problems = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version debe ser {SCHEMA_VERSION}")
    try:
        # fromisoformat no acepta la «Z» final hasta Python 3.11.
        datetime.fromisoformat(str(data.get("generated_at")).replace("Z", "+00:00"))
    except ValueError:
        problems.append("generated_at debe ser una fecha ISO 8601")

    standings = data.get("standings")
    if not isinstance(standings, list):
        return [*problems, "standings debe ser una lista"]

    names: set[str] = set()
    previous = None
    for position, row in enumerate(standings, start=1):
        if not isinstance(row, dict):
            problems.append(f"fila {position}: debe ser un objeto")
            continue
        label = f"fila {position} ({row.get('name')})"

        name = row.get("name")
        if not isinstance(name, str) or not name:
            problems.append(f"{label}: name debe ser un texto")
        elif name in names:
            problems.append(f"{label}: el nombre está repetido")
        else:
            names.add(name)
        if not isinstance(row.get("icon"), str):
            problems.append(f"{label}: icon debe ser un texto")
        authors = row.get("authors")
        if not isinstance(authors, list) or not all(isinstance(a, str) for a in authors):
            problems.append(f"{label}: authors debe ser una lista de textos")

        bad = [key for key in COUNTS if not _is_count(row.get(key))]
        if not _is_points(row.get("points")):
            bad.append("points")
        if bad:
            problems.append(f"{label}: {', '.join(bad)} deben ser números no negativos")
            continue

        if row["wins"] + row["draws"] + row["losses"] != row["played"]:
            problems.append(f"{label}: wins + draws + losses debe dar played")
        if row["forfeits"] > row["losses"]:
            problems.append(f"{label}: forfeits no puede ser mayor que losses")
        if previous is None:
            if row["rank"] != 1:
                problems.append(f"{label}: el primero debe tener rank 1")
        else:
            if row["points"] > previous["points"]:
                problems.append(f"{label}: la lista debe ir de más a menos puntos")
            if row["rank"] < previous["rank"]:
                problems.append(f"{label}: rank no puede bajar")
        previous = row
    return problems


def load_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_the_example_follows_the_format():
    assert leaderboard_problems(load_example()) == []


# Cada cambio estropea el ejemplo de una forma distinta; todas se deben detectar.
BROKEN = {
    "version-desconocida": lambda d: d.update(schema_version=2),
    "sin-fecha": lambda d: d.pop("generated_at"),
    "sin-lista": lambda d: d.update(standings={}),
    "sin-nombre": lambda d: d["standings"][0].pop("name"),
    "nombre-repetido": lambda d: d["standings"][1].update(name="minimax"),
    "cuentas-que-no-cuadran": lambda d: d["standings"][0].update(wins=22),
    "desordenada": lambda d: d["standings"].reverse(),
    "numero-negativo": lambda d: d["standings"][2].update(points=-1),
    "booleano-como-numero": lambda d: d["standings"][0].update(forfeits=True),
    "mas-abandonos-que-derrotas": lambda d: d["standings"][1].update(forfeits=5),
}


@pytest.mark.parametrize("change", [pytest.param(c, id=name) for name, c in BROKEN.items()])
def test_broken_leaderboards_are_detected(change):
    data = load_example()
    change(data)
    assert leaderboard_problems(data)


def test_the_page_has_everything_the_scoreboard_needs():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "leaderboard.js").read_text(encoding="utf-8")
    assert '<script src="leaderboard.js"></script>' in html
    # El marcador escribe las filas dentro del <tbody> de la tabla.
    assert "<tbody></tbody>" in html
    # Si alguien cambia un id en la página, el marcador dejaría de encontrarlo.
    ids = re.findall(r'getElementById\("([^"]+)"\)', script)
    assert ids
    for element_id in ids:
        assert f'id="{element_id}"' in html, element_id


def test_the_scoreboard_never_shows_a_stale_copy():
    script = (WEB / "leaderboard.js").read_text(encoding="utf-8")
    assert 'const FILE = "leaderboard.json"' in script
    assert 'cache: "no-cache"' in script


def test_the_scoreboard_never_writes_html():
    # Los nombres y autores los eligen quienes envían los bots: se escriben como
    # texto, nunca como HTML que el navegador ejecutaría.
    script = (WEB / "leaderboard.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "insertAdjacentHTML" not in script


def test_the_generated_leaderboard_is_never_committed():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "web/leaderboard.json" in ignored
