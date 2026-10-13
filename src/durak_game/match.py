"""Plays a whole game between two players, without any GUI."""

from __future__ import annotations

import logging
from collections.abc import Callable

from durak_bot.bot import AttackMove, Card, DurakBot, GameState, Move, PassMove, TakeMove
from durak_game.cards import describe_move, weakest_card
from durak_game.deck import Deck
from durak_game.engine import DurakEngine, IllegalMoveError, Phase
from durak_game.players import HumanPlayer
from durak_game.rules import Rules

logger: logging.Logger = logging.getLogger(__name__)


class Match:
    """One game between two ``DurakBot`` players, run on a ``DurakEngine``.

    The match asks whoever's turn it is for a move and gives it to the engine.
    It also calls the bots' optional hooks (``on_game_start``,
    ``on_round_start``, ``on_opponent_move``).

    If a bot crashes or sends an illegal move, it gets a safe default move
    instead: open with its weakest card, pass, or take (like the course engine).
    A ``HumanPlayer`` is shown the error and asked again.
    """

    def __init__(
        self,
        players: tuple[DurakBot, DurakBot],
        rules: Rules | None = None,
        seed: int | None = None,
        deck: Deck | None = None,
    ) -> None:
        """Create the engine for a new game; see ``DurakEngine`` for the arguments."""
        self.players: tuple[DurakBot, DurakBot] = players
        self.engine: DurakEngine = DurakEngine(rules=rules, seed=seed, deck=deck)
        self._names: tuple[str, str] = (players[0].get_name(), players[1].get_name())

    def name(self, player: int) -> str:
        """Display name of player 0 or 1."""
        return self._names[player]

    def play(self) -> int | None:
        """Play to the end. Return the winner's index (0 or 1), or None for a draw."""
        engine: DurakEngine = self.engine
        logger.info(
            "Trump card: %s. %s attacks first.", engine.trump_card, self.name(engine.attacker)
        )
        for index, player in enumerate(self.players):
            self._call_hook(index, player.on_game_start, engine.trump_suit, engine.hand(index))

        announced_round: int = 0
        while not engine.is_over:
            if engine.round_number != announced_round:
                announced_round = engine.round_number
                for index, player in enumerate(self.players):
                    self._call_hook(index, player.on_round_start, announced_round)

            mover: int = engine.current_player
            move: Move = self._next_move(mover)
            logger.info(
                "Round %d | %s %s", engine.round_number, self.name(mover), describe_move(move)
            )
            engine.apply(move)
            opponent: int = 1 - mover
            self._call_hook(opponent, self.players[opponent].on_opponent_move, move)

        if engine.winner is None:
            logger.info("Draw: both players ran out of cards at the same time.")
        else:
            logger.info(
                "%s wins; %s is the durak.",
                self.name(engine.winner),
                self.name(1 - engine.winner),
            )
        return engine.winner

    def _next_move(self, index: int) -> Move:
        """Ask player *index* for a legal move (or fall back to a default for bots)."""
        player: DurakBot = self.players[index]
        while True:
            state: GameState = self.engine.state_for(index)
            try:
                move: Move = player.make_move(state)
            except Exception:
                if isinstance(player, HumanPlayer):
                    raise
                logger.exception("%s crashed; playing a default move.", self.name(index))
                return self._default_move(index)
            try:
                self.engine.validate(move)
            except IllegalMoveError as error:
                if isinstance(player, HumanPlayer):
                    player.show_error(str(error))
                    continue
                reason: str = str(error)
            except Exception as error:  # a bot sent a broken object
                reason = f"broken move ({error!r})"
            else:
                return move
            logger.warning(
                "%s made an illegal move (%s); playing a default move.", self.name(index), reason
            )
            return self._default_move(index)

    def _default_move(self, index: int) -> Move:
        """A move that is always legal: open with the weakest card, pass, or take."""
        phase: Phase = self.engine.phase
        if phase is Phase.ATTACK:
            card: Card = weakest_card(self.engine.hand(index), self.engine.trump_suit)
            return AttackMove(cards=(card,))
        if phase is Phase.ADD:
            return PassMove()
        return TakeMove()

    def _call_hook(self, index: int, hook: Callable[..., None], *args: object) -> None:
        """Call ``hook(*args)`` for player *index*; a bot crashing there is logged, not fatal."""
        try:
            hook(*args)
        except Exception:
            if isinstance(self.players[index], HumanPlayer):
                raise
            logger.exception("%s crashed in a hook; ignoring.", self.name(index))
