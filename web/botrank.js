// Pantalla «Liguilla», primera parte: el ranking de bots, en gráfico.
//
// No necesita Python. Lee el mismo leaderboard.json que la clasificación oficial
// (lo publica el torneo diario de GitHub) y lo dibuja de dos formas:
//
// * un podio con los tres primeros y sus luchadores;
// * una barra por bot, dividida en sus partidas ganadas, empatadas y perdidas,
//   con los puntos al final. Al pasar el ratón por un trozo se ve el número.
//
// Todo se escribe como texto, nunca como HTML: los nombres de los bots los
// eligen sus autores, también los de otros equipos.

"use strict";

(function () {
  const { el, fighters } = window.Arena;
  const FILE = "leaderboard.json";

  const ui = {
    message: document.getElementById("bot-ranking-message"),
    podium: document.getElementById("podium"),
    bars: document.getElementById("bot-bars"),
    legend: document.getElementById("bot-legend"),
  };

  let standings = null;

  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

  function paintPodium(rows) {
    // El orden del podio: 2.º a la izquierda, 1.º en el centro, 3.º a la derecha.
    const order = [rows[1], rows[0], rows[2]].filter(Boolean);
    ui.podium.replaceChildren(
      ...order.map((row) => {
        const place = rows.indexOf(row) + 1;
        const figure = el("figure", { class: "fighter fighter-x" });
        fighters.render(figure, { kind: "bot", bot: row.name }, "", "");
        if (place === 1) fighters.setMood(figure, "winner", "¡Líder!");
        return el(
          "div",
          { class: `podium-place place-${place}` },
          figure,
          el("p", { class: "podium-name", text: `${row.icon || "🤖"} ${row.name}` }),
          el("p", { class: "podium-points", text: `${row.points} pts` }),
          el("div", { class: "podium-step", text: ["🥇", "🥈", "🥉"][place - 1] })
        );
      })
    );
    ui.podium.hidden = false;
  }

  function paintBars(rows) {
    const most = Math.max(...rows.map((r) => r.played), 1);
    ui.bars.replaceChildren(
      ...rows.map((row) => {
        const parts = [
          ["won", row.wins, plural(row.wins, "ganada", "ganadas")],
          ["drawn", row.draws, plural(row.draws, "empatada", "empatadas")],
          ["lost", row.losses, plural(row.losses, "perdida", "perdidas")],
        ];
        const bar = el(
          "div",
          {
            class: "bar",
            role: "img",
            "aria-label": `${row.name}: ${parts.map((p) => p[2]).join(", ")}`,
          },
          ...parts
            .filter(([, count]) => count > 0)
            .map(([cls, count, label]) =>
              el("span", {
                class: `bar-part ${cls}`,
                "data-width": String((100 * count) / most),
                title: label,
                text: count >= most / 12 ? String(count) : "",
              })
            )
        );
        return el(
          "div",
          { class: "bar-row" },
          el("span", { class: "bar-rank", text: String(row.rank) }),
          el(
            "span",
            { class: "bar-name" },
            `${row.icon || "🤖"} ${row.name}`,
            row.origin === "custom" ? el("span", { class: "tag sent", text: "enviado" }) : null
          ),
          bar,
          el("span", { class: "bar-points", text: `${row.points}` })
        );
      })
    );
    ui.bars.hidden = false;
    ui.legend.hidden = false;
    grow();
  }

  // Las barras crecen desde cero cada vez que se abre la pestaña.
  function grow() {
    const parts = ui.bars.querySelectorAll(".bar-part");
    for (const part of parts) part.style.width = "0%";
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        for (const part of parts) part.style.width = `${part.dataset.width}%`;
      })
    );
  }

  function paint(rows) {
    standings = rows;
    ui.message.hidden = true;
    paintPodium(rows);
    paintBars(rows);
  }

  async function load() {
    let response;
    try {
      response = await fetch(FILE, { cache: "no-cache" });
    } catch {
      ui.message.textContent = "No se ha podido descargar el ranking. Comprueba tu conexión.";
      return;
    }
    if (response.status === 404) {
      ui.message.textContent = "Todavía no se ha jugado ningún torneo.";
      return;
    }
    let data;
    try {
      data = await response.json();
    } catch {
      ui.message.textContent = "El ranking no se ha podido leer.";
      return;
    }
    const rows = Array.isArray(data && data.standings) ? data.standings : [];
    if (rows.length === 0) {
      ui.message.textContent = "El último torneo no tenía bots.";
      return;
    }
    paint(rows);
  }

  window.Arena.onScreen((name) => {
    if (name === "liguilla" && standings) grow();
  });

  load().catch((error) => {
    console.error(error);
    ui.message.textContent = "El ranking no se ha podido mostrar.";
  });
})();
