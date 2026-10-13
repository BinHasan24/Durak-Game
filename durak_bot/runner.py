"""Tournament runner for Durak bots.

Usage
-----
Run from the command line::

    python -m durak_bot.runner bot1.py bot2.py bot3.py --games 20

Or programmatically::

    from durak_bot.runner import TournamentRunner

    runner = TournamentRunner(num_games=10)
    runner.register_bot("Alice", alice_bot)
    runner.register_bot("Bob", bob_bot)
    result = runner.run()
    runner.print_results(result)
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from durak_bot.bot import DurakBot
from durak_bot.game import DurakGame


# ------------------------------------------------------------------ #
#  Data classes                                                       #
# ------------------------------------------------------------------ #


@dataclass
class MatchResult:
    """Result of all games between two bots."""

    bot1_name: str
    bot2_name: str
    bot1_wins: int
    bot2_wins: int
    draws: int

    @property
    def total(self) -> int:
        return self.bot1_wins + self.bot2_wins + self.draws


@dataclass
class TournamentResult:
    """Full tournament result with standings and per-match details."""

    standings: list[tuple[str, float]]
    """List of (bot_name, total_score) sorted by score descending."""

    matches: dict[tuple[str, str], MatchResult]
    """Match results keyed by (name1, name2) where name1 < name2."""

    num_games: int
    """Games played per matchup."""


# ------------------------------------------------------------------ #
#  Bot loading                                                        #
# ------------------------------------------------------------------ #


def load_bot_from_file(filepath: str | Path) -> DurakBot:
    """Load a DurakBot subclass from a Python file.

    The file must contain exactly one class that inherits from DurakBot.
    If multiple such classes exist, the first one found is used.

    Parameters
    ----------
    filepath:
        Path to a ``.py`` file containing a DurakBot subclass.

    Returns
    -------
    DurakBot
        An instance of the bot class found in the file.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    TypeError
        If no DurakBot subclass is found in the file.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Bot file not found: {filepath}")

    module_name = filepath.stem
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {filepath}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Find the first class that is a subclass of DurakBot (but not DurakBot itself).
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, DurakBot)
            and attr is not DurakBot
        ):
            return attr()

    raise TypeError(
        f"No DurakBot subclass found in {filepath}. "
        "Make sure your file defines a class that inherits from DurakBot."
    )


# ------------------------------------------------------------------ #
#  Tournament runner                                                  #
# ------------------------------------------------------------------ #


