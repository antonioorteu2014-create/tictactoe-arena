"""Estrategias de los bots del equipo.

Aquí vive *cómo piensa* cada bot. Su identidad (nombre, autores, icono) la declaran
los archivos de ``players/builtin/``, que heredan de estas clases. Así la
estrategia se puede probar y documentar como parte de la librería, y cualquiera
puede reutilizarla en su propio bot.

* [`GreedyBot`][tictactoe.bots.greedy.GreedyBot] — puntúa cada jugada con reglas
  sencillas y juega la mejor, sin mirar hacia delante.
* [`MinimaxBot`][tictactoe.bots.minimax.MinimaxBot] — busca entre las jugadas futuras
  con minimax y poda alfa-beta.
"""

from __future__ import annotations

from .greedy import GreedyBot, evaluate, score_move
from .minimax import MinimaxBot, SearchInfo

__all__ = ["GreedyBot", "MinimaxBot", "SearchInfo", "evaluate", "score_move"]
