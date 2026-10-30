"""El modo **preguntas**: para poner ficha hay que acertar una pregunta de la asignatura.

Pensado para que dos personas de la clase de Inteligencia Artificial se midan
también en lo que saben. Cada vez que un jugador elige una casilla, le sale una
pregunta tipo test (4 opciones, una correcta) sacada de los apuntes de la
asignatura. Si acierta, pone su ficha; si falla, no la pone y el turno pasa al
rival. Por lo demás, se gana como en el clásico.

No admite bots: la gracia es comparar lo que saben las personas.

**Formato del estado:** ``"<9 casillas>|<turno>"``, por ejemplo
``"X...O....|X"``. A diferencia del clásico, el turno se guarda: como fallar una
pregunta pasa el turno sin poner ficha, el número de fichas ya no dice a quién le
toca.

Las preguntas están en ``preguntas.json``, junto a este archivo. La página nunca
recibe la respuesta correcta antes de contestar: la comprueba
[`answer`][tictactoe.modes.quiz.answer].
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from .. import game
from .base import EMPTY, Mark, Mode, O, State, X, line_of, rival

QUESTIONS_FILE = Path(__file__).with_name("preguntas.json")
"""El banco de preguntas."""

OPTIONS = 4
"""Opciones de cada pregunta."""

_FORMAT = re.compile(r"([XO.]{9})\|([XO])")
_ID = re.compile(r"\d\d-\d\d-\d\d")


@dataclass(frozen=True)
class Question:
    """Una pregunta tipo test."""

    id: str
    """Identificador único: ``"<tema>-<archivo>-<número>"``, p. ej. ``"04-03-07"``."""
    tema: str
    """El tema de los apuntes del que sale."""
    pregunta: str
    opciones: tuple[str, ...]
    correcta: int
    """Posición (0-3) de la opción correcta."""
    explicacion: str
    """Por qué la correcta es la correcta."""

    def public(self) -> dict[str, Any]:
        """La pregunta sin la respuesta: lo que se le enseña al jugador."""
        return {
            "id": self.id,
            "tema": self.tema,
            "pregunta": self.pregunta,
            "opciones": list(self.opciones),
        }


def question_problems(data: object) -> list[str]:
    """Los problemas de un banco de preguntas, o una lista vacía si es válido."""
    if not isinstance(data, list) or not data:
        return ["el banco debe ser una lista no vacía"]
    problems = []
    seen: set[str] = set()
    for position, item in enumerate(data, start=1):
        label = f"pregunta {position}"
        if not isinstance(item, dict):
            problems.append(f"{label}: debe ser un objeto")
            continue
        qid = item.get("id")
        label = f"pregunta {qid!r}"
        if not isinstance(qid, str) or not _ID.fullmatch(qid):
            problems.append(f"{label}: id debe tener la forma '04-03-07'")
        elif qid in seen:
            problems.append(f"{label}: id repetido")
        else:
            seen.add(qid)
        for key in ("tema", "pregunta", "explicacion"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                problems.append(f"{label}: falta el texto de {key}")
        options = item.get("opciones")
        if (
            not isinstance(options, list)
            or len(options) != OPTIONS
            or not all(isinstance(o, str) and o.strip() for o in options)
        ):
            problems.append(f"{label}: debe tener {OPTIONS} opciones de texto")
        elif len({o.strip().lower() for o in options}) != OPTIONS:
            problems.append(f"{label}: tiene opciones repetidas")
        correct = item.get("correcta")
        if type(correct) is not int or not 0 <= correct < OPTIONS:
            problems.append(f"{label}: correcta debe ser un número del 0 al {OPTIONS - 1}")
    return problems


@cache
def load_questions() -> tuple[Question, ...]:
    """Cargar y comprobar el banco de preguntas (una sola vez)."""
    data = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    problems = question_problems(data)
    if problems:
        raise ValueError(f"banco de preguntas no válido: {problems[0]}")
    return tuple(
        Question(
            id=item["id"],
            tema=item["tema"],
            pregunta=item["pregunta"],
            opciones=tuple(item["opciones"]),
            correcta=item["correcta"],
            explicacion=item["explicacion"],
        )
        for item in data
    )


def get_question(question_id: str) -> Question:
    """La pregunta con ese id. Lanza ``ValueError`` si no existe."""
    for question in load_questions():
        if question.id == question_id:
            return question
    raise ValueError(f"no existe la pregunta {question_id!r}")


def pick_question(seed: int, exclude: frozenset[str] | set[str] = frozenset()) -> Question:
    """Una pregunta al azar que no esté en ``exclude`` (las ya usadas en la partida).

    Con la misma semilla sale la misma pregunta. Si ya se han usado todas, se
    vuelve a elegir entre todas.
    """
    questions = load_questions()
    fresh = [q for q in questions if q.id not in exclude] or list(questions)
    return random.Random(seed).choice(fresh)


def _parse(state: object) -> tuple[str, Mark]:
    if not isinstance(state, str):
        raise ValueError(f"el estado debe ser un str, no {type(state).__name__}")
    match = _FORMAT.fullmatch(state)
    if match is None:
        raise ValueError(f"estado mal formado: {state!r} (se espera '<9 casillas>|<turno>')")
    board, turn = match.groups()
    x_line, o_line = line_of(board, X), line_of(board, O)
    if x_line and o_line:
        raise ValueError(f"estado imposible: {state!r}: los dos tienen tres en raya")
    owner = X if x_line else O if o_line else None
    if owner is not None and turn == owner:
        raise ValueError(f"estado imposible: {state!r}: la línea es de quien tiene el turno")
    return board, turn


class QuizMode(Mode):
    """Tres en raya clásico, pero para poner ficha hay que acertar una pregunta."""

    key = "preguntas"
    name = "Preguntas IA"
    icon = "🎓"
    summary = "Para poner ficha, acierta una pregunta de IA."
    rules = (
        "Solo para dos personas.",
        "Elige casilla y responde: si aciertas, pones ficha.",
        "Si fallas, pasa el turno y la pregunta se queda en la casilla.",
    )
    humans_only = True

    def initial_state(self) -> State:
        return game.INITIAL_STATE + "|X"

    def current_player(self, state: State) -> Mark:
        return _parse(state)[1]

    def cells(self, state: State) -> str:
        return _parse(state)[0]

    def winner(self, state: State) -> Mark | None:
        board = self.cells(state)
        return X if line_of(board, X) else O if line_of(board, O) else None

    def is_terminal(self, state: State) -> bool:
        board = self.cells(state)
        return self.winner(state) is not None or EMPTY not in board

    def legal_moves(self, state: State) -> list[int]:
        if self.is_terminal(state):
            return []
        return [i for i, cell in enumerate(self.cells(state)) if cell == EMPTY]

    def apply_move(self, state: State, move: int) -> State:
        """Poner la ficha de quien tiene el turno (tras acertar) y pasar el turno."""
        if not self.is_legal(state, move):
            raise ValueError(f"movimiento ilegal {move!r} en {state!r}")
        board, turn = _parse(state)
        return f"{board[:move]}{turn}{board[move + 1 :]}|{rival(turn)}"

    def pass_turn(self, state: State) -> State:
        """Pasar el turno sin poner ficha (tras fallar)."""
        if self.is_terminal(state):
            raise ValueError("la partida ya ha terminado")
        board, turn = _parse(state)
        return f"{board}|{rival(turn)}"

    def highlight(self, state: State) -> list[int]:
        board = self.cells(state)
        return list(line_of(board, X) or line_of(board, O) or [])


def answer(state: State, cell: int, question_id: str, choice: int) -> dict[str, Any]:
    """Resolver el intento de poner ficha en ``cell`` respondiendo ``choice``.

    Devuelve el estado nuevo (con la ficha puesta si acierta, o con el turno
    pasado si falla) y si ha acertado. **Solo si acierta** devuelve también la
    correcta y la explicación: una pregunta fallada se queda en su casilla para
    el siguiente que la intente, así que no se puede revelar.
    """
    mode = QuizMode()
    if not mode.is_legal(state, cell):
        raise ValueError(f"la casilla {cell!r} no está disponible")
    if type(choice) is not int or not 0 <= choice < OPTIONS:
        raise ValueError(f"la respuesta debe ser un número del 0 al {OPTIONS - 1}")
    question = get_question(question_id)
    correct = choice == question.correcta
    new_state = mode.apply_move(state, cell) if correct else mode.pass_turn(state)
    return {
        "state": new_state,
        "correct": correct,
        "correct_choice": question.correcta if correct else None,
        "explanation": question.explicacion if correct else None,
    }
