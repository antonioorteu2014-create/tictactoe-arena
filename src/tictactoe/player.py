"""El API de jugadores: lo único que hay que implementar para escribir un bot.

Todo lo demás del proyecto (el ejecutor de partidas, el torneo, la web y los bots
que nos envíen otros equipos) depende de esta interfaz, así que es deliberadamente
pequeña. Un jugador hace dos cosas:

**Dice quién es.** [`get_name()`][tictactoe.player.Player.get_name],
[`get_authors()`][tictactoe.player.Player.get_authors] y
[`get_description()`][tictactoe.player.Player.get_description] son métodos de
clase, para que la clasificación, la documentación y la web lean la identidad de
un bot **sin construirlo**. Son abstractos: Python se niega a crear un bot que no
los haya implementado. [`get_icon()`][tictactoe.player.Player.get_icon] es
opcional y tiene un valor por defecto.

**Elige un movimiento.** [`choose_move()`][tictactoe.player.Player.choose_move]
recibe la posición y devuelve la casilla (0-8) donde quiere jugar. Es el único
método de juego obligatorio: cada método más que exigiéramos sería una forma más
de que un bot llegue roto.

Decisiones de diseño:

* **El jugador ve el estado completo.** El tres en raya no tiene información
  oculta, así que no hace falta construir una «vista» distinta para cada jugador.
* **El jugador no puede modificar el estado.** El estado es un ``str``, que en
  Python es inmutable: un bot no puede alterar el tablero de la partida, ni
  siquiera por error. Por eso no hace falta entregarle una copia.
* **El jugador no sabe con qué ficha juega hasta que mira el tablero.** Lo deduce
  con [`current_player()`][tictactoe.game.current_player]: el mismo bot puede
  jugar con X o con O sin que el ejecutor tenga que decírselo.
* **Se construye solo con** [`create()`][tictactoe.player.Player.create], que
  recibe una semilla. Un bot con azar la usa para que dos partidas con la misma
  semilla sean idénticas, lo que permite repetir exactamente una partida que
  falló. Un bot sin azar la ignora.
* **Los tiempos, el rival y el historial no son cosa del jugador.** Eso lo controla
  quien ejecuta la partida ([`tictactoe.match`][tictactoe.match]), no esta interfaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .game import Move, State


class Player(ABC):
    """Un jugador de tres en raya.

    Para escribir un bot, crea una subclase que implemente los tres métodos de
    identidad y [`choose_move()`][tictactoe.player.Player.choose_move]:

        from tictactoe import game
        from tictactoe.player import Player

        class PrimeraLibre(Player):
            @classmethod
            def get_name(cls) -> str:
                return "primera-libre"

            @classmethod
            def get_authors(cls) -> list[str]:
                return ["Tu Nombre"]

            @classmethod
            def get_description(cls) -> str:
                return "Juega siempre en la primera casilla libre."

            def choose_move(self, state: game.State) -> game.Move:
                return game.legal_moves(state)[0]
    """

    # ----------------------------------------------------------------- #
    # Identidad: se lee sin construir el jugador                        #
    # ----------------------------------------------------------------- #

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Devolver el nombre del jugador, único entre todos los admitidos.

        Es el que aparece en la clasificación, en la web y en la documentación.
        Corto y sin espacios, por ejemplo ``"aleatorio"`` o ``"minimax"``.
        """

    @classmethod
    @abstractmethod
    def get_authors(cls) -> list[str]:
        """Devolver los autores del jugador: una lista con al menos un nombre."""

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Devolver una o dos frases que expliquen **cómo decide** el jugador.

        Describe la estrategia, no la implementación: es lo que se muestra junto
        al nombre en la clasificación.
        """

    @classmethod
    def get_icon(cls) -> str:
        """Devolver un emoji que acompaña al nombre en la web y la clasificación.

        Es opcional: por defecto, ``"🤖"``. Un solo símbolo.
        """
        return "🤖"

    # ----------------------------------------------------------------- #
    # Construcción: la única forma en que el proyecto crea un jugador   #
    # ----------------------------------------------------------------- #

    @classmethod
    def create(cls, seed: int) -> Player:
        """Construir una instancia del jugador para una partida.

        La implementación por defecto ignora ``seed`` y llama a ``cls()``.
        Sobrescríbela si tu jugador usa azar (para sembrar su generador) o si su
        constructor necesita argumentos.

        Args:
            seed: semilla reproducible para esta partida. Nunca es ``None``.

        Returns:
            Un jugador listo para jugar.
        """
        return cls()

    # ----------------------------------------------------------------- #
    # Juego                                                             #
    # ----------------------------------------------------------------- #

    @abstractmethod
    def choose_move(self, state: State) -> Move:
        """Elegir un movimiento en la posición ``state``.

        Solo se llama cuando la partida no ha terminado y le toca a este jugador.
        Su ficha (``"X"`` u ``"O"``) es la que indica
        [`tictactoe.game.current_player()`][tictactoe.game.current_player].

        Args:
            state: la posición actual (ver [`tictactoe.game`][tictactoe.game]).

        Returns:
            La casilla, del 0 al 8, donde colocar la ficha. Debe ser un
            movimiento **legal**: un movimiento ilegal, devolver otra cosa o lanzar
            una excepción hace que el jugador **pierda la partida**.
        """

    def __repr__(self) -> str:  # pragma: no cover - solo cosmético
        return f"<{type(self).__name__} {self.get_name()!r}>"
