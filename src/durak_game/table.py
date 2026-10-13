"""Cards in play during the current round."""

from __future__ import annotations

from durak_bot.bot import Card


class Table:
    """Attacking cards and the cards covering them during one round.

    The table only stores cards. Whether a card may be played is decided by
    ``DurakEngine``.
    """

    def __init__(self) -> None:
        """Create an empty table."""
        self._pairs: list[tuple[Card, Card | None]] = []

    def __len__(self) -> int:
        """Number of attacking cards on the table, covered or not."""
        return len(self._pairs)

    @property
    def pairs(self) -> tuple[tuple[Card, Card | None], ...]:
        """(attacking card, covering card or None) pairs, as in ``GameState.table``."""
        return tuple(self._pairs)

    @property
    def undefended(self) -> tuple[Card, ...]:
        """Attacking cards that are not covered yet, in the order they were played."""
        return tuple(attack for attack, defence in self._pairs if defence is None)

    @property
    def card_count(self) -> int:
        """Total number of cards on the table (attacking and covering)."""
        return sum(1 if defence is None else 2 for _, defence in self._pairs)

    def ranks(self, include_defence: bool) -> set[str]:
        """Ranks on the table: of attacking cards, plus covering cards if *include_defence*."""
        ranks: set[str] = {attack.rank for attack, _ in self._pairs}
        if include_defence:
            ranks |= {defence.rank for _, defence in self._pairs if defence is not None}
        return ranks

    def add_attack(self, card: Card) -> None:
        """Put an attacking card on the table."""
        self._pairs.append((card, None))

    def cover(self, attack: Card, defence: Card) -> None:
        """Put *defence* on top of the uncovered attacking card *attack*.

        Raises:
            ValueError: If *attack* is not an uncovered card on the table.
        """
        for index, (card, cover) in enumerate(self._pairs):
            if card == attack and cover is None:
                self._pairs[index] = (card, defence)
                return
        raise ValueError(f"{attack} is not an uncovered card on the table.")

    def clear(self) -> list[Card]:
        """Remove every card from the table and return them."""
        cards: list[Card] = []
        for attack, defence in self._pairs:
            cards.append(attack)
            if defence is not None:
                cards.append(defence)
        self._pairs.clear()
        return cards
