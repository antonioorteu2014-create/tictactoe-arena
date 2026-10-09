# Tic-Tac-Toe Arena

[![Tests](https://github.com/antonioorteu2014-create/tictactoe-arena/actions/workflows/tests.yml/badge.svg)](https://github.com/antonioorteu2014-create/tictactoe-arena/actions/workflows/tests.yml)
[![Documentation](https://readthedocs.org/projects/tictactoe-arena/badge/?version=latest)](https://tictactoe-arena.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**▶ Juega ahora en el navegador:** <https://antonioorteu2014-create.github.io/tictactoe-arena/>

El **tres en raya** como proyecto open-source: el juego en una librería de Python,
una plataforma para que cualquiera programe y suba su propio bot, y un torneo
automático que enfrenta a todos los bots y publica la clasificación.

> **Estado:** en construcción. Ya se puede jugar contra un bot en la web, jugar
> entre dos personas en la terminal, y cualquiera puede escribir y enviar su
> propio bot. El torneo automático llega en el siguiente paso.

- **Documentación:** <https://tictactoe-arena.readthedocs.io>

## Instalación

Requiere **Python 3.10 o superior**.

```bash
git clone https://github.com/antonioorteu2014-create/tictactoe-arena.git
cd tictactoe-arena
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

En **Windows (PowerShell)**, las líneas del entorno son distintas:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

El entorno está activado cuando la línea de la terminal empieza por `(.venv)`.

Para comprobar que todo funciona:

```bash
pytest          # ejecuta las pruebas
ruff check .    # comprueba el estilo del código
```

Para probar la web en tu ordenador (hay que servir la carpeta, no abrir el
archivo con doble clic):

```bash
python scripts/build_web.py
python -m http.server 8000 --directory web    # y abre http://localhost:8000
```

## Jugar

En el **navegador**, contra un bot y sin instalar nada:
<https://antonioorteu2014-create.github.io/tictactoe-arena/>

En la terminal, entre dos personas:

```bash
tictactoe-play
```

(Si en Windows el comando no se reconoce, usa `python -m tictactoe`.)

O desde Python, sin ninguna interfaz:

```python
from tictactoe import game

state = game.initial_state()              # "........."
for move in [4, 1, 0, 2, 8]:              # casillas 0-8, por filas
    state = game.apply_move(state, move)
print(game.winner(state))                 # "X"
```

Las reglas completas y la representación del tablero están en
[Reglas del juego](https://tictactoe-arena.readthedocs.io/es/latest/rules/).

## Escribir un bot

Un bot es una clase que hereda de `tictactoe.player.Player` e implementa un
método, `choose_move(state)`, que devuelve la casilla (0-8) donde jugar. Se
envía por pull request: un archivo en `players/custom/` y una línea en
`players/custom/players.yaml`. Las pruebas lo examinan solas.

- [El API de jugador](https://tictactoe-arena.readthedocs.io/es/latest/upload-a-bot/player-api/):
  qué tiene que hacer un bot, con un ejemplo completo.
- [Enviar tu bot](https://tictactoe-arena.readthedocs.io/es/latest/upload-a-bot/submit-a-player/):
  el paso a paso hasta el pull request.

## Estructura del proyecto

```
tictactoe-arena/
├── src/tictactoe/      # la librería: reglas, API de jugadores y partidas
├── players/            # los bots: builtin/ (del equipo) y custom/ (enviados)
├── web/                # la página web (GitHub Pages + Pyodide)
├── scripts/            # build_web.py: empaqueta el Python para la web
├── tests/              # pruebas automáticas (pytest)
├── docs/               # documentación (MkDocs → Read the Docs)
├── .github/            # pruebas automáticas en GitHub Actions y plantilla de PR
├── pyproject.toml      # descripción del paquete y de sus dependencias
└── mkdocs.yml          # configuración del sitio de documentación
```

## Documentación

La documentación completa está publicada en
<https://tictactoe-arena.readthedocs.io>.

## Cómo contribuir

La rama `main` está protegida: todo cambio llega mediante un *pull request* que
necesita una revisión aprobatoria y las pruebas en verde. Ver
[CONTRIBUTING.md](CONTRIBUTING.md).

## Autores

Antonio Orteu, Álvaro Domingo y María Sanz — Inteligencia Artificial, 3.º MAT-A,
CUNEF Universidad (curso 2026/2027).

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).
