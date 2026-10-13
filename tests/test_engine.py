"""Tests for DurakEngine: the rules, step by step."""

from __future__ import annotations

import random

import pytest
from conftest import c, make_deck, total_cards

from durak_bot.bot import AttackMove, DefendMove, PassMove, TakeMove
from durak_game.engine import DurakEngine, IllegalMoveError, Phase
from durak_game.rules import Rules

# Trump is ♥ (last card of REST). Nobody holds a heart, so player 0 attacks first.
HAND0 = "6♠ 7♣ 8♦ 9♠ 10♣ J♦"
HAND1 = "7♠ 8♣ 9♦ 10♠ J♣ Q♦"
REST = "6♣ 6♦ Q♠ K♠ A♠ 6♥"
# Same, but player 0 holds two sixes (so after 6♠ is covered, 6♣ can be added).
HAND0_TWO_SIXES = "6♠ 6♣ 8♦ 9♠ 10♣ J♦"
REST_B = "7♦ 6♦ Q♠ K♠ A♠ 6♥"


def new_engine(rules: Rules | None = None) -> DurakEngine:
    return DurakEngine(rules=rules, deck=make_deck(HAND0, HAND1, REST))


def test_deal() -> None:
    engine = new_engine()
    assert engine.trump_suit == "♥"
    assert len(engine.hand(0)) == len(engine.hand(1)) == 6
    assert engine.deck_size == 6
    assert engine.attacker == 0
    assert engine.phase is Phase.ATTACK
    assert engine.current_player == 0


def test_lowest_trump_attacks_first() -> None:
    engine = DurakEngine(deck=make_deck("8♥ 6♠ 7♠ 8♠ 9♠ 10♠", "7♥ 6♣ 7♣ 8♣ 9♣ 10♣", "A♥"))
    assert engine.attacker == 1


def test_successful_defence_discards_and_swaps_roles() -> None:
    engine = new_engine()
    engine.apply(AttackMove(cards=(c("6♠"),)))
    assert engine.phase is Phase.DEFEND and engine.current_player == 1
    engine.apply(DefendMove(beats=((c("6♠"), c("7♠")),)))
    # Course rules: only attacking ranks (6) may be added; player 0 has no other 6,
    # so the round ends by itself.
    assert engine.phase is Phase.ATTACK
    assert engine.discard_size == 2
    assert engine.attacker == 1
    assert engine.round_number == 2
    assert len(engine.hand(0)) == len(engine.hand(1)) == 6
    assert c("6♣") in engine.hand(0)  # the old attacker drew first
    assert c("6♦") in engine.hand(1)


def test_classic_rules_allow_adding_defence_ranks() -> None:
    engine = new_engine(Rules.classic())
    engine.apply(AttackMove(cards=(c("6♠"),)))
    engine.apply(DefendMove(beats=((c("6♠"), c("7♠")),)))
    assert engine.phase is Phase.ADD  # player 0 may add 7♣ (rank of the covering card)
    engine.apply(AttackMove(cards=(c("7♣"),)))
    assert engine.phase is Phase.DEFEND


def test_take_keeps_the_same_attacker() -> None:
    engine = new_engine()
    engine.apply(AttackMove(cards=(c("6♠"),)))
    engine.apply(TakeMove())
    assert engine.attacker == 0
    assert engine.round_number == 2
    assert c("6♠") in engine.hand(1)
    assert len(engine.hand(1)) == 7
    assert len(engine.hand(0)) == 6  # refilled
    assert engine.discard_size == 0


def test_pass_ends_round() -> None:
    engine = DurakEngine(deck=make_deck(HAND0_TWO_SIXES, HAND1, REST_B))
    engine.apply(AttackMove(cards=(c("6♠"),)))
    engine.apply(DefendMove(beats=((c("6♠"), c("7♠")),)))
    assert engine.phase is Phase.ADD  # player 0 could add 6♣
    engine.apply(PassMove())
    assert engine.attacker == 1 and engine.phase is Phase.ATTACK


