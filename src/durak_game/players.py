"""Player types, and loading bots from files."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from durak_bot.bot import DurakBot
from durak_bot.runner import load_bot_from_file


class HumanPlayer(DurakBot, ABC):
    """A player controlled by a person (terminal now, GUI later).

    It is a ``DurakBot``, so ``Match`` treats people and bots the same way.
    The one difference: when a person makes an illegal move, ``Match`` shows
    the reason and asks again instead of playing a default move for them.
    """

    @abstractmethod
    def show_error(self, message: str) -> None:
        """Tell the person why their move was rejected."""


def load_bot(path: str | Path) -> DurakBot:
    """Load the first ``DurakBot`` subclass found in a ``.py`` file.

    Uses the course's own loader, so any tournament bot file works here.

    Raises:
        FileNotFoundError: If the file does not exist.
        TypeError: If the file has no ``DurakBot`` subclass.
    """
    return load_bot_from_file(path)
