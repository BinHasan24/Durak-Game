"""Command line: ``python -m durak_game`` (or the ``durak`` command after install).

Examples::

    python -m durak_game                                   # play against AggressiveBot
    python -m durak_game play --bot bots/random_bot.py     # play against another bot file
    python -m durak_game watch bots/random_bot.py bots/aggressive_bot.py
    python -m durak_game bench bots/random_bot.py bots/aggressive_bot.py --games 200
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from durak_bot.bot import DurakBot
from durak_game.console import ConsolePlayer
from durak_game.match import Match
from durak_game.players import load_bot
from durak_game.rules import Rules

BOTS_DIR: Path = Path(__file__).resolve().parents[2] / "bots"
DEFAULT_BOT: Path = BOTS_DIR / "aggressive_bot.py"
COMMANDS: frozenset[str] = frozenset({"play", "watch", "bench"})


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser with the play / watch / bench commands."""
    common: argparse.ArgumentParser = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--seed", type=int, default=None, help="shuffle seed (same seed = same deal)"
    )
    common.add_argument(
        "--classic", action="store_true", help="classic rules instead of the course rules"
    )

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="durak_game", description="Durak card game, text version."
    )
    commands: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command", required=True
    )

    play_parser: argparse.ArgumentParser = commands.add_parser(
        "play", parents=[common], help="play against a bot (default)"
    )
    play_parser.add_argument(
        "--bot", type=Path, default=DEFAULT_BOT, help="bot file to play against"
    )

    watch_parser: argparse.ArgumentParser = commands.add_parser(
        "watch", parents=[common], help="watch two bots play one game"
    )
    watch_parser.add_argument("bot1", type=Path)
    watch_parser.add_argument("bot2", type=Path)

    bench_parser: argparse.ArgumentParser = commands.add_parser(
        "bench", parents=[common], help="many bot-vs-bot games, count wins"
    )
    bench_parser.add_argument("bot1", type=Path)
    bench_parser.add_argument("bot2", type=Path)
    bench_parser.add_argument("--games", type=int, default=100)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the command line and run the chosen command. Returns the exit code."""
    args_list: list[str] = list(sys.argv[1:] if argv is None else argv)
    if not args_list or args_list[0] not in COMMANDS | {"-h", "--help"}:
        args_list.insert(0, "play")
    args: argparse.Namespace = build_parser().parse_args(args_list)
    rules: Rules = Rules.classic() if args.classic else Rules.course()

    if args.command == "play":
        return play(args.bot, rules, args.seed)
    if args.command == "watch":
        return watch(args.bot1, args.bot2, rules, args.seed)
    return bench(args.bot1, args.bot2, rules, args.seed, args.games)


def play(bot_path: Path, rules: Rules, seed: int | None) -> int:
    """A person plays one game against the bot in *bot_path*."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    human: ConsolePlayer = ConsolePlayer()
    match: Match = Match((human, load_bot(bot_path)), rules=rules, seed=seed)
    print(f"You play against {match.name(1)}. Trump card: {match.engine.trump_card}")
    try:
        winner: int | None = match.play()
    except (KeyboardInterrupt, EOFError):
        print("\nGame stopped.")
        return 1
    if winner is None:
        print("\nDraw!")
    elif winner == 0:
        print("\nYou won!")
    else:
        print(f"\nYou lost: {match.name(1)} won, you are the durak.")
    return 0


def watch(bot1_path: Path, bot2_path: Path, rules: Rules, seed: int | None) -> int:
    """Two bots play one game; every move is printed."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    Match((load_bot(bot1_path), load_bot(bot2_path)), rules=rules, seed=seed).play()
    return 0


def bench(bot1_path: Path, bot2_path: Path, rules: Rules, seed: int | None, games: int) -> int:
    """Play *games* games between two bots (swapping seats) and print the score."""
    logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    bots: tuple[DurakBot, DurakBot] = (load_bot(bot1_path), load_bot(bot2_path))
    wins: list[int] = [0, 0]
    draws: int = 0
    first_seed: int = seed if seed is not None else 0
    for game in range(games):
        swap: bool = game % 2 == 1
        seats: tuple[DurakBot, DurakBot] = (bots[1], bots[0]) if swap else bots
        winner: int | None = Match(seats, rules=rules, seed=first_seed + game).play()
        if winner is None:
            draws += 1
        else:
            bot_index: int = 1 - winner if swap else winner  # seat number -> bot1 / bot2
            wins[bot_index] += 1
    for number, bot in enumerate(bots):
        print(f"bot{number + 1} {bot.get_name():<20} {wins[number]:>5} wins")
    print(f"{'draws':<25} {draws:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
