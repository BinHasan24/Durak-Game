"""Bot interface, data types, and base class for Durak bots.

This module provides:
- Card: immutable playing card with rank and suit
- GameState: read-only snapshot of the game visible to a bot
- Move types: AttackMove, DefendMove, PassMove, TakeMove
- DurakBot: abstract base class that all competition bots must implement
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union

RANKS = ("6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS = ("♠", "♥", "♦", "♣")
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS)}


@dataclass(frozen=True, order=False)
class Card:
    """Immutable playing card.

    Attributes:
        rank: One of '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'.
        suit: One of '♠', '♥', '♦', '♣'.
    """

    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Invalid rank: {self.rank!r}. Must be one of {RANKS}")
        if self.suit not in SUITS:
            raise ValueError(f"Invalid suit: {self.suit!r}. Must be one of {SUITS}")

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return RANK_VALUES[self.rank] < RANK_VALUES[other.rank]

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return RANK_VALUES[self.rank] <= RANK_VALUES[other.rank]

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return RANK_VALUES[self.rank] > RANK_VALUES[other.rank]

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return RANK_VALUES[self.rank] >= RANK_VALUES[other.rank]

    def beats(self, other: Card, trump_suit: str) -> bool:
        """Check whether this card beats *other* under Durak rules.

        A card beats another if:
        - Same suit and higher rank, or
        - This card is trump and the other is not.
        """
        if self.suit == other.suit:
            return self > other
        return self.suit == trump_suit

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass(frozen=True)
class GameState:
    """Read-only snapshot of the game visible to a single player.

    Attributes:
        hand: Cards currently in the player's hand.
        table: Cards on the table as (attacking_card, defending_card | None).
            None means the card has not yet been beaten.
        trump_suit: The trump suit for this game ('♠', '♥', '♦', or '♣').
        deck_size: Number of cards remaining in the draw pile.
        opponent_card_count: Number of cards in the opponent's hand.
        is_attacking: True if the current player is the attacker.
        round_number: Current round number (starts at 1).
    """

    hand: tuple[Card, ...]
    table: tuple[tuple[Card, Card | None], ...]
    trump_suit: str
    deck_size: int
    opponent_card_count: int
    is_attacking: bool
    round_number: int

    @property
    def undefended_cards(self) -> tuple[Card, ...]:
        """Cards on the table that have not yet been beaten."""
        return tuple(atk for atk, dfn in self.table if dfn is None)

    @property
    def all_beaten(self) -> bool:
        """True if every card on the table has been beaten."""
        return len(self.table) > 0 and all(
            dfn is not None for _, dfn in self.table
        )


# --- Move types ---

@dataclass(frozen=True)
class AttackMove:
    """Attacker plays one or more cards.

    During the first attack of a round, card ranks are unrestricted.
    During subsequent attacks (adding cards), ranks must match a rank
    already present on the table.  The total number of cards on the table
    must not exceed 6.
    """
    cards: tuple[Card, ...]

    def __post_init__(self) -> None:
        if not self.cards:
            raise ValueError("AttackMove must contain at least one card")


@dataclass(frozen=True)
class DefendMove:
    """Defender beats one or more attacking cards.

    Each entry is a pair (attacking_card, defending_card).
    All undefended cards on the table must be covered (partial defense
    is not allowed — use TakeMove instead if you cannot beat everything).
    """
    beats: tuple[tuple[Card, Card], ...]

    def __post_init__(self) -> None:
        if not self.beats:
            raise ValueError("DefendMove must contain at least one beat")


@dataclass(frozen=True)
class PassMove:
    """Attacker chooses not to add more cards this round."""


@dataclass(frozen=True)
class TakeMove:
    """Defender takes all cards from the table."""


Move = Union[AttackMove, DefendMove, PassMove, TakeMove]


class DurakBot(ABC):
    """Abstract base class for Durak bots.

    Subclass this and implement at least `get_name` and `make_move`.
    Each method receives a `GameState` snapshot and must return a legal `Move`.

    Lifecycle hooks (optional to override):
        on_game_start  — called once before the first round.
        on_round_start — called at the start of each round.
        on_opponent_move — called after every opponent move (for tracking).
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return a human-readable name for this bot."""

    @abstractmethod
    def make_move(self, state: GameState) -> Move:
        """Choose a move given the current game state.

        When ``state.is_attacking`` is True, return an `AttackMove` or `PassMove`.
        When ``state.is_attacking`` is False, return a `DefendMove` or `TakeMove`.
        """

    def on_game_start(self, trump_suit: str, hand: tuple[Card, ...]) -> None:
        """Called once before the first round begins.

        Args:
            trump_suit: The trump suit for this game.
            hand: Your initial hand.
        """

    def on_round_start(self, round_number: int) -> None:
        """Called at the start of each round.

        Args:
            round_number: 1-based round counter.
        """

    def on_opponent_move(self, move: Move) -> None:
        """Called after the opponent makes a move.

        Use this to track opponent behaviour (card counting, etc.).
        """
