"""Example Durak bot: aggressive strategy.

Always attacks with the lowest cards and defends whenever possible.
"""

from durak_bot.bot import (
    AttackMove,
    Card,
    DefendMove,
    DurakBot,
    GameState,
    Move,
    PassMove,
    TakeMove,
)


class AggressiveBot(DurakBot):
    """Attacks with the lowest cards. Defends whenever it can."""

    def get_name(self) -> str:
        return "AggressiveBot"

    def make_move(self, state: GameState) -> Move:
        if state.is_attacking:
            return self._attack(state)
        return self._defend(state)

    def _attack(self, state: GameState) -> Move:
        hand = list(state.hand)
        if not hand:
            return PassMove()

        if state.table:
            ranks_on_table = {a.rank for a, _ in state.table}
            matching = sorted(c for c in hand if c.rank in ranks_on_table)
            room = 6 - len(state.table)

            if matching and room > 0:
                return AttackMove(cards=tuple(matching[:room]))
            return PassMove()

        # Play up to 3 lowest cards.
        return AttackMove(cards=tuple(sorted(hand)[:3]))

    def _defend(self, state: GameState) -> Move:
        hand = sorted(state.hand)
        undefended = state.undefended_cards

        if not undefended:
            return TakeMove()

        beats: list[tuple[Card, Card]] = []
        remaining = list(hand)

        for atk_card in undefended:
            candidates = sorted(
                c for c in remaining if c.beats(atk_card, state.trump_suit)
            )
            if not candidates:
                return TakeMove()
            chosen = candidates[0]
            beats.append((atk_card, chosen))
            remaining.remove(chosen)

        return DefendMove(beats=tuple(beats))
