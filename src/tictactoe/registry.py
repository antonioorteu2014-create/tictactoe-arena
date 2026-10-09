"""El registro de jugadores: qué bots están admitidos en el proyecto.

Los bots se descubren **solo** a través de listas de admitidos escritas a mano
(``players.yaml``), nunca recorriendo una carpeta. Es una decisión de seguridad:
cuando alguien abre un pull request con un bot, quien revisa ve en el mismo cambio
el archivo nuevo y la línea que lo admite. Recorrer la carpeta automáticamente
escondería qué se está admitiendo y ejecutaría código de un desconocido solo por
estar ahí.

Hay **dos** listas, cada una junto a los bots que admite::

    players/
      builtin/players.yaml   los bots del equipo
      custom/players.yaml    los bots enviados por pull request

La separación hace que un bot enviado solo toque ``custom/``: dos envíos nunca
chocan en la misma lista y ninguno puede modificar los bots del equipo.

Una lista solo dice **qué archivo y qué clase** se admiten. La identidad del bot
(nombre, autores, descripción) la declara la propia clase, de modo que hay una
única fuente de verdad: un bot no puede llamarse de una forma en la lista y de
otra en el código.

Cargar un bot **importa su archivo**, es decir, ejecuta su código. Es aceptable
solo porque los archivos llegan a través de pull requests revisados.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .player import Player

#: Raíz del repositorio (la carpeta que contiene ``src/``).
REPO_ROOT = Path(__file__).resolve().parents[2]
#: Carpeta con todos los jugadores, una subcarpeta por origen.
PLAYERS_DIR = REPO_ROOT / "players"

BUILTIN = "builtin"
"""Origen de los bots del equipo."""

CUSTOM = "custom"
"""Origen de los bots enviados por pull request."""

DEFAULT_MANIFESTS: dict[str, Path] = {
    BUILTIN: PLAYERS_DIR / BUILTIN / "players.yaml",
    CUSTOM: PLAYERS_DIR / CUSTOM / "players.yaml",
}
"""Las listas de admitidos del proyecto, como ``origen -> ruta``, en orden de carga."""


class ManifestError(Exception):
    """Una lista de admitidos o uno de sus bots no cumple los requisitos."""


NAME_PATTERN = re.compile(r"[\w-]{1,40}")
"""Formato de un nombre de jugador: de 1 a 40 letras, números, ``-`` o ``_``.

