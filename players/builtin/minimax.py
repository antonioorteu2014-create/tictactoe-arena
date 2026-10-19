"""El jugador ``minimax``: busca hacia delante con poda alfa-beta (tarea 3.2).

Con la profundidad completa (9) juega perfecto: nunca pierde. La estrategia está
en :mod:`tictactoe.bots.minimax`; aquí solo se declara su identidad.
"""

from __future__ import annotations

from tictactoe.bots import MinimaxBot


class Minimax(MinimaxBot):
    @classmethod
    def get_name(cls) -> str:
        return "minimax"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Antonio Orteu", "Álvaro Domingo", "María Sanz"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Imagina todas las jugadas futuras suponiendo que los dos juegan perfecto "
            "(minimax con poda alfa-beta) y elige la mejor. Nunca pierde."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🧠"
