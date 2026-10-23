"""El torneo: todos los bots contra todos, y una clasificación en un archivo.

Es una **liguilla**: cada jugador admitido se enfrenta a cada uno de los demás,
en los dos órdenes de salida (con X y con O) y varias partidas por emparejamiento.
Una victoria vale 1 punto, un empate medio y una derrota nada.

Decisiones de diseño:

* **Reutiliza** [`play_game()`][tictactoe.match.play_game] **sin modificarlo.**
  El torneo solo decide quién juega contra quién y cuenta resultados.
* **Es reproducible.** Todo sale de una única semilla: el mismo torneo produce la
  misma clasificación dos veces seguidas. De cada partida se deriva una semilla
  propia, así que añadir un bot no cambia las partidas de los demás.
* **Un bot malo solo se perjudica a sí mismo** (requisito 4.1). Cada partida se
  juega en un **proceso aparte**, vigilado desde fuera:

    * si un bot lanza una excepción o devuelve un movimiento ilegal, pierde (eso
      ya lo controla ``play_game``);
    * si tarda más que el límite en mover, se cierra su proceso y pierde por
      tiempo (``timeout``);
    * si hace caer el proceso entero (por ejemplo con ``os._exit``), pierde por
      caída (``crash``).

  En todos los casos el motivo queda anotado y el torneo sigue con la siguiente
  partida.
* **El resultado va a un archivo**, ``results/leaderboard.json``, y no solo a la
  pantalla: lo lee la web, se guarda en el historial de git y se ve en el diff de
  un pull request.

Uso::

    tictactoe-tournament                         # 10 partidas por emparejamiento
    tictactoe-tournament --games 20 --seed 7
    python -m tictactoe.tournament --output otra/ruta.json

Los **resultados** dependen solo de la semilla. Lo único que puede variar entre
ordenadores es un bot que juega justo en el límite de tiempo.
"""

from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import game
from .match import play_game
from .registry import DEFAULT_MANIFESTS, REPO_ROOT, load_players

TIMEOUT = "timeout"
"""Un jugador tardó más que el límite en elegir movimiento y perdió."""

CRASH = "crash"
"""El proceso de la partida cayó mientras un jugador pensaba, y ese jugador perdió."""

VOID = "void"
"""La partida no se pudo jugar y no se puede culpar a nadie: no da puntos."""

SCHEMA_VERSION = 1
"""Versión del formato de ``leaderboard.json``. Sube si cambia su estructura."""

DEFAULT_OUTPUT = REPO_ROOT / "results" / "leaderboard.json"
"""Dónde se escribe la clasificación por defecto."""

DEFAULT_GAMES = 10
"""Partidas por emparejamiento y sentido (cada bot juega 10 con X y 10 con O)."""

DEFAULT_SEED = 0
"""La semilla de la que sale todo el torneo."""

DEFAULT_MOVE_TIME_LIMIT = 1.0
"""Segundos que tiene un jugador para elegir cada movimiento."""

STARTUP_TIME_LIMIT = 60.0
"""Segundos para arrancar el proceso de una partida y cargar los bots."""

# Quién está pensando ahora mismo, compartido entre el proceso de la partida y el
# torneo. Es un número porque es lo que cabe en una variable compartida.
_NOBODY = 0
_CODE = {game.X: 1, game.O: 2}
_MARK = {1: game.X, 2: game.O}


@dataclass(frozen=True)
class GameRecord:
    """Una partida del torneo.

    Attributes:
        x: el nombre del jugador que llevó X.
        o: el nombre del jugador que llevó O.
        seed: la semilla de la partida (de ella salen las de los dos jugadores).
        winner: el nombre del ganador, o ``None`` si hubo empate o se anuló.
        ending: cómo terminó: ``normal``, ``illegal_move``, ``error``,
            [`TIMEOUT`][tictactoe.tournament.TIMEOUT],
            [`CRASH`][tictactoe.tournament.CRASH] o
            [`VOID`][tictactoe.tournament.VOID].
        detail: en un abandono, qué hizo mal quien perdió; si no, ``""``.
        moves: los movimientos jugados. Vacío si la partida no terminó dentro de
            su proceso (tiempo agotado o caída).
    """

    x: str
    o: str
    seed: int
    winner: str | None
    ending: str
    detail: str
    moves: tuple[int, ...]

    @property
    def loser(self) -> str | None:
        """El nombre del que perdió, o ``None`` si hubo empate o se anuló."""
        if self.winner is None:
            return None
        return self.o if self.winner == self.x else self.x


