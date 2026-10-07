# Tic-Tac-Toe Arena

**Tic-Tac-Toe Arena** es el tres en raya convertido en un proyecto open-source.
Reúne tres piezas: el juego, escrito como una librería de Python que cualquiera
puede instalar; una plataforma para que otros desarrolladores programen sus
propios bots sin tocar el código del juego; y un torneo automático que enfrenta a
todos los bots y publica la clasificación.

!!! note "Proyecto en construcción"
    Por ahora existe la base del proyecto: el paquete instalable, las pruebas
    automáticas y este sitio de documentación. Las reglas del juego, el API de
    jugadores y el torneo se documentarán aquí a medida que se implementen.

## Instalación

Requiere **Python 3.10 o superior**.

```bash
git clone https://github.com/antonioorteu2014-create/tictactoe-arena.git
cd tictactoe-arena
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Autores

Antonio Orteu, Álvaro Domingo y María Sanz — Inteligencia Artificial, 3.º MAT-A,
CUNEF Universidad (curso 2026/2027). Distribuido bajo la licencia MIT.
