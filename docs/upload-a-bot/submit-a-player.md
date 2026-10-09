# Enviar tu bot

Este tutorial te lleva **desde cero hasta un pull request** con tu bot en
`tictactoe-arena`. No necesitas conocer el código del proyecto: solo seguir los
pasos en orden.

Necesitas:

- Una cuenta de **GitHub**.
- **git** y **Python 3.10 o superior** instalados. Compruébalo en una terminal con
  `git --version` y `python3 --version` (en Windows, `python --version`).

Qué es un bot y qué tiene que hacer está explicado en
[El API de jugador](player-api.md). Aquí vamos directamente a enviarlo.

---

## 1. Haz un fork del repositorio

Un **fork** es tu propia copia del repositorio en tu cuenta de GitHub: ahí
podrás subir tus cambios sin necesitar permisos en el nuestro.

1. Abre <https://github.com/antonioorteu2014-create/tictactoe-arena>.
2. Pulsa **Fork** (arriba a la derecha) y después **Create fork**.

## 2. Descarga tu fork y prepara el proyecto

En una terminal, sustituyendo `TU-USUARIO` por tu usuario de GitHub:

=== "Mac / Linux"

    ```bash
    git clone https://github.com/TU-USUARIO/tictactoe-arena.git
    cd tictactoe-arena
    git switch -c anadir-mi-bot
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    ```

=== "Windows (PowerShell)"

    ```powershell
    git clone https://github.com/TU-USUARIO/tictactoe-arena.git
    cd tictactoe-arena
    git switch -c anadir-mi-bot
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    ```

- `git switch -c anadir-mi-bot` crea una **rama** para tu cambio.
- `.venv` es un entorno aislado para el proyecto. Sabrás que está activado
  porque la línea de la terminal empieza por `(.venv)`.

Para comprobar que todo está bien, ejecuta `pytest -q`: debe terminar con
`passed` y sin `failed`.

## 3. Crea el archivo de tu bot

Crea un archivo en la carpeta **`players/custom/`**. Ponle de nombre tu usuario
de GitHub y el de tu bot, con guiones, para que no choque con el de nadie:
`players/custom/TU-USUARIO-oportunista.py`.

Copia dentro este bot completo y cámbialo a tu gusto. Como mínimo, cambia el
**nombre** (`get_name`), los **autores** y la **descripción**:

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

!!! warning "El nombre debe ser único"
    `get_name()` no puede coincidir con el de ningún otro bot del proyecto. Si ya
    existe, las pruebas fallarán con el mensaje «el nombre … está repetido».

## 4. Apunta tu bot en la lista de admitidos

Ningún bot entra solo por estar en la carpeta: hay que **admitirlo** en
`players/custom/players.yaml`. Abre ese archivo y añade **una** entrada con el
nombre de tu archivo y el de tu clase. Si la lista está vacía (`players: []`),
sustituye esa línea; si ya hay otros bots, añade la tuya al final:

```yaml
players:
  - file: TU-USUARIO-oportunista.py
    class: Oportunista
```

No toques nada más del archivo ni de ningún otro.

## 5. Comprueba que tu bot pasa el examen

Ejecuta las pruebas del proyecto. La **prueba de contrato** encuentra tu bot sola
(no tienes que escribir pruebas) y comprueba que tiene identidad, que se
construye con una semilla, que devuelve siempre movimientos legales y que juega
partidas completas sin abandonar:

```bash
pytest -q
ruff check players/custom
```

Las dos órdenes deben terminar sin errores: `pytest` con `passed` y sin
`failed`, y `ruff` con `All checks passed!`. Si `pytest` falla, el mensaje dice
qué ha hecho mal tu bot y en qué posición, por ejemplo:

```text
oportunista no cumple el contrato:
  Oportunista devolvió el movimiento ilegal 4 en 'XO.XO....'
```

Si quieres ver a tu bot jugar una partida contra el bot aleatorio:

```bash
python -c "
from tictactoe.registry import load_players
from tictactoe.match import play_game
players = load_players()
yo = players['oportunista'].cls.create(0)
rival = players['aleatorio'].cls.create(0)
print(play_game(yo, rival))
"
```

(Cambia `oportunista` por el nombre de tu bot.)

## 6. Sube tu rama

```bash
git add players/custom
git commit -m "Añadir el bot oportunista"
git push -u origin anadir-mi-bot
```

Al hacer `git push`, GitHub puede pedirte usuario y contraseña. La contraseña
normal no sirve: hace falta un **token**. Créalo en GitHub, en *Settings →
Developer settings → Personal access tokens → Tokens (classic)*, con el permiso
`repo`. Un token es como una contraseña: no lo pegues nunca en un chat ni en un
archivo.

## 7. Abre el pull request

1. Abre tu fork en GitHub. Aparecerá un aviso con el botón **Compare & pull
   request**: púlsalo.
2. Comprueba que arriba pone **base repository:
   `antonioorteu2014-create/tictactoe-arena`**, **base: `main`**, y a la derecha
   tu fork y tu rama `anadir-mi-bot`.
3. Rellena la plantilla: qué hace tu bot y cómo lo has probado.
4. Pulsa **Create pull request**.

## 8. Qué pasa después

- **Las comprobaciones automáticas** se ejecutan solas en tu pull request: las
  mismas pruebas que ejecutaste en el paso 5, en Python 3.10, 3.12 y 3.14. Si
  alguna sale en rojo, abre el detalle para ver el error, corrígelo en tu
  ordenador, haz otro commit y `git push`: el pull request se actualiza solo.
- **Un miembro del equipo revisa** tu bot: comprueba que solo has añadido tu
  archivo y tu línea en la lista, y que cumple las normas.
- Con las comprobaciones en verde y la revisión aprobada, **lo fusionamos**, y
  tu bot pasa a formar parte del proyecto: aparecerá en la web y en el torneo.

## Criterios de aceptación

Tu pull request se acepta si:

- [x] Solo añade **un archivo** en `players/custom/` y **una entrada** en
      `players/custom/players.yaml`.
- [x] La clase hereda de `tictactoe.player.Player` y tiene un nombre único.
- [x] Las comprobaciones automáticas están en verde.
- [x] Solo usa la librería estándar de Python y el paquete `tictactoe`.
- [x] No accede a la red ni a archivos, ni ejecuta otros programas.