@pytest.mark.parametrize(
    ("move", "reason"),
    [
        (PassMove(), "open the round"),
        (TakeMove(), "Only the defender"),
        (AttackMove(cards=(c("A♠"),)), "not in the attacker's hand"),
        (AttackMove(cards=(c("6♠"), c("6♠"))), "twice"),
    ],
)
def test_illegal_opening_moves(move: AttackMove | PassMove | TakeMove, reason: str) -> None:
    engine = new_engine()
    with pytest.raises(IllegalMoveError, match=reason):
        engine.apply(move)
    assert engine.phase is Phase.ATTACK  # nothing changed


def test_illegal_defences() -> None:
    engine = new_engine()
    engine.apply(AttackMove(cards=(c("6♠"), c("8♦"))))
    with pytest.raises(IllegalMoveError, match="exactly once"):
        engine.apply(DefendMove(beats=((c("6♠"), c("7♠")),)))  # 8♦ left uncovered
    with pytest.raises(IllegalMoveError, match="does not beat"):
        engine.apply(DefendMove(beats=((c("6♠"), c("8♣")), (c("8♦"), c("9♦")))))
    with pytest.raises(IllegalMoveError, match="not in the defender's hand"):
        engine.apply(DefendMove(beats=((c("6♠"), c("A♠")), (c("8♦"), c("9♦")))))
    with pytest.raises(IllegalMoveError, match="defender's turn"):
        engine.apply(AttackMove(cards=(c("9♠"),)))
    assert engine.phase is Phase.DEFEND


def test_cannot_add_rank_not_on_table() -> None:
    engine = DurakEngine(deck=make_deck(HAND0_TWO_SIXES, HAND1, REST_B))
    engine.apply(AttackMove(cards=(c("6♠"),)))
    engine.apply(DefendMove(beats=((c("6♠"), c("7♠")),)))
    with pytest.raises(IllegalMoveError, match="rank is not on the table"):
        engine.apply(AttackMove(cards=(c("9♠"),)))


def test_opening_with_mixed_ranks_depends_on_rules() -> None:
    mixed = AttackMove(cards=(c("6♠"), c("8♦")))
    assert new_engine(Rules.course()).is_legal(mixed)
    assert not new_engine(Rules.classic()).is_legal(mixed)


def test_at_most_six_attacking_cards() -> None:
    engine = new_engine()
    assert engine.is_legal(AttackMove(cards=tuple(engine.hand(0))))
    assert not new_engine(Rules(max_attack_cards=3)).is_legal(
        AttackMove(cards=tuple(engine.hand(0)))
    )


def test_random_games_keep_all_cards_and_finish() -> None:
    """Play 300 games with random legal moves; check the rules never lose a card."""
    for seed in range(300):
        rng = random.Random(seed)
        engine = DurakEngine(seed=seed, rules=Rules.classic() if seed % 2 else Rules.course())
        moves = 0
        while not engine.is_over:
            engine.apply(random_legal_move(engine, rng))
            assert total_cards(engine) == 36
            moves += 1
            assert moves < 2000, "game does not end"
        assert engine.deck_size == 0
        if engine.winner is not None:
            assert engine.hand(engine.winner) == ()
            assert engine.hand(1 - engine.winner) != ()


def random_legal_move(
    engine: DurakEngine, rng: random.Random
) -> AttackMove | DefendMove | PassMove | TakeMove:
    """Pick a simple random legal move (test helper)."""
    hand = list(engine.hand(engine.current_player))
    if engine.phase is Phase.DEFEND:
        beats = []
        for attack in [a for a, d in engine.table if d is None]:
            options = [card for card in hand if card.beats(attack, engine.trump_suit)]
            if not options or rng.random() < 0.2:
                return TakeMove()
            choice = rng.choice(options)
            hand.remove(choice)
            beats.append((attack, choice))
        return DefendMove(beats=tuple(beats))
    if engine.phase is Phase.ADD:
        for card in rng.sample(hand, len(hand)):
            move = AttackMove(cards=(card,))
            if rng.random() < 0.7 and engine.is_legal(move):
                return move
        return PassMove()
    return AttackMove(cards=(rng.choice(hand),))
