"""
Generator invariants -- PROJECT_PLAN.md section 8, subject IV.4.

Every test states a property that must hold for *any* maze, so each one
runs across both algorithms, perfect and braided, five sizes and eight
seeds.  Test ids name the case ("kruskal-braided-20x15-s3"), so a
failure is reproducible with a single MazeGenerator call.

Nothing here imports from app/: these are library invariants, and the
library is not allowed to know the app exists.
"""

from collections import deque
from typing import Any

import pytest

from mazegen import (
    ALL_WALLS,
    BIT,
    BIT_EAST,
    BIT_NORTH,
    BIT_SOUTH,
    BIT_WEST,
    Coord,
    MazeGenerator,
    edges_to_grid,
)
from mazegen.pattern import MIN_HEIGHT, MIN_WIDTH, glyph_cells

Case = tuple[str, bool, int, int, int]
Grid = list[list[int]]

ALGORITHMS = ("dfs", "kruskal")
SIZES = ((5, 5), (11, 9), (15, 11), (20, 15), (31, 21))
SEEDS = range(8)

# Only these two deltas, so each open wall is counted once.
SOUTH_EAST: tuple[Coord, ...] = ((1, 0), (0, 1))

CASES: list[Case] = [
    (algorithm, perfect, width, height, seed)
    for algorithm in ALGORITHMS
    for perfect in (True, False)
    for width, height in SIZES
    for seed in SEEDS
]


def _case_id(case: Case) -> str:
    """Readable pytest id, e.g. 'kruskal-braided-20x15-s3'."""
    algorithm, perfect, width, height, seed = case
    shape = "perfect" if perfect else "braided"
    return f"{algorithm}-{shape}-{width}x{height}-s{seed}"


@pytest.fixture(scope="session", params=CASES, ids=_case_id)
def maze(request: pytest.FixtureRequest) -> MazeGenerator:
    """One maze per (algorithm, perfect, size, seed) combination."""
    algorithm, perfect, width, height, seed = request.param
    return MazeGenerator(
        width=width,
        height=height,
        entry=(0, 0),
        exit=(width - 1, height - 1),
        perfect=perfect,
        seed=seed,
        algorithm=algorithm,
    )


def free_cells(maze: MazeGenerator) -> set[Coord]:
    """Every cell the algorithms were allowed to carve."""
    return {
        (x, y)
        for y in range(maze.height)
        for x in range(maze.width)
        if (x, y) not in maze.pattern_cells
    }


def neighbours(grid: Grid, cell: Coord) -> list[Coord]:
    """The cells reachable from *cell* through an open wall."""
    x, y = cell
    height, width = len(grid), len(grid[0])
    return [
        (x + dx, y + dy)
        for (dx, dy), bit in BIT.items()
        if not grid[y][x] & bit
        and 0 <= x + dx < width
        and 0 <= y + dy < height
    ]


def distances(grid: Grid, start: Coord) -> dict[Coord, int]:
    """Hop counts from *start*, found without using solver.py.

    The solver is the thing under test, so the reference distance has to
    come from somewhere else.
    """
    seen = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for neighbour in neighbours(grid, cell):
            if neighbour not in seen:
                seen[neighbour] = seen[cell] + 1
                queue.append(neighbour)
    return seen


def test_adjacent_cells_agree_about_their_shared_wall(
    maze: MazeGenerator,
) -> None:
    """IV.4: a wall is either there for both cells or for neither."""
    grid = maze.grid
    for y in range(maze.height):
        for x in range(maze.width):
            for (dx, dy), bit in BIT.items():
                nx, ny = x + dx, y + dy
                if not (0 <= nx < maze.width and 0 <= ny < maze.height):
                    continue
                back = BIT[(-dx, -dy)]
                assert bool(grid[y][x] & bit) == bool(grid[ny][nx] & back), (
                    f"({x},{y}) and ({nx},{ny}) disagree"
                )


def test_outer_border_is_closed(maze: MazeGenerator) -> None:
    """IV.4: entry and exit are cells, so the border is never a gap."""
    grid = maze.grid
    last_row, last_column = maze.height - 1, maze.width - 1
    assert all(grid[0][x] & BIT_NORTH for x in range(maze.width))
    assert all(grid[last_row][x] & BIT_SOUTH for x in range(maze.width))
    assert all(grid[y][0] & BIT_WEST for y in range(maze.height))
    assert all(grid[y][last_column] & BIT_EAST for y in range(maze.height))


def test_glyph_cells_are_fully_walled(maze: MazeGenerator) -> None:
    """IV.4: the '42' is drawn by cells with all four walls closed."""
    grid = maze.grid
    assert all(grid[y][x] == ALL_WALLS for x, y in maze.pattern_cells)


def test_every_free_cell_is_reachable(maze: MazeGenerator) -> None:
    """IV.4: full connectivity, no isolated cells outside the glyph."""
    assert set(distances(maze.grid, maze.entry)) == free_cells(maze)


def test_perfect_maze_is_a_spanning_tree(maze: MazeGenerator) -> None:
    """A connected graph with cells-1 edges has exactly one path."""
    if not maze.perfect:
        pytest.skip("only perfect mazes are trees")
    grid = maze.grid
    edges = sum(
        1
        for y in range(maze.height)
        for x in range(maze.width)
        for delta in SOUTH_EAST
        if not grid[y][x] & BIT[delta]
    )
    assert edges == len(free_cells(maze)) - 1


