// Pantalla «Jugar»: cualquier modo, con personas o bots en cada ficha.
//
// No sabe las reglas: cada posición (turno, casillas libres, ganador, la ficha que
// desaparece, el tablero donde toca jugar...) se la da el motor, que se la
// pregunta al Python del proyecto. Aquí solo se pregunta, se dibuja y se espera
// a la persona o al bot al que le toca.

"use strict";

(function () {
  const { el, storage, settings, showError, clearError, fighters } = window.Arena;
  const HUMAN = "__human__";

  const ui = {
    setup: document.getElementById("setup"),
    mode: document.getElementById("mode"),
    newGame: document.getElementById("new-game"),
    status: document.getElementById("status"),
    board: document.getElementById("board"),
    hint: document.getElementById("board-hint"),
    pause: document.getElementById("pause"),
    rematch: document.getElementById("rematch"),
    log: document.getElementById("move-log"),
    logEmpty: document.getElementById("move-log-empty"),
    quiz: document.getElementById("quiz"),
    quizWho: document.getElementById("quiz-who"),
    quizTopic: document.getElementById("quiz-topic"),
    quizQuestion: document.getElementById("quiz-question"),
    quizOptions: document.getElementById("quiz-options"),
    quizResult: document.getElementById("quiz-result"),
    quizNote: document.getElementById("quiz-note"),
    quizContinue: document.getElementById("quiz-continue"),
  };
  const fighterUi = {
    X: document.getElementById("fighter-X"),
    O: document.getElementById("fighter-O"),
  };
  const seatUi = {
    X: {
      select: document.getElementById("seat-x"),
      name: document.getElementById("name-x"),
      info: document.getElementById("seat-x-info"),
    },
    O: {
      select: document.getElementById("seat-o"),
      name: document.getElementById("name-o"),
      info: document.getElementById("seat-o-info"),
    },
  };

  let engine = null;
  let modes = [];
  // La partida en curso:
  //   mode      la descripción del modo (de Python)
  //   seats     {X, O}: {kind: "human"|"bot", name, bot}
  //   position  la última respuesta del motor
  //   phase     "human", "bot", "quiz", "busy" u "over"
  //   paused    bot contra bot en pausa
  //   used      las preguntas ya acertadas (modo preguntas)
  //   pending   modo preguntas: la pregunta que espera en cada casilla tras un
  //             fallo, con las opciones ya falladas: {casilla: {question, failed}}
  //   lastMove  la última casilla jugada (para marcarla)
  let game = null;
  // Cada partida nueva incrementa este número: una jugada de bot pendiente de
  // una partida anterior lo compara y se descarta.
  let generation = 0;

  const modeByKey = (key) => modes.find((m) => m.key === key);
  const seed = () => Math.floor(Math.random() * 2 ** 31);

  // ------------------------------------------------------------------------
  // Preparar la partida
  // ------------------------------------------------------------------------

  function fillModes() {
    ui.mode.replaceChildren(
      ...modes.map((m) => el("option", { value: m.key, text: `${m.icon} ${m.name}` }))
    );
  }

  function fillSeats() {
    const mode = modeByKey(ui.mode.value);
    const names = storage.get("arena.names", { X: "", O: "" });
    for (const mark of ["X", "O"]) {
      const { select, name } = seatUi[mark];
      const previous = select.value;
      const options = [el("option", { value: HUMAN, text: "👤 Persona" })];
      for (const bot of mode.bots) {
        const sent = bot.origin === "custom" ? " · enviado" : "";
        options.push(el("option", { value: bot.name, text: `${bot.icon} ${bot.name}${sent}` }));
      }
      select.replaceChildren(...options);
      const values = options.map((o) => o.value);
      if (values.includes(previous)) {
        select.value = previous;
      } else if (mark === "O" && mode.bots.length > 0) {
        // Por defecto, una persona (X) contra el bot más fuerte (O).
        const strong = mode.bots.find((b) => b.name === "minimax" || b.name === "montecarlo");
        select.value = (strong || mode.bots[mode.bots.length - 1]).name;
      } else {
        select.value = HUMAN;
      }
      select.disabled = mode.humans_only;
      if (!name.value) name.value = names[mark] || "";
    }
    paintSeatInfo();
  }

  // Los luchadores de la partida que se está preparando (o de la que se juega).
  function paintFighters() {
    // Durante una partida, los que juegan; si no, los que se están eligiendo.
    const seats = game && game.phase !== "over" ? game.seats : previewSeats();
    for (const mark of ["X", "O"]) {
      if (!fighterUi[mark]) continue; // en este diseño la pantalla no tiene luchadores
      fighters.render(fighterUi[mark], seats[mark], mark, seatName(seats[mark], mark));
    }
  }

  function previewSeats() {
    const seats = {};
    for (const mark of ["X", "O"]) {
      const { select, name } = seatUi[mark];
      seats[mark] =
        select.value === HUMAN
          ? { kind: "human", name: name.value.trim() || `Invitado ${mark}` }
          : { kind: "bot", bot: select.value, name: select.value };
    }
    return seats;
  }

  function seatName(seat, mark) {
    if (seat.kind === "human") return seat.name || `Invitado ${mark}`;
    const bot = modeByKey(ui.mode.value)?.bots.find((b) => b.name === seat.bot);
    return bot ? `${bot.icon} ${bot.name}` : seat.bot;
  }

  function paintSeatInfo() {
    if (!game || game.phase === "over") {
      paintFighters();
      for (const mark of ["X", "O"]) if (fighterUi[mark]) fighters.setMood(fighterUi[mark], "");
    }
    const mode = modeByKey(ui.mode.value);
    for (const mark of ["X", "O"]) {
      const { select, name, info } = seatUi[mark];
      const human = select.value === HUMAN;
      name.hidden = !human;
      name.previousElementSibling.hidden = !human;
      // Cómo piensa cada bot se explica en la pantalla «Bots», no aquí.
      info.textContent = human && mode.humans_only ? "Este modo es solo para personas." : "";
    }
  }

  function readSeats() {
    const seats = {};
    const names = {};
    for (const mark of ["X", "O"]) {
      const { select, name } = seatUi[mark];
      if (select.value === HUMAN) {
        const typed = name.value.trim().slice(0, 24);
        names[mark] = typed;
        seats[mark] = { kind: "human", name: typed || `Invitado ${mark}` };
      } else {
        seats[mark] = { kind: "bot", bot: select.value, name: select.value };
      }
    }
    storage.set("arena.names", { ...storage.get("arena.names", {}), ...names });
    return seats;
  }

  function start(seats) {
    clearError();
    const mode = modeByKey(ui.mode.value);
    let position;
    try {
      position = engine.modeNewGame(mode.key, seats, seed());
    } catch (error) {
      showError(error.message);
      return;
    }
    generation += 1;
    if (ui.quiz.open) ui.quiz.close();
    game = { mode, seats, position, phase: "busy", paused: false, used: [], pending: {}, lastMove: null };
    paintFighters();
    ui.log.replaceChildren();
    ui.logEmpty.hidden = false;
    ui.rematch.hidden = true;
    const botsOnly = seats.X.kind === "bot" && seats.O.kind === "bot";
    ui.pause.hidden = !botsOnly;
    ui.pause.textContent = "⏸ Pausar";
    advance();
  }

  // ------------------------------------------------------------------------
  // El turno
  // ------------------------------------------------------------------------

  function who(mark) {
    const seat = game.seats[mark];
    const bot = seat.kind === "bot" ? game.mode.bots.find((b) => b.name === seat.bot) : null;
    return bot ? `${bot.icon} ${bot.name}` : seat.name;
  }

  function advance() {
    const position = game.position;
    if (position.terminal) {
      finish(null);
      return;
    }
    const mover = position.turn;
    if (game.seats[mover].kind === "human") {
      game.phase = "human";
      paint();
      return;
    }
    game.phase = "bot";
    paint();
    if (game.paused) return;
    const mine = generation;
    setTimeout(() => {
      if (mine !== generation || game.paused) return;
      let answer;
      try {
        answer = engine.modeBotMove(game.position.state);
      } catch (error) {
        showError(error.message);
        game.phase = "over";
        paint();
        return;
      }
      if (answer.forfeit) {
        finish({ by: answer.forfeit_by, detail: answer.detail });
        return;
      }
      logMove(mover, answer.move, game.position);
      game.lastMove = answer.move;
      game.position = answer;
      advance();
    }, settings.botDelay);
  }

  function humanPick(move) {
    if (game.phase !== "human") return;
    if (game.mode.key === "preguntas") {
      openQuestion(move);
      return;
    }
    let answer;
    try {
      answer = engine.modePlay(game.position.state, move);
    } catch (error) {
      showError(error.message);
      return;
    }
    logMove(game.position.turn, move, game.position);
    game.lastMove = move;
    game.position = answer;
    advance();
  }

  function finish(forfeit) {
    game.phase = "over";
    game.forfeit = forfeit;
    ui.pause.hidden = true;
    ui.rematch.hidden = false;
    paint();
    const position = game.position;
    let winner = position.winner;
    if (forfeit) winner = forfeit.by === "X" ? "O" : "X";
    if (game.seats.X.kind === "human" || game.seats.O.kind === "human") {
      window.Arena.recordGame?.({
        at: new Date().toISOString(),
        mode: game.mode.key,
        x: { kind: game.seats.X.kind, name: game.seats.X.name },
        o: { kind: game.seats.O.kind, name: game.seats.O.name },
        winner: winner || null,
        forfeit: Boolean(forfeit),
      });
    }
  }

  // ------------------------------------------------------------------------
  // El modo «Preguntas IA»
  // ------------------------------------------------------------------------

  const LETTERS = ["A", "B", "C", "D"];

  function openQuestion(cell) {
    if (!game.pending[cell]) {
      // Pregunta nueva, distinta de las acertadas y de las que esperan en otras casillas.
      const busy = Object.values(game.pending).map((p) => p.question.id);
      let question;
      try {
        question = engine.quizQuestion(seed(), [...game.used, ...busy]);
      } catch (error) {
        showError(error.message);
        return;
      }
      game.pending[cell] = { question, failed: [] };
    }
    const { question, failed } = game.pending[cell];
    game.phase = "quiz";
    const mark = game.position.turn;
    ui.quizWho.replaceChildren(
      el("span", { class: mark === "X" ? "mark-x" : "mark-o", text: mark }),
      ` ${who(mark)} · casilla ${cell + 1}`
    );
    ui.quizTopic.textContent = `Tema: ${question.tema}`;
    ui.quizQuestion.textContent = question.pregunta;
    ui.quizResult.hidden = true;
    ui.quizContinue.hidden = true;
    ui.quizNote.hidden = failed.length === 0;
    ui.quizNote.textContent =
      failed.length === 1
        ? "Esta pregunta ya se ha fallado: la opción tachada no es."
        : `Esta pregunta ya se ha fallado ${failed.length} veces: las opciones tachadas no son.`;
    ui.quizOptions.replaceChildren(
      ...question.opciones.map((text, choice) =>
        el(
          "button",
          {
            type: "button",
            class: failed.includes(choice) ? "button crossed" : "button",
            disabled: failed.includes(choice),
            onclick: () => answerQuestion(cell, question, choice),
          },
          el("span", { class: "letter", text: LETTERS[choice] }),
          text
        )
      )
    );
    paint();
    ui.quiz.showModal();
    ui.quizOptions.querySelector("button:not([disabled])").focus();
  }

  function answerQuestion(cell, question, choice) {
    let answer;
    try {
      answer = engine.quizAnswer(game.position.state, cell, question.id, choice);
    } catch (error) {
      ui.quiz.close();
      showError(error.message);
      return;
    }
    const buttons = [...ui.quizOptions.querySelectorAll("button")];
    buttons.forEach((button, index) => {
      button.disabled = true;
      if (answer.correct && index === answer.correct_choice) button.classList.add("correct");
      else if (index === choice) button.classList.add("wrong");
    });
    ui.quizNote.hidden = true;
    ui.quizResult.className = `quiz-result ${answer.correct ? "good" : "bad"}`;
    if (answer.correct) {
      // Acertada: se ve la explicación y la casilla queda libre de pregunta.
      ui.quizResult.replaceChildren(
        el("strong", { text: "¡Correcto! Pones tu ficha." }),
        el("p", { text: answer.explanation })
      );
      delete game.pending[cell];
      game.used.push(question.id);
    } else {
      // Fallada: no se revela la buena; la pregunta se queda para el siguiente.
      ui.quizResult.replaceChildren(
        el("strong", { text: "Incorrecto. Pasa el turno." }),
        el("p", { text: "La pregunta se queda en esta casilla para el siguiente que la intente." })
      );
      game.pending[cell].failed.push(choice);
    }
    ui.quizResult.hidden = false;
    ui.quizContinue.hidden = false;
    ui.quizContinue.focus();

    const mark = game.position.turn;
    const entry = answer.correct
      ? `${mark} acierta (${question.tema}) → casilla ${cell + 1}`
      : `${mark} falla (${question.tema}): pasa el turno`;
    addLog(mark, entry, !answer.correct);
    if (answer.correct) game.lastMove = cell;
    game.position = answer;
    game.pendingAdvance = true;
  }

  ui.quizContinue.addEventListener("click", () => ui.quiz.close());
  // Una pregunta no se puede esquivar: ni con Escape ni cerrando sin responder.
  ui.quiz.addEventListener("cancel", (event) => {
    if (ui.quizContinue.hidden) event.preventDefault();
  });
  ui.quiz.addEventListener("close", () => {
    if (game && game.pendingAdvance) {
      game.pendingAdvance = false;
      advance();
    }
  });

  // ------------------------------------------------------------------------
  // Registro de jugadas
  // ------------------------------------------------------------------------

  function describeMove(move) {
    return `casilla ${move + 1}`;
  }

  function logMove(mark, move, before) {
    let text = `${mark} (${who(mark)}) → ${describeMove(move)}`;
    if (before.vanishing !== null && before.vanishing !== undefined) {
      text += ` · se va su ficha de la ${before.vanishing + 1}`;
    }
    addLog(mark, text, false);
  }

  function addLog(mark, text, failed) {
    ui.logEmpty.hidden = true;
    const item = el("li", { class: `${mark.toLowerCase()}${failed ? " fail" : ""}`, text });
    ui.log.append(item);
    item.scrollIntoView({ block: "nearest" });
  }

  // ------------------------------------------------------------------------
  // Dibujo: el ÚNICO sitio donde se pinta el tablero, siempre a partir del estado.
  // ------------------------------------------------------------------------

  function cellButton(index, mark, position, clickable) {
    const legal = clickable && position.legal.includes(index);
    const classes = ["cell"];
    if (mark === "X") classes.push("x");
    if (mark === "O") classes.push("o");
    if (position.highlight.includes(index)) classes.push("win");
    if (position.vanishing === index) classes.push("vanishing");
    if (game && game.lastMove === index) classes.push("last");
    const waiting = game && game.pending && game.pending[index] && mark === ".";
    if (waiting) classes.push("pending");
    const label =
      mark === "."
        ? `${describeMove(index)}, libre${waiting ? ", con una pregunta pendiente" : ""}`
        : `${describeMove(index)}, ${mark}${position.vanishing === index ? ", desaparecerá" : ""}`;
    return el("button", {
      type: "button",
      class: classes.join(" "),
      text: mark === "." ? (waiting ? "?" : "") : mark,
      "aria-label": label,
      disabled: !legal,
      onclick: legal ? () => humanPick(index) : null,
    });
  }

  function paintBoard(position, clickable) {
    const cells = position.cells;
    ui.board.className = "board";
    ui.board.replaceChildren(
      ...[...cells].map((mark, i) => cellButton(i, mark, position, clickable))
    );
  }

  function statusText() {
    const position = game.position;
    if (game.phase === "over") {
      if (game.forfeit) {
        const loser = game.forfeit.by;
        const winner = loser === "X" ? "O" : "X";
        return `Gana ${who(winner)} (${winner}): ${who(loser)} pierde por abandono (${game.forfeit.detail}).`;
      }
      if (position.winner) {
        const loser = position.winner === "X" ? "O" : "X";
        if (game.mode.key === "inverso") {
          return `🎉 Gana ${who(position.winner)} (${position.winner}): ${who(loser)} hizo tres en raya.`;
        }
        return `🎉 Gana ${who(position.winner)} (${position.winner}).`;
      }
      if (position.max_plies && position.plies >= position.max_plies) {
        return `Empate: ${position.max_plies} movimientos sin tres en raya.`;
      }
      return "Empate.";
    }
    const mark = position.turn;
    if (game.phase === "bot") {
      return game.paused ? `En pausa. Le toca a ${who(mark)} (${mark}).` : `${who(mark)} (${mark}) está pensando…`;
    }
    return `Te toca, ${who(mark)}: juegas con ${mark}.`;
  }

  function hintText() {
    const position = game.position;
    if (game.phase === "over") return "Pulsa «Revancha» para cambiar de fichas, o prepara otra partida.";
    const key = game.mode.key;
    if (key === "tres-fichas") {
      const left = `Movimiento ${position.plies + 1} de ${position.max_plies}.`;
      return position.vanishing !== null ? `${left} La ficha marcada «se va» desaparece al mover.` : left;
    }
    if (key === "preguntas" && game.phase === "human") {
      return Object.keys(game.pending).length > 0
        ? "Elige una casilla y responde. Las casillas con «?» guardan una pregunta que alguien falló."
        : "Elige una casilla: te saldrá una pregunta. Si fallas, pasa el turno.";
    }
    if (key === "inverso") return "Recuerda: quien hace tres en raya, pierde.";
    return "";
  }

  function paintMoods() {
    const position = game.position;
    for (const mark of ["X", "O"]) {
      const figure = fighterUi[mark];
      if (!figure) continue;
      if (game.phase === "over") {
        let winner = position.winner;
        if (game.forfeit) winner = game.forfeit.by === "X" ? "O" : "X";
        if (!winner) fighters.setMood(figure, "draw", "Empate");
        else if (winner === mark) fighters.setMood(figure, "winner", "¡Gana!");
        else fighters.setMood(figure, "loser", "K.O.");
      } else if (position.turn === mark) {
        const thinking = game.seats[mark].kind === "bot" && !game.paused;
        fighters.setMood(figure, thinking ? "thinking" : "turn", thinking ? "Pensando…" : "¡Te toca!");
      } else {
        fighters.setMood(figure, "");
      }
    }
  }

  function paint() {
    paintBoard(game.position, game.phase === "human");
    paintMoods();
    ui.status.textContent = statusText();
    ui.hint.textContent = hintText();
  }

  // ------------------------------------------------------------------------
  // Botones
  // ------------------------------------------------------------------------

  ui.mode.addEventListener("change", fillSeats);
  for (const mark of ["X", "O"]) {
    seatUi[mark].select.addEventListener("change", paintSeatInfo);
    seatUi[mark].name.addEventListener("input", () => {
      if (!game || game.phase === "over") paintFighters();
    });
  }

  ui.setup.addEventListener("submit", (event) => {
    event.preventDefault();
    start(readSeats());
  });

  ui.rematch.addEventListener("click", () => {
    // Revancha: los mismos jugadores (los que estén elegidos), cambiando de ficha.
    const values = { X: seatUi.X.select.value, O: seatUi.O.select.value };
    const names = { X: seatUi.X.name.value, O: seatUi.O.name.value };
    for (const [mark, other] of [["X", "O"], ["O", "X"]]) {
      seatUi[mark].select.value = values[other];
      seatUi[mark].name.value = names[other];
    }
    paintSeatInfo();
    start(readSeats());
  });

  ui.pause.addEventListener("click", () => {
    game.paused = !game.paused;
    ui.pause.textContent = game.paused ? "▶ Seguir" : "⏸ Pausar";
    if (!game.paused) advance();
    else paint();
  });

  // Antes de la primera partida, el tablero ya se ve, vacío.
  ui.board.replaceChildren(
    ...Array.from({ length: 9 }, (_, i) =>
      el("button", { type: "button", class: "cell", disabled: true, "aria-label": `casilla ${i + 1}, libre` })
    )
  );

  window.Arena.engine
    .then((ready) => {
      engine = ready;
      modes = engine.modes;
      fillModes();
      fillSeats();
      ui.mode.disabled = false;
      ui.newGame.disabled = false;
    })
    .catch(() => {
      ui.status.textContent = "No se puede jugar: Python no ha arrancado.";
    });
})();
