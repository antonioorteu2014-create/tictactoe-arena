# Modos de juego

Además del clásico, la web tiene tres variantes del tres en raya. Todas están
en la librería, en el paquete [`tictactoe.modes`](api.md#tictactoe.modes), y
siguen la misma interfaz que el clásico: de quién es el turno, qué movimientos son
legales, cómo queda el tablero y quién gana. La web no sabe ninguna regla: se las
pregunta a este paquete, igual que las pruebas.

| Modo | Idea | Bots |
|---|---|---|
| ⭕ **Clásico** | El de siempre. | Los de la plataforma: los del equipo y los [enviados por pull request](upload-a-bot/submit-a-player.md). |
| 🔄 **Inverso** | Pierde quien hace tres en raya. | aleatorio, voraz, minimax |
| ♻️ **Tres fichas** | Solo tres fichas por jugador: la cuarta borra la más antigua. | aleatorio, voraz, minimax |
| 🎓 **Preguntas IA** | Para poner ficha hay que acertar una pregunta de la asignatura. | Ninguno: solo personas |

El torneo y el API `Player` siguen siendo del modo clásico: los modos son para
jugar en la web.

## Las reglas

### 🔄 Inverso

El tablero, los turnos y los movimientos son los del clásico, y la partida también
termina con la primera línea o con el tablero lleno. Lo único que cambia es el
resultado: **quien hace tres en raya pierde**. Hay que obligar al rival a hacerla.

Como la partida termina en el mismo momento que en el clásico, los estados válidos
son exactamente los mismos: el modo reutiliza `tictactoe.game` y solo da la vuelta
al ganador.

### ♻️ Tres fichas

Cada jugador solo puede tener **tres fichas** en el tablero. Si ya tiene tres, al
poner la cuarta **desaparece su ficha más antigua**. La web la marca («se va»)
antes de mover. Gana quien hace tres en raya. El tablero nunca se llena, así que,
para que la partida no dure para siempre, **tras 60 movimientos sin ganador es
empate**.

El estado guarda, además de las casillas, **el orden** en que se pusieron (para
saber cuál desaparece) y **el número de movimientos** (cuando los dos tienen tres
fichas, el tablero ya no dice de quién es el turno): `"40|8|3"` significa X en 4
(la más antigua) y 0, O en 8, y 3 movimientos jugados.

### 🎓 Preguntas IA

Pensado para que **dos personas** de la clase se midan también en lo que saben de
Inteligencia Artificial:

1. Al elegir una casilla sale una **pregunta tipo test** (4 opciones, una correcta)
   sacada de los apuntes de la asignatura.
2. Si **aciertas**, pones tu ficha y se ve la explicación de la respuesta.
3. Si **fallas**, no la pones y el **turno pasa** al rival. **La pregunta se queda
   en esa casilla** (marcada con «?») para el siguiente que la intente, con la
   opción fallada tachada. No se revela cuál era la buena: así el rival tiene su
   oportunidad, y una pista (una opción menos).
4. Se gana como en el clásico.

No se puede esquivar una pregunta: una vez elegida la casilla, hay que responder.
No admite bots, porque la gracia es comparar lo que saben las personas.

Como fallar pasa el turno sin poner ficha, el número de fichas ya no dice a quién le
toca: el estado guarda el turno (`"X...O....|X"`).

**El banco de preguntas** está en `src/tictactoe/modes/preguntas.json`: 200
preguntas, 10 por cada tema de los apuntes (de la introducción a la optimización
multiobjetivo). Cada una tiene su tema, las cuatro opciones, la correcta y una
explicación breve que se muestra al responder. **La página nunca recibe la respuesta
correcta antes de contestar**, y tampoco después de un fallo: la comprueba Python
([`answer`][tictactoe.modes.quiz.answer]), que solo la devuelve cuando se acierta.
Una prueba automática revisa el banco entero: identificadores únicos, cuatro
opciones distintas, una correcta válida y que la correcta no caiga siempre en la
misma letra.

## Los bots de los modos

En el inverso y en tres fichas juegan **los mismos tres bots del equipo**, con la
misma idea, aplicada a las reglas de cada modo. Están en
[`tictactoe.modes.bots`](api.md#tictactoe.modes.bots): reciben el modo y la
posición, y usan solo las reglas del propio modo.

| Bot | Cómo decide |
|---|---|
| 🎲 **aleatorio** | Al azar entre los movimientos legales. |
| 🦈 **voraz** | Mira solo la jugada siguiente: gana si puede y bloquea si debe. Es una búsqueda de 2 jugadas. |
| 🧠 **minimax** | Minimax (negamax) con poda alfa-beta y memoria. En el inverso llega al final de la partida y juega perfecto; en tres fichas mira 7 jugadas y valora lo que ve con las amenazas de cada uno. |

En el modo clásico juegan los bots de la plataforma ([Nuestros bots](bots.md)) y
los que envían los compañeros. La web explica cada estrategia en la pestaña
**Bots** del menú.

### Lo que comprueban las pruebas

- El minimax del inverso elige una jugada perfecta en **las 4.520 posiciones** del
  juego, comparado con un solucionador independiente sin poda.
- El minimax de tres fichas gana a un bot aleatorio y no deja pasar una victoria
  inmediata.
- Cada modo ofrece exactamente los tres bots del equipo, y todos juegan movimientos
  legales.
