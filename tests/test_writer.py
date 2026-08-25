"""
Output file format -- subject IV.5, PROJECT_PLAN.md section 7.9.

The writer lives in app/ but the bit convention it serialises is J's, so
these live next to the generator invariants rather than the app tests.
"""

from pathlib import Path

import pytest

from app.writer import format_maze, write_maze
from mazegen import MazeGenerator

WIDTH, HEIGHT = 20, 15
ENTRY, EXIT = (0, 0), (WIDTH - 1, HEIGHT - 1)
HEX_DIGITS = set("0123456789ABCDEF")


@pytest.fixture(scope="module")
def maze() -> MazeGenerator:
    return MazeGenerator(WIDTH, HEIGHT, ENTRY, EXIT, seed=42)


@pytest.fixture(scope="module")
def text(maze: MazeGenerator) -> str:
    return format_maze(maze)


def test_one_uppercase_hex_digit_per_cell(text: str) -> None:
    rows = text.splitlines()[:HEIGHT]
    assert all(len(row) == WIDTH for row in rows)
    assert set("".join(rows)) <= HEX_DIGITS


def test_a_blank_line_separates_the_grid_from_the_metadata(
    text: str,
) -> None:
    lines = text.splitlines()
    assert lines[HEIGHT] == ""
    assert len(lines) == HEIGHT + 4


def test_entry_and_exit_are_written_as_x_y(text: str) -> None:
    lines = text.splitlines()
    assert lines[HEIGHT + 1] == f"{ENTRY[0]},{ENTRY[1]}"
    assert lines[HEIGHT + 2] == f"{EXIT[0]},{EXIT[1]}"


def test_the_path_is_the_move_string(
    text: str, maze: MazeGenerator
) -> None:
    """IV.5 wants the NESW moves here, not coordinates."""
    assert text.splitlines()[HEIGHT + 3] == maze.solution_string


def test_every_line_ends_with_a_newline(text: str) -> None:
    """Including the last one -- the easiest byte in the subject to miss."""
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_the_grid_survives_a_round_trip(
    text: str, maze: MazeGenerator
) -> None:
    rows = text.splitlines()[:HEIGHT]
    assert [[int(digit, 16) for digit in row] for row in rows] == maze.grid


def test_write_maze_writes_exactly_what_format_maze_returns(
    tmp_path: Path, maze: MazeGenerator, text: str
) -> None:
    path = tmp_path / "maze_out.txt"
    write_maze(maze, str(path))
    assert path.read_text(encoding="utf-8") == text


def test_the_same_seed_gives_a_byte_identical_file(tmp_path: Path) -> None:
    """Section 8: determinism, checked where it is actually observable."""
    written = []
    for name in ("first.txt", "second.txt"):
        path = tmp_path / name
        write_maze(
            MazeGenerator(WIDTH, HEIGHT, ENTRY, EXIT, seed=7), str(path)
        )
        written.append(path.read_bytes())
    assert written[0] == written[1]
