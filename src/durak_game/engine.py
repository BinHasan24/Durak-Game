"""Durak game engine.

``DurakEngine`` holds the whole game and changes it one move at a time. The
player whose turn it is sends a move (``AttackMove``, ``DefendMove``,
``PassMove`` or ``TakeMove`` from the course module ``durak_bot``); the engine
checks it against the rules and applies it.

The engine never asks anybody for a move and never prints anything. Asking
players is the job of ``Match`` (text mode) or, later, the GUI.
"""

from __future__ import annotations

import logging
import random
from enum import Enum, auto

from durak_bot.bot import (
    RANK_VALUES,
    AttackMove,
    Card,
    DefendMove,
    GameState,
    Move,
    PassMove,
    TakeMove,
)
from durak_game.cards import cards_to_text, describe_move
from durak_game.deck import Deck
from durak_game.rules import Rules
from durak_game.table import Table

logger: logging.Logger = logging.getLogger(__name__)

HAND_SIZE: int = 6
PLAYERS: tuple[int, int] = (0, 1)


class Phase(Enum):
    """What the engine is waiting for."""

    ATTACK = auto()
    """The attacker must open the round with one or more cards."""
    DEFEND = auto()
    """The defender must cover every uncovered card at once, or take."""
    ADD = auto()
    """Everything is covered; the attacker may add more cards or pass."""
    GAME_OVER = auto()
    """No more moves."""


class IllegalMoveError(ValueError):
    """A move breaks the rules. The message says why."""


