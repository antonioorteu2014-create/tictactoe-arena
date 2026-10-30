// Pantalla «Torneo», primera parte: un torneo por eliminatorias, en directo.
//
// Se eligen los bots, Python sortea el cuadro (tictactoe.knockout) y juega las
// partidas de una en una. Cada partida se enseña jugada a jugada, con los dos
// luchadores cara a cara, y el cuadro se redibuja: el que gana avanza, el que
// pierde queda tachado. Al final sale el campeón.
//
// La clasificación oficial (la liguilla que juega GitHub cada día) la dibuja
// leaderboard.js, más abajo en la misma pantalla.

"use strict";

(function () {
  const { el, settings, showError, fighters } = window.Arena;

  const ui = {
    form: document.getElementById("arena-form"),
    bots: document.getElementById("arena-bots"),
    start: document.getElementById("arena-start"),
    pause: document.getElementById("arena-pause"),
    fast: document.getElementById("arena-fast"),
    live: document.getElementById("arena-live"),
    liveTitle: document.getElementById("live-title"),
    liveBoard: document.getElementById("live-board"),
    liveResult: document.getElementById("live-result"),
    liveX: document.getElementById("live-X"),
    liveO: document.getElementById("live-O"),
    champion: document.getElementById("champion"),
    championFighter: document.getElementById("champion-fighter"),
    championName: document.getElementById("champion-name"),
    bracket: document.getElementById("bracket"),
  };

  let engine = null;
  let icons = {};
  let running = false;
  let paused = false;
  let fast = false;
  let resume = null; // la función que continúa tras una pausa

  const label = (name) => (name ? `${icons[name] || "🤖"} ${name}` : "");
  const bot = (name) => ({ kind: "bot", bot: name });

  // Esperar `ms`, respetando la pausa y el modo sin animación.
  function wait(ms) {
    return new Promise((resolve) => {
      const go = () => setTimeout(resolve, fast ? 0 : ms);
      if (paused) resume = go;
      else go();
    });
  }

  // ------------------------------------------------------------------------
  // El cuadro
  // ------------------------------------------------------------------------

  function paintBracket(bracket, current) {
    // La última columna, después de la final: el campeón.
    const champion = el(
      "div",
      { class: "bracket-round" },
      el("h3", { text: "Campeón" }),
      el(
        "div",
        { class: "bracket-ties" },
        el(
          "div",
          { class: `tie champ${bracket.champion ? " done" : ""}` },
          el(
            "div",
            { class: `tie-row${bracket.champion ? " won" : " empty"}` },
            el("span", {
              class: "tie-name",
              text: bracket.champion ? `🏆 ${label(bracket.champion)}` : "por decidir",
            })
          )
        )
      )
    );
    ui.bracket.replaceChildren(
      ...bracket.rounds.map((round, r) =>
        el(
          "div",
          { class: "bracket-round" },
          el("h3", { text: round.name }),
          el(
            "div",
            { class: "bracket-ties" },
            ...round.ties.map((tie, i) => paintTie(tie, current && current.round === r && current.tie === i))
          )
        )
      ),
      champion
    );
  }

  function paintTie(tie, isCurrent) {
    const classes = ["tie"];
    if (isCurrent) classes.push("current");
    if (tie.winner) classes.push("done");
    const row = (name, score) => {
      const cls = ["tie-row"];
      if (!name) cls.push("empty");
      if (tie.winner && name === tie.winner) cls.push("won");
      if (tie.winner && name && name !== tie.winner) cls.push("out");
      return el(
        "div",
        { class: cls.join(" ") },
        el("span", { class: "tie-name", text: name ? label(name) : tie.decided_by === "pase directo" ? "— pase directo —" : "por decidir" }),
        el("span", { class: "tie-score", text: name && tie.b !== null && tie.games.length ? String(score) : "" })
      );
    };
    return el(
      "div",
      { class: classes.join(" ") },
      row(tie.a, tie.score[0]),
      row(tie.b, tie.score[1]),
      tie.decided_by && tie.decided_by !== "partidas"
        ? el("span", { class: "tie-note", text: tie.decided_by })
        : null
    );
  }

  // ------------------------------------------------------------------------
  // La partida en directo
  // ------------------------------------------------------------------------

  const LINES = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6],
    [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6],
  ]; // prettier-ignore

  function paintMini(cells, line = []) {
    ui.liveBoard.replaceChildren(
      ...[...cells].map((mark, i) =>
        el("span", {
          class: `cell${mark === "X" ? " x" : mark === "O" ? " o" : ""}${line.includes(i) ? " win" : ""}`,
          text: mark === "." ? "" : mark,
        })
      )
    );
  }

  async function showGame(event, bracket) {
    const { game } = event;
    const round = bracket.rounds[event.round];
    const tie = round.ties[event.tie];
    const number = tie.games.length;
    ui.live.hidden = false;
    ui.liveTitle.textContent = `${round.name} · ${label(tie.a)} contra ${label(tie.b)} · partida ${number}${number > 2 ? " (muerte súbita)" : ""}`;
    fighters.render(ui.liveX, bot(game.x), "X", label(game.x));
    fighters.render(ui.liveO, bot(game.o), "O", label(game.o));
    ui.liveResult.textContent = "";

    const cells = [..."........."];
    paintMini(cells.join(""));
    for (const [index, move] of game.moves.entries()) {
      const mark = index % 2 === 0 ? "X" : "O";
      fighters.setMood(ui.liveX, mark === "X" ? "thinking" : "");
      fighters.setMood(ui.liveO, mark === "O" ? "thinking" : "");
      await wait(Math.max(120, settings.botDelay * 0.7));
      cells[move] = mark;
      paintMini(cells.join(""));
    }
    const board = cells.join("");
    const line = LINES.find((l) => l.every((i) => board[i] !== "." && board[i] === board[l[0]])) || [];
    paintMini(board, line);

    const winnerMark = game.winner === game.x ? "X" : game.winner === game.o ? "O" : null;
    for (const [mark, figure] of [["X", ui.liveX], ["O", ui.liveO]]) {
      if (!winnerMark) fighters.setMood(figure, "draw", "Empate");
      else fighters.setMood(figure, mark === winnerMark ? "winner" : "loser", mark === winnerMark ? "¡Gana!" : "K.O.");
    }
    let text = game.winner ? `Gana ${label(game.winner)}` : "Empate";
    if (game.ending !== "normal") text += ` (abandono: ${game.detail})`;
    if (event.tie_over) {
      text += `. ${label(tie.winner)} pasa${tie.decided_by === "sorteo" ? " por sorteo" : ""}.`;
    }
    ui.liveResult.textContent = text;
    await wait(event.tie_over ? settings.botDelay * 3 : settings.botDelay * 2);
  }

  function showChampion(name) {
    ui.champion.hidden = false;
    fighters.render(ui.championFighter, bot(name), "🏆", label(name));
    fighters.setMood(ui.championFighter, "winner", "¡Campeón!");
    ui.championName.textContent = label(name);
    ui.champion.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  // ------------------------------------------------------------------------
  // El torneo
  // ------------------------------------------------------------------------

  async function run() {
    const names = [...ui.bots.querySelectorAll("input:checked")].map((box) => box.value);
    let answer;
    try {
      answer = engine.knockoutStart(names, Math.floor(Math.random() * 2 ** 31));
    } catch (error) {
      ui.liveResult.textContent = "";
      ui.live.hidden = true;
      showError(error.message, "");
      return;
    }
    running = true;
    paused = false;
    fast = false;
    ui.start.disabled = true;
    ui.pause.hidden = false;
    ui.fast.hidden = false;
    ui.pause.textContent = "⏸ Pausar";
    ui.champion.hidden = true;
    paintBracket(answer.bracket, null);

    while (!answer.bracket.done) {
      try {
        answer = engine.knockoutStep();
      } catch (error) {
        showError(error.message);
        break;
      }
      if (!answer.event) break;
      paintBracket(answer.bracket, answer.event);
      await showGame(answer.event, answer.bracket);
      paintBracket(answer.bracket, null);
    }
    if (answer.bracket.champion) showChampion(answer.bracket.champion);
    running = false;
    ui.start.disabled = false;
    ui.start.textContent = "🎲 Sortear otro torneo";
    ui.pause.hidden = true;
    ui.fast.hidden = true;
  }

  ui.form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!running) run();
  });

  ui.pause.addEventListener("click", () => {
    paused = !paused;
    ui.pause.textContent = paused ? "▶ Seguir" : "⏸ Pausar";
    if (!paused && resume) {
      const go = resume;
      resume = null;
      go();
    }
  });

  ui.fast.addEventListener("click", () => {
    fast = true;
    ui.fast.hidden = true;
  });

  window.Arena.engine
    .then((ready) => {
      engine = ready;
      icons = Object.fromEntries(engine.players.map((p) => [p.name, p.icon]));
      ui.bots.replaceChildren(
        ...engine.players.map((p) =>
          el(
            "label",
            {},
            el("input", { type: "checkbox", value: p.name, checked: true }),
            `${p.icon} ${p.name}`,
            p.origin === "custom" ? el("span", { class: "tag sent", text: "enviado" }) : null
          )
        )
      );
      ui.start.disabled = false;
    })
    .catch(() => {
      ui.bots.replaceChildren(el("p", { class: "muted", text: "No disponible: Python no ha arrancado." }));
    });
})();
