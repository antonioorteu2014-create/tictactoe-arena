"""Un torneo por eliminatorias (un cuadro), el que se juega en la web.

El torneo oficial (``tictactoe.tournament``) es una liguilla: todos contra todos y
una clasificación completa. Este es el otro formato clásico: los bots se
emparejan en un **cuadro**, el que pierde una eliminatoria se va a casa y el que
gana pasa a la siguiente ronda, hasta la final.

Reglas de cada eliminatoria:

* Se juegan **dos partidas**, una con cada ficha, porque en el tres en raya
  empezar es una ventaja. Pasa quien gane más.
* Si empatan (en el tres en raya, dos bots buenos empatan siempre), **muerte
  súbita**: hasta ``SUDDEN_DEATH`` partidas más, alternando las fichas; pasa el
  primero que gane una.
* Si siguen empatados, **sorteo** (con la semilla del torneo, así que se repite).
* Un bot que falla, hace trampa o no se puede crear pierde esa partida, como en
  el torneo oficial.

Si el número de bots no es una potencia de 2, algunos pasan la primera ronda sin
jugar (**pase directo**). El sorteo del cuadro sale de la semilla: la misma
semilla da el mismo torneo.

Las partidas se juegan **de una en una** con [`step`][tictactoe.knockout.Knockout.step],
para que la web pueda enseñar cada una y redibujar el cuadro entre partida y
partida.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import game
from .match import play_game
from .player import Player

GAMES_PER_TIE = 2
"""Partidas de cada eliminatoria: una con cada ficha."""

SUDDEN_DEATH = 3
"""Partidas extra, como mucho, si la eliminatoria acaba empatada."""

BY_GAMES = "partidas"
BY_SUDDEN_DEATH = "muerte súbita"
BY_DRAW = "sorteo"
BY_BYE = "pase directo"


def round_name(ties: int) -> str:
    """El nombre de una ronda según cuántas eliminatorias tiene."""
    return {1: "Final", 2: "Semifinales", 4: "Cuartos de final", 8: "Octavos de final"}.get(
        ties, f"Ronda de {2 * ties}"
    )


@dataclass
class Tie:
    """Una eliminatoria entre ``a`` y ``b`` (``None``: aún no se sabe, o pase directo)."""

    a: str | None = None
    b: str | None = None
    games: list[dict[str, Any]] = field(default_factory=list)
    winner: str | None = None
    decided_by: str | None = None

    def wins(self, name: str | None) -> int:
        return sum(1 for g in self.games if name is not None and g["winner"] == name)

    def to_json(self) -> dict[str, Any]:
        return {
            "a": self.a,
            "b": self.b,
            "score": [self.wins(self.a), self.wins(self.b)],
            "games": self.games,
            "winner": self.winner,
            "decided_by": self.decided_by,
        }


class Knockout:
    """Un torneo por eliminatorias entre los bots ``names``.

    Args:
        factories: cómo crear cada bot a partir de una semilla (``nombre -> create``).
        names: los bots que juegan (al menos 2, sin repetir).
        seed: la semilla de la que sale todo: el cuadro, las partidas y los sorteos.
    """

    def __init__(
        self, factories: dict[str, Callable[[int], Player]], names: list[str], seed: int
    ) -> None:
        names = list(names)
        if len(names) < 2 or len(set(names)) != len(names):
            raise ValueError("hacen falta al menos dos bots distintos")
        unknown = [n for n in names if n not in factories]
        if unknown:
            raise ValueError(f"no existe el bot {unknown[0]!r}")
        self.factories = factories
        self.rng = random.Random(seed)

        order = names[:]
        self.rng.shuffle(order)
        size = 1
        while size < len(order):
            size *= 2
        byes = size - len(order)
        # Los primeros del sorteo pasan directos; el resto se empareja.
        first = [Tie(order[i], None) for i in range(byes)]
        rest = order[byes:]
        first += [Tie(rest[i], rest[i + 1]) for i in range(0, len(rest), 2)]
        self.rng.shuffle(first)  # que los pases directos no queden todos juntos
        self.rounds: list[list[Tie]] = [first]
        while len(self.rounds[-1]) > 1:
            self.rounds.append([Tie() for _ in range(len(self.rounds[-1]) // 2)])
        for index, tie in enumerate(first):
            if tie.b is None:
                self._decide(0, index, tie.a, BY_BYE)

    # ------------------------------------------------------------------ estado

    @property
    def champion(self) -> str | None:
        """El ganador del torneo, cuando termina."""
        return self.rounds[-1][0].winner

    @property
    def done(self) -> bool:
        return self.champion is not None

    def _next_tie(self) -> tuple[int, int, Tie] | None:
        for r, ties in enumerate(self.rounds):
            for i, tie in enumerate(ties):
                if tie.winner is None and tie.a is not None and tie.b is not None:
                    return r, i, tie
        return None

    def _decide(self, r: int, i: int, winner: str, how: str) -> None:
        tie = self.rounds[r][i]
        tie.winner, tie.decided_by = winner, how
        if r + 1 < len(self.rounds):
            following = self.rounds[r + 1][i // 2]
            if i % 2 == 0:
                following.a = winner
            else:
                following.b = winner

    # ---------------------------------------------------------------- partidas

    def _play(self, name_x: str, name_o: str) -> dict[str, Any]:
        seed = self.rng.randrange(2**32)
        try:
            x = self.factories[name_x](seed)
        except Exception as exc:
            return _forfeit(name_x, name_o, name_o, f"{name_x} no se pudo crear: {exc}")
        try:
            o = self.factories[name_o](seed + 1)
        except Exception as exc:
            return _forfeit(name_x, name_o, name_x, f"{name_o} no se pudo crear: {exc}")
        result = play_game(x, o)
        winner = {game.X: name_x, game.O: name_o}.get(result.winner)
        return {
            "x": name_x,
            "o": name_o,
            "winner": winner,
            "moves": list(result.moves),
            "ending": result.ending,
            "detail": result.detail,
        }

    def step(self) -> dict[str, Any] | None:
        """Jugar la siguiente partida. Devuelve qué ha pasado, o ``None`` si ya terminó."""
        found = self._next_tie()
        if found is None:
            return None
        r, i, tie = found
        number = len(tie.games)
        # Partidas pares: a lleva X; impares: b lleva X.
        name_x, name_o = (tie.a, tie.b) if number % 2 == 0 else (tie.b, tie.a)
        record = self._play(name_x, name_o)
        tie.games.append(record)

        played = len(tie.games)
        wins_a, wins_b = tie.wins(tie.a), tie.wins(tie.b)
        if played >= GAMES_PER_TIE and wins_a != wins_b:
            how = BY_GAMES if played == GAMES_PER_TIE else BY_SUDDEN_DEATH
            self._decide(r, i, tie.a if wins_a > wins_b else tie.b, how)
        elif played >= GAMES_PER_TIE + SUDDEN_DEATH:
            self._decide(r, i, self.rng.choice([tie.a, tie.b]), BY_DRAW)
        return {
            "round": r,
            "tie": i,
            "game": record,
            "tie_over": tie.winner is not None,
            "champion": self.champion,
        }

    def to_json(self) -> dict[str, Any]:
        """El cuadro entero, para dibujarlo."""
        return {
            "rounds": [
                {"name": round_name(len(ties)), "ties": [t.to_json() for t in ties]}
                for ties in self.rounds
            ],
            "champion": self.champion,
            "done": self.done,
        }


def _forfeit(name_x: str, name_o: str, winner: str, detail: str) -> dict[str, Any]:
    return {
        "x": name_x,
        "o": name_o,
        "winner": winner,
        "moves": [],
        "ending": "error",
        "detail": detail,
    }
