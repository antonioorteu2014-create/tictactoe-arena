// La base de la página: las pestañas, la configuración, los errores y el arranque
// de Python. Las pantallas (play.js, league.js, arena.js, leaderboard.js) usan lo
// que se publica aquí en `window.Arena`.
//
// La página no sabe las reglas del juego: se las pregunta al Python del proyecto
// a través del motor (engine.js). Aquí solo se pregunta y se dibuja.

"use strict";

(function () {
  const SCREENS = ["menu", "reglas", "bots", "jugar", "liguilla", "torneo", "ajustes"];
  const errorBox = document.getElementById("error");

  // ------------------------------------------------------------------------
  // Utilidades
  // ------------------------------------------------------------------------

  // Crea un elemento. El texto va siempre como texto (nunca como HTML): los
  // nombres de los bots y de los jugadores los escribe cualquiera.
  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value === undefined || value === null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children) {
      if (child !== null && child !== undefined) node.append(child);
    }
    return node;
  }

  // localStorage puede no estar disponible (modo privado, bloqueado...): la página
  // sigue funcionando, solo que sin recordar nada.
  const storage = {
    get(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    },
  };

  // ------------------------------------------------------------------------
  // Errores: siempre visibles. Una web estática no tiene registro en un servidor,
  // así que un error que no se muestra es un error que nadie llega a ver.
  // ------------------------------------------------------------------------

  function showError(message, hint = "Prueba otra vez o recarga la página.") {
    const sentence = /[.!?]$/.test(message) ? message : `${message}.`;
    errorBox.textContent = `Algo ha ido mal: ${sentence} ${hint}`.trim();
    errorBox.hidden = false;
  }

  function clearError() {
    errorBox.hidden = true;
  }

  window.addEventListener("error", (event) => showError(event.message || "error desconocido"));
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    showError(reason && reason.message ? reason.message : String(reason));
  });

  // ------------------------------------------------------------------------
  // Pestañas: cada una es una sección; la dirección (#jugar...) dice cuál se ve.
  // ------------------------------------------------------------------------

  const listeners = [];

  function currentScreen() {
    const name = location.hash.replace("#", "");
    // Los enlaces antiguos a la clasificación (#leaderboard) llevan al torneo.
    if (name === "leaderboard") return "torneo";
    return SCREENS.includes(name) ? name : "menu";
  }

  function showScreen() {
    const name = currentScreen();
    for (const section of document.querySelectorAll("section.screen")) {
      section.hidden = section.dataset.screen !== name;
    }
    for (const link of document.querySelectorAll(".tabs a")) {
      if (link.dataset.screen === name) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    for (const listener of listeners) listener(name);
  }

  window.addEventListener("hashchange", () => {
    showScreen();
    window.scrollTo(0, 0);
  });

  // ------------------------------------------------------------------------
  // Configuración
  // ------------------------------------------------------------------------

  const settings = {
    theme: storage.get("arena.theme", "auto"),
    botDelay: storage.get("arena.botDelay", 450),
  };

  function applyTheme() {
    if (settings.theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", settings.theme);
  }

  const themeSelect = document.getElementById("setting-theme");
  const speedSelect = document.getElementById("setting-speed");
  themeSelect.value = settings.theme;
  speedSelect.value = String(settings.botDelay);
  if (!speedSelect.value) speedSelect.value = "450";
  themeSelect.addEventListener("change", () => {
    settings.theme = themeSelect.value;
    storage.set("arena.theme", settings.theme);
    applyTheme();
  });
  speedSelect.addEventListener("change", () => {
    settings.botDelay = Number(speedSelect.value);
    storage.set("arena.botDelay", settings.botDelay);
  });
  applyTheme();

  // ------------------------------------------------------------------------
  // Python: se arranca una vez, en segundo plano, nada más abrir la página.
  // ------------------------------------------------------------------------

  const engineStatus = document.getElementById("engine-status");
  const enginePromise = window
    .bootEngine((message) => {
      engineStatus.textContent = message;
    })
    .then((engine) => {
      engineStatus.hidden = true;
      return engine;
    })
    .catch((error) => {
      engineStatus.textContent = `No se pudo arrancar Python: ${error.message}`;
      showError(error.message, "");
      throw error;
    });

  // ------------------------------------------------------------------------
  // Reglas: una tarjeta por modo, con las reglas que da Python.
  // ------------------------------------------------------------------------

  enginePromise
    .then((engine) => {
      document.getElementById("rules-list").replaceChildren(
        ...engine.modes.map((mode) =>
          el(
            "article",
            { class: "panel rule-card" },
            el("h2", { text: `${mode.icon} ${mode.name}` }),
            el("p", { class: "rule-summary", text: mode.summary }),
            el("ul", {}, ...mode.rules.map((rule) => el("li", { text: rule }))),
            el("p", {
              class: "muted",
              text: mode.humans_only ? "Solo para dos personas." : "Contra un bot o contra otra persona.",
            })
          )
        )
      );
    })
    .catch(() => {});

  window.Arena = {
    el,
    storage,
    settings,
    showError,
    clearError,
    engine: enginePromise,
    onScreen: (listener) => listeners.push(listener),
  };

  // Tras cargar todos los scripts, se muestra la pestaña de la dirección y se
  // dibujan los luchadores de la pantalla «Bots».
  window.addEventListener("DOMContentLoaded", () => {
    for (const figure of document.querySelectorAll("#screen-bots .fighter")) {
      const name = figure.dataset.bot;
      window.Arena.fighters.render(figure, { kind: "bot", bot: name }, "", "");
    }
    showScreen();
  });
})();
