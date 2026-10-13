"""Example Durak bot: random strategy.

This bot picks a random legal move.  Use it as a baseline or for testing
the tournament runner.
"""

import random

from durak_bot.bot import (
    AttackMove,
    Card,
    DefendMove,
    DurakBot,
    GameState,
    PassMove,
    TakeMove,
    Move,
)


class RandomBot(DurakBot):
    """Picks a random legal move at each decision point."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._name = f"RandomBot({seed})"

    def get_name(self) -> str:
        return self._name

    def make_move(self, state: GameState) -> Move:
        if state.is_attacking:
            return self._attack_move(state)
        return self._defend_move(state)

    # ------------------------------------------------------------------ #

    def _attack_move(self, state: GameState) -> Move:
        hand = list(state.hand)
        if not hand:
            return PassMove()

        if state.table:
            # Can add cards whose rank matches the table.
            ranks_on_table = {a.rank for a, _ in state.table}
            matching = [c for c in hand if c.rank in ranks_on_table]
            room = 6 - len(state.table)

            if matching and room > 0:
                count = self._rng.randint(1, min(len(matching), room))
                chosen = self._rng.sample(matching, count)
                return AttackMove(cards=tuple(chosen))

            return PassMove()

        # First attack: play 1-3 random cards.
        count = self._rng.randint(1, min(3, len(hand)))
        chosen = self._rng.sample(hand, count)
        return AttackMove(cards=tuple(chosen))

    def _defend_move(self, state: GameState) -> Move:
        hand = list(state.hand)
        undefended = state.undefended_cards

        if not undefended:
            return TakeMove()

        beats: list[tuple[Card, Card]] = []
        remaining = list(hand)

        for atk_card in undefended:
            candidates = [
                c for c in remaining if c.beats(atk_card, state.trump_suit)
            ]
            if not candidates:
                # Cannot beat all → take.
                return TakeMove()
            chosen = self._rng.choice(candidates)
            beats.append((atk_card, chosen))
            remaining.remove(chosen)

        return DefendMove(beats=tuple(beats))
