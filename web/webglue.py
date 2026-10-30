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
from tictactoe.knockout import Knockout
from tictactoe.modes import MODE_BOTS, MODES, ModeBot, get_mode
from tictactoe.modes import quiz as quiz_mode
from tictactoe.player import Player
from tictactoe.registry import BUILTIN, CUSTOM, AdmittedPlayer, load_players

_PLAYERS: dict[str, AdmittedPlayer] = {}
"""Los bots admitidos, cargados por ``init``."""

_BOT: Player | None = None
"""El bot rival de la partida en curso (API antigua: ``new_game``/``bot_move``)."""

_MODE_KEY = "clasico"
"""El modo de la partida en curso (pantalla «Jugar»)."""

_SEATS: dict[str, Player | ModeBot | None] = {game.X: None, game.O: None}
"""Quién juega con cada ficha en la partida en curso: un bot, o ``None`` si es una persona."""


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


# --------------------------------------------------------------------------- #
# Los modos de juego (pantalla «Jugar»)                                       #
# --------------------------------------------------------------------------- #


def modes_json() -> str:
    """Los modos de juego y los bots que admite cada uno.

    Los bots del modo clásico son los de la plataforma (los del equipo y los
    enviados por pull request); los de los demás modos, los de
    ``tictactoe.modes``.
    """
    modes = []
    for key, mode in MODES.items():
        if key == "clasico":
            bots = [
                {
                    "name": p.name,
                    "icon": p.cls.get_icon(),
                    "description": p.cls.get_description(),
                    "authors": p.cls.get_authors(),
                    "origin": p.origin,
                }
                for p in _PLAYERS.values()
            ]
        else:
            bots = [
                {
                    "name": spec.name,
                    "icon": spec.icon,
                    "description": spec.description,
                    "authors": ["Antonio Orteu", "Álvaro Domingo", "María Sanz"],
                    "origin": BUILTIN,
                }
                for spec in MODE_BOTS[key]
            ]
        modes.append({**mode.info(), "bots": bots})
    return _ok(modes=modes)


def _create_seat(mode_key: str, seat: Any, seed: int) -> Player | ModeBot | None:
    """El jugador de un asiento: ``None`` para una persona, o el bot ya creado."""
    if not isinstance(seat, dict) or seat.get("kind") not in ("human", "bot"):
        raise ValueError("cada ficha debe ser una persona o un bot")
    if seat["kind"] == "human":
        return None
    name = seat.get("bot")
    if mode_key == "clasico":
        admitted = _PLAYERS.get(name)
        if admitted is None:
            raise ValueError(f"no existe el bot {name!r}")
        return admitted.cls.create(seed)
    for spec in MODE_BOTS[mode_key]:
        if spec.name == name:
            return spec.create(seed)
    raise ValueError(f"el modo {mode_key!r} no tiene el bot {name!r}")


def mode_new_game(mode_key: str, seats_json: str, seed: int) -> str:
    """Empezar una partida de ``mode_key``.

    ``seats_json`` dice quién juega con cada ficha:
    ``{"X": {"kind": "human"}, "O": {"kind": "bot", "bot": "minimax"}}``.
    """
    global _MODE_KEY, _SEATS
    try:
        mode = get_mode(mode_key)
        seats = json.loads(seats_json)
        if mode.humans_only and any(
            isinstance(s, dict) and s.get("kind") == "bot" for s in seats.values()
        ):
            return _error(f"el modo {mode.name} es solo para personas")
        _SEATS = {
            mark: _create_seat(mode_key, seats.get(mark), int(seed) + offset)
            for offset, mark in enumerate((game.X, game.O))
        }
    except Exception as exc:
        _SEATS = {game.X: None, game.O: None}
        return _error(f"no se pudo empezar la partida: {_text(exc)}")
    _MODE_KEY = mode_key
    return _ok(**mode.describe(mode.initial_state()))


def mode_play(state_json: str, move_json: str) -> str:
    """Aplicar el movimiento de una persona en la partida en curso."""
    mode = get_mode(_MODE_KEY)
    try:
        state = json.loads(state_json)
        move = json.loads(move_json)
        if not mode.is_legal(state, move):
            return _error(f"la casilla {move!r} no está disponible")
        return _ok(**mode.describe(mode.apply_move(state, move)))
    except Exception as exc:
        return _error(_text(exc))