class DurakEngine:
    """Two-player Durak, one move at a time. Players are numbered 0 and 1.

    Typical use::

        engine = DurakEngine(seed=42)
        while not engine.is_over:
            player = engine.current_player
            state = engine.state_for(player)   # what that player may see
            move = ...                         # from a bot or a human
            engine.apply(move)                 # IllegalMoveError if not allowed
        print(engine.winner)
    """

    def __init__(
        self,
        rules: Rules | None = None,
        seed: int | None = None,
        deck: Deck | None = None,
    ) -> None:
        """Shuffle, deal 6 cards to each player and choose the first attacker.

        Args:
            rules: Rule variant. Default: the course tournament rules.
            seed: Shuffle seed, so the same seed gives the same deal.
                Ignored when *deck* is given.
            deck: A ready deck (useful in tests). Needs at least 12 cards.

        Raises:
            ValueError: If the deck has fewer than 12 cards.
        """
        self.rules: Rules = rules if rules is not None else Rules.course()
        self._deck: Deck = deck if deck is not None else Deck.shuffled(random.Random(seed))
        if len(self._deck) < 2 * HAND_SIZE:
            raise ValueError(f"The deck needs at least {2 * HAND_SIZE} cards to deal.")
        self._hands: tuple[list[Card], list[Card]] = ([], [])
        for hand in self._hands:
            for _ in range(HAND_SIZE):
                hand.append(self._deck.draw())
        self._table: Table = Table()
        self._discard: list[Card] = []
        self._attacker: int = self._first_attacker()
        self._phase: Phase = Phase.ATTACK
        self._round_number: int = 1
        self._winner: int | None = None

    # ------------------------------------------------------------------ #
    #  What anybody can see                                               #
    # ------------------------------------------------------------------ #

    @property
    def phase(self) -> Phase:
        """What the engine is waiting for."""
        return self._phase

    @property
    def attacker(self) -> int:
        """Index of the attacking player in the current round."""
        return self._attacker

    @property
    def defender(self) -> int:
        """Index of the defending player in the current round."""
        return 1 - self._attacker

    @property
    def current_player(self) -> int:
        """Index of the player who must move now.

        Raises:
            RuntimeError: If the game is over.
        """
        if self._phase is Phase.GAME_OVER:
            raise RuntimeError("The game is over; nobody moves.")
        return self.defender if self._phase is Phase.DEFEND else self._attacker

    @property
    def round_number(self) -> int:
        """Current round, starting from 1."""
        return self._round_number

    @property
    def trump_card(self) -> Card:
        """The face-up card under the deck."""
        return self._deck.trump_card

    @property
    def trump_suit(self) -> str:
        """The trump suit."""
        return self._deck.trump_suit

    @property
    def deck_size(self) -> int:
        """Cards left in the draw pile."""
        return len(self._deck)

    @property
    def discard_size(self) -> int:
        """Cards removed from the game (successfully defended rounds)."""
        return len(self._discard)

    @property
    def table(self) -> tuple[tuple[Card, Card | None], ...]:
        """(attacking card, covering card or None) pairs on the table."""
        return self._table.pairs

    @property
    def table_card_count(self) -> int:
        """Total number of cards on the table."""
        return self._table.card_count

    @property
    def is_over(self) -> bool:
        """True when the game has ended."""
        return self._phase is Phase.GAME_OVER

    @property
    def winner(self) -> int | None:
        """Index of the winner, or None while playing or after a draw."""
        return self._winner

    def hand(self, player: int) -> tuple[Card, ...]:
        """Cards of *player*, sorted by rank (the GUI must only show your own hand)."""
        self._check_player(player)
        return tuple(sorted(self._hands[player]))

    def state_for(self, player: int) -> GameState:
        """Everything *player* is allowed to see, in the course's ``GameState`` format."""
        self._check_player(player)
        return GameState(
            hand=self.hand(player),
            table=self._table.pairs,
            trump_suit=self.trump_suit,
            deck_size=len(self._deck),
            opponent_card_count=len(self._hands[1 - player]),
            is_attacking=player == self._attacker,
            round_number=self._round_number,
        )

    # ------------------------------------------------------------------ #
    #  Moves                                                              #
    # ------------------------------------------------------------------ #

    def is_legal(self, move: Move) -> bool:
        """Return True if *move* is allowed right now."""
        try:
            self.validate(move)
        except IllegalMoveError:
            return False
        return True

    def validate(self, move: Move) -> None:
        """Do nothing if *move* is allowed right now.

        Raises:
            IllegalMoveError: If it is not allowed; the message says why.
        """
        if self._phase is Phase.GAME_OVER:
            raise IllegalMoveError("The game is over.")
        match move:
            case AttackMove():
                if self._phase is Phase.DEFEND:
                    raise IllegalMoveError("It is the defender's turn.")
                self._check_attack(move.cards)
            case DefendMove():
                if self._phase is not Phase.DEFEND:
                    raise IllegalMoveError("There is nothing to cover.")
                self._check_defence(move.beats)
            case PassMove():
                if self._phase is Phase.ATTACK:
                    raise IllegalMoveError("You must open the round with at least one card.")
                if self._phase is Phase.DEFEND:
                    raise IllegalMoveError(
                        "The defender cannot pass: cover the cards or take them."
                    )
            case TakeMove():
                if self._phase is not Phase.DEFEND:
                    raise IllegalMoveError("Only the defender can take, while cards are uncovered.")
            case _:
                raise IllegalMoveError(f"Not a move: {move!r}")

    def apply(self, move: Move) -> None:
        """Check *move* and carry it out.

        Raises:
            IllegalMoveError: If the move is not allowed (nothing changes then).
        """
        self.validate(move)
        logger.debug(
            "Round %d: player %d %s",
            self._round_number,
            self.current_player,
            describe_move(move),
        )
        match move:
            case AttackMove():
                attacker_hand: list[Card] = self._hands[self._attacker]
                for card in move.cards:
                    attacker_hand.remove(card)
                    self._table.add_attack(card)
                self._phase = Phase.DEFEND
            case DefendMove():
                defender_hand: list[Card] = self._hands[self.defender]
                for attack, defence in move.beats:
                    defender_hand.remove(defence)
                    self._table.cover(attack, defence)
                if self._attacker_can_add():
                    self._phase = Phase.ADD
                else:
                    self._end_round(taken=False)
            case PassMove():
                self._end_round(taken=False)
            case TakeMove():
                self._end_round(taken=True)

    # ------------------------------------------------------------------ #
    #  Rule checks                                                        #
    # ------------------------------------------------------------------ #

    def _check_attack(self, cards: tuple[Card, ...]) -> None:
        """Raise IllegalMoveError unless the attacker may play *cards* now."""
        if not cards:
            raise IllegalMoveError("Play at least one card.")
        hand: list[Card] = self._hands[self._attacker]
        for card in cards:
            if card not in hand:
                raise IllegalMoveError(f"{card} is not in the attacker's hand.")
        if len(set(cards)) != len(cards):
            raise IllegalMoveError("The same card is played twice.")
        limit: int = self.rules.max_attack_cards
        if len(self._table) + len(cards) > limit:
            raise IllegalMoveError(f"At most {limit} attacking cards per round.")
        if self._phase is Phase.ATTACK:
            if self.rules.first_attack_same_rank and len({card.rank for card in cards}) > 1:
                raise IllegalMoveError("Opening cards must all have the same rank.")
        else:
            allowed: set[str] = self._table.ranks(include_defence=self.rules.add_defence_ranks)
            for card in cards:
                if card.rank not in allowed:
                    raise IllegalMoveError(f"{card} cannot be added: its rank is not on the table.")
        if self.rules.limit_to_defender_hand:
            uncovered_count: int = len(self._table.undefended) + len(cards)
            if uncovered_count > len(self._hands[self.defender]):
                raise IllegalMoveError("The defender does not have that many cards.")

    def _check_defence(self, beats: tuple[tuple[Card, Card], ...]) -> None:
        """Raise IllegalMoveError unless *beats* covers every uncovered card legally."""
        uncovered: tuple[Card, ...] = self._table.undefended
        covered: list[Card] = [attack for attack, _ in beats]
        used: list[Card] = [defence for _, defence in beats]
        if len(set(covered)) != len(covered) or set(covered) != set(uncovered):
            raise IllegalMoveError(
                f"Cover every uncovered card exactly once ({cards_to_text(uncovered)}), or take."
            )
        if len(set(used)) != len(used):
            raise IllegalMoveError("The same card is used twice.")
        hand: list[Card] = self._hands[self.defender]
        for attack, defence in beats:
            if defence not in hand:
                raise IllegalMoveError(f"{defence} is not in the defender's hand.")
            if not defence.beats(attack, self.trump_suit):
                raise IllegalMoveError(f"{defence} does not beat {attack}.")

    def _attacker_can_add(self) -> bool:
        """True if, after a full defence, the attacker has at least one card to add."""
        if len(self._table) >= self.rules.max_attack_cards:
            return False
        if self.rules.limit_to_defender_hand and not self._hands[self.defender]:
            return False
        allowed: set[str] = self._table.ranks(include_defence=self.rules.add_defence_ranks)
        return any(card.rank in allowed for card in self._hands[self._attacker])

    # ------------------------------------------------------------------ #
    #  Round flow                                                         #
    # ------------------------------------------------------------------ #

    def _first_attacker(self) -> int:
        """The player holding the lowest trump attacks first; player 0 if nobody has one."""
        lowest: tuple[int, int] | None = None  # (rank value, player)
        for player in PLAYERS:
            for card in self._hands[player]:
                if card.suit == self.trump_suit:
                    candidate: tuple[int, int] = (RANK_VALUES[card.rank], player)
                    if lowest is None or candidate < lowest:
                        lowest = candidate
        return 0 if lowest is None else lowest[1]

    def _end_round(self, taken: bool) -> None:
        """Clear the table, refill hands, pick the next attacker, check for game over.

        Args:
            taken: True if the defender took the cards (then the same player
                attacks again); False if the defence succeeded (cards are
                discarded and the defender attacks next).
        """
        attacker: int = self._attacker
        defender: int = self.defender
        cards: list[Card] = self._table.clear()
        if taken:
            self._hands[defender].extend(cards)
        else:
            self._discard.extend(cards)
            self._attacker = defender
        self._refill(attacker)  # the attacker of the finished round draws first
        self._refill(defender)
        if self._check_game_over():
            return
        self._round_number += 1
        self._phase = Phase.ATTACK

    def _refill(self, player: int) -> None:
        """Draw cards for *player* until they hold 6 or the deck is empty."""
        hand: list[Card] = self._hands[player]
        while len(hand) < HAND_SIZE and len(self._deck) > 0:
            hand.append(self._deck.draw())

    def _check_game_over(self) -> bool:
        """End the game if the deck is empty and someone has no cards; return True if it ended."""
        if len(self._deck) > 0:
            return False
        empty: list[int] = [player for player in PLAYERS if not self._hands[player]]
        if not empty:
            return False
        self._phase = Phase.GAME_OVER
        self._winner = empty[0] if len(empty) == 1 else None
        logger.debug("Game over after %d rounds, winner: %s", self._round_number, self._winner)
        return True

    @staticmethod
    def _check_player(player: int) -> None:
        """Raise ValueError unless *player* is 0 or 1."""
        if player not in PLAYERS:
            raise ValueError(f"Player must be 0 or 1, got {player!r}.")
