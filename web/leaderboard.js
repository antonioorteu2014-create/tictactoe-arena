// El marcador: dibuja la clasificación del último torneo.
//
// No juega partidas ni necesita Python: descarga leaderboard.json, el archivo
// que genera el torneo, y lo pinta en una tabla. Es independiente del juego: si
// el marcador falla, el tablero sigue funcionando, y al revés.
//
// El formato del archivo está acordado en la issue #10 y se comprueba en 
// tests/test_leaderboard_web.py.

"use strict";

// Todo va dentro de esta función para no chocar con los nombres de app.js (ui,
// game...): los scripts normales de una página comparten las variables globales.
(function () {
  const FILE = "leaderboard.json";
  const SCHEMA_VERSION = 1;
  // Las columnas de números, en el mismo orden que en la tabla de index.html.
  const NUMBERS = ["played", "wins", "draws", "losses", "forfeits", "points"];

  const message = document.getElementById("leaderboard-message");
  const table = document.getElementById("leaderboard-table");
  const rows = table.querySelector("tbody");
  const updated = document.getElementById("leaderboard-updated");

  // Muestra un aviso en lugar de la tabla.
  function say(text) {
    message.textContent = text;
    message.hidden = false;
    table.hidden = true;
    updated.hidden = true;
  }

  //El primer problema del archivo, o "" si se puede pintar.
  function problem(data) {
    if (!data || typeof data !== "object") {
      return "no es un objeto JSON";
    }
    if (data.schema_version !== SCHEMA_VERSION) {
      return `versión de formato desconocida (${data.schema_version})`;
    }
    if (!Array.isArray(data.standings)) {
      return "falta la lista de bots (standings)";
    }
    for (const row of data.standings) {
      if (!row || typeof row.name !== "string") {
        return "hay un bot sin nombre";
      }
      for (const key of ["rank", ...NUMBERS]) {
        if (typeof row[key] !== "number") {
          return `al bot ${row.name} le falta el dato ${key}`;
        }
      }
    }
    return "";
  }

  // Crea una celda con texto. Siempre como texto (textContent), nunca como HTML:
  // los nombres los eligen los autores de los bots, también los de otros equipos.
  function cell(tag, text, className) {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) {
      element.className = className;
    }
    return element;
  }

  function paint(data) {
    rows.replaceChildren();
    for (const row of data.standings) {
      const line = document.createElement("tr");
      line.append(cell("td", String(row.rank), "num"));

      const bot = cell("th", `${row.icon || ""} ${row.name}`.trim());
      bot.scope = "row";
      if (Array.isArray(row.authors) && row.authors.length > 0) {
        bot.append(cell("small", row.authors.join(", ")));
      }
      if (row.origin === "custom") {
        // Los bots enviados por otros equipos, para distinguirlos de los nuestros.
        bot.append(cell("span", "enviado por compañeros", "tag sent"));
      }
      line.append(bot);

      for (const key of NUMBERS) {
        line.append(cell("td", String(row[key]), "num"));
      }
      rows.append(line);
    }

    const when = new Date(data.generated_at);
    if (Number.isNaN(when.getTime())) {
      updated.hidden = true;
    } else {
      const date = when.toLocaleString("es-ES", { dateStyle: "long", timeStyle: "short" });
      updated.textContent = `Actualizada el ${date}.`;
      updated.hidden = false;
    }
    message.hidden = true;
    table.hidden = false;
  }

  async function load() {
    let response;
    try {
      // "no-cache": pregunta siempre al servidor si hay una versión nueva, para
      // no enseñar la clasificación de ayer guardada en el navegador.
      response = await fetch(FILE, { cache: "no-cache" });
    } catch (error) {
      say("No se ha podido descargar la clasificación. Comprueba tu conexión a internet.");
      return;
    }
    if (response.status === 404) {
      // Antes del primer torneo el archivo no existe: no es un error.
      say("Todavía no se ha jugado ningún torneo.");
      return;
    }
    if (!response.ok) {
      say(`No se ha podido descargar la clasificación (error ${response.status}).`);
      return;
    }

    let data;
    try {
      data = await response.json();
    } catch (error) {
      say("La clasificación no se ha podido leer: el archivo no es un JSON válido.");
      return;
    }
    const wrong = problem(data);
    if (wrong) {
      say(`La clasificación no se ha podido leer: ${wrong}.`);
      return;
    }
    if (data.standings.length === 0) {
      say("El último torneo no tenía bots.");
      return;
    }
    paint(data);
  }

  load().catch((error) => {
    // El motivo se apunta en la consola del navegador (F12 → Console).
    console.error(error);
    say("La clasificación no se ha podido mostrar.");
  });
})();


