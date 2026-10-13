"""Rule variants for the game."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    """Settings that differ between the course tournament engine and classic Durak.

    Attributes:
        max_attack_cards: Most attacking cards allowed in one round.
        first_attack_same_rank: If True, the opening cards of a round must all
            have the same rank. If False, any cards may open the round.
        add_defence_ranks: If True, the attacker may add cards matching the rank
            of any card on the table. If False, only ranks of attacking cards count.
        limit_to_defender_hand: If True, there can never be more uncovered cards
            on the table than cards in the defender's hand.
    """

    max_attack_cards: int = 6
    first_attack_same_rank: bool = False
    add_defence_ranks: bool = False
    limit_to_defender_hand: bool = False

    @classmethod
    def course(cls) -> Rules:
        """Rules of the course engine (``durak_bot/game.py``).

        With these rules every tournament bot behaves here exactly as in the tournament.
        """
        return cls()

    @classmethod
    def classic(cls) -> Rules:
        """Classic two-player podkidnoy Durak."""
        return cls(
            first_attack_same_rank=True,
            add_defence_ranks=True,
            limit_to_defender_hand=True,
        )
