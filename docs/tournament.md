# El torneo

El torneo decide qué bot es mejor. Enfrenta a **todos los bots admitidos** (los
del equipo y los enviados por pull request) y escribe la clasificación en
`results/leaderboard.json`.

```bash
tictactoe-tournament                      # 10 partidas por emparejamiento y sentido
tictactoe-tournament --games 20 --seed 7  # más partidas, otra semilla
```

Si el comando no se reconoce (por ejemplo en Windows sin el entorno activado),
`python -m tictactoe.tournament` hace lo mismo.

## Las reglas del torneo

- **Liguilla.** Cada bot juega contra cada uno de los demás, **con X y con O**,
  porque en el tres en raya empezar es una ventaja. Con 3 bots y 10 partidas, cada
  bot juega 40.
- **Puntos.** Victoria 1, empate ½, derrota 0. A igualdad de puntos manda quien
  tiene más victorias; si siguen empatados, comparten puesto.
- **Reproducible.** Todo sale de una única semilla (`--seed`, por defecto 0). El
  mismo torneo da la misma clasificación dos veces seguidas. Cada partida tiene su
  propia semilla, calculada a partir de la del torneo y de los dos nombres, así
  que añadir un bot no cambia las partidas de los demás.
- **Un segundo por movimiento.** Se cambia con `--time-limit`.

## Un bot malo solo se perjudica a sí mismo

El torneo se ejecuta sin nadie mirando y con código de otras personas dentro. Lo
que no puede pasar es que un bot se lleve por delante toda la ejecución. Por eso
**cada partida se juega en un proceso aparte**, vigilado desde fuera:

| Lo que hace el bot | Qué pasa | Motivo anotado |
|---|---|---|
| Lanza una excepción (o llama a `exit()`) | Pierde la partida | `error` |
| Devuelve una casilla ocupada, fuera del tablero o algo que no es un número | Pierde la partida | `illegal_move` |
| Tarda más que el límite en mover | Se cierra su proceso y pierde | `timeout` |
| Hace caer el proceso entero | Pierde la partida | `crash` |

En todos los casos el **rival gana**, el motivo queda en el JSON y el torneo
sigue con la siguiente partida. La columna «Abandonos» de la clasificación
cuenta estas derrotas.

Las pruebas lo demuestran con bots rotos a propósito: uno que lanza un error,
uno que hace trampa, uno que se queda dormido y uno que tira el proceso. Cada uno
pierde solo sus partidas y la tabla sale completa.

!!! note "Lo que no protege"
    Un proceso aparte con límite de tiempo frena a un bot torpe, no a uno escrito
    para hacer daño (que borre archivos, por ejemplo). Contra eso protege la
    revisión: ningún bot entra en el torneo sin un pull request aprobado.

## El archivo `leaderboard.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-18T12:00:00+00:00",
  "settings": { "seed": 0, "games_per_pairing": 10, "move_time_limit": 1.0 },
  "standings": [
    {
      "rank": 1, "name": "minimax", "icon": "🧠",
      "authors": ["Antonio Orteu", "Álvaro Domingo", "María Sanz"],
      "description": "…", "origin": "builtin",
      "played": 40, "wins": 19, "draws": 21, "losses": 0, "forfeits": 0, "points": 29.5
    }
  ],
  "games": [
    { "x": "minimax", "o": "voraz", "seed": 123, "winner": null,
      "ending": "normal", "detail": "", "moves": [4, 0, 8, 2, 1, 7, 6, 3, 5] }
  ]
}
```

| Campo | Qué es |
|---|---|
| `schema_version` | Versión del formato. Sube si cambia la estructura. |
| `generated_at` | Cuándo terminó el torneo (hora UTC). |
| `settings` | Semilla, partidas y límite de tiempo usados. |
| `standings` | La clasificación, ya ordenada, con todo lo que la web necesita para dibujarla. |
| `games` | Cada partida: quién llevó cada ficha, el ganador (`null` si empate), cómo terminó y los movimientos. |

Se guarda en un archivo, y no solo en la pantalla, para que lo lea la web, quede en
el historial de git y se vea en el diff de un pull request.

## Se juega solo cada día

La web publica siempre la clasificación de un torneo recién jugado. El torneo se
juega dentro del flujo que publica la web (`.github/workflows/pages.yml`), en
tres momentos:

- **Todos los días a las 05:00 UTC** (`schedule`), sin que nadie haga nada.
- **Cada vez que cambia `main`** (`push`), por ejemplo al fusionar un bot nuevo:
  así entra en la tabla al momento.
- **A mano**, con el botón **Run workflow** de la pestaña Actions
  (`workflow_dispatch`).

El flujo deja la clasificación en `web/leaderboard.json`, junto a la página, y
el marcador la descarga con `cache: "no-cache"` para no enseñar una copia vieja.
Ese archivo se genera en cada publicación y no se guarda en git.

!!! note "Por qué no se hace commit de la clasificación"
    `main` está protegida: solo entra un pull request aprobado y con las pruebas
    en verde, sin excepciones. Un flujo que hiciera `git push` a `main` sería
    rechazado. Además, GitHub no lanza ningún flujo con los commits que hace
    otro flujo, así que la web no se enteraría. Jugar el torneo en el mismo
    flujo que publica la web evita los dos problemas.