class TournamentRunner:
    """Round-robin tournament runner for Durak bots.

    Parameters
    ----------
    num_games:
        Number of games to play per matchup.  Each matchup is played
        twice (once with each bot as the first player) for fairness.
    base_seed:
        Base random seed.  Each matchup uses a deterministic seed derived
        from this value so results are reproducible.
    """

    def __init__(self, num_games: int = 10, base_seed: int = 42) -> None:
        self.num_games = num_games
        self.base_seed = base_seed
        self._bots: dict[str, DurakBot] = {}

    def register_bot(self, name: str, bot: DurakBot) -> None:
        """Register a bot for the tournament."""
        self._bots[name] = bot

    def load_bot(self, filepath: str | Path, name: str | None = None) -> str:
        """Load and register a bot from a Python file.

        Parameters
        ----------
        filepath:
            Path to a ``.py`` file containing a DurakBot subclass.
        name:
            Display name.  Defaults to the file stem.

        Returns
        -------
        str
            The name the bot was registered under.
        """
        filepath = Path(filepath)
        bot = load_bot_from_file(filepath)
        bot_name = name or bot.get_name() or filepath.stem
        # Ensure unique names by appending a counter.
        if bot_name in self._bots:
            counter = 2
            base = bot_name
            while bot_name in self._bots:
                bot_name = f"{base} #{counter}"
                counter += 1
        self.register_bot(bot_name, bot)
        return bot_name

    # ------------------------------------------------------------------ #

    def run(self) -> TournamentResult:
        """Run the full round-robin tournament.

        Returns
        -------
        TournamentResult
            Complete standings and match results.
        """
        names = list(self._bots.keys())
        scores: dict[str, float] = defaultdict(float)
        matches: dict[tuple[str, str], MatchResult] = {}

        for idx, (name1, name2) in enumerate(itertools.combinations(names, 2)):
            bot1, bot2 = self._bots[name1], self._bots[name2]
            seed = self.base_seed + idx * self.num_games * 2

            w1, w2, draws = 0, 0, 0

            for i in range(self.num_games):
                # First half: bot1 attacks first.
                game1 = DurakGame(bot1, bot2, seed=seed + i)
                winner1 = game1.play_game()

                # Second half: bot2 attacks first.
                game2 = DurakGame(bot2, bot1, seed=seed + self.num_games + i)
                winner2 = game2.play_game()

                # Translate results: 0 = first player, 1 = second player.
                for winner, other_idx in [(winner1, 1), (winner2, 0)]:
                    if winner == 0:
                        if other_idx == 1:
                            w1 += 1
                        else:
                            w2 += 1
                    elif winner == 1:
                        if other_idx == 1:
                            w2 += 1
                        else:
                            w1 += 1
                    else:
                        draws += 1

                scores[name1] += self._outcome_score(winner1, 0)
                scores[name2] += self._outcome_score(winner1, 1)
                scores[name2] += self._outcome_score(winner2, 0)
                scores[name1] += self._outcome_score(winner2, 1)

            key = tuple(sorted((name1, name2)))
            matches[key] = MatchResult(
                bot1_name=key[0],
                bot2_name=key[1],
                bot1_wins=w1 if key[0] == name1 else w2,
                bot2_wins=w2 if key[0] == name1 else w1,
                draws=draws,
            )

        standings = sorted(scores.items(), key=lambda x: -x[1])
        return TournamentResult(
            standings=standings,
            matches=matches,
            num_games=self.num_games,
        )

    @staticmethod
    def _outcome_score(winner: int | None, player_idx: int) -> float:
        """Convert a game result to points for *player_idx*."""
        if winner is None:
            return 0.5
        return 1.0 if winner == player_idx else 0.0

    # ------------------------------------------------------------------ #
    #  Output                                                             #
    # ------------------------------------------------------------------ #

    def print_results(self, result: TournamentResult) -> None:
        """Print a human-readable summary of the tournament."""
        total_games_per_matchup = self.num_games * 2
        n = len(result.standings)

        print("=" * 64)
        print("  DURAK TOURNAMENT RESULTS")
        print("=" * 64)
        print(f"  Bots:            {n}")
        print(f"  Games/matchup:   {total_games_per_matchup}")
        print(f"  Total games:     {total_games_per_matchup * n * (n - 1) // 2}")
        print()

        # Standings table.
        print(f"  {'#':<4} {'Bot':<25} {'Score':>7}")
        print("  " + "-" * 38)
        for rank, (name, score) in enumerate(result.standings, 1):
            print(f"  {rank:<4} {name:<25} {score:>7.1f}")
        print()

        # Match details.
        print("  MATCH RESULTS")
        print("  " + "-" * 56)
        print(f"  {'Bot 1':<18} {'Bot 2':<18} {'W':>4} {'D':>4} {'L':>4}")
        print("  " + "-" * 56)
        for (name1, name2), match in sorted(result.matches.items()):
            print(
                f"  {match.bot1_name:<18} {match.bot2_name:<18} "
                f"{match.bot1_wins:>4} {match.draws:>4} {match.bot2_wins:>4}"
            )
        print("=" * 64)


# ------------------------------------------------------------------ #
#  CLI entry point                                                    #
# ------------------------------------------------------------------ #


def main() -> None:
    """Command-line entry point for the tournament runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a Durak bot tournament.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python -m durak_bot.runner my_bot.py opponent_bot.py --games 20\n"
        ),
    )
    parser.add_argument(
        "bots",
        nargs="+",
        help="Paths to Python files containing DurakBot subclasses.",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=10,
        help="Number of games per matchup for each side (default: 10).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base random seed for reproducibility (default: 42).",
    )

    args = parser.parse_args()

    if len(args.bots) < 2:
        parser.error("At least 2 bot files are required.")

    runner = TournamentRunner(num_games=args.games, base_seed=args.seed)

    for bot_path in args.bots:
        try:
            name = runner.load_bot(bot_path)
            print(f"  Loaded bot: {name}  ({bot_path})")
        except (FileNotFoundError, TypeError, ImportError) as exc:
            print(f"  ERROR loading {bot_path}: {exc}", file=sys.stderr)
            sys.exit(1)

    print()
    result = runner.run()
    runner.print_results(result)


if __name__ == "__main__":
    main()
