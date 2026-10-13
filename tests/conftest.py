"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path

from durak_bot.bot import Card
from durak_game.cards import parse_cards
from durak_game.deck import Deck
from durak_game.engine import DurakEngine

BOTS_DIR: Path = Path(__file__).resolve().parents[1] / "bots"


def make_deck(hand0: str, hand1: str, rest: str) -> Deck:
    """Deck where player 0 gets *hand0*, player 1 gets *hand1*; last card of *rest* is trump."""
    return Deck(parse_cards(hand0) + parse_cards(hand1) + parse_cards(rest))


def total_cards(engine: DurakEngine) -> int:
    """Count every card in the game: hands + deck + table + discard."""
    in_hands = len(engine.hand(0)) + len(engine.hand(1))
    return in_hands + engine.deck_size + engine.table_card_count + engine.discard_size


def c(text: str) -> Card:
    """Short way to write one card in tests, e.g. c("10♥")."""
    (card,) = parse_cards(text)
    return card
