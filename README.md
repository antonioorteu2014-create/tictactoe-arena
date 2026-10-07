# Tic-Tac-Toe Arena

[![Tests](https://github.com/antonioorteu2014-create/tictactoe-arena/actions/workflows/tests.yml/badge.svg)](https://github.com/antonioorteu2014-create/tictactoe-arena/actions/workflows/tests.yml)
[![Documentation](https://readthedocs.org/projects/tictactoe-arena/badge/?version=latest)](https://tictactoe-arena.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

El **tres en raya** como proyecto open-source: el juego en una librería de Python,
una plataforma para que cualquiera programe y suba su propio bot, y un torneo
automático que enfrenta a todos los bots y publica la clasificación.

> **Estado:** en construcción. Por ahora existe la base del proyecto (paquete
> instalable, pruebas automáticas y documentación); el juego llega en los
> siguientes pasos.

## Instalación

Requiere **Python 3.10 o superior**.

```bash
git clone https://github.com/antonioorteu2014-create/tictactoe-arena.git
cd tictactoe-arena
python3 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Para comprobar que todo funciona:

```bash
pytest          # ejecuta las pruebas
ruff check .    # comprueba el estilo del código
```

## Estructura del proyecto

```
tictactoe-arena/
├── src/tictactoe/      # la librería: el código del juego
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
necesita una revisión aprobatoria y las pruebas en verde.

## Autores

Antonio Orteu, Álvaro Domingo y María Sanz — Inteligencia Artificial, 3.º MAT-A,
CUNEF Universidad (curso 2026/2027).

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).
