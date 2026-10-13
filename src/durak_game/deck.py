"""The draw pile."""

from __future__ import annotations

import random
from collections.abc import Iterable

from durak_bot.bot import RANKS, SUITS, Card


def full_deck() -> list[Card]:
    """Return all 36 cards (6 to Ace in every suit), not shuffled."""
    return [Card(rank, suit) for suit in SUITS for rank in RANKS]


class Deck:
    """Face-down draw pile whose bottom card is turned face up to show the trump.

    The face-up card is drawn last, so the trump suit stays known after the
    pile is empty.
    """

    def __init__(self, cards_in_draw_order: Iterable[Card]) -> None:
        """Create a pile from cards listed in the order they will be drawn.

        The last card in the list is the face-up trump card.

        Raises:
            ValueError: If there are no cards or a card appears twice.
        """
        cards: list[Card] = list(cards_in_draw_order)
        if not cards:
            raise ValueError("A deck needs at least one card.")
        if len(set(cards)) != len(cards):
            raise ValueError("A deck cannot contain the same card twice.")
        self._trump_card: Card = cards[-1]
        self._pile: list[Card] = cards[::-1]  # the next card to draw is at the end

    @classmethod
    def shuffled(cls, rng: random.Random | None = None) -> Deck:
        """Return a shuffled 36-card deck; pass a seeded ``rng`` to repeat a deal."""
        cards: list[Card] = full_deck()
        (rng if rng is not None else random.Random()).shuffle(cards)
        return cls(cards)

    @property
    def trump_card(self) -> Card:
        """The face-up bottom card (it is drawn last)."""
        return self._trump_card

    @property
    def trump_suit(self) -> str:
        """Suit of the trump card."""
        return self._trump_card.suit

    def __len__(self) -> int:
        """Number of cards left to draw."""
        return len(self._pile)

    def draw(self) -> Card:
        """Remove and return the top card.

        Raises:
            IndexError: If the pile is empty.
        """
        if not self._pile:
            raise IndexError("Cannot draw from an empty deck.")
        return self._pile.pop()
