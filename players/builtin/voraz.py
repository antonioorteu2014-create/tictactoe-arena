"""El jugador ``voraz``: el primer bot con estrategia (tarea 3.1 de la guía).

Puntúa cada jugada con reglas sencillas (ganar, bloquear, preferir las casillas
con más líneas abiertas) y juega la mejor, sin mirar hacia delante. La estrategia
está en :mod:`tictactoe.bots.greedy`; aquí solo se declara su identidad.
"""

from __future__ import annotations

from tictactoe.bots import GreedyBot


class Voraz(GreedyBot):
    @classmethod
    def get_name(cls) -> str:
        return "voraz"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Antonio Orteu", "Álvaro Domingo", "María Sanz"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Gana si puede, bloquea si debe y si no prefiere el centro y las esquinas. "
            "No mira más allá de la jugada actual, así que no ve venir las dobles amenazas."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🦈"
