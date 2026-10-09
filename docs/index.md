# Tic-Tac-Toe Arena

**Tic-Tac-Toe Arena** es el tres en raya convertido en un proyecto open-source.
Reúne tres piezas: el juego, escrito como una librería de Python que cualquiera
puede instalar; una plataforma para que otros desarrolladores programen sus
propios bots sin tocar el código del juego; y un torneo automático que enfrenta a
todos los bots y publica la clasificación.

!!! note "Proyecto en construcción"
    Ya están las [reglas del juego](rules.md), implementadas y probadas, y se
    puede jugar una partida entre dos personas en la terminal. El API de
    jugadores, los bots, la web y el torneo se documentarán aquí a medida que se
    implementen.

## Instalación

Requiere **Python 3.10 o superior**.

```bash
git clone https://github.com/antonioorteu2014-create/tictactoe-arena.git
cd tictactoe-arena
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

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
