"""El puente entre la página web y el Python del proyecto (se ejecuta con Pyodide).

La página no conoce las reglas del tres en raya: se las pregunta a este módulo,
que usa exactamente el mismo ``tictactoe.game`` y los mismos bots que las pruebas
y el torneo. Así no existe una segunda versión de las reglas en JavaScript que
pueda acabar distinta.

Todo cruza la frontera Python ↔ JavaScript como **texto JSON**: la página llama
con ``JSON.stringify`` y lee con ``JSON.parse``. Ningún error de Python cruza esa
frontera como excepción: cada función devuelve ``{"ok": false, "error": ...}``
para que la página lo muestre en lugar de quedarse a medias.

Cada respuesta de partida lleva el **estado completo** de la posición (ver
``_describe``), y la página se redibuja siempre a partir de él.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tictactoe import game
from tictactoe.player import Player
from tictactoe.registry import BUILTIN, CUSTOM, AdmittedPlayer, load_players

_PLAYERS: dict[str, AdmittedPlayer] = {}
"""Los bots admitidos, cargados por ``init``."""

_BOT: Player | None = None
"""El bot rival de la partida en curso."""


def _text(obj: object) -> str:
    """``str(obj)`` sin riesgo: lo que lanza un bot podría fallar incluso al mostrarlo."""
    try:
        return str(obj)
    except Exception:
        return f"<{type(obj).__name__}>"


def _ok(**payload: Any) -> str:
    return json.dumps({"ok": True, **payload}, ensure_ascii=False)


def _error(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)


def _describe(state: game.State) -> dict[str, Any]:
    """Todo lo que la página necesita para dibujar una posición."""
    winner = game.winner(state)
    return {
        "state": state,
        "turn": game.current_player(state),
        "legal": game.legal_moves(state),
        "terminal": game.is_terminal(state),
        "winner": winner,
        "draw": game.is_draw(state),
        "line": list(game.winning_line(state) or []),
    }


def init(base_dir: str) -> str:
    """Cargar los bots de las listas de admitidos que hay bajo ``base_dir``.

    Devuelve lo mismo que ``players_json``.
    """
    global _PLAYERS
    base = Path(base_dir) / "players"
    try:
        _PLAYERS = load_players(
            {BUILTIN: base / BUILTIN / "players.yaml", CUSTOM: base / CUSTOM / "players.yaml"}
        )
    except Exception as exc:
        return _error(f"no se pudieron cargar los bots: {exc}")
    return players_json()


def players_json() -> str:
    """Los bots disponibles, con su identidad, en el orden de las listas."""
    return _ok(
        players=[
            {
                "name": p.name,
                "icon": p.cls.get_icon(),
                "authors": p.cls.get_authors(),
                "description": p.cls.get_description(),
                "origin": p.origin,
            }
            for p in _PLAYERS.values()
        ]
    )


def new_game(bot_name: str, seed: int) -> str:
    """Preparar al bot ``bot_name`` y devolver la posición inicial."""
    global _BOT
    admitted = _PLAYERS.get(bot_name)
    if admitted is None:
        return _error(f"no existe el bot {bot_name!r}")
    try:
        _BOT = admitted.cls.create(int(seed))
    except Exception as exc:
        _BOT = None
        return _error(f"el bot {bot_name!r} no se pudo crear: {exc}")
    return _ok(**_describe(game.initial_state()))


def status(state_json: str) -> str:
    """Describir la posición ``state_json`` (útil para depurar desde la consola)."""
    try:
        return _ok(**_describe(json.loads(state_json)))
    except Exception as exc:
        return _error(f"posición no válida: {exc}")


def legal_moves(state_json: str) -> str:
    """Los movimientos legales de ``state_json``, como lista JSON."""
    try:
        return json.dumps(game.legal_moves(json.loads(state_json)))
    except Exception as exc:
        return _error(f"posición no válida: {exc}")


def play(state_json: str, move_json: str) -> str:
    """Aplicar el movimiento de la persona y devolver la posición nueva."""
    try:
        state = json.loads(state_json)
        move = json.loads(move_json)
    except Exception as exc:
        return _error(f"datos no válidos: {exc}")
    try:
        if not game.is_legal(state, move):
            return _error(f"la casilla {move!r} no está disponible")
        return _ok(**_describe(game.apply_move(state, move)))
    except Exception as exc:
        return _error(str(exc))


def bot_move(state_json: str) -> str:
    """Pedir su movimiento al bot rival y devolver la posición nueva.

    Igual que en ``tictactoe.match.play_game``: si el bot lanza una excepción o
    devuelve un movimiento ilegal, **pierde por abandono** y la respuesta lo
    explica (``"forfeit": true``) en lugar de romper la página.
    """
    try:
        state = json.loads(state_json)
        if not game.is_valid_state(state) or game.is_terminal(state):
            return _error("no es una posición en la que el bot pueda jugar")
    except Exception as exc:
        return _error(f"posición no válida: {exc}")
    if _BOT is None:
        return _error("no hay ninguna partida empezada")

    try:
        move = _BOT.choose_move(state)
    except (Exception, SystemExit, GeneratorExit) as exc:
        return _ok(
            forfeit=True,
            detail=f"el bot falló: {type(exc).__name__}: {_text(exc)}",
            **_describe(state),
        )
    if not game.is_legal(state, move):
        return _ok(
            forfeit=True,
            detail="el bot devolvió un movimiento ilegal",
            **_describe(state),
        )
    return _ok(forfeit=False, move=move, **_describe(game.apply_move(state, move)))
