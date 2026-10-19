// La interfaz: dibuja el tablero, recoge los clics y alterna los turnos con el bot.
//
// No sabe las reglas del juego: cada posición (de quién es el turno, qué
// casillas están libres, si alguien ha ganado) se la da el motor (engine.js),
// que se la pregunta al Python del proyecto. La página solo pregunta y dibuja.

"use strict";

// Pausa antes de que juegue el bot, para que la partida no parezca instantánea.
const BOT_DELAY_MS = 450;

const ui = {
  error: document.getElementById("error"),
  bot: document.getElementById("bot"),
  side: document.getElementById("side"),
  newGame: document.getElementById("new-game"),
  description: document.getElementById("bot-description"),
  status: document.getElementById("status"),
  board: document.getElementById("board"),
};

let engine = null;
// La partida en curso:
//   position  la última respuesta del motor (estado, turno, casillas libres…)
//   human     la ficha de la persona: "X" u "O"
//   phase     "human" (le toca a la persona), "bot", "busy" u "over"
//   forfeit   si el bot perdió por abandono, el motivo
//   failed    si la partida se interrumpió por un error inesperado
//   botMove   la última casilla en la que jugó el bot (para anunciarla)
//   keyboard  si la persona juega con el teclado (para no perderle el foco)
let game = null;
// Cada partida nueva incrementa este número. Una jugada del bot que estaba
// pendiente de una partida anterior lo compara y se descarta.
let generation = 0;

// --------------------------------------------------------------------------
// Errores: siempre visibles. Una web estática no tiene registro en un servidor,
// así que un error que no se muestra es un error que nadie llega a ver.
// --------------------------------------------------------------------------

function showError(message, hint = "Prueba con «Nueva partida» o recarga la página.") {
  const sentence = /[.!?]$/.test(message) ? message : `${message}.`;
  ui.error.textContent = `Algo ha ido mal: ${sentence} ${hint}`.trim();
  ui.error.hidden = false;
}

window.addEventListener("error", (event) => showError(event.message || "error desconocido"));
window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason;
  showError(reason && reason.message ? reason.message : String(reason));
});

// --------------------------------------------------------------------------
// Dibujo: el ÚNICO sitio donde se pinta el tablero, siempre a partir del estado.
// --------------------------------------------------------------------------

// Pinta en `container` el tablero de `position`. Si se pasa `onPick`, las
// casillas libres se pueden pulsar y llaman a `onPick(casilla)`.
function paintBoard(container, position, onPick) {
  const cells = [];
  const winning = new Set(position ? position.line : []);
  for (let cell = 0; cell < 9; cell += 1) {
    const mark = position ? position.state[cell] : ".";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cell";
    button.dataset.cell = String(cell);
    if (mark !== ".") {
      button.textContent = mark;
      button.classList.add(mark.toLowerCase());
    }
    if (winning.has(cell)) {
      button.classList.add("win");
    }
    const playable = Boolean(onPick && position && position.legal.includes(cell));
    button.disabled = !playable;
    button.setAttribute(
      "aria-label",
      `Casilla ${cell + 1}: ${mark === "." ? "vacía" : mark}`
    );
    if (playable) {
      button.addEventListener("click", (event) => onPick(cell, event));
    }
    cells.push(button);
  }
  container.replaceChildren(...cells);
}

function botLabel() {
  const player = engine && engine.players.find((p) => p.name === game.botName);
  return player ? `${player.icon} ${player.name}` : "el bot";
}

function statusText() {
  if (!game) {
    return "Cargando…";
  }
  const { position, human, phase } = game;
  // Dónde jugó el bot: imprescindible para seguir la partida con lector de pantalla.
  const botMoved = game.botMove === null ? "" : ` (jugó en la casilla ${game.botMove + 1})`;
  if (phase === "over") {
    if (game.failed) {
      return "Partida interrumpida por un error.";
    }
    if (game.forfeit) {
      return `¡Has ganado! ${botLabel()} ha perdido por abandono (${game.forfeit}).`;
    }
    if (position.draw) {
      return "Empate.";
    }
    return position.winner === human ? "¡Has ganado! 🎉" : `Gana ${botLabel()}${botMoved}.`;
  }
  if (phase === "human") {
    const lead = game.botMove === null ? "" : `${botLabel()} jugó en la casilla ${game.botMove + 1}. `;
    return `${lead}Te toca. Juegas con ${human}.`;
  }
  return `${botLabel()} está pensando…`;
}

