"""Jugar una partida de tres en raya en la terminal, entre dos personas.

Se lanza con el comando ``tictactoe-play`` (o ``python -m tictactoe``). Es el
único módulo del paquete que lee del teclado e imprime: las reglas
(:mod:`tictactoe.game`) siguen siendo puras, y ``import tictactoe`` no muestra
nada por pantalla.

Las casillas se piden del **1 al 9**, que es más natural para una persona, y se
traducen a los movimientos 0-8 de :mod:`tictactoe.game`. Las casillas vacías se
dibujan con su número, así que el tablero dice a la vez qué está libre y qué
escribir.
"""

from __future__ import annotations

from collections.abc import Callable

from . import game

Reader = Callable[[str], str]
Writer = Callable[[str], None]


def format_board(state: game.State) -> str:
    """Dibujar el tablero, con el número (1-9) de cada casilla vacía."""
    cells = [mark if mark != game.EMPTY else str(i + 1) for i, mark in enumerate(state)]
    rows = [" " + " | ".join(cells[r * game.SIZE : (r + 1) * game.SIZE]) for r in range(game.SIZE)]
    return "\n---+---+---\n".join(rows)


def ask_move(state: game.State, read: Reader, write: Writer) -> game.Move:
    """Pedir una casilla hasta recibir una legal, y devolverla como movimiento 0-8."""
    player = game.current_player(state)
    while True:
        text = read(f"Turno de {player}. Elige casilla (1-9): ").strip()
        if not text.isdigit():
            write("  Escribe un número del 1 al 9.")
            continue
        move = int(text) - 1
        if not 0 <= move < game.CELLS:
            write("  Esa casilla no existe: elige un número del 1 al 9.")
            continue
        if not game.is_legal(state, move):
            write("  Esa casilla ya está ocupada: elige otra.")
            continue
        return move


def play(read: Reader = input, write: Writer = print) -> game.Player | None:
    """Jugar una partida completa entre dos personas.

    ``read`` y ``write`` son, por defecto, el teclado y la pantalla. Se pueden
    sustituir para probar la partida sin teclado (ver ``tests/test_cli.py``).

    Returns:
        El ganador (``"X"`` u ``"O"``), o ``None`` si la partida acaba en empate.
    """
    state = game.initial_state()
    write("Tres en raya. Empieza X.\n")
    while not game.is_terminal(state):
        write(format_board(state) + "\n")
        state = game.apply_move(state, ask_move(state, read, write))

    write(format_board(state) + "\n")
    result = game.winner(state)
    write("¡Empate!" if result is None else f"¡Gana {result}!")
    return result


def main() -> None:
    """Punto de entrada del comando ``tictactoe-play``."""
    try:
        play()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C o Ctrl+D: salir sin volcar un traceback en la pantalla.
        print("\nPartida interrumpida.")


if __name__ == "__main__":
    main()
