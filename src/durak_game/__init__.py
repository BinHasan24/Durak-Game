"""Durak card game.

The game uses the course's ``durak_bot`` types (``Card``, ``GameState``, the
move classes and ``DurakBot``), so any bot written for the course tournament
can play in this game unchanged.

Layers:
    rules, deck, table, engine  -- game logic (no input/output)
    players, match              -- who moves and how they are asked
    console, __main__           -- text interface (the GUI comes next)
"""

from durak_game.deck import Deck
from durak_game.engine import DurakEngine, IllegalMoveError, Phase
from durak_game.match import Match
from durak_game.players import HumanPlayer, load_bot
from durak_game.rules import Rules
from durak_game.table import Table

__all__: list[str] = [
    "Deck",
    "DurakEngine",
    "HumanPlayer",
    "IllegalMoveError",
    "Match",
    "Phase",
    "Rules",
    "Table",
    "load_bot",
]