def test_no_fully_open_3x3_block(maze: MazeGenerator) -> None:
    """IV.4: 2x3 and 3x2 are allowed, 3x3 never is."""
    grid = maze.grid
    for y0 in range(maze.height - 2):
        for x0 in range(maze.width - 2):
            horizontal = all(
                not grid[y][x] & BIT_EAST
                for y in range(y0, y0 + 3)
                for x in range(x0, x0 + 2)
            )
            vertical = all(
                not grid[y][x] & BIT_SOUTH
                for y in range(y0, y0 + 2)
                for x in range(x0, x0 + 3)
            )
            assert not (horizontal and vertical), (
                f"3x3 open block at ({x0},{y0})"
            )


def test_solution_never_crosses_a_wall(maze: MazeGenerator) -> None:
    grid = maze.grid
    path = maze.solution
    assert path[0] == maze.entry
    assert path[-1] == maze.exit
    for a, b in zip(path, path[1:]):
        step = (b[0] - a[0], b[1] - a[1])
        assert step in BIT, f"{a} -> {b} is not one orthogonal step"
        assert not grid[a[1]][a[0]] & BIT[step], f"{a} -> {b} crosses a wall"


def test_solution_is_the_shortest_path(maze: MazeGenerator) -> None:
    """IV.5 asks for the *shortest* path, which is why the solver is BFS."""
    reference = distances(maze.grid, maze.entry)
    assert len(maze.solution) - 1 == reference[maze.exit]


def test_solution_string_matches_the_path(maze: MazeGenerator) -> None:
    assert set(maze.solution_string) <= set("NESW")
    assert len(maze.solution_string) == len(maze.solution) - 1


def test_replaying_the_steps_rebuilds_the_maze(maze: MazeGenerator) -> None:
    """Section 4.1: the animation and the maze can never disagree.

    This is the one test that catches an animation drifting away from
    the generation it is supposed to be showing.
    """
    replayed = edges_to_grid(
        maze.width,
        maze.height,
        {
            frozenset((step.a, step.b))
            for step in maze.steps()
            if step.kind == "open" and step.b is not None
        },
    )
    assert replayed == maze.grid


def test_the_same_seed_rebuilds_the_same_maze(maze: MazeGenerator) -> None:
    """IV.4: reproducibility via a seed."""
    twin = MazeGenerator(
        width=maze.width,
        height=maze.height,
        entry=maze.entry,
        exit=maze.exit,
        perfect=maze.perfect,
        seed=maze.seed,
        algorithm=maze.algorithm,
    )
    assert twin.grid == maze.grid
    assert twin.solution == maze.solution
    assert twin.solution_string == maze.solution_string
    assert list(twin.steps()) == list(maze.steps())


def test_an_omitted_seed_is_still_reported_and_reusable() -> None:
    """A good-looking random maze has to be reproducible afterwards."""
    maze = MazeGenerator(12, 10, (0, 0), (11, 9))
    assert isinstance(maze.seed, int)
    twin = MazeGenerator(12, 10, (0, 0), (11, 9), seed=maze.seed)
    assert twin.grid == maze.grid


def test_the_two_algorithms_produce_different_mazes() -> None:
    """The bonus is only worth claiming if the choice actually matters."""
    dfs = MazeGenerator(20, 15, (0, 0), (19, 14), seed=5, algorithm="dfs")
    kruskal = MazeGenerator(
        20, 15, (0, 0), (19, 14), seed=5, algorithm="kruskal"
    )
    assert dfs.grid != kruskal.grid
    assert {step.kind for step in dfs.steps()} == {
        "visit", "open", "backtrack", "done",
    }
    assert {step.kind for step in kruskal.steps()} == {
        "consider", "open", "reject", "done",
    }


def test_the_glyph_is_drawn_when_it_fits() -> None:
    maze = MazeGenerator(15, 15, (0, 0), (14, 14), seed=1)
    assert maze.pattern_skipped is None
    assert maze.pattern_cells == glyph_cells(15, 15)


def test_the_glyph_is_skipped_when_the_maze_is_too_small() -> None:
    """IV.4 allows omitting the pattern, but the app has to say so."""
    maze = MazeGenerator(MIN_WIDTH - 1, MIN_HEIGHT - 1, (0, 0), (8, 6))
    assert maze.pattern_cells == frozenset()
    assert maze.pattern_skipped is not None
    assert f"{MIN_WIDTH}x{MIN_HEIGHT}" in maze.pattern_skipped


def test_the_glyph_is_skipped_when_it_would_swallow_the_entry() -> None:
    entry = sorted(glyph_cells(15, 15))[0]
    maze = MazeGenerator(15, 15, entry, (14, 14), seed=1)
    assert maze.pattern_cells == frozenset()
    assert maze.pattern_skipped is not None
    assert "entry or exit" in maze.pattern_skipped


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (dict(width=1, height=5, entry=(0, 0), exit=(0, 4)), "at least"),
        (dict(width=5, height=5, entry=(9, 0), exit=(4, 4)), "outside"),
        (dict(width=5, height=5, entry=(0, 0), exit=(9, 4)), "outside"),
        (dict(width=5, height=5, entry=(2, 2), exit=(2, 2)), "different"),
    ],
    ids=["too-small", "entry-outside", "exit-outside", "entry-is-exit"],
)
def test_invalid_parameters_raise_valueerror(
    kwargs: dict[str, Any], message: str
) -> None:
    """IV.2: the app turns these into a message, never a traceback."""
    with pytest.raises(ValueError, match=message):
        MazeGenerator(**kwargs)


def test_an_unknown_algorithm_raises_valueerror() -> None:
    """Reachable by a library user; the config parser blocks the app path."""
    with pytest.raises(ValueError, match="unknown algorithm"):
        MazeGenerator(10, 10, (0, 0), (9, 9), algorithm="prim")