function render() {
  const humanCanPlay = game && game.phase === "human";
  paintBoard(ui.board, game && game.position, humanCanPlay ? onHumanPick : null);
  ui.status.textContent = statusText();
  // Repintar sustituye las casillas y el foco se perdería. Si la persona juega
  // con el teclado, se lo devolvemos a una casilla libre cuando le toca.
  if (humanCanPlay && game.keyboard) {
    const target = ui.board.querySelector(".cell:not([disabled])");
    if (target) {
      target.focus({ preventScroll: true });
    }
  }
}

// --------------------------------------------------------------------------
// Turnos
// --------------------------------------------------------------------------

// Decide qué toca después de cada jugada y vuelve a dibujar.
function advance() {
  const { position, human } = game;
  if (position.terminal) {
    game.phase = "over";
  } else if (position.turn === human) {
    game.phase = "human";
  } else {
    game.phase = "bot";
    scheduleBotTurn(generation);
  }
  render();
}

function onHumanPick(cell, event) {
  // Doble clic, clic durante el turno del bot o con la partida terminada:
  // no hace nada. La casilla tiene que estar libre según el motor.
  if (!game || game.phase !== "human" || !game.position.legal.includes(cell)) {
    return;
  }
  // Un «clic» lanzado con Intro o Espacio llega con detail === 0.
  game.keyboard = Boolean(event && event.detail === 0);
  game.phase = "busy"; // bloquea más clics hasta que el motor responda
  try {
    game.position = engine.play(game.position.state, cell);
  } catch (error) {
    game.phase = "human";
    render();
    showError(error.message);
    return;
  }
  advance();
}

function scheduleBotTurn(myGeneration) {
  setTimeout(() => {
    if (myGeneration !== generation || !game || game.phase !== "bot") {
      return; // la partida cambió mientras tanto
    }
    try {
      const answer = engine.botMove(game.position.state);
      game.position = answer;
      if (!answer.forfeit) {
        game.botMove = answer.move;
      }
      if (answer.forfeit) {
        game.forfeit = answer.detail;
        game.phase = "over";
        render();
        return;
      }
    } catch (error) {
      game.phase = "over";
      game.failed = true;
      render();
      showError(error.message);
      return;
    }
    advance();
  }, BOT_DELAY_MS);
}

function startGame() {
  generation += 1;
  ui.error.hidden = true;
  const botName = ui.bot.value;
  const seed = Math.floor(Math.random() * 2 ** 31);
  try {
    const position = engine.newGame(botName, seed);
    game = {
      position,
      botName,
      human: ui.side.value,
      phase: "busy",
      forfeit: null,
      failed: false,
      botMove: null,
      keyboard: game ? game.keyboard : false,
    };
  } catch (error) {
    game = null;
    render();
    showError(error.message);
    return;
  }
  advance();
}

function showDescription() {
  const player = engine.players.find((p) => p.name === ui.bot.value);
  ui.description.textContent = player
    ? `${player.description} (de ${player.authors.join(", ")})`
    : "";
}

// --------------------------------------------------------------------------
// Arranque
// --------------------------------------------------------------------------

function setControlsEnabled(enabled) {
  ui.bot.disabled = !enabled;
  ui.side.disabled = !enabled;
  ui.newGame.disabled = !enabled;
}

async function main() {
  paintBoard(ui.board, null, null);
  setControlsEnabled(false);
  try {
    engine = await window.bootEngine((message) => {
      ui.status.textContent = message;
    });
  } catch (error) {
    ui.status.textContent = "No se pudo cargar el juego.";
    // Abierta con doble clic, recargar no sirve: el propio mensaje dice qué hacer.
    const hint = location.protocol === "file:" ? "" : "Recarga la página para intentarlo de nuevo.";
    showError(error.message, hint);
    return;
  }

  for (const player of engine.players) {
    const option = document.createElement("option");
    option.value = player.name;
    option.textContent = `${player.icon} ${player.name}`;
    ui.bot.appendChild(option);
  }
  ui.bot.addEventListener("change", () => {
    showDescription();
    startGame();
  });
  ui.side.addEventListener("change", startGame);
  ui.newGame.addEventListener("click", startGame);

  setControlsEnabled(true);
  showDescription();
  startGame();
}

main();
