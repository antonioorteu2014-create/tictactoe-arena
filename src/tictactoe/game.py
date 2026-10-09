"""Reglas del tres en raya, como funciones puras.

Las reglas completas, en prosa, están en ``docs/rules.md``. Este módulo es su
única implementación: la terminal, los bots, la web y el torneo llaman a estas
funciones, y por eso todos están de acuerdo sobre qué es legal y quién gana.

Decisiones de diseño:

* El **estado** es un ``str`` de 9 caracteres, una casilla por carácter, leyendo
  el tablero por filas: ``"X"``, ``"O"`` o ``"."`` (vacía). Un ``str`` es
  inmutable, así que un bot no puede modificar por accidente el tablero que
  recibe; es *hashable*, así que sirve como clave de un diccionario (memoización
  en minimax); y se imprime y viaja como JSON sin conversión.
* Un **movimiento** es un ``int`` del 0 al 8: la casilla donde se coloca la
  ficha. Quién la coloca no se indica, porque siempre es el jugador al que le
  toca.
* El **turno no se guarda**: se deduce del tablero. Siempre empieza X, así que
  con tantas X como O le toca a X, y con una X más le toca a O. Así no puede
  existir un estado cuyo turno contradiga a su tablero.
* Todas las funciones son **puras**: no imprimen, no leen la entrada y no
  dependen de ningún estado global. Reciben una posición y devuelven una
  respuesta.
* La frontera es **estricta**: un estado mal formado o imposible, o un
  movimiento ilegal, lanzan ``ValueError`` en lugar de hacer en silencio algo
  razonable. El error de un bot falla en el sitio donde se produce.
"""

from __future__ import annotations

State = str
"""Una posición: 9 caracteres ``"X"``, ``"O"`` o ``"."``, por filas."""

Move = int
"""Un movimiento: el número de casilla, del 0 al 8, donde se coloca la ficha."""

Mark = str
"""La ficha de un jugador: ``"X"`` u ``"O"``.

No confundir con [`tictactoe.player.Player`][tictactoe.player.Player], la interfaz de los bots."""

X: Mark = "X"
# Ruff avisa (E741) de que `O` se confunde con el cero. Aquí es el nombre del
# jugador, el mismo símbolo que se ve en el tablero, y llamarlo de otra forma
# haría el código más difícil de leer que de escribir mal.
O: Mark = "O"  # noqa: E741
EMPTY = "."

SIZE = 3
CELLS = SIZE * SIZE

INITIAL_STATE: State = EMPTY * CELLS
"""El tablero vacío, ``"........."``. Siempre empieza X."""

WINNING_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # filas
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columnas
    (0, 4, 8), (2, 4, 6),             # diagonales
)
"""Las 8 líneas que dan la victoria: 3 filas, 3 columnas y 2 diagonales."""


# --------------------------------------------------------------------------- #
# Validación del estado                                                       #
# --------------------------------------------------------------------------- #


def _find_lines(state: State, player: Mark) -> list[tuple[int, int, int]]:
    """Las líneas que ``player`` tiene completas en ``state`` (sin validar)."""
    return [line for line in WINNING_LINES if all(state[i] == player for i in line)]


def _check_state(state: object) -> None:
    """Lanzar ``ValueError`` si ``state`` no es una posición alcanzable.

    No basta con que tenga la forma correcta: también tiene que poder aparecer
    en una partida real. Se rechazan, por ejemplo, un tablero con más O que X
    (siempre empieza X), o uno en el que la partida siguió después de que
    alguien hiciera tres en raya.
    """
    if not isinstance(state, str):
        raise ValueError(
            f"el estado debe ser un str, no {type(state).__name__}: {state!r}"
        )
    if len(state) != CELLS:
        raise ValueError(
            f"el estado debe tener {CELLS} casillas, tiene {len(state)}: {state!r}"
        )
    invalid = set(state) - {X, O, EMPTY}
    if invalid:
        raise ValueError(
            f"el estado solo puede contener {X!r}, {O!r} y {EMPTY!r}; "
            f"contiene {sorted(invalid)}: {state!r}"
        )

    xs, os_ = state.count(X), state.count(O)
    if xs not in (os_, os_ + 1):
        raise ValueError(
            f"estado imposible: siempre empieza X, así que X debe tener tantas "
            f"fichas como O o una más (X={xs}, O={os_}): {state!r}"
        )

    x_won = bool(_find_lines(state, X))
    o_won = bool(_find_lines(state, O))
    if x_won and o_won:
        raise ValueError(f"estado imposible: los dos jugadores tienen tres en raya: {state!r}")
    # Quien acaba de ganar es quien acaba de mover: si ganó X, X tiene una ficha
    # más; si ganó O, las cuentas están igualadas. Cualquier otra cuenta
    # significa que se siguió jugando después de terminar la partida.
    if x_won and xs != os_ + 1:
        raise ValueError(f"estado imposible: se siguió jugando después de ganar X: {state!r}")
    if o_won and xs != os_:
        raise ValueError(f"estado imposible: se siguió jugando después de ganar O: {state!r}")


