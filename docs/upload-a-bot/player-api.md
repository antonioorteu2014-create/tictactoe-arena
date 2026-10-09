# El API de jugador

Un **bot** (o *jugador*) es una clase de Python que hereda de
`tictactoe.player.Player`. No hace falta conocer el resto del proyecto: basta con
implementar **cuatro métodos**, y el proyecto se encarga de todo lo demás (los
turnos, comprobar los movimientos, el torneo y la web).

!!! tip "¿Quieres enviar tu bot?"
    Esta página explica **qué** tiene que hacer un bot. El paso a paso para
    enviarlo por pull request está en [Enviar tu bot](submit-a-player.md).

## Lo que tienes que implementar

| Método | Obligatorio | Qué devuelve |
|---|---|---|
| `get_name()` | sí | El nombre de tu bot, **único** en el proyecto: hasta 40 letras, números, guiones o guiones bajos, sin espacios. Ejemplo: `"oportunista"`. |
| `get_authors()` | sí | La lista de autores, con al menos un nombre: `["Ana García"]`. |
| `get_description()` | sí | Una o dos frases que expliquen **cómo decide** tu bot. |
| `choose_move(state)` | sí | La casilla, del 0 al 8, donde quieres jugar. |
| `get_icon()` | no | Un emoji para la web y la clasificación. Por defecto, 🤖. |
| `create(seed)` | no | Cómo construir tu bot para una partida. Sobrescríbelo si usas azar. |

Los tres primeros son **métodos de clase** (`@classmethod`): el proyecto lee la
identidad de tu bot sin construirlo, para mostrarla en la web y en la
clasificación.

## Lo que recibes: el tablero

`choose_move` recibe el tablero como un **texto de 9 caracteres**, una casilla
por carácter, leyendo por filas de izquierda a derecha y de arriba abajo:

- `"X"`: casilla con ficha de X.
- `"O"`: casilla con ficha de O (la letra, no el cero).
- `"."`: casilla vacía.

```
"X.O.X...O"   es el tablero    X | . | O
                               . | X | .
                               . | . | O
```

El tablero **no se puede modificar**: es un `str`, y Python no permite cambiar
un `str`. Si quieres probar jugadas, usa `game.apply_move`, que devuelve un
tablero nuevo.

**¿Con qué ficha juegas?** No te lo dicen: se deduce del tablero, porque siempre
empieza X. Usa `game.current_player(state)`, que devuelve `"X"` u `"O"`. Así, el
mismo bot sirve para jugar con las dos fichas.

Solo se te llama cuando **la partida no ha terminado** y **te toca a ti**: siempre
hay al menos una casilla libre.

## Lo que devuelves: una casilla

Un `int` de Python del **0 al 8**, con esta numeración:

```
 0 | 1 | 2
---+---+---
 3 | 4 | 5
---+---+---
 6 | 7 | 8
```

!!! warning "Si tu bot hace algo no permitido, pierde la partida"
    Si `choose_move` devuelve una casilla ocupada, un número fuera de 0-8, algo
    que no sea un `int` (por ejemplo `"4"`, `4.0` o `None`) o **lanza una
    excepción**, tu bot **pierde esa partida por abandono**. La partida, el resto
    de bots y el torneo siguen funcionando con normalidad.

## Funciones útiles del módulo `tictactoe.game`

Las reglas del juego están en `tictactoe.game`. Son las mismas que usa el
proyecto para arbitrar, así que tu bot y el árbitro nunca discrepan:

| Función | Qué hace |
|---|---|
| `legal_moves(state)` | Las casillas donde se puede jugar, de menor a mayor. |
| `apply_move(state, move)` | El tablero **nuevo** tras jugar `move` (el original no cambia). |
| `current_player(state)` | A quién le toca: `"X"` u `"O"`. |
| `winner(state)` | `"X"`, `"O"` o `None` si nadie ha ganado (todavía o porque hubo empate). |
| `is_terminal(state)` | Si la partida ha terminado. |
| `is_draw(state)` | Si la partida ha terminado en empate. |
| `WINNING_LINES` | Las 8 líneas ganadoras, como tríos de casillas. |

La lista completa, con todos los detalles, está en la
[Referencia del API](../api.md).

## Un bot completo

Este bot gana si puede, bloquea si debe y, si no, juega al azar. Es un archivo
completo, listo para copiar:

```python
"""El jugador «oportunista»: gana si puede, bloquea si debe y, si no, juega al azar."""

from __future__ import annotations

import random

from tictactoe import game
from tictactoe.player import Player


class Oportunista(Player):
    """Gana si puede, bloquea si debe y, si no, juega al azar."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    @classmethod
    def create(cls, seed: int) -> Oportunista:
        return cls(seed)

    @classmethod
    def get_name(cls) -> str:
        return "oportunista"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Tu Nombre"]

    @classmethod
    def get_description(cls) -> str:
        return (
            "Gana si puede en una jugada, bloquea si el rival puede ganar y, "
            "si no, juega al azar."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🦊"

    def choose_move(self, state: game.State) -> game.Move:
        me = game.current_player(state)
        rival = game.O if me == game.X else game.X
        moves = game.legal_moves(state)

        # 1. Si alguna jugada completa una línea mía, la juego y gano.
        for move in moves:
            if _completes_line(state, move, me):
                return move

        # 2. Si el rival completaría una línea en alguna casilla, la ocupo yo.
        for move in moves:
            if _completes_line(state, move, rival):
                return move

        # 3. Si no, al azar.
        return self._rng.choice(moves)


def _completes_line(state: game.State, cell: game.Move, mark: str) -> bool:
    """¿Poner `mark` en la casilla libre `cell` completaría una línea de tres?"""
    for line in game.WINNING_LINES:
        if cell in line and all(state[c] == mark for c in line if c != cell):
            return True
    return False
```

!!! note "Sobre el azar y la semilla"
    El proyecto construye cada bot con `create(seed)`. Si tu bot usa azar, crea
    un generador propio con esa semilla, como en el ejemplo
    (`random.Random(seed)`), en lugar de usar el `random` global: así, con la
    misma semilla, tu bot juega exactamente igual, y una partida que falle se
    puede repetir. Si tu bot no usa azar, no hace falta que sobrescribas
    `create`.

## Normas para que tu bot sea admitido

- Hereda de `tictactoe.player.Player` e implementa los cuatro métodos
  obligatorios.
- Su nombre es único (las pruebas rechazan un nombre repetido).
- Devuelve **siempre** un movimiento legal y no lanza excepciones.
- Solo usa la librería estándar de Python y el paquete `tictactoe`: nada de
  dependencias extra.
- No accede a la red ni a archivos, ni ejecuta otros programas.
- Responde rápido: el torneo pondrá un límite de tiempo por partida.

La **prueba de contrato** (`tests/test_players.py`) comprueba automáticamente en
cada pull request, sin que tengas que escribir pruebas para tu bot, que este se
carga, que su identidad es válida y su nombre único, que se construye con una
semilla, que devuelve movimientos legales y que juega partidas completas sin
perder por abandono. Las demás normas (dependencias, red, archivos) las
comprueba la persona que revisa el pull request, y el límite de tiempo llegará
con el torneo.