@dataclass
class Standing:
    """La línea de un jugador en la clasificación."""

    name: str
    icon: str
    authors: list[str]
    description: str
    origin: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    forfeits: int = 0
    """Derrotas por hacer algo no permitido (error, ilegal, tiempo o caída)."""

    @property
    def points(self) -> float:
        """1 por victoria y 0,5 por empate."""
        return self.wins + 0.5 * self.draws


@dataclass
class TournamentResult:
    """El resultado completo de un torneo."""

    standings: list[Standing]
    games: list[GameRecord]
    settings: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Una partida en su propio proceso                                            #
# --------------------------------------------------------------------------- #


class _Watched:
    """Envuelve a un jugador para que el torneo sepa quién piensa y desde cuándo."""

    def __init__(self, inner: Any, mark: str, thinking: Any, since: Any) -> None:
        self._inner = inner
        self._code = _CODE[mark]
        self._thinking = thinking
        self._since = since

    def choose_move(self, state: game.State) -> game.Move:
        # Primero la hora y después quién: el torneo nunca ve a alguien
        # pensando con la hora de la jugada anterior.
        self._since.value = time.monotonic()
        self._thinking.value = self._code
        try:
            return self._inner.choose_move(state)
        finally:
            self._thinking.value = _NOBODY


def _worker(
    manifests: dict[str, Path],
    names: dict[str, str],
    seeds: dict[str, int],
    thinking: Any,
    since: Any,
    conn: Any,
) -> None:
    """Lo que se ejecuta en el proceso de una partida. Envía el resultado por ``conn``."""
    players = load_players(manifests)
    built = {}
    for mark in (game.X, game.O):
        rival = game.O if mark == game.X else game.X
        # Construir un jugador también es código del bot: se vigila igual.
        since.value = time.monotonic()
        thinking.value = _CODE[mark]
        try:
            built[mark] = players[names[mark]].cls.create(seeds[mark])
        except (Exception, SystemExit) as exc:
            conn.send(
                {
                    "winner": rival,
                    "ending": "error",
                    "detail": f"{mark} lanzó {type(exc).__name__} al crearse",
                    "moves": [],
                }
            )
            return
        finally:
            thinking.value = _NOBODY

    result = play_game(
        _Watched(built[game.X], game.X, thinking, since),
        _Watched(built[game.O], game.O, thinking, since),
    )
    conn.send(
        {
            "winner": result.winner,
            "ending": result.ending,
            "detail": result.detail,
            "moves": list(result.moves),
        }
    )


def _game_seeds(seed: int) -> dict[str, int]:
    """Las semillas de los dos jugadores, derivadas de la de la partida."""
    rng = random.Random(seed)
    return {game.X: rng.randrange(2**32), game.O: rng.randrange(2**32)}


