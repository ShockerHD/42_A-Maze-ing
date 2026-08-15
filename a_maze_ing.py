"""
A-Maze-ing entry point: read a config, generate a maze, draw it.

"""

import sys

from pydantic import ValidationError

from app.config import load_config
from app.renderer import Renderer
from mazegen import MazeGenerator

DEFAULT_CONFIG = "config.txt"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print(f"usage: {argv[0]} [config file]", file=sys.stderr)
        return EXIT_USAGE
    path = argv[1] if len(argv) == 2 else DEFAULT_CONFIG

    try:
        config = load_config(path)
    except OSError as error:
        print(f"error: cannot read {path}: {error.strerror}", file=sys.stderr)
        return EXIT_ERROR
    except ValidationError as error:
        for detail in error.errors():
            key = ".".join(str(part) for part in detail["loc"]) or "config"
            reason = detail["msg"].removeprefix("Value error, ")
            print(f"error: {path}: {key}: {reason}", file=sys.stderr)
        return EXIT_ERROR
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR

    try:
        maze = MazeGenerator(
            width=config.width,
            height=config.height,
            entry=config.entry,
            exit=config.exit,
            perfect=config.perfect,
            seed=config.seed,
            algorithm=config.algorithm,
        )
    except ValueError as error:
        print(f"error: {path}: {error}", file=sys.stderr)
        return EXIT_ERROR

    try:
        Renderer(maze).run()
    except SystemExit as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
