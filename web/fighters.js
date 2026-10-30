// Los luchadores: un personaje con guantes de boxeo para cada jugador.
//
// Cada bot tiene el suyo (el minimax es un cerebro, el voraz un tiburón y el
// aleatorio un dado), los bots que envían los compañeros son un robot y una
// persona es un boxeador. Se dibujan en SVG dentro de la página, sin imágenes
// que descargar, y se animan solo con CSS (style.css, «Luchadores»): botan
// mientras esperan, lanzan golpes cuando les toca, celebran al ganar y quedan KO
// al perder.

"use strict";

(function () {
  const INK = "#2b2118";

  // Un guante de boxeo mirando a la derecha, centrado en (0, 0).
  function glove(cls, x, y) {
    return `
      <g class="glove ${cls}" transform="translate(${x} ${y})"><g class="g">
        <rect x="-19" y="-7" width="8" height="15" rx="2" fill="#f6f1e4" stroke="${INK}" stroke-width="2"/>
        <ellipse cx="0" cy="0" rx="13" ry="12" fill="#c8102e" stroke="${INK}" stroke-width="2"/>
        <ellipse cx="2" cy="6" rx="7" ry="4" fill="#9d0c24"/>
        <path d="M-5 -7 q6 -4 12 1" stroke="#ff8090" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      </g></g>`;
  }

  const ARMS = `
    <path d="M56 92 Q44 96 37 92" stroke="${INK}" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M84 90 Q98 86 104 84" stroke="${INK}" stroke-width="4" fill="none" stroke-linecap="round"/>`;

  const EYES = (y, dx = 2) => `
    <circle cx="60" cy="${y}" r="6.5" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
    <circle cx="80" cy="${y}" r="6.5" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
    <circle cx="${60 + dx}" cy="${y + 1}" r="3" fill="${INK}"/>
    <circle cx="${80 + dx}" cy="${y + 1}" r="3" fill="${INK}"/>
    <path d="M52 ${y - 10} L66 ${y - 6}" stroke="${INK}" stroke-width="3" stroke-linecap="round"/>
    <path d="M88 ${y - 10} L74 ${y - 6}" stroke="${INK}" stroke-width="3" stroke-linecap="round"/>`;

  const BODIES = {
    // Minimax: un cerebro visto de lado, con sus pliegues, el cerebelo y el tronco.
    brain: `
      <path d="M90 92 Q93 106 98 118 L106 116 Q100 104 101 92 Z" fill="#8c2a5a" stroke="${INK}" stroke-width="1.5"/>
      <path d="M70 86 Q78 104 98 102 Q114 100 114 86 Q96 94 70 86 Z" fill="#d6558e" stroke="${INK}" stroke-width="1.5"/>
      <path d="M78 94 q10 4 22 0 M84 99 q8 2 16 -1" stroke="#8c2a5a" stroke-width="2" fill="none" stroke-linecap="round"/>
      <path d="M24 64 Q20 40 40 32 Q48 16 68 20 Q84 10 100 20 Q120 20 126 40 Q136 56 126 72
               Q122 88 104 88 Q92 96 76 88 Q60 96 46 88 Q26 86 24 64 Z"
            fill="#eb9cc6" stroke="#9c3a6c" stroke-width="2"/>
      <g stroke="#d6558e" stroke-width="3.6" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M36 50 q8 -10 18 -6 m-8 -2 l-4 -8"/>
        <path d="M58 30 q2 10 -6 16"/>
        <path d="M70 24 q10 6 6 18 q-2 8 8 12"/>
        <path d="M92 24 q-6 10 4 16 m0 0 q6 2 12 -4"/>
        <path d="M112 34 q8 6 6 16"/>
        <path d="M30 70 q10 -6 18 2 q6 6 14 2"/>
        <path d="M56 56 q14 -8 26 -2"/>
        <path d="M44 80 q8 -4 14 2"/>
        <path d="M116 64 q-8 6 -4 14"/>
      </g>
      <circle cx="92" cy="58" r="7.5" fill="#fff" stroke="${INK}" stroke-width="1.6"/>
      <circle cx="110" cy="56" r="7.5" fill="#fff" stroke="${INK}" stroke-width="1.6"/>
      <circle cx="95" cy="59" r="3.4" fill="${INK}"/><circle cx="113" cy="57" r="3.4" fill="${INK}"/>
      <path d="M83 46 L99 51 M119 44 L105 49" stroke="${INK}" stroke-width="3.4" stroke-linecap="round"/>
      <path d="M94 74 q9 5 18 -2" stroke="${INK}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M46 90 Q40 98 33 96" stroke="${INK}" stroke-width="4.5" fill="none" stroke-linecap="round"/>
      <path d="M96 84 Q104 84 104 84" stroke="${INK}" stroke-width="4.5" fill="none" stroke-linecap="round"/>`,
    // Voraz: un tiburón musculoso con una sonrisa llena de dientes.
    shark: `
      <path d="M36 44 L40 12 L62 38 Z" fill="#4f7088" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
      <path d="M30 60 Q22 98 44 120 L96 120 Q106 96 96 66 Z" fill="#6a8ea8" stroke="${INK}" stroke-width="2"/>
      <path d="M56 70 Q50 96 60 120 L84 120 Q90 96 86 72 Z" fill="#1f2a30"/>
      <path d="M28 54 Q30 26 68 22 Q104 20 132 42 Q124 52 108 56 Q82 68 50 68 Q30 66 28 54 Z"
            fill="#6a8ea8" stroke="${INK}" stroke-width="2"/>
      <path d="M58 60 Q92 70 126 46 Q120 60 104 68 Q84 78 62 70 Z" fill="#eef2f5" stroke="${INK}" stroke-width="1.5"/>
      <path d="M62 58 Q94 70 126 45 Q116 66 94 70 Q74 72 62 58 Z" fill="#7a1d28" stroke="${INK}" stroke-width="2"/>
      <path d="M64 59 L68 65 L72 61 L76 67 L80 62 L84 68 L88 63 L92 68 L96 62 L100 66 L104 59 L108 62 L112 55 L116 57 L120 50 L124 47 Z"
            fill="#fff" stroke="${INK}" stroke-width="1"/>
      <path d="M72 70 L76 65 L80 70 L84 66 L88 71 L92 66 L96 70 L100 64 L104 67 L108 61 L112 63 L104 69 L90 72 Z"
            fill="#fff" stroke="${INK}" stroke-width="1"/>
      <path d="M40 46 v14 M46 44 v15 M52 43 v14" stroke="#3e5a6e" stroke-width="2.4" stroke-linecap="round"/>
      <circle cx="96" cy="36" r="5" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
      <circle cx="98" cy="37" r="2.6" fill="${INK}"/>
      <path d="M86 28 L106 35" stroke="${INK}" stroke-width="4" stroke-linecap="round"/>
      <circle cx="122" cy="40" r="1.6" fill="${INK}"/>
      <path d="M28 82 Q14 92 22 104 Q30 112 40 104" fill="#6a8ea8" stroke="${INK}" stroke-width="2"/>
      <path d="M84 74 Q104 62 116 76 Q124 90 108 96 Q94 100 84 90 Z" fill="#6a8ea8" stroke="${INK}" stroke-width="2"/>
      <path d="M92 76 q10 -6 18 2" stroke="#9fbcd0" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <path d="M96 92 q6 4 12 0" stroke="#3e5a6e" stroke-width="2" fill="none" stroke-linecap="round"/>`,
    // Aleatorio: un dado.
    dice: `
      <g transform="rotate(-8 70 74)">
        <rect x="38" y="42" width="64" height="64" rx="13" fill="#fbfaf5" stroke="${INK}" stroke-width="2.5"/>
        <circle cx="52" cy="56" r="4.5" fill="${INK}"/><circle cx="88" cy="92" r="4.5" fill="${INK}"/>
        <circle cx="88" cy="56" r="4.5" fill="#c8102e"/><circle cx="52" cy="92" r="4.5" fill="#c8102e"/>
        <circle cx="62" cy="70" r="6" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
        <circle cx="78" cy="70" r="6" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
        <circle cx="63" cy="71" r="2.8" fill="${INK}"/><circle cx="79" cy="71" r="2.8" fill="${INK}"/>
        <path d="M61 84 q9 8 18 0" stroke="${INK}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      </g>`,
    // Un bot de los compañeros: un robot.
    robot: `
      <line x1="70" y1="44" x2="70" y2="30" stroke="${INK}" stroke-width="3"/>
      <circle class="antenna" cx="70" cy="28" r="5" fill="#d4a017" stroke="${INK}" stroke-width="2"/>
      <rect x="44" y="44" width="52" height="44" rx="10" fill="#a9b4bb" stroke="${INK}" stroke-width="2"/>
      <rect x="53" y="56" width="13" height="10" rx="2" fill="#4cc9f0" stroke="${INK}" stroke-width="1.5"/>
      <rect x="74" y="56" width="13" height="10" rx="2" fill="#4cc9f0" stroke="${INK}" stroke-width="1.5"/>
      <path d="M56 76 h28 M60 76 v5 M66 76 v5 M72 76 v5 M78 76 v5" stroke="${INK}" stroke-width="2"/>
      <rect x="52" y="88" width="36" height="22" rx="6" fill="#8d999f" stroke="${INK}" stroke-width="2"/>`,
    // Una persona: un boxeador.
    person: `
      <path d="M50 88 Q70 80 90 88 L88 112 L52 112 Z" fill="#0e3b2e" stroke="${INK}" stroke-width="2"/>
      <path d="M52 92 L88 92" stroke="#d4a017" stroke-width="3"/>
      <circle cx="70" cy="62" r="22" fill="#f1c7a0" stroke="${INK}" stroke-width="2"/>
      <path d="M48 56 Q70 40 92 56 L92 50 Q70 30 48 50 Z" fill="#3a2a1a"/>
      <rect x="47" y="52" width="46" height="7" rx="3" fill="#b23a48"/>
      <circle cx="62" cy="66" r="2.8" fill="${INK}"/><circle cx="78" cy="66" r="2.8" fill="${INK}"/>
      <path d="M62 75 q8 6 16 0" stroke="${INK}" stroke-width="2.5" fill="none" stroke-linecap="round"/>`,
  };

  // El tiburón y el cerebro dibujan sus propios brazos.
  const OWN_ARMS = new Set(["shark", "brain"]);

  const BY_BOT = {
    aleatorio: "dice",
    voraz: "shark",
    minimax: "brain",
  };

  // Qué personaje le toca a un jugador: {kind: "human"} o {kind: "bot", bot}.
  function kindFor(seat) {
    if (!seat || seat.kind === "human") return "person";
    return BY_BOT[seat.bot] || "robot";
  }

  function drawing(kind) {
    const markup =
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 130" aria-hidden="true">` +
      `${glove("back", 30, 92)}<g class="body">${BODIES[kind]}</g>` +
      `${OWN_ARMS.has(kind) ? "" : ARMS}${glove("front", 110, 84)}` +
      `</svg>`;
    // El dibujo es nuestro y fijo; los nombres se escriben aparte, como texto.
    const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
    return document.importNode(doc.documentElement, true);
  }

  // Pinta en `figure` el luchador de `seat`, con su ficha y su nombre.
  function render(figure, seat, mark, name) {
    if (!figure) return; // la pantalla no tiene sitio para este luchador
    const kind = kindFor(seat);
    if (figure.dataset.kind !== kind) {
      const art = document.createElement("div");
      art.className = "fighter-art";
      art.append(drawing(kind));
      const caption = document.createElement("figcaption");
      const badge = document.createElement("span");
      const label = document.createElement("span");
      const bubble = document.createElement("span");
      badge.className = `fighter-mark mark-${mark.toLowerCase()}`;
      label.className = "fighter-name";
      bubble.className = "fighter-bubble";
      bubble.hidden = true;
      caption.append(badge, label);
      figure.replaceChildren(bubble, art, caption);
      figure.dataset.kind = kind;
    }
    figure.querySelector(".fighter-mark").textContent = mark;
    figure.querySelector(".fighter-mark").hidden = !mark;
    figure.querySelector("figcaption").hidden = !mark && !name;
    figure.querySelector(".fighter-name").textContent = name;
  }

  // El estado del luchador: "", "turn", "thinking", "winner", "loser" o "draw".
  function setMood(figure, mood, bubble = "") {
    if (!figure) return;
    for (const m of ["turn", "thinking", "winner", "loser", "draw"]) {
      figure.classList.toggle(m, m === mood);
    }
    const node = figure.querySelector(".fighter-bubble");
    if (node) {
      node.textContent = bubble;
      node.hidden = !bubble;
    }
  }

  window.Arena.fighters = { kindFor, render, setMood };
})();
