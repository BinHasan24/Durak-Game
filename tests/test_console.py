"""Tests for the text interface (typed input -> moves)."""

from __future__ import annotations

from conftest import c

from durak_bot.bot import AttackMove, DefendMove, GameState, PassMove, TakeMove
from durak_game.console import ConsolePlayer, parse_move

HAND = (c("6♠"), c("7♥"), c("9♠"))


def state(attacking: bool, table: tuple = ()) -> GameState:
    return GameState(
        hand=HAND,
        table=table,
        trump_suit="♥",
        deck_size=10,
        opponent_card_count=6,
        is_attacking=attacking,
        round_number=1,
    )


def test_attack_with_numbers() -> None:
    assert parse_move("1 3", state(True)) == AttackMove(cards=(c("6♠"), c("9♠")))


def test_pass_only_after_cards_are_on_table() -> None:
    assert parse_move("p", state(True)) is None
    assert parse_move("p", state(True, ((c("8♠"), c("9♠")),))) == PassMove()


def test_defend_and_take() -> None:
    defending = state(False, ((c("8♠"), None),))
    assert parse_move("3", defending) == DefendMove(beats=((c("8♠"), c("9♠")),))
    assert parse_move("t", defending) == TakeMove()
    assert parse_move("1 2", defending) is None  # two cards for one uncovered card


def test_bad_input_is_rejected() -> None:
    for text in ["", "abc", "0", "4", "1 x"]:
        assert parse_move(text, state(True)) is None


def test_console_player_asks_until_input_is_valid() -> None:
    typed = iter(["hello", "2"])
    printed: list[str] = []
    player = ConsolePlayer(read=lambda prompt: next(typed), write=printed.append)
    assert player.make_move(state(True)) == AttackMove(cards=(c("7♥"),))
    assert any("Type card numbers" in line for line in printed)
