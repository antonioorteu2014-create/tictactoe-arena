"""Pruebas de la partida de terminal (``tictactoe.cli``), sin teclado.

La partida recibe las funciones de lectura y escritura como parámetros, así que
aquí se le pasa una lista de respuestas preparadas en lugar del teclado.
"""

from __future__ import annotations

import subprocess
import sys

from tictactoe import cli, game


def _scripted(answers: list[str]):
    """Un sustituto de ``input`` que devuelve ``answers`` en orden."""
    pending = iter(answers)
    return lambda _prompt: next(pending)


def _play(answers: list[str]) -> tuple[str | None, str]:
    """Jugar con respuestas preparadas; devolver el ganador y todo lo impreso."""
    printed: list[str] = []
    result = cli.play(read=_scripted(answers), write=printed.append)
    return result, "\n".join(printed)


def test_format_board_numbers_empty_cells():
    assert cli.format_board("X.O.X...O") == (
        " X | 2 | O\n"
        "---+---+---\n"
        " 4 | X | 6\n"
        "---+---+---\n"
        " 7 | 8 | O"
    )


def test_x_wins_a_full_game():
    # X: 5, 1, 9 (diagonal); O: 2, 3.
    result, output = _play(["5", "2", "1", "3", "9"])
    assert result == game.X
    assert "¡Gana X!" in output


def test_o_wins_a_full_game():
    # X: 1, 2, 9; O: 5, 3, 7 (diagonal 3-5-7).
    result, output = _play(["1", "5", "2", "3", "9", "7"])
    assert result == game.O
    assert "¡Gana O!" in output


def test_draw_game():
    #  X | O | X
    #  X | O | O
    #  O | X | X
    result, output = _play(["1", "2", "3", "5", "4", "6", "8", "7", "9"])
    assert result is None
    assert "¡Empate!" in output


def test_invalid_input_is_asked_again_and_does_not_count_as_a_move():
    answers = [
        "hola",  # no es un número
        "",  # vacío
        "0",  # fuera de rango
        "10",  # fuera de rango
        "-3",  # negativo
        "5",  # X en el centro
        "5",  # O intenta la misma casilla: ocupada
        "1",  # O en la esquina
        "2",  # X
        "4",  # O
        "8",  # X completa la columna central 2-5-8
    ]
    result, output = _play(answers)
    assert result == game.X
    assert output.count("Escribe un número del 1 al 9.") == 3  # "hola", "" y "-3"
    assert output.count("Esa casilla no existe") == 2
    assert output.count("ya está ocupada") == 1


def test_importing_the_package_prints_nothing():
    # El paquete debe ser importable y silencioso: solo la terminal imprime.
    completed = subprocess.run(
        [sys.executable, "-c", "import tictactoe, tictactoe.game"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout == ""
    assert completed.stderr == ""
