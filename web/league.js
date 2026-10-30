// Pantalla «Liguilla»: la clasificación de las personas que juegan en «Jugar».
//
// No necesita Python. Cada partida terminada con al menos una persona se guarda
// en el navegador (localStorage) y la tabla se calcula a partir de esa lista.
// Una web en GitHub Pages no tiene servidor ni base de datos: por eso la
// liguilla es la de este navegador, y la página lo dice.

"use strict";

(function () {
  const { el, storage } = window.Arena;
  const KEY = "arena.league";
  const MAX_GAMES = 2000;

  const ui = {
    mode: document.getElementById("league-mode"),
    rival: document.getElementById("league-rival"),
    empty: document.getElementById("league-empty"),
    table: document.getElementById("league-table"),
    rows: document.getElementById("league-rows"),
    recent: document.getElementById("league-recent"),
    recentEmpty: document.getElementById("league-recent-empty"),
    clear: document.getElementById("league-clear"),
    confirm: document.getElementById("league-confirm"),
    yes: document.getElementById("league-clear-yes"),
    no: document.getElementById("league-clear-no"),
  };

  // Nombres de los modos, para los filtros y la lista de partidas. Se completan
  // cuando arranca Python; mientras, se usa la clave.
  const modeNames = {};

  function games() {
    const saved = storage.get(KEY, []);
    return Array.isArray(saved) ? saved.filter(isGame) : [];
  }

  // Lo guardado puede venir de una versión anterior o estar estropeado.
  function isGame(g) {
    return (
      g &&
      typeof g.mode === "string" &&
      g.x &&
      g.o &&
      typeof g.x.name === "string" &&
      typeof g.o.name === "string" &&
      (g.winner === null || g.winner === "X" || g.winner === "O")
    );
  }

  function recordGame(game) {
    const all = games();
    all.push(game);
    storage.set(KEY, all.slice(-MAX_GAMES));
    paint();
  }

  // La tabla: una fila por persona, con los filtros aplicados.
  function standings(list, rival) {
    const table = new Map();
    for (const g of list) {
      for (const [mark, seat, other] of [
        ["X", g.x, g.o],
        ["O", g.o, g.x],
      ]) {
        if (seat.kind !== "human") continue;
        if (rival !== "all" && other.kind !== rival) continue;
        const key = seat.name.trim().toLocaleLowerCase("es");
        if (!table.has(key)) {
          table.set(key, { name: seat.name.trim(), played: 0, wins: 0, draws: 0, losses: 0 });
        }
        const row = table.get(key);
        row.played += 1;
        if (g.winner === null) row.draws += 1;
        else if (g.winner === mark) row.wins += 1;
        else row.losses += 1;
      }
    }
    const rows = [...table.values()].map((r) => ({ ...r, points: r.wins + r.draws / 2 }));
    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.wins - a.wins ||
        a.played - b.played ||
        a.name.localeCompare(b.name, "es")
    );
    let rank = 0;
    let previous = null;
    rows.forEach((row, index) => {
      const tie = `${row.points}/${row.wins}`;
      if (tie !== previous) {
        rank = index + 1;
        previous = tie;
      }
      row.rank = rank;
    });
    return rows;
  }

  function paint() {
    const mode = ui.mode.value || "all";
    const rival = ui.rival.value;
    const all = games();
    const filtered = mode === "all" ? all : all.filter((g) => g.mode === mode);
    const rows = standings(filtered, rival);

    ui.rows.replaceChildren(
      ...rows.map((r) =>
        el(
          "tr",
          {},
          el("td", { class: "num", text: String(r.rank) }),
          el("th", { scope: "row", text: r.name }),
          el("td", { class: "num", text: String(r.played) }),
          el("td", { class: "num", text: String(r.wins) }),
          el("td", { class: "num", text: String(r.draws) }),
          el("td", { class: "num", text: String(r.losses) }),
          el("td", { class: "num", text: `${Math.round((100 * r.wins) / r.played)} %` }),
          el("td", { class: "num", text: String(r.points) })
        )
      )
    );
    ui.table.hidden = rows.length === 0;
    ui.empty.hidden = rows.length > 0;

    const recent = filtered.slice(-10).reverse();
    ui.recent.replaceChildren(
      ...recent.map((g) => {
        const result =
          g.winner === null
            ? "empate"
            : `gana ${g.winner === "X" ? g.x.name : g.o.name}${g.forfeit ? " (abandono)" : ""}`;
        const when = new Date(g.at);
        const date = Number.isNaN(when.getTime())
          ? ""
          : when.toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" });
        return el(
          "li",
          {},
          `${g.x.name} (X) contra ${g.o.name} (O) · ${modeNames[g.mode] || g.mode}: ${result} `,
          el("span", { class: "when", text: date })
        );
      })
    );
    ui.recentEmpty.hidden = recent.length > 0;
  }

  function fillModes(modes) {
    const current = ui.mode.value;
    ui.mode.replaceChildren(
      el("option", { value: "all", text: "Todos los modos" }),
      ...modes.map((m) => el("option", { value: m.key, text: `${m.icon} ${m.name}` }))
    );
    ui.mode.value = current || "all";
    if (!ui.mode.value) ui.mode.value = "all";
  }

  ui.mode.addEventListener("change", paint);
  ui.rival.addEventListener("change", paint);

  // Borrar pide confirmación en la propia página.
  ui.clear.addEventListener("click", () => {
    ui.clear.hidden = true;
    ui.confirm.hidden = false;
    ui.no.focus();
  });
  ui.no.addEventListener("click", () => {
    ui.confirm.hidden = true;
    ui.clear.hidden = false;
  });
  ui.yes.addEventListener("click", () => {
    storage.set(KEY, []);
    ui.confirm.hidden = true;
    ui.clear.hidden = false;
    paint();
  });

  // Si se juega en otra pestaña del navegador, esta se pone al día.
  window.addEventListener("storage", (event) => {
    if (event.key === KEY) paint();
  });
  window.Arena.onScreen((name) => {
    if (name === "liguilla") paint();
  });

  fillModes([]);
  paint();
  window.Arena.engine
    .then((engine) => {
      for (const m of engine.modes) modeNames[m.key] = `${m.icon} ${m.name}`;
      fillModes(engine.modes);
      paint();
    })
    .catch(() => {});

  window.Arena.recordGame = recordGame;
  window.Arena.leagueStandings = standings; // para depurar desde la consola
})();
