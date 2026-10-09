"""La prueba de contrato: el examen que debe pasar cualquier jugador admitido.

Recorre **todos** los jugadores de las listas de admitidos (``players/builtin`` y
``players/custom``) y les aplica las mismas comprobaciones. Admitir un bot nuevo
no exige escribir ninguna prueba: en cuanto su línea aparece en
``players/custom/players.yaml``, esta prueba lo examina. Si está roto, el pull
request se pone en rojo solo.

Para demostrar que el examen funciona, al final del archivo hay bots rotos a
propósito, y se comprueba que el examen los suspende a todos.
"""

from __future__ import annotations

import sys

import pytest

from tictactoe import game
from tictactoe.match import ERROR, ILLEGAL_MOVE, play_game
from tictactoe.player import Player
from tictactoe.registry import (
    BUILTIN,
    DEFAULT_MANIFESTS,
    AdmittedPlayer,
    ManifestError,
    load_players,
)

#: Semillas con las que se construye cada jugador: un bot con azar puede comportarse
#: distinto con cada una.
SEEDS = (0, 1, 2)

#: Posiciones en las que todo jugador debe devolver un movimiento legal. Las
#: incómodas primero: es ahí donde se rompen los bots.
POSITIONS = [
    game.INITIAL_STATE,
    # Las nueve aperturas posibles: le toca a O.
    *(game.apply_move(game.INITIAL_STATE, cell) for cell in range(9)),
    "X.O.X...O",  # media partida, varias opciones
    "XX.OO....",  # X puede ganar en la casilla 2 (y O amenaza en la 5)
    "XO.XO....",  # X gana en la casilla 6 (columna 0-3-6)
    "XX..O....",  # O debe bloquear en la casilla 2
    "XOXXOO.X.",  # quedan dos casillas
    "XOXXOOOX.",  # queda una sola casilla
]


def _load() -> tuple[dict[str, AdmittedPlayer], Exception | None]:
    """Cargar el registro; si falla, devolver el error para mostrarlo en una prueba."""
    try:
        return load_players(), None
    except ManifestError as exc:
        return {}, exc


ADMITTED, LOAD_ERROR = _load()


#: El rival de referencia, el bot aleatorio. Se carga solo de la lista del equipo:
#: así, un bot enviado que no se pueda cargar hace fallar únicamente
#: test_admitted_players_load, con su mensaje, y no arrastra al resto de pruebas.
REFERENCE = load_players({BUILTIN: DEFAULT_MANIFESTS[BUILTIN]})["aleatorio"].cls


def _rival(seed: int) -> Player:
    """Un rival de referencia nuevo para cada partida."""
    return REFERENCE.create(seed + 1000)


def contract_problems(cls: type[Player]) -> list[str]:
    """Aplicar el examen a la clase ``cls`` y devolver los problemas encontrados.

    Una lista vacía significa que ``cls`` cumple el contrato.
    """
    problems: list[str] = []
    name = cls.__name__

    for seed in SEEDS:
        # 1. Se puede construir con una semilla.
        try:
            player = cls.create(seed)
        except (Exception, SystemExit) as exc:
            problems.append(f"{name}.create({seed}) lanzó {type(exc).__name__}: {exc}")
            continue
        if not isinstance(player, cls):
            problems.append(f"{name}.create({seed}) no devolvió un {name}")
            continue

        # 2. Devuelve un movimiento legal en cada posición de prueba.
        for state in POSITIONS:
            try:
                move = player.choose_move(state)
            except (Exception, SystemExit) as exc:
                problems.append(f"{name} lanzó {type(exc).__name__} en {state!r}: {exc}")
                break
            if not game.is_legal(state, move):
                problems.append(f"{name} devolvió el movimiento ilegal {move!r} en {state!r}")
                break

        # 3. Termina partidas completas, con X y con O, sin abandonar.
        for plays_x in (True, False):
            mine = cls.create(seed)
            result = (
                play_game(mine, _rival(seed)) if plays_x else play_game(_rival(seed), mine)
            )
            my_mark = game.X if plays_x else game.O
            if result.is_forfeit and result.loser == my_mark:
                problems.append(
                    f"{name} perdió por abandono jugando con {my_mark} (semilla {seed}): "
                    f"{result.detail}"
                )
    return problems


