// El motor: arranca Python en el navegador (Pyodide), carga nuestro paquete y
// ofrece a la página las funciones del puente (webglue.py).
//
// La página nunca aplica las reglas del juego por su cuenta: todo lo que sabe
// del tres en raya se lo pregunta a Python, que usa el mismo código que las
// pruebas y el torneo.

const PYODIDE_VERSION = "0.28.0";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const MOUNT = "/lib/tictactoe-web";
// Tiempo máximo para descargar y arrancar Python. Si la conexión se corta a mitad,
// Pyodide se queda esperando sin dar error: así la página lo dice en vez de
// quedarse colgada para siempre.
const BOOT_TIMEOUT_MS = 90000;
const NETWORK_HINT = "Comprueba tu conexión a internet.";

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`no se pudo descargar ${src}`));
    document.head.appendChild(script);
  });
}

// Rechaza `promise` si tarda más de `ms` milisegundos.
function withTimeout(promise, ms, message) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

// Convierte la respuesta JSON del puente en un objeto (o lista). Si el puente
// informa de un error ({"ok": false}), lo lanza como excepción con su mensaje.
function parse(json) {
  const answer = JSON.parse(json);
  if (answer && !Array.isArray(answer) && answer.ok === false) {
    throw new Error(answer.error);
  }
  return answer;
}

async function startPython(onStatus) {
  onStatus("Descargando Python para el navegador… (la primera vez tarda unos segundos)");
  try {
    await loadScript(`${PYODIDE_CDN}pyodide.js`);
  } catch {
    throw new Error(`No se pudo descargar Python para el navegador. ${NETWORK_HINT}`);
  }
  const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

  onStatus("Preparando las librerías…");
  // loadPackage no lanza un error si falla la descarga: solo lo avisa por aquí.
  const failed = [];
  await pyodide.loadPackage("pyyaml", { errorCallback: (message) => failed.push(message) });
  if (failed.length > 0) {
    console.error(failed.join("\n"));
    throw new Error(`No se pudieron descargar las librerías del juego. ${NETWORK_HINT}`);
  }
  return pyodide;
}

// Arranca el motor. `onStatus` recibe mensajes de progreso para mostrarlos.
async function bootEngine(onStatus = () => {}) {
  if (location.protocol === "file:") {
    // Abierta con doble clic, el navegador no deja descargar py.zip.
    throw new Error(
      "La página no funciona abierta con doble clic. Sírvela con " +
        "«python -m http.server 8000 --directory web» y abre http://localhost:8000."
    );
  }
  const pyodide = await withTimeout(
    startPython(onStatus),
    BOOT_TIMEOUT_MS,
    `Python tarda demasiado en descargarse. ${NETWORK_HINT}`
  );

  onStatus("Cargando el juego…");
  // `cache: "no-cache"` hace que, tras publicar una versión nueva, el navegador
  // no se quede con el paquete antiguo.
  let response;
  try {
    response = await fetch("py.zip", { cache: "no-cache" });
  } catch {
    throw new Error(`No se pudo descargar el juego (py.zip). ${NETWORK_HINT}`);
  }
  if (!response.ok) {
    throw new Error(
      "No se encontró py.zip. En local, ejecuta antes: python scripts/build_web.py."
    );
  }
  pyodide.FS.mkdirTree(MOUNT);
  pyodide.unpackArchive(await response.arrayBuffer(), "zip", { extractDir: MOUNT });
  pyodide.runPython(`import sys; sys.path.insert(0, ${JSON.stringify(MOUNT)})`);

  onStatus("Cargando los bots…");
  let glue;
  try {
    glue = pyodide.pyimport("webglue");
  } catch (error) {
    console.error(error); // el detalle técnico, para quien depure
    throw new Error("No se pudo arrancar el juego en el navegador.");
  }
  const players = parse(glue.init(MOUNT)).players;
  if (players.length === 0) {
    throw new Error("no hay ningún bot admitido");
  }

  // La interfaz pública que usa app.js (y que se puede probar desde la consola
  // del navegador: por ejemplo, `Engine.legalMoves("X........")`).
  const engine = {
    pyodide, // acceso directo a Python, para depurar desde la consola
    players,
    newGame: (botName, seed) => parse(glue.new_game(botName, seed)),
    play: (state, move) => parse(glue.play(JSON.stringify(state), JSON.stringify(move))),
    botMove: (state) => parse(glue.bot_move(JSON.stringify(state))),
    status: (state) => parse(glue.status(JSON.stringify(state))),
    legalMoves: (state) => parse(glue.legal_moves(JSON.stringify(state))),
  };
  window.Engine = engine;
  return engine;
}

window.bootEngine = bootEngine;
