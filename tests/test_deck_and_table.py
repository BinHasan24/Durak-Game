"""Tests for Deck and Table."""

from __future__ import annotations

import random

import pytest
from conftest import c

from durak_game.cards import card_power, parse_cards, weakest_card
from durak_game.deck import Deck, full_deck
from durak_game.table import Table


def test_full_deck_has_36_different_cards() -> None:
    cards = full_deck()
    assert len(cards) == 36
    assert len(set(cards)) == 36


def test_same_seed_gives_same_deal() -> None:
    first = Deck.shuffled(random.Random(7))
    second = Deck.shuffled(random.Random(7))
    assert [first.draw() for _ in range(36)] == [second.draw() for _ in range(36)]


def test_trump_card_is_drawn_last() -> None:
    deck = Deck(parse_cards("6♠ 7♠ 8♥"))
    assert deck.trump_card == c("8♥")
    assert [deck.draw() for _ in range(3)] == parse_cards("6♠ 7♠ 8♥")
    assert len(deck) == 0
    assert deck.trump_suit == "♥"  # still known after the deck is empty
    with pytest.raises(IndexError):
        deck.draw()


def test_deck_rejects_duplicates_and_empty_lists() -> None:
    with pytest.raises(ValueError):
        Deck(parse_cards("6♠ 6♠"))
    with pytest.raises(ValueError):
        Deck([])


def test_table_cover_and_ranks() -> None:
    table = Table()
    table.add_attack(c("7♠"))
    table.add_attack(c("7♦"))
    table.cover(c("7♠"), c("9♠"))
    assert table.undefended == (c("7♦"),)
    assert table.ranks(include_defence=False) == {"7"}
    assert table.ranks(include_defence=True) == {"7", "9"}
    assert table.card_count == 3
    with pytest.raises(ValueError):
        table.cover(c("7♠"), c("10♠"))  # already covered
    assert sorted(table.clear()) == sorted(parse_cards("7♠ 7♦ 9♠"))
    assert len(table) == 0


def test_weakest_card_prefers_non_trumps() -> None:
    hand = parse_cards("6♥ A♠ 9♣")
    assert weakest_card(hand, "♥") == c("9♣")
    assert card_power(c("A♠"), "♥") < card_power(c("6♥"), "♥")