# --------------------------------------------------------------------------- #
# El examen, aplicado a todos los jugadores admitidos                         #
# --------------------------------------------------------------------------- #


def test_admitted_players_load():
    """Las listas de admitidos se leen y todos sus bots cumplen la plantilla."""
    assert LOAD_ERROR is None, f"no se pudieron cargar los jugadores: {LOAD_ERROR}"
    assert "aleatorio" in ADMITTED


@pytest.mark.parametrize("name", sorted(ADMITTED))
def test_player_passes_the_contract(name):
    admitted = ADMITTED[name]
    assert admitted.cls.get_name() == name
    problems = contract_problems(admitted.cls)
    assert not problems, f"{name} ({admitted.file}) no cumple el contrato:\n" + "\n".join(
        problems
    )


# --------------------------------------------------------------------------- #
# El examen funciona: suspende a los bots rotos a propósito                   #
# --------------------------------------------------------------------------- #


class _Base(Player):
    """Identidad común de los bots rotos (lo roto es su forma de jugar)."""

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["pruebas"]

    @classmethod
    def get_description(cls) -> str:
        return "Bot roto a propósito para comprobar el examen."


class LanzaError(_Base):
    def choose_move(self, state):
        raise RuntimeError("me he roto")


class Tramposo(_Base):
    """Juega siempre en la casilla 0, aunque esté ocupada."""

    def choose_move(self, state):
        return 0


class NoResponde(_Base):
    def choose_move(self, state):
        return None


class DevuelveTexto(_Base):
    def choose_move(self, state):
        return str(game.legal_moves(state)[0])


class DevuelveBooleano(_Base):
    """True vale 1 en Python, pero no es una casilla."""

    def choose_move(self, state):
        return True


class SaleDelPrograma(_Base):
    """Un exit() olvidado al depurar: no debe cerrar el programa entero."""

    def choose_move(self, state):
        sys.exit(1)


class NumeroTrucado(_Base):
    """Devuelve un «int» que miente al compararse y al sumarse."""

    def choose_move(self, state):
        class Trucado(int):
            def __eq__(self, other):
                return True

            __hash__ = int.__hash__

            def __add__(self, other):
                return "!"

        return Trucado(game.legal_moves(state)[0])


class ModificaTablero(_Base):
    """Intenta escribir en el tablero que recibe. Un str no lo permite."""

    def choose_move(self, state):
        state[0] = "X"
        return 0


BROKEN = [
    (LanzaError, ERROR),
    (Tramposo, ILLEGAL_MOVE),
    (NoResponde, ILLEGAL_MOVE),
    (DevuelveTexto, ILLEGAL_MOVE),
    (DevuelveBooleano, ILLEGAL_MOVE),
    (NumeroTrucado, ILLEGAL_MOVE),
    (SaleDelPrograma, ERROR),
    (ModificaTablero, ERROR),
]


@pytest.mark.parametrize("cls", [cls for cls, _ in BROKEN], ids=lambda c: c.__name__)
def test_the_contract_rejects_broken_players(cls):
    assert contract_problems(cls), f"el examen debería suspender a {cls.__name__}"


@pytest.mark.parametrize("cls, ending", BROKEN, ids=[c.__name__ for c, _ in BROKEN])
def test_broken_player_loses_cleanly_without_dragging_the_other(cls, ending):
    # Juega con X y con O: siempre pierde él, por abandono, y gana el rival.
    for broken_is_x in (True, False):
        broken, rival = cls.create(0), _rival(0)
        result = play_game(broken, rival) if broken_is_x else play_game(rival, broken)
        broken_mark = game.X if broken_is_x else game.O
        assert result.ending == ending
        assert result.loser == broken_mark
        assert result.detail
        # La partida quedó en una posición válida: nada se corrompió.
        assert game.is_valid_state(result.final_state)


def test_the_board_cannot_be_modified_by_a_player():
    state = "X.O.X...O"
    with pytest.raises(TypeError):
        ModificaTablero.create(0).choose_move(state)
    assert state == "X.O.X...O"
