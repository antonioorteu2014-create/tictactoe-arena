#!/usr/bin/env python3
"""Medir los bots: enfrentarlos N partidas y sacar una tabla de resultados.

Cada pareja se juega **en los dos sentidos** (cada bot con X y con O), porque en
el tres en raya mover primero es una ventaja: un bot probado solo como X es un
bot del que no se sabe nada. La semilla es fija, así que volver a ejecutar el
comando da exactamente los mismos números.

Uso::

    python scripts/benchmark.py                      # todos los bots, 100 partidas
    python scripts/benchmark.py --games 200 --seed 7
    python scripts/benchmark.py voraz aleatorio      # solo esos bots

La salida está en Markdown, lista para pegar en la documentación.
"""

from __future__ import annotations

import argparse
import itertools
import time
from dataclasses import dataclass, field

from tictactoe import game
from tictactoe.player import Player
from tictactoe.registry import AdmittedPlayer, load_players


@dataclass
class Tally:
    """Resultados de un bot contra otro, separados según la ficha con la que jugó."""

    wins: dict[str, int] = field(default_factory=lambda: {game.X: 0, game.O: 0})
    draws: dict[str, int] = field(default_factory=lambda: {game.X: 0, game.O: 0})
    losses: dict[str, int] = field(default_factory=lambda: {game.X: 0, game.O: 0})
    forfeits: int = 0


@dataclass
class Timing:
    """Tiempo que tarda un bot en elegir jugada, acumulado en todas sus partidas."""

    total: float = 0.0
    moves: int = 0
    worst: float = 0.0

    def add(self, seconds: float) -> None:
        self.total += seconds
        self.moves += 1
        self.worst = max(self.worst, seconds)


def _play_timed(
    players: dict[str, Player], timing: dict[str, Timing], names: dict[str, str]
) -> tuple[game.Mark | None, str | None]:
    """Jugar una partida midiendo cada jugada. Devuelve (ganador, quién abandonó)."""
    state = game.initial_state()
    while not game.is_terminal(state):
        mark = game.current_player(state)
        started = time.perf_counter()
        try:
            move = players[mark].choose_move(state)
        except Exception:
            return (game.O if mark == game.X else game.X), mark
        timing[names[mark]].add(time.perf_counter() - started)
        if not game.is_legal(state, move):
            return (game.O if mark == game.X else game.X), mark
        state = game.apply_move(state, move)
    return game.winner(state), None


def run(
    admitted: dict[str, AdmittedPlayer], games: int, seed: int
) -> tuple[dict[tuple[str, str], Tally], dict[str, Timing]]:
    """Jugar ``games`` partidas de cada pareja en cada sentido."""
    tallies: dict[tuple[str, str], Tally] = {}
    timing = {name: Timing() for name in admitted}
    for a, b in itertools.combinations(admitted, 2):
        tallies[a, b], tallies[b, a] = Tally(), Tally()
        for x_name, o_name in ((a, b), (b, a)):
            for g in range(games):
                game_seed = seed * 1_000_003 + g  # una semilla distinta y fija por partida
                players = {
                    game.X: admitted[x_name].cls.create(game_seed),
                    game.O: admitted[o_name].cls.create(game_seed + 500_000),
                }
                names = {game.X: x_name, game.O: o_name}
                winner, forfeit = _play_timed(players, timing, names)
                for name, mark, other in ((x_name, game.X, o_name), (o_name, game.O, x_name)):
                    tally = tallies[name, other]
                    if winner is None:
                        tally.draws[mark] += 1
                    elif winner == mark:
                        tally.wins[mark] += 1
                    else:
                        tally.losses[mark] += 1
                    if forfeit == mark:
                        tally.forfeits += 1
    return tallies, timing


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def report(
    tallies: dict[tuple[str, str], Tally], timing: dict[str, Timing], games: int, seed: int
) -> str:
    """La tabla de resultados, en Markdown."""
    lines = [
        f"{games} partidas por pareja y sentido (semilla {seed}); "
        "es decir, cada bot juega "
        f"{games} veces con X y {games} con O contra cada rival.",
        "",
        "| Bot | Rival | Gana | Empata | Pierde | Gana con X | Gana con O | Abandonos |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for (name, rival), t in tallies.items():
        played = 2 * games
        lines.append(
            f"| {name} | {rival} "
            f"| {_pct(sum(t.wins.values()), played)} "
            f"| {_pct(sum(t.draws.values()), played)} "
            f"| {_pct(sum(t.losses.values()), played)} "
            f"| {_pct(t.wins[game.X], games)} "
            f"| {_pct(t.wins[game.O], games)} "
            f"| {t.forfeits} |"
        )
    lines += [
        "",
        "| Bot | Jugadas medidas | Tiempo medio por jugada | Jugada más lenta |",
        "|---|---:|---:|---:|",
    ]
    for name, t in timing.items():
        mean = 1000 * t.total / t.moves if t.moves else 0.0
        lines.append(f"| {name} | {t.moves} | {mean:.2f} ms | {1000 * t.worst:.1f} ms |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("players", nargs="*", help="bots a enfrentar (por defecto, todos)")
    parser.add_argument("--games", type=int, default=100, help="partidas por pareja y sentido")
    parser.add_argument(
        "--seed", type=int, default=0, help="semilla (misma semilla = mismos números)"
    )
    args = parser.parse_args(argv)

    admitted = load_players()
    if args.players:
        unknown = [name for name in args.players if name not in admitted]
        if unknown:
            parser.error(f"bots desconocidos: {', '.join(unknown)} (hay: {', '.join(admitted)})")
        admitted = {name: admitted[name] for name in args.players}
    if len(admitted) < 2:
        parser.error("hacen falta al menos dos bots")

    tallies, timing = run(admitted, args.games, args.seed)
    print(report(tallies, timing, args.games, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