def is_valid_state(state: object) -> bool:
    """Indicar si ``state`` es una posición que puede aparecer en una partida.

    Comprueba la forma (``str`` de 9 caracteres ``"X"``, ``"O"`` o ``"."``) y
    que la posición sea alcanzable jugando según las reglas.

    Args:
        state: cualquier objeto.

    Returns:
        ``True`` si es un estado válido, ``False`` en otro caso. Nunca lanza.
    """
    try:
        _check_state(state)
    except ValueError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Consultas sobre una posición                                                #
# --------------------------------------------------------------------------- #


def initial_state() -> State:
    """Devolver la posición inicial: el tablero vacío."""
    return INITIAL_STATE


def current_player(state: State) -> Mark:
    """Devolver el jugador al que le toca mover.

    Se deduce del tablero: si hay tantas X como O le toca a X, y si hay una X
    más le toca a O. En una posición terminal devuelve a quien le tocaría, aunque
    ya no pueda mover.

    Raises:
        ValueError: si ``state`` no es una posición válida.
    """
    _check_state(state)
    return X if state.count(X) == state.count(O) else O


def winning_line(state: State) -> tuple[int, int, int] | None:
    """Devolver las tres casillas del tres en raya, o ``None`` si no lo hay.

    Si un mismo movimiento completa dos líneas a la vez, devuelve la primera en
    el orden de [`WINNING_LINES`][tictactoe.game.WINNING_LINES].

    Raises:
        ValueError: si ``state`` no es una posición válida.
    """
    _check_state(state)
    for player in (X, O):
        lines = _find_lines(state, player)
        if lines:
            return lines[0]
    return None


def winner(state: State) -> Mark | None:
    """Devolver el ganador (``"X"`` u ``"O"``), o ``None`` si no lo hay.

    ``None`` significa que la partida sigue en juego **o** que ha terminado en
    empate; [`is_terminal()`][tictactoe.game.is_terminal] los distingue.

    Raises:
        ValueError: si ``state`` no es una posición válida.
    """
    line = winning_line(state)
    return None if line is None else state[line[0]]


def is_terminal(state: State) -> bool:
    """Indicar si la partida ha terminado: hay tres en raya o el tablero está lleno.

    Raises:
        ValueError: si ``state`` no es una posición válida.
    """
    return winner(state) is not None or EMPTY not in state


def is_draw(state: State) -> bool:
    """Indicar si la partida ha terminado en empate: tablero lleno y sin ganador.

    Raises:
        ValueError: si ``state`` no es una posición válida.
    """
    return winner(state) is None and EMPTY not in state


def legal_moves(state: State) -> list[Move]:
    """Devolver todos los movimientos legales, de menor a mayor casilla.

    Son las casillas vacías, salvo que la partida haya terminado: entonces no hay
    ninguno, aunque queden casillas libres.

    Raises:
        ValueError: si ``state`` no es una posición válida.
    """
    if is_terminal(state):
        return []
    return [cell for cell, mark in enumerate(state) if mark == EMPTY]


def is_legal(state: State, move: object) -> bool:
    """Indicar si ``move`` es legal en ``state``.

    Es la única definición de «movimiento legal» del proyecto: el torneo la usa
    para descalificar a un bot que devuelve un movimiento ilegal.

    ``move`` se anota como ``object`` y no como [`Move`][tictactoe.game.Move] a propósito: su
    trabajo es juzgar lo que devuelve un bot en el que no se confía, que puede
    ser cualquier cosa (``None``, ``"4"``, ``4.0``, ``True``…).

    Raises:
        ValueError: si ``state`` no es una posición válida. Un movimiento mal
            formado no lanza: devuelve ``False``.
    """
    # Solo un `int` exacto. Se excluyen las subclases: `bool` lo es (True == 1, y un
    # bot que devuelve True no ha elegido la casilla 1), y una subclase hecha a
    # medida podría cambiar cómo se compara o se suma.
    if type(move) is not int:
        return False
    if not 0 <= move < CELLS:
        return False
    return not is_terminal(state) and state[move] == EMPTY


def apply_move(state: State, move: Move) -> State:
    """Devolver la posición **nueva** que resulta de jugar ``move``.

    La ficha colocada es la del jugador al que le toca. ``state`` no se modifica
    (un ``str`` no se puede modificar).

    Args:
        state: la posición actual.
        move: la casilla, del 0 al 8, donde colocar la ficha.

    Returns:
        La posición siguiente.

    Raises:
        ValueError: si ``state`` no es una posición válida o ``move`` no es legal
            en ella.
    """
    if not is_legal(state, move):
        raise ValueError(f"movimiento ilegal {move!r} en el estado {state!r}")
    return state[:move] + current_player(state) + state[move + 1 :]