def play_isolated(
    name_x: str,
    name_o: str,
    seed: int,
    *,
    manifests: dict[str, Path] | None = None,
    move_time_limit: float = DEFAULT_MOVE_TIME_LIMIT,
) -> GameRecord:
    """Jugar una partida en un proceso aparte, con límite de tiempo por movimiento.

    Nunca lanza una excepción por culpa de un jugador: cualquier fallo se
    convierte en una derrota de quien lo causó, con el motivo en ``detail``.

    Args:
        name_x: el jugador admitido que lleva X.
        name_o: el jugador admitido que lleva O.
        seed: la semilla de la partida.
        manifests: las listas de admitidos de las que cargar a los jugadores.
        move_time_limit: segundos por movimiento.

    Returns:
        El [`GameRecord`][tictactoe.tournament.GameRecord] de la partida.
    """
    if manifests is None:
        manifests = DEFAULT_MANIFESTS
    names = {game.X: name_x, game.O: name_o}

    def record(winner_mark: str | None, ending: str, detail: str, moves=()) -> GameRecord:
        winner = names[winner_mark] if winner_mark in names else None
        return GameRecord(name_x, name_o, seed, winner, ending, detail, tuple(moves))

    def blame(code: int, ending: str, detail: str) -> GameRecord:
        if code not in _MARK:
            return record(None, VOID, detail)
        culprit = _MARK[code]
        return record(game.O if culprit == game.X else game.X, ending, f"{culprit} {detail}")

    # «spawn» arranca un Python limpio: se comporta igual en Mac, Windows y Linux.
    ctx = multiprocessing.get_context("spawn")
    thinking = ctx.Value("i", _NOBODY, lock=False)
    since = ctx.Value("d", 0.0, lock=False)
    receiver, sender = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_worker,
        args=(dict(manifests), names, _game_seeds(seed), thinking, since, sender),
        daemon=True,
    )
    started = time.monotonic()
    process.start()
    sender.close()  # así, si el proceso muere, el receptor lo nota
    try:
        while True:
            if receiver.poll(0.01):
                try:
                    data = receiver.recv()
                except EOFError:  # el proceso cerró sin enviar nada: cayó
                    process.join(1)
                    return blame(
                        thinking.value,
                        CRASH,
                        f"hizo caer el proceso de la partida (código {process.exitcode})",
                    )
                return record(data["winner"], data["ending"], data["detail"], data["moves"])
            code = thinking.value
            if code != _NOBODY and time.monotonic() - since.value > move_time_limit:
                return blame(code, TIMEOUT, f"tardó más de {move_time_limit:g} s en mover")
            if code == _NOBODY and time.monotonic() - started > STARTUP_TIME_LIMIT:
                return blame(code, VOID, "la partida no llegó a empezar a tiempo")
    finally:
        if process.is_alive():
            process.kill()
        process.join()
        receiver.close()


# --------------------------------------------------------------------------- #
# La liguilla                                                                 #
# --------------------------------------------------------------------------- #


def _pairing_seed(seed: int, name_x: str, name_o: str, index: int) -> int:
    """Semilla de una partida. Con un texto, ``random`` da lo mismo en cada ejecución."""
    return random.Random(f"{seed}:{name_x}:{name_o}:{index}").randrange(2**32)


def run_tournament(
    *,
    manifests: dict[str, Path] | None = None,
    games_per_pairing: int = DEFAULT_GAMES,
    seed: int = DEFAULT_SEED,
    move_time_limit: float = DEFAULT_MOVE_TIME_LIMIT,
) -> TournamentResult:
    """Jugar la liguilla entre todos los jugadores admitidos.

    Args:
        manifests: las listas de admitidos. Por defecto, las del proyecto.
        games_per_pairing: partidas por emparejamiento **y sentido**.
        seed: la semilla de la que sale todo el torneo.
        move_time_limit: segundos por movimiento.

    Returns:
        La clasificación ordenada, todas las partidas y la configuración usada.
    """
    if manifests is None:
        manifests = DEFAULT_MANIFESTS
    if games_per_pairing < 1:
        raise ValueError("games_per_pairing debe ser al menos 1")

    admitted = load_players(manifests)
    table = {
        name: Standing(
            name=name,
            icon=p.cls.get_icon(),
            authors=list(p.cls.get_authors()),
            description=p.cls.get_description(),
            origin=p.origin,
        )
        for name, p in admitted.items()
    }

    games: list[GameRecord] = []
    for name_x, name_o in itertools.permutations(admitted, 2):
        for index in range(games_per_pairing):
            rec = play_isolated(
                name_x,
                name_o,
                _pairing_seed(seed, name_x, name_o, index),
                manifests=manifests,
                move_time_limit=move_time_limit,
            )
            games.append(rec)
            if rec.ending == VOID:
                continue
            for name in (name_x, name_o):
                table[name].played += 1
            if rec.winner is None:
                table[name_x].draws += 1
                table[name_o].draws += 1
            else:
                table[rec.winner].wins += 1
                table[rec.loser].losses += 1
                if rec.ending != "normal":
                    table[rec.loser].forfeits += 1

    standings = sorted(
        table.values(), key=lambda s: (-s.points, -s.wins, s.forfeits, s.name.casefold())
    )
    settings = {
        "seed": seed,
        "games_per_pairing": games_per_pairing,
        "move_time_limit": move_time_limit,
    }
    return TournamentResult(standings=standings, games=games, settings=settings)