Sin espacios, porque el nombre aparece en la web, en la clasificación y en los
nombres de las pruebas. Dos nombres que solo se diferencian en mayúsculas
(``"Bot"`` y ``"bot"``) se consideran el mismo."""


@dataclass(frozen=True)
class AdmittedPlayer:
    """Un jugador admitido por una lista.

    Attributes:
        name: su nombre (el que devuelve ``get_name()``), único en el registro.
        cls: la clase del jugador, lista para ``cls.create(seed)``.
        origin: la lista que lo admitió: [`BUILTIN`][tictactoe.registry.BUILTIN]
            o [`CUSTOM`][tictactoe.registry.CUSTOM].
        file: el archivo ``.py`` donde está definido.
    """

    name: str
    cls: type[Player]
    origin: str
    file: Path


def _read_entries(manifest: Path) -> list[dict[str, str]]:
    """Leer y validar la forma de una lista de admitidos."""
    if not manifest.is_file():
        raise ManifestError(f"no existe la lista de admitidos {manifest}")
    try:
        data: Any = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{manifest} no es un YAML válido: {exc}") from exc

    if not isinstance(data, dict) or "players" not in data:
        raise ManifestError(f"{manifest} debe tener una clave 'players' con una lista")
    entries = data["players"]
    if entries is None:  # `players:` sin nada debajo
        return []
    if not isinstance(entries, list):
        raise ManifestError(f"en {manifest}, 'players' debe ser una lista")

    checked: list[dict[str, str]] = []
    for i, entry in enumerate(entries, start=1):
        where = f"en {manifest}, la entrada {i}"
        if not isinstance(entry, dict) or set(entry) != {"file", "class"}:
            raise ManifestError(f"{where} debe tener exactamente 'file' y 'class': {entry!r}")
        for key, value in entry.items():
            if not isinstance(value, str):
                raise ManifestError(
                    f"{where}: '{key}' debe ser un texto, no {type(value).__name__}: {value!r}"
                )
            if not value.strip():
                raise ManifestError(f"{where}: el campo '{key}' está vacío")
        # Solo un nombre de archivo .py, sin carpetas: cada lista admite únicamente
        # archivos de su propia carpeta, así que un envío no puede cargar nada de
        # fuera de players/custom/.
        file = entry["file"]
        if Path(file).name != file or "\\" in file or not file.endswith(".py"):
            raise ManifestError(
                f"{where}: 'file' debe ser solo el nombre de un archivo .py de esta misma "
                f"carpeta, sin rutas: {file!r}"
            )
        checked.append(entry)
    return checked


def _load_class(file: Path, class_name: str, origin: str) -> type[Player]:
    """Importar ``file`` y devolver su clase ``class_name``, comprobando que es un bot."""
    if not file.is_file():
        raise ManifestError(f"no existe el archivo del jugador {file}")

    module_name = f"tictactoe_players.{origin}.{file.stem.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        raise ManifestError(f"no se puede importar {file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except (Exception, SystemExit) as exc:  # SystemExit: un exit() suelto en el archivo
        sys.modules.pop(module_name, None)
        raise ManifestError(f"error al importar {file}: {exc!r}") from exc

    cls = getattr(module, class_name, None)
    if not (inspect.isclass(cls) and issubclass(cls, Player)):
        raise ManifestError(
            f"{file} no define una clase {class_name!r} que herede de tictactoe.player.Player"
        )
    if inspect.isabstract(cls):
        missing = ", ".join(sorted(cls.__abstractmethods__))
        raise ManifestError(f"{class_name} ({file}) no implementa: {missing}")
    return cls


def _ask(cls: type[Player], method: str, where: str) -> Any:
    """Llamar a un método de identidad; si falla, explicar cuál y por qué."""
    try:
        return getattr(cls, method)()
    except (Exception, SystemExit) as exc:
        # El fallo típico es olvidar @classmethod: get_name() pide entonces `self`.
        raise ManifestError(
            f"{where}: {method}() lanzó {type(exc).__name__}: {exc} "
            "(¿falta @classmethod encima del método?)"
        ) from exc


def _check_identity(cls: type[Player], file: Path) -> str:
    """Comprobar la identidad declarada por ``cls`` y devolver su nombre."""
    where = f"{cls.__name__} ({file.name})"
    name = _ask(cls, "get_name", where)
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ManifestError(
            f"{where}: get_name() debe devolver de 1 a 40 letras, números, '-' o '_', "
            f"sin espacios: {name!r}"
        )
    authors = _ask(cls, "get_authors", where)
    if not (
        isinstance(authors, list)
        and authors
        and all(isinstance(a, str) and a.strip() for a in authors)
    ):
        raise ManifestError(
            f"{where}: get_authors() debe devolver una lista con al menos un nombre: {authors!r}"
        )
    description = _ask(cls, "get_description", where)
    if not isinstance(description, str) or not description.strip():
        raise ManifestError(f"{where}: get_description() debe devolver un texto no vacío")
    icon = _ask(cls, "get_icon", where)
    if not isinstance(icon, str) or not icon.strip():
        raise ManifestError(f"{where}: get_icon() debe devolver un texto no vacío")
    return name


def load_players(
    manifests: dict[str, Path] | None = None,
) -> dict[str, AdmittedPlayer]:
    """Cargar todos los jugadores admitidos por las listas ``manifests``.

    Args:
        manifests: ``origen -> ruta del players.yaml``. Por defecto, las dos
            listas del proyecto ([`DEFAULT_MANIFESTS`][tictactoe.registry.DEFAULT_MANIFESTS]).

    Returns:
        ``nombre -> AdmittedPlayer``, en el orden en que aparecen en las listas.

    Raises:
        ManifestError: si una lista está mal formada, un bot no se puede cargar,
            no cumple la plantilla, declara una identidad inválida o repite el
            nombre de otro.
    """
    if manifests is None:
        manifests = DEFAULT_MANIFESTS

    players: dict[str, AdmittedPlayer] = {}
    for origin, manifest in manifests.items():
        manifest = Path(manifest)
        for entry in _read_entries(manifest):
            file = manifest.parent / entry["file"]
            cls = _load_class(file, entry["class"], origin)
            name = _check_identity(cls, file)
            same = [other for other in players.values() if other.name.casefold() == name.casefold()]
            if same:
                raise ManifestError(
                    f"el nombre {name!r} está repetido ({same[0].name!r}): {file} y "
                    f"{same[0].file} (cada jugador debe tener un nombre único, sin "
                    "distinguir mayúsculas)"
                )
            players[name] = AdmittedPlayer(name=name, cls=cls, origin=origin, file=file)
    return players