def mode_bot_move(state_json: str) -> str:
    """Que juegue el bot al que le toca y devolver la posición nueva.

    Si el bot falla o hace trampa, **pierde por abandono** (``"forfeit": true``),
    como en el torneo, en vez de romper la página.
    """
    mode = get_mode(_MODE_KEY)
    try:
        state = json.loads(state_json)
        if mode.is_terminal(state):
            return _error("la partida ya ha terminado")
        mover = mode.current_player(state)
    except Exception as exc:
        return _error(f"posición no válida: {_text(exc)}")
    bot = _SEATS.get(mover)
    if bot is None:
        return _error(f"a {mover} no le juega ningún bot")

    try:
        if isinstance(bot, ModeBot):
            move = bot.choose_move(mode, state)
        else:
            move = bot.choose_move(state)
    except (Exception, SystemExit, GeneratorExit) as exc:
        return _ok(
            forfeit=True,
            forfeit_by=mover,
            detail=f"el bot falló: {type(exc).__name__}: {_text(exc)}",
            **mode.describe(state),
        )
    if not mode.is_legal(state, move):
        return _ok(
            forfeit=True,
            forfeit_by=mover,
            detail="el bot devolvió un movimiento ilegal",
            **mode.describe(state),
        )
    return _ok(forfeit=False, move=move, **mode.describe(mode.apply_move(state, move)))


# --------------------------------------------------------------------------- #
# El modo preguntas                                                           #
# --------------------------------------------------------------------------- #


def quiz_question(seed: int, used_json: str) -> str:
    """Una pregunta nueva (sin la respuesta), distinta de las ya usadas en la partida.

    Una pregunta fallada no se cambia: la página la guarda en su casilla para el
    siguiente que la intente, y solo pide una nueva cuando alguien la acierta.
    """
    try:
        used = set(json.loads(used_json))
        return _ok(question=quiz_mode.pick_question(int(seed), used).public())
    except Exception as exc:
        return _error(f"no se pudo elegir una pregunta: {_text(exc)}")


def quiz_answer(state_json: str, cell: int, question_id: str, choice: int) -> str:
    """Comprobar la respuesta: con acierto se pone la ficha; con fallo pasa el turno."""
    mode = get_mode("preguntas")
    try:
        state = json.loads(state_json)
        result = quiz_mode.answer(state, int(cell), str(question_id), int(choice))
    except Exception as exc:
        return _error(_text(exc))
    return _ok(
        correct=result["correct"],
        correct_choice=result["correct_choice"],
        explanation=result["explanation"],
        **mode.describe(result["state"]),
    )


def quiz_topics() -> str:
    """Los temas del banco de preguntas y cuántas hay de cada uno."""
    counts: dict[str, int] = {}
    for question in quiz_mode.load_questions():
        counts[question.tema] = counts.get(question.tema, 0) + 1
    return _ok(topics=[{"tema": t, "count": n} for t, n in counts.items()])


# --------------------------------------------------------------------------- #
# Un torneo por eliminatorias en el navegador (pantalla «Torneo»)              #
# --------------------------------------------------------------------------- #

_KNOCKOUT: Knockout | None = None
"""El torneo por eliminatorias en curso."""


def knockout_start(names_json: str, seed: int) -> str:
    """Sortear un cuadro de eliminatorias entre los bots ``names_json`` (modo clásico)."""
    global _KNOCKOUT
    try:
        names = json.loads(names_json)
        if not isinstance(names, list):
            return _error("hay que elegir una lista de bots")
        factories = {name: p.cls.create for name, p in _PLAYERS.items()}
        _KNOCKOUT = Knockout(factories, names, int(seed))
    except Exception as exc:
        _KNOCKOUT = None
        return _error(_text(exc))
    return _ok(event=None, bracket=_KNOCKOUT.to_json())


def knockout_step() -> str:
    """Jugar la siguiente partida del cuadro y devolver qué ha pasado y el cuadro."""
    if _KNOCKOUT is None:
        return _error("no hay ningún torneo empezado")
    try:
        event = _KNOCKOUT.step()
    except Exception as exc:
        return _error(_text(exc))
    return _ok(event=event, bracket=_KNOCKOUT.to_json())
