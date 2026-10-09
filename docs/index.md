# Tic-Tac-Toe Arena

**Tic-Tac-Toe Arena** es el tres en raya convertido en un proyecto open-source.
Reúne tres piezas: el juego, escrito como una librería de Python que cualquiera
puede instalar; una plataforma para que otros desarrolladores programen sus
propios bots sin tocar el código del juego; y un torneo automático que enfrenta a
todos los bots y publica la clasificación.

!!! note "Proyecto en construcción"
    Ya están las [reglas del juego](rules.md) y la plataforma de bots: se puede
    jugar entre dos personas en la terminal y cualquiera puede
    [escribir y enviar su propio bot](upload-a-bot/player-api.md). La web
    jugable y el torneo se documentarán aquí a medida que se implementen.

## ¿Quieres escribir un bot?

1. Lee [El API de jugador](upload-a-bot/player-api.md): qué tiene que hacer un
   bot, con un ejemplo completo.
2. Sigue [Enviar tu bot](upload-a-bot/submit-a-player.md): el paso a paso hasta
   el pull request.
3. Consulta la [Referencia del API](api.md) cuando necesites un detalle.

## Instalación

Requiere **Python 3.10 o superior**.

=== "Mac / Linux"

    ```bash
    git clone https://github.com/antonioorteu2014-create/tictactoe-arena.git
    cd tictactoe-arena
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    ```

=== "Windows (PowerShell)"

    ```powershell
    git clone https://github.com/antonioorteu2014-create/tictactoe-arena.git
    cd tictactoe-arena
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    ```

El entorno está activado cuando la línea de la terminal empieza por `(.venv)`.

## Jugar en la terminal

Dos personas, un teclado:

```bash
tictactoe-play
```

Cada jugador escribe el número de la casilla donde quiere poner su ficha, del 1
al 9. Las casillas libres se muestran con su número.

## Usar el juego desde Python

Las reglas son funciones puras del módulo `tictactoe.game`. Una partida completa,
sin ninguna interfaz:

```python
from tictactoe import game

state = game.initial_state()              # "........."
for move in [4, 1, 0, 2, 8]:              # X: 4, 0, 8 · O: 1, 2
    state = game.apply_move(state, move)

print(state)                              # "XOO.X...X"
print(game.winner(state))                 # "X"
print(game.is_terminal(state))            # True
```

Cómo se representan el tablero y los movimientos está explicado al final de las
[reglas del juego](rules.md#como-lo-representa-el-codigo).

## Autores

Antonio Orteu, Álvaro Domingo y María Sanz — Inteligencia Artificial, 3.º MAT-A,
CUNEF Universidad (curso 2026/2027). Distribuido bajo la licencia MIT.
