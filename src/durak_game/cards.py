"""Small helpers for comparing, reading and printing cards and moves."""

from __future__ import annotations

from collections.abc import Iterable

from durak_bot.bot import (
    RANK_VALUES,
    AttackMove,
    Card,
    DefendMove,
    Move,
    PassMove,
    TakeMove,
)


def card_power(card: Card, trump_suit: str) -> tuple[bool, int]:
    """Return a sort key: every non-trump is weaker than every trump, then by rank.

    Example with trump ♥: 6♠ < A♠ < 6♥ < A♥.
    """
    return (card.suit == trump_suit, RANK_VALUES[card.rank])


def weakest_card(cards: Iterable[Card], trump_suit: str) -> Card:
    """Return the cheapest card to give away: the lowest non-trump, else the lowest trump.

    Raises:
        ValueError: If *cards* is empty.
    """
    return min(cards, key=lambda card: card_power(card, trump_suit))


def parse_card(text: str) -> Card:
    """Turn text like ``"10♥"`` into a ``Card`` (rank first, suit symbol last).

    Raises:
        ValueError: If the rank or suit is not valid.
    """
    cleaned: str = text.strip()
    return Card(rank=cleaned[:-1], suit=cleaned[-1:])


def parse_cards(text: str) -> list[Card]:
    """Turn space-separated text like ``"6♠ 10♥"`` into a list of cards."""
    return [parse_card(word) for word in text.split()]


def cards_to_text(cards: Iterable[Card]) -> str:
    """Join cards with spaces, e.g. ``"6♠ 10♥"``."""
    return " ".join(str(card) for card in cards)


def describe_move(move: Move) -> str:
    """Return a short description of a move, e.g. ``"plays 7♠ 7♥"``."""
    match move:
        case AttackMove():
            return f"plays {cards_to_text(move.cards)}"
        case DefendMove():
            covers: str = ", ".join(f"{attack} with {defence}" for attack, defence in move.beats)
            return f"covers {covers}"
        case PassMove():
            return "passes"
        case TakeMove():
            return "takes the cards"
    return f"sends something that is not a move: {move!r}"
