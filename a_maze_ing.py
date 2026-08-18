"""
A-Maze-ing entry point: read a config, generate a maze, draw it.

"""

import random
import sys

from pydantic import ValidationError

from app.config import load_config
from app.renderer import Renderer
from mazegen import MazeGenerator
from app.writer import write_maze

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

    def make_maze() -> MazeGenerator:
        seed = config.seed
        if seed is None:
            seed = random.SystemRandom().randrange(2 ** 32)
        print(f"seed: {seed}", flush=True)
        maze = MazeGenerator(
            width=config.width,
            height=config.height,
            entry=config.entry,
            exit=config.exit,
            perfect=config.perfect,
            seed=seed,
            algorithm=config.algorithm,
        )
        return maze

    def regenerate() -> MazeGenerator:
        maze = make_maze()
        try:
            write_maze(maze, config.output_file)
        except OSError as error:
            print(f"warning: cannot write {config.output_file}: "
                  f"{error.strerror}", file=sys.stderr)
        return maze

    try:
        maze = make_maze()
    except ValueError as error:
        print(f"error: {path}: {error}", file=sys.stderr)
        return EXIT_ERROR

    try:
        write_maze(maze, config.output_file)
    except OSError as error:
        print(f"error: cannot write {config.output_file}: {error.strerror}",
              file=sys.stderr)
        return EXIT_ERROR

    try:
        Renderer(maze, regenerate).run()
    except SystemExit as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
