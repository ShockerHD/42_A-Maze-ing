"""

Format and write maze data to output file

"""

from mazegen.generator import MazeGenerator


def format_maze(maze: MazeGenerator) -> str:
    rows = "\n".join("".join(f"{cell:X}" for cell in row) for row in maze.grid)
    entry_x, entry_y = maze.entry
    exit_x, exit_y = maze.exit
    return (f"{rows}\n\n"
            f"{entry_x},{entry_y}\n"
            f"{exit_x},{exit_y}\n"
            f"{maze.solution_string}\n")


def write_maze(maze: MazeGenerator, path: str) -> None:
    with open(path, "w", encoding="utf-8") as out:
        out.write(format_maze(maze))
