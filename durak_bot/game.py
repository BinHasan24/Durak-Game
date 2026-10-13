"""Durak game engine.

Implements standard podkidnoy (подкидной) Durak for 2 players with a 36-card deck.

Rules summary:
- 36-card deck: ranks 6–Ace in four suits.
- Each player starts with 6 cards; the bottom card of the deck determines trump.
- Attacker plays card(s); defender must beat each card (higher same-suit or trump)
  or take all cards from the table.
- After all cards are beaten, the attacker may add more cards whose rank matches
  any rank already on the table (max 6 attacking cards per round).
- If the defender takes, the attacker draws first; otherwise, the defender draws first.
  Both draw up to 6 cards.
- The first player to empty their hand (once the deck is gone) wins.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from durak_bot.bot import (
    RANKS,
    SUITS,
    AttackMove,
    Card,
    DefendMove,
    GameState,
    PassMove,
    TakeMove,
)

if TYPE_CHECKING:
    from durak_bot.bot import DurakBot, Move

MAX_TABLE_SIZE = 6


class DurakGame:
    """2-player podkidnoy Durak game engine.

    Parameters
    ----------
    bot1:
        First player bot (index 0).  Attacks first in round 1.
    bot2:
        Second player bot (index 1).
    seed:
        Optional RNG seed for reproducible shuffles.
    """

    def __init__(
        self,
        bot1: DurakBot,
        bot2: DurakBot,
        seed: int | None = None,
    ) -> None:
        self.bots: tuple[DurakBot, DurakBot] = (bot1, bot2)
        self._rng = random.Random(seed)
        self._hands: list[list[Card]] = [[], []]
        self._deck: list[Card] = []
        self._trump_suit: str = ""
        self._attacker: int = 0
        self._round_num: int = 0

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def play_game(self) -> int | None:
        """Play a full game to completion.

        Returns
        -------
        int | None
            Index of the winning bot (0 or 1), or ``None`` for a draw.
        """
        self._setup()

        while True:
            result = self._play_round()
            if result is not None:
                return result

    # ------------------------------------------------------------------ #
    #  Setup                                                              #
    # ------------------------------------------------------------------ #

    def _setup(self) -> None:
        deck = [Card(rank, suit) for rank in RANKS for suit in SUITS]
        self._rng.shuffle(deck)

        self._hands = [sorted(deck[:6]), sorted(deck[6:12])]
        self._deck = deck[12:]
        self._trump_suit = self._deck[0].suit if self._deck else SUITS[0]
        self._attacker = 0
        self._round_num = 0

        for idx, bot in enumerate(self.bots):
            bot.on_game_start(self._trump_suit, tuple(self._hands[idx]))

    # ------------------------------------------------------------------ #
    #  Round logic                                                        #
    # ------------------------------------------------------------------ #

    def _play_round(self) -> int | None:
        """Execute one round (attack + defence + draw).

        Returns the winner index if the game ends, otherwise ``None``.
        """
        winner = self._check_winner()
        if winner is not None:
            return winner

        self._round_num += 1
        for bot in self.bots:
            bot.on_round_start(self._round_num)

        attacker, defender = self._attacker, 1 - self._attacker
        table: list[tuple[Card, Card | None]] = []

        # --- Initial attack (attacker MUST play at least one card) ------
        state = self._build_state(attacker, table, is_attacking=True)
        move = self._safe_move(attacker, state)
        if isinstance(move, AttackMove) and self._validate_attack(attacker, table, move):
            self._apply_attack(attacker, table, move)
        else:
            # Fallback: auto-play the first card in hand.
            self._auto_attack(attacker, table)

        # --- Defence / add loop -----------------------------------------
        while True:
            # --- Defender's decision ------------------------------------
            state = self._build_state(defender, table, is_attacking=False)
            move = self._safe_move(defender, state)

            if isinstance(move, TakeMove):
                self._apply_take(defender, table)
                self._draw_after_round(attacker, defender)
                self._attacker = attacker  # Same attacker continues
                return self._check_winner()

            if isinstance(move, DefendMove):
                self._apply_defense(defender, table, move)
            else:
                # Unexpected move from defender → treat as Take.
                self._apply_take(defender, table)
                self._draw_after_round(attacker, defender)
                self._attacker = attacker
                return self._check_winner()

            # --- All beaten? -------------------------------------------
            if any(d is None for _, d in table):
                # Partial defence → defender takes remaining unbeaten cards.
                remaining = [a for a, d in table if d is None]
                self._hands[defender].extend(remaining)
                # Keep beaten cards on table for discard, then draw.
                self._draw_after_round(attacker, defender)
                self._attacker = 1 - attacker  # Defender becomes attacker
                return self._check_winner()

            # All beaten — can the attacker add more?
            if not self._can_add_cards(attacker, table):
                self._draw_after_round(attacker, defender)
                self._attacker = defender  # Defender becomes attacker
                return self._check_winner()

            # --- Attacker adds or passes --------------------------------
            state = self._build_state(attacker, table, is_attacking=True)
            move = self._safe_move(attacker, state)

            if isinstance(move, AttackMove) and self._validate_attack(
                attacker, table, move
            ):
                self._apply_attack(attacker, table, move)
                # Loop back → defender must beat the new cards.
                continue

            # Pass (or any other move treated as pass).
            break

        # Round ends normally: cards go to discard.
        self._draw_after_round(attacker, defender)
        self._attacker = defender  # Defender becomes attacker
        return self._check_winner()

    # ------------------------------------------------------------------ #
    #  Move application                                                   #
    # ------------------------------------------------------------------ #

    def _apply_attack(
        self,
        attacker: int,
        table: list[tuple[Card, Card | None]],
        move: AttackMove,
    ) -> None:
        """Remove cards from attacker's hand and place them on the table."""
        for card in move.cards:
            if card in self._hands[attacker]:
                self._hands[attacker].remove(card)
                table.append((card, None))

    def _apply_defense(
        self,
        defender: int,
        table: list[tuple[Card, Card | None]],
        move: DefendMove,
    ) -> None:
        """Apply defending beats to the table."""
        for atk_card, dfn_card in move.beats:
            for i, (a, d) in enumerate(table):
                if a == atk_card and d is None and dfn_card in self._hands[defender]:
                    if dfn_card.beats(atk_card, self._trump_suit):
                        table[i] = (a, dfn_card)
                        self._hands[defender].remove(dfn_card)
                        break

    def _apply_take(
        self,
        defender: int,
        table: list[tuple[Card, Card | None]],
    ) -> None:
        """Defender takes all cards (attacking and defending) from the table."""
        for atk, dfn in table:
            self._hands[defender].append(atk)
            if dfn is not None:
                self._hands[defender].append(dfn)
        table.clear()

    # ------------------------------------------------------------------ #
    #  Drawing                                                            #
    # ------------------------------------------------------------------ #

    def _draw_after_round(self, attacker: int, defender: int) -> None:
        """Both players draw up to 6 cards.  Attacker draws first."""
        for player in (attacker, defender):
            while len(self._hands[player]) < 6 and self._deck:
                self._hands[player].append(self._deck.pop(0))

    # ------------------------------------------------------------------ #
    #  Validation                                                         #
    # ------------------------------------------------------------------ #

    def _validate_attack(
        self,
        attacker: int,
        table: list[tuple[Card, Card | None]],
        move: AttackMove,
    ) -> bool:
        """Check that an AttackMove is legal."""
        if not move.cards:
            return False

        hand = self._hands[attacker]
        # All played cards must be in the attacker's hand.
        available = list(hand)
        for card in move.cards:
            if card in available:
                available.remove(card)
            else:
                return False

        # Total attacking cards on the table must not exceed MAX_TABLE_SIZE.
        attacking_count = len(table) + len(move.cards)
        if attacking_count > MAX_TABLE_SIZE:
            return False

        # If the table already has cards, ranks must match.
        if table:
            ranks_on_table = {card.rank for card, _ in table}
            if not all(c.rank in ranks_on_table for c in move.cards):
                return False

        return True

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _can_add_cards(
        self, attacker: int, table: list[tuple[Card, Card | None]]
    ) -> bool:
        """Check whether the attacker can legally add more cards."""
        if len(table) >= MAX_TABLE_SIZE:
            return False
        if not self._hands[attacker]:
            return False
        ranks_on_table = {card.rank for card, _ in table}
        return any(c.rank in ranks_on_table for c in self._hands[attacker])

    def _check_winner(self) -> int | None:
        """Return the winner index, or ``None`` if the game is still ongoing."""
        if self._deck:
            return None
        empty = [i for i in (0, 1) if not self._hands[i]]
        if len(empty) == 1:
            return empty[0]
        return None  # Both still have cards, or both empty (draw).

    def _build_state(
        self,
        player: int,
        table: list[tuple[Card, Card | None]],
        is_attacking: bool,
    ) -> GameState:
        """Construct a read-only GameState snapshot for *player*."""
        return GameState(
            hand=tuple(sorted(self._hands[player])),
            table=tuple(table),
            trump_suit=self._trump_suit,
            deck_size=len(self._deck),
            opponent_card_count=len(self._hands[1 - player]),
            is_attacking=is_attacking,
            round_number=self._round_num,
        )

    def _auto_attack(self, attacker: int, table: list[tuple[Card, Card | None]]) -> None:
        """Fallback: play the attacker's lowest card."""
        if self._hands[attacker]:
            card = min(self._hands[attacker])
            self._hands[attacker].remove(card)
            table.append((card, None))

    def _safe_move(self, player: int, state: GameState) -> Move:
        """Get a move from a bot, catching any exceptions."""
        try:
            return self.bots[player].make_move(state)
        except Exception:
            # On error, return a conservative default.
            if state.is_attacking:
                if state.hand:
                    return AttackMove(cards=(state.hand[0],))
                return PassMove()
            return TakeMove()
