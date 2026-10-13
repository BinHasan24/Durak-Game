"""Tests for Match: whole games, course bots, broken bots, human retries."""

from __future__ import annotations

import pytest
from conftest import BOTS_DIR, c, make_deck

from durak_bot.bot import AttackMove, DurakBot, GameState, Move, PassMove, TakeMove
from durak_game.match import Match
from durak_game.players import HumanPlayer, load_bot
from durak_game.rules import Rules


class CrashingBot(DurakBot):
    """Raises an exception on every move."""

    def get_name(self) -> str:
        return "Crasher"

    def make_move(self, state: GameState) -> Move:
        raise RuntimeError("boom")


class CheatingBot(DurakBot):
    """Always plays the ace of spades, whether it has it or not."""

    def get_name(self) -> str:
        return "Cheater"

    def make_move(self, state: GameState) -> Move:
        return AttackMove(cards=(c("A♠"),))


class ScriptedHuman(HumanPlayer):
    """A 'person' who first tries to pass at the opening, then plays the first card."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.tried_pass = False

    def get_name(self) -> str:
        return "Human"

    def make_move(self, state: GameState) -> Move:
        if not self.tried_pass:
            self.tried_pass = True
            return PassMove()
        if state.is_attacking:
            return AttackMove(cards=(state.hand[0],)) if not state.table else PassMove()
        return TakeMove()

    def show_error(self, message: str) -> None:
        self.errors.append(message)


@pytest.mark.parametrize("rules", [Rules.course(), Rules.classic()])
def test_course_bots_play_full_games(rules: Rules) -> None:
    """External bot files from the course load and finish 100 games each way."""
    for seed in range(100):
        bots = (load_bot(BOTS_DIR / "random_bot.py"), load_bot(BOTS_DIR / "aggressive_bot.py"))
        match = Match(bots, rules=rules, seed=seed)
        winner = match.play()
        assert match.engine.is_over
        assert winner in (0, 1, None)


@pytest.mark.parametrize("bad_bot", [CrashingBot(), CheatingBot()])
def test_broken_bots_get_default_moves(bad_bot: DurakBot) -> None:
    good_bot = load_bot(BOTS_DIR / "aggressive_bot.py")
    for seed in range(20):
        assert Match((bad_bot, good_bot), seed=seed).play() in (0, 1, None)


def test_human_is_asked_again_after_illegal_move() -> None:
    human = ScriptedHuman()
    deck = make_deck("6♠ 7♣ 8♦ 9♠ 10♣ J♦", "7♠ 8♣ 9♦ 10♠ J♣ Q♦", "6♣ 6♦ Q♠ K♠ A♠ 6♥")
    match = Match((human, load_bot(BOTS_DIR / "aggressive_bot.py")), deck=deck)
    match.play()
    assert human.errors and "open the round" in human.errors[0]
