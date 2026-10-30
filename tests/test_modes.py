"""Pruebas de los modos de juego: el inverso, tres fichas y preguntas.

Como en ``test_game.py``, lo importante es que las reglas sean correctas en los
casos límite y que la frontera sea estricta: un estado mal formado o un
movimiento ilegal lanzan ``ValueError``.
"""

from __future__ import annotations

import json
import random

import pytest

from tictactoe import game
from tictactoe.modes import MODE_BOTS, MODES, RandomBot, SearchBot, get_mode, quiz
from tictactoe.modes.moving import MAX_PLIES

CLASSIC = get_mode("clasico")
MISERE = get_mode("inverso")
MOVING = get_mode("tres-fichas")
QUIZ = get_mode("preguntas")


def play(mode, moves, state=None):
    state = mode.initial_state() if state is None else state
    for move in moves:
        state = mode.apply_move(state, move)
    return state


# --------------------------------------------------------------------------- #
# Comunes a todos los modos                                                    #
# --------------------------------------------------------------------------- #


def test_the_five_modes_are_registered_in_order():
    assert list(MODES) == ["clasico", "inverso", "tres-fichas", "preguntas"]
    with pytest.raises(ValueError, match="no existe"):
        get_mode("ajedrez")


@pytest.mark.parametrize("key", list(MODES))
def test_random_games_always_end_with_legal_moves(key):
    mode = MODES[key]
    rng = random.Random(key)
    for _ in range(40):
        state = mode.initial_state()
        for _ in range(200):
            if mode.is_terminal(state):
                break
            moves = mode.legal_moves(state)
            assert moves == sorted(moves) and moves
            state = mode.apply_move(state, rng.choice(moves))
        assert mode.is_terminal(state)
        assert mode.legal_moves(state) == []
        description = mode.describe(state)
        json.dumps(description)  # todo lo que va a la web es JSON
        assert description["turn"] is None
        assert len(description["cells"]) == mode.board_size**2


@pytest.mark.parametrize("key", list(MODES))
@pytest.mark.parametrize("move", [True, 4.0, "4", None, -1, 9])
def test_non_int_or_out_of_range_moves_are_never_legal(key, move):
    mode = MODES[key]
    assert not mode.is_legal(mode.initial_state(), move)
    with pytest.raises(ValueError):
        mode.apply_move(mode.initial_state(), move)


@pytest.mark.parametrize("key", list(MODES))
@pytest.mark.parametrize("state", [None, 7, "", "basura", "XXXXXXXXX|X|X"])
def test_malformed_states_raise(key, state):
    with pytest.raises(ValueError):
        MODES[key].legal_moves(state)


def test_info_is_json_and_complete():
    for mode in MODES.values():
        info = mode.info()
        json.dumps(info)
        assert info["rules"] and info["summary"] and info["name"] and info["icon"]


# --------------------------------------------------------------------------- #
# Clásico e inverso                                                            #
# --------------------------------------------------------------------------- #


def test_classic_mode_is_tictactoe_game():
    state = play(CLASSIC, [0, 3, 1, 4, 2])
    assert state == game.apply_move("XX.OO....", 2)
    assert CLASSIC.winner(state) == "X"
    assert CLASSIC.highlight(state) == [0, 1, 2]


def test_misere_the_line_maker_loses():
    state = play(MISERE, [0, 3, 1, 4, 2])  # X hace la línea de arriba
    assert MISERE.is_terminal(state)
    assert MISERE.winner(state) == "O"
    assert MISERE.highlight(state) == [0, 1, 2]
    assert MISERE.describe(state)["losing_line"] is True


def test_misere_full_board_without_line_is_a_draw():
    state = play(MISERE, [0, 1, 2, 4, 3, 5, 7, 6, 8])
    assert game.winner(state) is None and MISERE.is_draw(state)


# --------------------------------------------------------------------------- #
# Tres fichas                                                                 #
# --------------------------------------------------------------------------- #


def test_moving_the_fourth_piece_removes_the_oldest():
    state = play(MOVING, [0, 3, 1, 4, 8, 5])  # O hace la fila del medio
    assert MOVING.winner(state) == "O"
    state = play(MOVING, [0, 3, 1, 4, 8, 7])
    assert state == "018|347|6"
    assert MOVING.vanishing(state) == 0  # le toca a X, que tiene 3: se irá la del 0
    state = MOVING.apply_move(state, 2)
    assert state == "182|347|7"
    assert MOVING.cells(state)[0] == "."
    # La línea 0-1-2 no cuenta: el 0 ya se fue.
    assert MOVING.winner(state) is None


