# mazegen

A small, dependency-free maze generator. It carves a rectangular grid into a
maze, keeps a "42" glyph closed off inside it, and hands you both the wall
data and the shortest path from entry to exit.

Requires Python 3.10 or later. Pure standard library.

## Install

```sh
pip install mazegen-0.1.0-py3-none-any.whl
```

## Quick start

```python
from mazegen import MazeGenerator

maze = MazeGenerator(width=20, height=15, entry=(0, 0), exit=(19, 14))

print(maze.grid[0])           # wall bitmasks of the first row
print(maze.solution_string)   # e.g. "SSESEESSW..."
print(maze.seed)              # replay this maze later
```

The maze is generated in the constructor, so a fresh instance is always ready
to use.

## Parameters

```python
MazeGenerator(
    width, height,          # grid size in cells, at least 2x2
    entry, exit,            # (x, y) cells, x = column, y = row, top-left origin
    perfect=True,           # True: exactly one path between any two cells
    seed=None,              # int for a reproducible maze, None to pick one
    algorithm="dfs",        # "dfs" or "kruskal"
)
```

* `perfect=False` removes some dead ends (braiding), which creates loops and
  therefore several routes to the exit. Corridors never open into a 3x3 area.
* `seed=None` draws a random seed; the one actually used is always available
  as `maze.seed`, so any maze can be reproduced.
* Both algorithms produce a perfect maze; `dfs` (randomised depth-first
  search) gives long winding corridors, `kruskal` a more uniform mix.

Invalid arguments raise `ValueError`: a maze smaller than 2x2, an entry or
exit outside the grid, entry equal to exit, or an unknown algorithm name.

```python
maze = MazeGenerator(
    width=30, height=30, entry=(0, 0), exit=(29, 29),
    perfect=False, seed=42, algorithm="kruskal",
)
```

## The generated structure

### `maze.grid` -> `list[list[int]]`

Row-major wall bitmasks, `grid[y][x]`. One bit per side, set means the wall is
closed:

| Bit | Value | Direction |
| --- | ----- | --------- |
| 0   | 1     | North     |
| 1   | 2     | East      |
| 2   | 4     | South     |
| 3   | 8     | West      |

The constants `BIT_NORTH`, `BIT_EAST`, `BIT_SOUTH`, `BIT_WEST` and `ALL_WALLS`
(`0xF`, every wall closed) are exported for this. Neighbouring cells always
agree about the wall between them, and the outer border is always closed.

```python
from mazegen import BIT_EAST

if maze.grid[y][x] & BIT_EAST:
    ...  # cannot walk from (x, y) to (x + 1, y)
```

`BIT` maps a `(dx, dy)` step to its bit, and `MOVE` maps the same step to its
letter, which is handy when walking the grid:

```python
from mazegen import BIT, MOVE

BIT[(0, -1)]   # 1, north
MOVE[(0, -1)]  # "N"
```

### `maze.solution` -> `list[Coord]`

The shortest path as cells, entry first, exit last. Computed on first access
and cached.

### `maze.solution_string` -> `str`

The same path as a string of `N`, `E`, `S` and `W` moves.

### `maze.pattern_cells` -> `frozenset[Coord]`

The cells forming the "42" glyph. They are fully closed off and excluded from
the maze, so nothing routes through them.

### `maze.pattern_skipped` -> `str | None`

`None` when the glyph was drawn, otherwise the reason it was dropped -- the
maze is too small for it, entry or exit falls inside it, or it would
disconnect the maze. Worth reporting to the user:

```python
if maze.pattern_skipped:
    print(f"'42' pattern omitted: {maze.pattern_skipped}")
```

### `maze.seed` -> `int`

The seed used, always a concrete integer even when none was passed. Feeding it
back to the constructor rebuilds the exact same maze.

### `maze.steps()` -> `Iterator[Step]`

Replays the last generation as discrete events, for animating the carving. A
`Step` has `kind`, `a` and an optional `b`; `kind` is one of `open`,
`consider`, `reject`, `visit`, `backtrack` and `done`. An `open` step means the
wall between `a` and `b` was removed.

```python
for step in maze.steps():
    if step.kind == "open":
        draw_opening(step.a, step.b)
```

### `maze.generate()`

Carves a new maze in place from the same seed and settings, resetting the
grid, the steps and the cached solution. `MazeGenerator` calls it once during
construction; call it again to redraw with a different `algorithm` or
`perfect` value:

```python
maze.algorithm = "kruskal"
maze.generate()
```

## Helper

`edges_to_grid(width, height, edges)` turns a set of open edges -- each a
`frozenset` of two adjacent coordinates -- into the same row-major bitmask
grid, in case you build a maze by other means and want the same output format.
