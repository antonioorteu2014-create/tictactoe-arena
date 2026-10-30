# La web

La web está en
**[antonioorteu2014-create.github.io/tictactoe-arena](https://antonioorteu2014-create.github.io/tictactoe-arena/)**
y funciona sin instalar nada, también en el móvil. Es una página estática
(GitHub Pages) que ejecuta el Python del proyecto **dentro del navegador** con
[Pyodide](https://pyodide.org): las reglas y los bots son exactamente los mismos
que en las pruebas y en el torneo.

El menú lleva a seis secciones:

| Sección | Qué hay |
|---|---|
| **Jugar** | Eliges el modo y quién juega con cada ficha: una persona o uno de los bots. Persona contra bot, dos personas, o dos bots (con pausa). A la izquierda se prepara la partida, en el centro está el tablero y a la derecha el registro de jugadas. |
| **Torneo** | Un **torneo por eliminatorias** en directo y, debajo, la [clasificación oficial](tournament.md). |
| **Liguilla** | La clasificación de las personas que han jugado, por modos y por tipo de rival. |
| **Reglas** | Las reglas de cada [modo de juego](modes.md). |
| **Bots** | Cómo piensa cada bot: aleatorio, voraz y minimax. |
| **Configuración** | Tema claro u oscuro y velocidad de los bots. |

## El diseño

El aspecto es el diseño **«Holograma»** de María: una aurora de color de fondo,
paneles de cristal con el filo teñido de aurora y un tablero de cristal en el que
las fichas se dibujan con luz (las X en turquesa y violeta, las O en magenta y
ámbar); la línea ganadora se enciende. Los títulos van en Michroma y el texto en
Barlow Condensed (Google Fonts). Hay tema claro y oscuro.

## Los luchadores

Cada bot tiene su personaje con guantes de boxeo: el **minimax** es un cerebro 🧠,
el **voraz** un tiburón musculoso 🦈 y el **aleatorio** un dado 🎲; los bots que
envían los compañeros salen como un robot. Aparecen en la pantalla **Bots**, en el
**podio** del ranking y en el **torneo en directo**: botan mientras esperan,
lanzan golpes cuando les toca, saltan al ganar y quedan K.O. al perder. Están
dibujados en SVG dentro de la propia página y se animan solo con CSS. Si el
sistema pide reducir el movimiento, no se animan.

## Cómo está hecha

```
web/
├── index.html      todas las pantallas
├── style.css       el aspecto (tema claro y oscuro)
├── engine.js       arranca Python (Pyodide) y carga el paquete (py.zip)
├── webglue.py      el puente: la página le pregunta y Python responde en JSON
├── app.js          pestañas, configuración y errores
├── fighters.js     los luchadores (SVG animado con CSS)
├── play.js         la pantalla «Jugar»
├── league.js       la liguilla de jugadores
├── arena.js        el torneo por eliminatorias
└── leaderboard.js  la clasificación oficial (results/leaderboard.json)
```

- **La página no sabe las reglas.** Cada posición (de quién es el turno, qué
  casillas están libres, quién ha ganado, qué ficha desaparece, en qué tablero toca
  jugar) se la da `webglue.py`, que usa `tictactoe.modes`. No hay una segunda
  versión de las reglas en JavaScript que pueda acabar distinta.
- **Un bot que falla no rompe la página.** Si lanza un error o devuelve un
  movimiento ilegal, pierde por abandono, igual que en el torneo.
- **Nada de lo que escriben otros se trata como HTML.** Los nombres de los bots y
  de los jugadores se escriben siempre como texto. Una prueba comprueba que ningún
  script usa `innerHTML`.

## La liguilla de jugadores

Cada partida que termina en «Jugar» con al menos una persona se apunta en la
liguilla: quién llevaba cada ficha, el modo y el resultado. La tabla se calcula a
partir de esa lista (victoria 1, empate ½, derrota 0), y se puede filtrar por modo
y por tipo de rival (personas o bots).

!!! note "Por qué se guarda en el navegador"
    GitHub Pages sirve archivos, pero no tiene servidor ni base de datos donde
    guardar resultados. Por eso la liguilla se guarda en el propio navegador
    (`localStorage`): es la liguilla **de ese ordenador**. Es la opción sin
    servidores, sin cuentas y sin datos personales fuera del ordenador de quien
    juega. Una liguilla compartida entre ordenadores necesitaría un servicio
    externo y control de trampas.

## El torneo por eliminatorias

La pestaña Torneo empieza con un torneo **por eliminatorias** que se juega en
directo en el navegador ([`tictactoe.knockout`](api.md#tictactoe.knockout)):

1. Se eligen los bots y Python **sortea el cuadro**. Si no son una potencia de 2,
   algunos pasan la primera ronda sin jugar (pase directo).
2. Cada **eliminatoria** son dos partidas, una con cada ficha (empezar es una
   ventaja). Si empatan, **muerte súbita** (hasta tres partidas más) y, si siguen
   empatados, **sorteo**. Dos bots perfectos empatan siempre, así que el sorteo es
   necesario.
3. Cada partida se ve **jugada a jugada**, con los dos luchadores cara a cara, y
   el cuadro se redibuja: el que gana avanza (dorado) y el que pierde queda
   tachado. Se puede pausar o saltar la animación.
4. Al final sale el **campeón**, en la última columna del cuadro.

Debajo sigue la **clasificación oficial**, que es otra cosa: una liguilla (todos
contra todos) que juega GitHub cada día; ver [El torneo](tournament.md). Es la
que cubre los requisitos 4.1 y 4.2.

A diferencia del torneo oficial, en el navegador no se puede abrir un proceso
aparte para cada partida, así que no hay límite de tiempo: un bot que falla o hace
trampa pierde, pero uno que se queda pensando para siempre bloquearía la página.
Por eso solo entran bots que ya han pasado la revisión de un pull request.

## Probarla en tu ordenador

```bash
python scripts/build_web.py              # empaqueta el Python en web/py.zip
tictactoe-tournament --output web/leaderboard.json   # opcional: la clasificación
python -m http.server 8000 --directory web
```

Y abre <http://localhost:8000>. Abierta con doble clic no funciona: el navegador no
deja descargar `py.zip` desde un archivo local.