def test_moving_a_line_with_the_new_piece_wins():
    # X tiene 4, 8 y 6 (la más antigua, el 4); O tiene 0, 1 y 5.
    state = play(MOVING, [4, 0, 8, 1, 6, 5])
    assert MOVING.current_player(state) == "X"
    # X tiene 4, 8, 6; al poner 2, se va el 4 y quedan 8, 6, 2: no es línea.
    after = MOVING.apply_move(state, 2)
    assert MOVING.winner(after) is None
    # X tiene 4, 8, 6; poner en 7 deja 8, 6, 7: línea de abajo.
    after = MOVING.apply_move(state, 7)
    assert MOVING.cells(after) == "OO...OXXX"
    assert MOVING.winner(after) == "X"
    assert MOVING.highlight(after) == [6, 7, 8]


def test_moving_draw_after_the_move_limit():
    # Dos bots al azar casi nunca llegan; se fabrica un estado al límite.
    rng = random.Random(3)
    state = MOVING.initial_state()
    while not MOVING.is_terminal(state):
        moves = MOVING.legal_moves(state)
        safe = [m for m in moves if MOVING.winner(MOVING.apply_move(state, m)) is None]
        state = MOVING.apply_move(state, rng.choice(safe or moves))
    assert MOVING.winner(state) is None
    assert state.endswith(f"|{MAX_PLIES}")
    assert MOVING.is_draw(state)


@pytest.mark.parametrize(
    "state",
    [
        "0|1|3",  # tras 3 movimientos X debe tener 2 fichas
        "012|346|6",  # X tiene línea pero acaba de mover O
        "00|1|3",  # casilla repetida
        "01|0|3",  # casilla de los dos
        "0123|456|7",  # más de tres fichas
        f"012|345|{MAX_PLIES + 2}",
    ],
)
def test_moving_impossible_states_raise(state):
    with pytest.raises(ValueError):
        MOVING.legal_moves(state)


# --------------------------------------------------------------------------- #
# Preguntas                                                                   #
# --------------------------------------------------------------------------- #