# --------------------------------------------------------------------------- #
# La clasificación en un archivo                                              #
# --------------------------------------------------------------------------- #


def to_json(result: TournamentResult, now: datetime | None = None) -> dict[str, Any]:
    """El contenido de ``leaderboard.json``: todo lo que la web necesita para dibujarlo."""
    if now is None:
        now = datetime.now(timezone.utc)
    rows = []
    rank = 0
    previous = None
    for position, s in enumerate(result.standings, start=1):
        # Mismos puntos y victorias, mismo puesto.
        if (s.points, s.wins) != previous:
            rank = position
            previous = (s.points, s.wins)
        rows.append(
            {
                "rank": rank,
                "name": s.name,
                "icon": s.icon,
                "authors": s.authors,
                "description": s.description,
                "origin": s.origin,
                "played": s.played,
                "wins": s.wins,
                "draws": s.draws,
                "losses": s.losses,
                "forfeits": s.forfeits,
                "points": s.points,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "settings": result.settings,
        "standings": rows,
        "games": [
            {
                "x": g.x,
                "o": g.o,
                "seed": g.seed,
                "winner": g.winner,
                "ending": g.ending,
                "detail": g.detail,
                "moves": list(g.moves),
            }
            for g in result.games
        ],
    }


def write_leaderboard(result: TournamentResult, path: Path = DEFAULT_OUTPUT) -> Path:
    """Escribir la clasificación en ``path`` (creando su carpeta). Devuelve la ruta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(to_json(result), ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def format_table(result: TournamentResult) -> str:
    """La clasificación como tabla de texto, para la terminal."""
    header = f"{'#':>2}  {'Jugador':<16} {'PJ':>4} {'G':>4} {'E':>4} {'P':>4}"
    lines = [f"{header} {'Abandonos':>9} {'Pts':>6}"]
    for row in to_json(result)["standings"]:
        lines.append(
            f"{row['rank']:>2}  {row['icon']} {row['name']:<14} {row['played']:>4} "
            f"{row['wins']:>4} {row['draws']:>4} {row['losses']:>4} "
            f"{row['forfeits']:>9} {row['points']:>6g}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del comando ``tictactoe-tournament``."""
    parser = argparse.ArgumentParser(
        prog="tictactoe-tournament",
        description="Liguilla entre todos los bots admitidos; escribe la clasificación en JSON.",
    )
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES,
                        help="partidas por emparejamiento y sentido (por defecto, %(default)s)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="semilla del torneo (por defecto, %(default)s)")
    parser.add_argument("--time-limit", type=float, default=DEFAULT_MOVE_TIME_LIMIT,
                        help="segundos por movimiento (por defecto, %(default)s)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="dónde escribir el JSON (por defecto, results/leaderboard.json)")
    args = parser.parse_args(argv)

    result = run_tournament(
        games_per_pairing=args.games, seed=args.seed, move_time_limit=args.time_limit
    )
    print(format_table(result))
    for g in result.games:
        if g.ending not in ("normal",):
            print(f"  · {g.x} vs {g.o}: {g.ending} — {g.detail}")
    path = write_leaderboard(result, args.output)
    print(f"\nClasificación escrita en {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
