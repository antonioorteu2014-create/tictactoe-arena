# Reglas del juego

El **tres en raya** (*tic-tac-toe*) es un juego por turnos para **dos jugadores**
sobre un tablero de 3 × 3 casillas. Esta página lo describe por completo: con ella
se puede jugar una partida en papel sin haber oído hablar nunca del juego.

## Los jugadores

Hay dos jugadores, **X** y **O**. Cada uno coloca siempre fichas de su símbolo.

## La posición inicial

El tablero empieza **vacío**: nueve casillas libres.

```
 . | . | .
---+---+---
 . | . | .
---+---+---
 . | . | .
```

**Siempre empieza X.** Después los jugadores se alternan: X, O, X, O…

## El turno

En su turno, el jugador **coloca una ficha de su símbolo en una casilla vacía**.
Eso es todo lo que se puede hacer:

- No se puede colocar una ficha en una casilla ocupada.
- No se puede mover ni retirar una ficha ya colocada.
- **No se puede pasar el turno.** Mientras la partida no haya terminado siempre
  queda al menos una casilla vacía, así que siempre hay un movimiento posible.

## El final de la partida

La partida termina en cuanto ocurre una de estas dos cosas:

1. **Tres en raya.** Un jugador tiene tres fichas suyas en línea: en una de las
   **3 filas**, en una de las **3 columnas** o en una de las **2 diagonales**. Ese
   jugador **gana**.
2. **Tablero lleno.** Las nueve casillas están ocupadas y nadie ha hecho tres en
   raya. La partida termina en **empate** (tablas).

Si la última casilla libre completa un tres en raya, la partida es una
**victoria**, no un empate: la línea se comprueba antes que el tablero lleno.

Una vez terminada la partida ya no se puede jugar ningún movimiento más.

## Información oculta y azar

El tres en raya **no tiene información oculta**: los dos jugadores ven siempre el
tablero entero. Tampoco **tiene azar**: no hay dados, cartas ni sorteos. Lo que
ocurre en la partida depende solo de las decisiones de los jugadores.

Por eso es un juego **resuelto**: si los dos jugadores juegan perfectamente, la
partida termina siempre en empate.

## Cómo lo representa el código

Para quien programe un bot, o use la librería desde Python, el juego se
representa con tipos básicos.

### El estado: una cadena de 9 caracteres

Una posición es un `str` de longitud 9, una letra por casilla, leyendo el tablero
**por filas, de izquierda a derecha y de arriba abajo**:

- `"X"`: casilla con ficha de X.
- `"O"`: casilla con ficha de O. Es la letra O mayúscula, no el número cero.
- `"."`: casilla vacía.

Por ejemplo, el estado `"X.O.X...O"` corresponde a este tablero:

```
 X | . | O
---+---+---
 . | X | .
---+---+---
 . | . | O
```

El estado **no guarda a quién le toca**, porque se deduce del tablero: como
siempre empieza X, si hay tantas X como O le toca a X, y si hay una X más le toca
a O.

### El movimiento: un número del 0 al 8

Un movimiento es el **número de la casilla** donde se coloca la ficha, con la
misma numeración que el estado:

```
 0 | 1 | 2
---+---+---
 3 | 4 | 5
---+---+---
 6 | 7 | 8
```

El jugador que coloca la ficha no hace falta indicarlo: siempre es el jugador al
que le toca.

!!! note "En la terminal se numera del 1 al 9"
    Para que jugar a mano resulte natural, el juego de terminal
    (`tictactoe-play`) pide las casillas del **1 al 9**. Por dentro se traducen a
    la numeración 0-8 de esta sección.
