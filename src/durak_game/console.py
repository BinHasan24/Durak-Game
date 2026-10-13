"""Text interface: a person plays by typing card numbers in the terminal."""

from __future__ import annotations

from collections.abc import Callable

from durak_bot.bot import (
    AttackMove,
    Card,
    DefendMove,
    GameState,
    Move,
    PassMove,
    TakeMove,
)
from durak_game.cards import cards_to_text, describe_move
from durak_game.players import HumanPlayer

HELP: str = (
    "Type card numbers separated by spaces (e.g. '1' or '2 3'). "
    "Defending: one number per uncovered card, in the order shown. "
    "'p' = pass (attacker, after everything is covered), 't' = take (defender)."
)


class ConsolePlayer(HumanPlayer):
    """Shows the game in the terminal and reads moves from the keyboard."""

    def __init__(
        self,
        name: str = "You",
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print,
    ) -> None:
        """Create the player.

        Args:
            name: Name shown in the game log.
            read: Function that shows a prompt and returns a typed line
                (``input`` by default; tests pass a fake).
            write: Function that prints a line (``print`` by default).
        """
        self._name: str = name
        self._read: Callable[[str], str] = read
        self._write: Callable[[str], None] = write

    def get_name(self) -> str:
        """Return the player's name."""
        return self._name

    def make_move(self, state: GameState) -> Move:
        """Show the situation and keep asking until the input can be read as a move."""
        self._show(state)
        while True:
            move: Move | None = parse_move(self._read(prompt_for(state)), state)
            if move is not None:
                return move
            self._write(HELP)

    def show_error(self, message: str) -> None:
        """Print why the last move was rejected."""
        self._write(f"Illegal move: {message}")

    def on_game_start(self, trump_suit: str, hand: tuple[Card, ...]) -> None:
        """Announce the trump suit."""
        self._write(f"New game. Trump suit: {trump_suit}")

    def on_round_start(self, round_number: int) -> None:
        """Print a round header."""
        self._write(f"\n=== Round {round_number} ===")

    def on_opponent_move(self, move: Move) -> None:
        """Print what the opponent did."""
        self._write(f"Opponent {describe_move(move)}.")

    def _show(self, state: GameState) -> None:
        """Print trump, deck, table and the numbered hand."""
        self._write(
            f"Trump {state.trump_suit} | deck: {state.deck_size} | "
            f"opponent's cards: {state.opponent_card_count}"
        )
        if state.table:
            pairs: str = "  ".join(
                f"[{attack} / {defence if defence is not None else '?'}]"
                for attack, defence in state.table
            )
            self._write(f"Table: {pairs}")
        numbered: str = "  ".join(
            f"{number}) {card}" for number, card in enumerate(state.hand, start=1)
        )
        self._write(f"Your hand: {numbered}")


def prompt_for(state: GameState) -> str:
    """Return the input prompt for the current situation."""
    if not state.is_attacking:
        return f"Cover {cards_to_text(state.undefended_cards)} (numbers) or t to take: "
    if state.table:
        return "Add cards (numbers) or p to pass: "
    return "Attack with (numbers): "


def parse_move(text: str, state: GameState) -> Move | None:
    """Turn typed text into a move, or return None if it cannot be read.

    This only checks the format; the rules are checked by the engine.
    """
    words: list[str] = text.strip().lower().split()
    if not words:
        return None
    if words == ["p"]:
        return PassMove() if state.is_attacking and state.table else None
    if words == ["t"]:
        return TakeMove() if not state.is_attacking else None
    cards: tuple[Card, ...] | None = pick_cards(words, state.hand)
    if cards is None:
        return None
    if state.is_attacking:
        return AttackMove(cards=cards)
    uncovered: tuple[Card, ...] = state.undefended_cards
    if len(cards) != len(uncovered):
        return None
    return DefendMove(beats=tuple(zip(uncovered, cards, strict=True)))


def pick_cards(words: list[str], hand: tuple[Card, ...]) -> tuple[Card, ...] | None:
    """Turn 1-based card numbers into cards from *hand*; None if any number is bad."""
    cards: list[Card] = []
    for word in words:
        if not word.isdigit() or not 1 <= int(word) <= len(hand):
            return None
        cards.append(hand[int(word) - 1])
    return tuple(cards)
