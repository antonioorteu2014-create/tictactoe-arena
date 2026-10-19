#!/usr/bin/env python3
"""Empaquetar el Python del proyecto para que la web lo ejecute en el navegador.

La página web usa el **mismo** Python que las pruebas y el torneo, a través de
Pyodide. Este script lo reúne en un único archivo, ``web/py.zip``::

    py.zip
    ├── tictactoe/     el paquete (copiado de src/)
    ├── players/       los bots: builtin/ y custom/, cada uno con su players.yaml
    └── webglue.py     el puente entre la página y el Python

En el navegador, ``web/engine.js`` descarga ``py.zip``, lo descomprime e importa
``webglue``.

``py.zip`` es un archivo **generado**: no se guarda en git (está en .gitignore).
Lo crea el flujo de publicación (``.github/workflows/pages.yml``) cada vez que
cambia ``main``. Para probar la web en local::

    python scripts/build_web.py
    python -m http.server 8000 --directory web
    # y abrir http://localhost:8000
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"
ZIP_PATH = WEB / "py.zip"

#: Lo que no debe viajar al navegador.
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.md")


def build(zip_path: Path = ZIP_PATH) -> Path:
    """Crear ``zip_path`` con el paquete, los bots y el puente. Devuelve la ruta."""
    staging = zip_path.parent / "py"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        shutil.copytree(REPO_ROOT / "src" / "tictactoe", staging / "tictactoe", ignore=_IGNORE)
        shutil.copytree(REPO_ROOT / "players", staging / "players", ignore=_IGNORE)
        shutil.copy2(WEB / "webglue.py", staging / "webglue.py")

        zip_path.unlink(missing_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(staging).as_posix())
    finally:
        # La carpeta intermedia se borra siempre: el flujo de publicación sube
        # toda web/, y dejarla publicaría una copia suelta del paquete.
        shutil.rmtree(staging, ignore_errors=True)
    return zip_path


def main() -> int:
    path = build()
    print(f"Creado {path} ({path.stat().st_size // 1024} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
