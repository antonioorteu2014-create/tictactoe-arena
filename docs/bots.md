# Nuestros bots

El proyecto trae tres bots, de menos a más fuerte. Cualquier bot nuevo se mide
contra ellos.

| Bot | Cómo decide | Mira hacia delante | Contra un rival perfecto |
|---|---|---|---|
| 🎲 `aleatorio` | Al azar entre las casillas libres | No | Pierde casi siempre |
| 🦈 `voraz` | Reglas sencillas: ganar, bloquear, preferir el centro | No | Pierde ante las dobles amenazas |
| 🧠 `minimax` | Busca todas las jugadas futuras (minimax con poda alfa-beta) | Hasta el final | **Empata: nunca pierde** |

## Resultados medidos

Generados con este comando. La semilla fija hace que los **resultados** salgan
siempre iguales; los **tiempos** dependen del ordenador y varían un poco entre
ejecuciones:

```bash
python scripts/benchmark.py --games 100 --seed 0
```

100 partidas por pareja y sentido: cada bot juega 100 veces con X y 100 con O
contra cada rival. Los porcentajes de las tres primeras columnas son sobre las 200
partidas; los de «Gana con X» y «Gana con O», sobre las 100 de cada lado.

| Bot | Rival | Gana | Empata | Pierde | Gana con X | Gana con O |
|---|---|---:|---:|---:|---:|---:|
| voraz | aleatorio | 94% | 6% | 1% | 99% | 88% |
| minimax | aleatorio | 86% | 14% | **0%** | 99% | 74% |
| minimax | voraz | 22% | 78% | **0%** | 45% | 0% |

| Bot | Tiempo medio por jugada | Jugada más lenta |
|---|---:|---:|
| aleatorio | 0,00 ms | 0,4 ms |
| voraz | 0,04 ms | 2,6 ms |
| minimax | 4,9 ms | 30 ms |

Lo que dicen los números:

- **El voraz gana el 94% al aleatorio** (más del 80% que pide la guía).
- **El minimax no pierde nunca**, contra nadie, ni con X ni con O. Las pruebas lo
  demuestran para *todas* las partidas posibles, no solo para estas.
- **El minimax gana al voraz** en el 22% de las partidas (45% cuando juega con X) y
  empata el resto. Con O no le gana nunca: el voraz siempre toma el centro y desde
  ahí ningún jugador perfecto puede forzar la victoria.
- **Contra el aleatorio, el minimax gana algo menos que el voraz** (86% frente a
  94%). Está explicado más abajo, en sus debilidades.

Los tiempos son de un portátil (MacBook Air) en una ejecución concreta. En la web,
donde Python corre dentro del navegador, la primera jugada del minimax tarda unos
130 ms, todavía muy por debajo de un segundo, y las siguientes, unos pocos ms.

---

## 🎲 aleatorio

Elige al azar entre las casillas libres, con un generador propio sembrado con la
semilla de la partida. No tiene estrategia: es la referencia que cualquier otro
bot debe superar. Pierde si el rival amenaza, porque no bloquea; y si gana, es por
casualidad.

---

## 🦈 voraz

Puntúa **cada jugada posible** y juega la que más puntúa. No mira hacia delante:
solo se pregunta qué tal es *esta* jugada.

### La puntuación

Para una casilla libre `c`, siendo «yo» el jugador al que le toca:

| Regla | Puntos |
|---|---:|
| Poner mi ficha en `c` completa una línea mía (**gano**) | 10.000 |
| Poner la ficha del rival en `c` completaría una línea suya (**bloqueo**) | 1.000 |
| Por cada línea que pasa por `c` y no tiene fichas del rival (**líneas abiertas**) | 1 |

Cada nivel supera a todos los de abajo juntos (como mucho hay 4 líneas abiertas
por casilla), así que ganar manda sobre bloquear y bloquear sobre la posición. Con
el tablero vacío, el centro toca 4 líneas, las esquinas 3 y los lados 2: por eso
abre siempre en el centro.

Si varias casillas empatan en la puntuación máxima, elige una **al azar** con su
generador sembrado.

### En qué juega mal

- **No ve las dobles amenazas.** Si el rival juega de forma que tendrá *dos* líneas
  a falta de una ficha a la vez, el voraz solo puede bloquear una. Verlas venir
  exige mirar jugadas hacia delante, y eso es justo lo que no hace.
- **No prepara sus propias dobles amenazas**: solo gana si el rival le deja una
  línea sin bloquear.

---

## 🧠 minimax

Para cada jugada posible, imagina la partida hasta el final suponiendo que **los
dos jugadores juegan lo mejor posible**, y elige la jugada con el mejor resultado
garantizado.

### El algoritmo

Se implementa como *negamax*: el valor de una posición para el jugador al que le
toca es **el opuesto** del valor de la mejor respuesta del rival. Es el mismo
minimax, con una sola función en lugar de una que maximiza y otra que minimiza.

```text
valor(posición, profundidad, alfa, beta):     # para el jugador al que le toca
    si el rival acaba de hacer tres en raya:
        devolver -(1000 + casillas libres)    # perder; cuanto antes, peor
    si el tablero está lleno:
        devolver 0                            # empate
    si profundidad == 0:
        devolver evaluación(posición)         # no se puede mirar más lejos
    mejor = -infinito
    para cada jugada, en el orden centro, esquinas, lados:
        v = -valor(posición tras la jugada, profundidad - 1, -beta, -alfa)
        mejor = max(mejor, v)
        alfa  = max(alfa, v)
        si alfa >= beta: parar                # poda alfa-beta
    devolver mejor
```

