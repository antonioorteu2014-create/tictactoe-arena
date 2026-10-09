# Cómo contribuir a Tic-Tac-Toe Arena

¡Gracias por querer contribuir! La contribución más habitual es **enviar un
bot**, y para eso hay un tutorial paso a paso:

- **[Enviar tu bot](https://tictactoe-arena.readthedocs.io/es/latest/upload-a-bot/submit-a-player/)**
  (qué tiene que hacer un bot: [El API de jugador](https://tictactoe-arena.readthedocs.io/es/latest/upload-a-bot/player-api/)).

## Enviar un bot, en resumen

1. Haz un **fork** del repositorio y crea una rama.
2. Añade **un archivo** en `players/custom/` con una clase que herede de
   `tictactoe.player.Player` (nombre del archivo: `tu-usuario-tu-bot.py`).
3. Añade **una entrada** en `players/custom/players.yaml`:

   ```yaml
   players:
     - file: tu-usuario-tu-bot.py
       class: TuBot
   ```

4. Comprueba en local que todo pasa: `pytest -q` y `ruff check players/custom`.
5. Abre un **pull request** contra `main` y rellena la plantilla.

No toques ningún otro archivo. La prueba de contrato (`tests/test_players.py`)
examina tu bot automáticamente: no hace falta que escribas pruebas.

## Criterios de aceptación de un bot

- Un solo archivo en `players/custom/` y una sola entrada en su `players.yaml`.
- Hereda de `tictactoe.player.Player` y su nombre (`get_name()`) es único.
- Devuelve siempre movimientos legales y no lanza excepciones.
- Solo usa la librería estándar de Python y el paquete `tictactoe`.
- No accede a la red ni a archivos, ni ejecuta otros programas.
- Las comprobaciones automáticas del pull request están en verde.

## Otras contribuciones

Para cualquier otro cambio (el juego, la web, la documentación…), abre primero
una *issue* explicando la propuesta. Todo cambio llega a `main` mediante un pull
request que necesita una revisión aprobatoria y las comprobaciones en verde.