def test_question_bank_is_valid_and_covers_every_topic():
    data = json.loads(quiz.QUESTIONS_FILE.read_text(encoding="utf-8"))
    assert quiz.question_problems(data) == []
    questions = quiz.load_questions()
    assert len(questions) >= 200
    topics = {q.tema for q in questions}
    assert len(topics) == 20
    for question in questions:
        assert len(question.pregunta) <= 200
        assert all(len(o) <= 100 for o in question.opciones)
    # La respuesta correcta no cae siempre en la misma letra.
    positions = [q.correcta for q in questions]
    assert all(positions.count(p) > len(positions) // 8 for p in range(quiz.OPTIONS))


def _question(**changes):
    item = {
        "id": "01-01-01",
        "tema": "t",
        "pregunta": "p",
        "opciones": list("abcd"),
        "correcta": 0,
        "explicacion": "e",
    }
    return [{**item, **changes}]


BAD_BANKS = {
    "vacio": [],
    "id-mal": _question(id="1"),
    "tres-opciones": _question(opciones=list("abc")),
    "opcion-repetida": _question(opciones=list("abca")),
    "correcta-fuera": _question(correcta=4),
    "correcta-bool": _question(correcta=True),
    "sin-explicacion": _question(explicacion=" "),
    "id-repetido": _question() + _question(),
}


@pytest.mark.parametrize("bank", list(BAD_BANKS.values()), ids=list(BAD_BANKS))
def test_broken_question_banks_are_detected(bank):
    assert quiz.question_problems(bank)


def test_public_question_hides_the_answer():
    question = quiz.pick_question(0)
    public = question.public()
    assert set(public) == {"id", "tema", "pregunta", "opciones"}
    assert "correcta" not in json.dumps(public)


def test_pick_question_avoids_used_ones_and_is_reproducible():
    first = quiz.pick_question(5)
    assert quiz.pick_question(5) == first
    used = {q.id for q in quiz.load_questions()} - {first.id}
    assert quiz.pick_question(1, used) == first  # solo queda esa
    every = {q.id for q in quiz.load_questions()}
    assert quiz.pick_question(1, every).id in every  # agotadas: vuelve a empezar


def test_right_answer_places_the_piece_wrong_answer_passes_the_turn():
    question = quiz.pick_question(7)
    start = QUIZ.initial_state()
    right = quiz.answer(start, 4, question.id, question.correcta)
    assert right["correct"] is True
    assert right["state"] == "....X....|O"
    wrong_choice = (question.correcta + 1) % quiz.OPTIONS
    wrong = quiz.answer(start, 4, question.id, wrong_choice)
    assert wrong["correct"] is False
    assert wrong["state"] == ".........|O"  # sin ficha, y le toca a O
    # La pregunta se queda para el siguiente: no se revela la respuesta.
    assert wrong["correct_choice"] is None and wrong["explanation"] is None
    assert right["correct_choice"] == question.correcta
    assert right["explanation"] == question.explicacion


def test_quiz_rejects_bad_answers():
    question = quiz.pick_question(0)
    start = QUIZ.initial_state()
    with pytest.raises(ValueError):
        quiz.answer(start, 9, question.id, 0)
    with pytest.raises(ValueError):
        quiz.answer(start, 0, question.id, 4)
    with pytest.raises(ValueError):
        quiz.answer(start, 0, "99-99-99", 0)
    with pytest.raises(ValueError):
        quiz.answer("X..X..X..|O", 1, question.id, 0)  # la partida ya terminó


def test_quiz_turn_is_stored_not_counted():
    # Tras fallar, O puede tener más fichas que X: el estado lo permite.
    state = "OO.X.....|X"
    assert QUIZ.current_player(state) == "X"
    assert QUIZ.legal_moves(state) == [2, 4, 5, 6, 7, 8]
    with pytest.raises(ValueError):
        QUIZ.legal_moves("XXX......|X")  # la línea es de quien tiene el turno


def test_quiz_is_humans_only():
    assert QUIZ.humans_only and MODE_BOTS["preguntas"] == ()


# --------------------------------------------------------------------------- #
# Los bots de los modos                                                       #
# --------------------------------------------------------------------------- #


def _solve(mode, state, memo):
    """Resultado exacto para quien mueve (1, 0, -1): sin poda ni trucos."""
    if state in memo:
        return memo[state]
    if mode.is_terminal(state):
        winner = mode.winner(state)
        value = 0 if winner is None else (1 if winner == mode.current_player(state) else -1)
    else:
        value = max(-_solve(mode, mode.apply_move(state, m), memo) for m in mode.legal_moves(state))
    memo[state] = value
    return value


def test_misere_minimax_plays_perfectly_from_every_position():
    memo: dict[str, int] = {}
    bot = SearchBot(0, depth=9)
    seen, pending = set(), [MISERE.initial_state()]
    while pending:
        state = pending.pop()
        if state in seen or MISERE.is_terminal(state):
            continue
        seen.add(state)
        best = _solve(MISERE, state, memo)
        move = bot.choose_move(MISERE, state)
        assert -_solve(MISERE, MISERE.apply_move(state, move), memo) == best, state
        pending.extend(MISERE.apply_move(state, m) for m in MISERE.legal_moves(state))
    assert len(seen) == 4520


def test_search_bot_takes_a_win_in_moving_mode():
    state = play(MOVING, [4, 0, 8, 1, 6, 5])
    assert SearchBot(0, depth=3).choose_move(MOVING, state) == 7


def test_search_bot_beats_random_in_moving_mode():
    wins = 0
    for seed in range(10):
        for search_is_x in (True, False):
            players = {"X": SearchBot(seed, depth=4), "O": RandomBot(seed)}
            if not search_is_x:
                players = {"X": RandomBot(seed), "O": SearchBot(seed, depth=4)}
            state = MOVING.initial_state()
            while not MOVING.is_terminal(state):
                bot = players[MOVING.current_player(state)]
                state = MOVING.apply_move(state, bot.choose_move(MOVING, state))
            wins += MOVING.winner(state) == ("X" if search_is_x else "O")
    assert wins >= 16


@pytest.mark.parametrize("key", [k for k, specs in MODE_BOTS.items() if specs])
def test_every_offered_bot_plays_legal_moves(key):
    mode = MODES[key]
    for spec in MODE_BOTS[key]:
        bot = spec.create(0)
        state = mode.initial_state()
        for _ in range(6):
            if mode.is_terminal(state):
                break
            move = bot.choose_move(mode, state)
            assert mode.is_legal(state, move), (key, spec.name)
            state = mode.apply_move(state, move)


def test_bots_reject_bad_parameters():
    with pytest.raises(ValueError):
        SearchBot(0, depth=0)
    with pytest.raises(ValueError):
        SearchBot(0).choose_move(CLASSIC, "XXXOO....")


def test_every_mode_offers_the_team_bots_only():
    for key, specs in MODE_BOTS.items():
        if specs:
            assert [s.name for s in specs] == ["aleatorio", "voraz", "minimax"], key