Las piezas que pide la guía:

- **Valor de las posiciones terminales.** Ganar vale 1.000 más las casillas que
  quedan libres, así que prefiere **ganar antes**. Perder vale lo mismo en negativo,
  así que, si va a perder, **retrasa la derrota** para dar al rival más ocasiones de
  equivocarse. El empate vale 0.
- **Evaluación de las posiciones no terminales.** Si llega al límite de profundidad
  sin que acabe la partida: por cada línea que solo tiene fichas mías, +1 si tiene
  una y +10 si tiene dos; lo mismo en negativo por las líneas que solo tienen fichas
  del rival. Las líneas con fichas de los dos no cuentan, porque ya no las puede
  ganar nadie. Es la misma idea que el voraz.
- **Límite de profundidad.** Por defecto, 9 movimientos: en el tres en raya caben
  todas las jugadas que quedan, así que el bot juega **perfecto**. Con menos
  profundidad juega peor, y sirve para medir qué aporta mirar más lejos:

    ```python
    from tictactoe.registry import load_players

    Minimax = load_players()["minimax"].cls
    corto_de_vista = Minimax(seed=0, depth=2)   # solo mira 2 movimientos
    ```

### Poda alfa-beta y memoria

- **Poda alfa-beta.** `alfa` es lo mejor que ya tiene garantizado quien mueve y
  `beta`, lo mejor que tiene garantizado el rival. Si una jugada demuestra que el
  rival nunca dejaría llegar a esa rama (`alfa >= beta`), deja de mirarla. El
  resultado es idéntico al de minimax sin poda. Probar primero las jugadas que
  suelen ser buenas (centro, esquinas, lados) hace que pode antes.
- **Memoria de posiciones (tabla de transposición).** Muchas posiciones se
  alcanzan por caminos distintos. El bot guarda el valor de cada posición que ya
  ha calculado, junto con si es exacto o solo un límite por culpa de la poda, y no
  la vuelve a buscar. La memoria dura toda la partida.

Con las dos cosas, la jugada más cara (el tablero vacío) examina unas 4.400
posiciones para calcular el valor de cada jugada, en vez de las 550.000 que
examinaría minimax sin poda ni memoria. Contando también el cálculo de trampas
del desempate (siguiente apartado), son unas 12.000, que es lo que informa
`last_search.nodes`, y tarda unas decenas de milisegundos.

### Elegir entre jugadas igual de buenas: poner trampas

Con juego perfecto el tres en raya es empate, así que a menudo **varias jugadas
tienen el mismo valor** (por ejemplo, todas llevan al empate). Para saber cuáles
empatan, en la raíz el bot busca cada jugada **con la ventana completa**
(`alfa = -infinito`, `beta = +infinito`), sin podar entre ellas: así obtiene el
valor exacto de cada una, y no solo «no mejor que la anterior». Para elegir entre
ellas, el bot imagina un rival **corto de vista**, como un novato o el voraz: si
puede ganar en una jugada, gana; si tiene que bloquear, bloquea; y si no, elige al
azar. Para cada jugada candidata calcula qué proporción de las respuestas de ese
rival le llevan a perder, y elige la que más. Una respuesta «le lleva a perder»
si, tras ella, la búsqueda (con dos movimientos menos de profundidad) da al bot
un valor de al menos 1.000: una victoria asegurada. Si siguen empatando, desempata con
la proporción contra un rival que juega totalmente al azar, después con la
puntuación del voraz y, por último, al azar con su generador sembrado.

La trampa buena es la que ese rival no ve venir: casi siempre, una jugada que
prepara una **doble amenaza**. Así es como el minimax gana al voraz.

### Qué piensa (opcional de la guía)

Después de cada jugada, el bot guarda en `last_search` lo que ha pensado: la
casilla elegida, su valor (≥ 1.000: victoria asegurada; ≤ −1.000: derrota
asegurada si el rival no falla; 0: empate con juego perfecto), todas las jugadas
que empataban en ese valor, la profundidad, cuántas posiciones ha examinado y
cuánto ha tardado.

### En qué juega mal

- **Contra un rival perfecto solo puede empatar.** Es una propiedad del tres en
  raya, no del bot.
- **Las trampas suponen un rival que bloquea.** Contra un rival que juega al azar
  rinden más otras jugadas, las que crean amenazas simples, porque ese rival no
  las bloquea. Por eso, contra el aleatorio, el minimax gana algo menos (86%) que el
  voraz (94%). Lo probamos: sumar los dos modelos de rival sube al 92-95% contra el
  aleatorio, pero el minimax deja de ganar al voraz (100% de empates). Una misma
  jugada no puede ser la mejor trampa para los dos tipos de rival, y elegimos el
  modelo que funciona contra quien bloquea, que es lo que hace una persona.
- **Con O no gana nunca al voraz**: el voraz abre en el centro y desde ahí no hay
  victoria forzada para nadie.
- **Con profundidad limitada** depende de la evaluación, que solo cuenta líneas
  abiertas: no ve una doble amenaza que se prepara más allá de su horizonte.

## Usarlos desde Python

```python
from tictactoe.match import play_game
from tictactoe.registry import load_players

bots = load_players()
minimax = bots["minimax"].cls.create(0)
voraz = bots["voraz"].cls.create(0)

result = play_game(minimax, voraz)   # minimax con X
print(result.winner, result.moves)
print(minimax.last_search)           # qué pensó en su última jugada
```

La referencia completa de las clases está en la [Referencia del API](api.md).
