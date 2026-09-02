*This project has been created as part of the 42 curriculum by aselezen, jkarl.*

# A-Maze-ing

## Description

A-Maze-ing generates a maze from a configuration file, writes it to disk in
the required text format, and draws it in a MiniLibX window that animates the
generation as it happens.

The maze can be **perfect** (exactly one route between any two cells) or
**braided** (dead ends opened up, so several routes exist), is carved by
either **Kruskal's algorithm** or an **iterative depth-first search**, and
always carries a "42" glyph of fully-walled cells where the grid is large
enough to hold one.

The project is split in two along a single line: `mazegen/` never reads a
file, never prints and never draws. It takes typed parameters and returns
data structures. Everything touching the filesystem, the terminal or the
screen lives in `app/`. That is what makes `mazegen` reusable on its own,
and it is why the package can be installed and imported from anywhere.

## Instructions

Requires Linux, Python 3.10+, [uv](https://docs.astral.sh/uv/), and the
MiniLibX wheel `mlx-2.2-py3-none-any.whl` at the repository root.

```sh
make install     # uv sync, plus a native MiniLibX rebuild where needed
make run         # generate from config.txt, write the output, open the window
make debug       # the same under pdb
make lint        # flake8 + mypy
make lint-strict # flake8 + mypy --strict
make build       # rebuild the mazegen wheel into the repository root
make clean       # caches, the venv and the generated output file
```

`make install` rebuilds `libmlx.so` from the MiniLibX sources when the
architecture needs it: the shipped wheel is tagged `py3-none-any` but
contains a prebuilt **x86-64** shared object, so on any other architecture
importing it fails with a misleading "cannot open shared object file".

### Controls

| Key | Action |
|---|---|
| `R` | Generate a new maze and animate the carve |
| `P` | Reveal or hide the shortest path |
| `C` | Cross-fade to the next colour scheme |
| `SPC` | Replay the carve of the maze on screen |
| `ESC` or `Q` | Quit |

`Ctrl-C` cannot interrupt `mlx_loop` from Python, so quitting is done with a
key. The legend along the bottom of the window lists the same bindings, so
nothing has to be memorised from this file.

## Configuration file

`KEY=VALUE`, one per line. The default configuration is `config.txt`; pass
another path as the only argument (`uv run a_maze_ing.py other.txt`).

| Key | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `WIDTH` | integer ≥ 2 | yes | — | Columns |
| `HEIGHT` | integer ≥ 2 | yes | — | Rows |
| `ENTRY` | `x,y` | yes | — | Entry cell, origin top-left |
| `EXIT` | `x,y` | yes | — | Exit cell, must differ from `ENTRY` |
| `OUTPUT_FILE` | path | yes | — | Where the maze is written |
| `PERFECT` | boolean | yes | — | `TRUE` for a perfect maze, `FALSE` to braid it |
| `SEED` | integer | no | random | Fixing it reproduces a maze exactly |
| `ALGORITHM` | `dfs` or `kruskal` | no | `dfs` | Which algorithm carves the maze |

**Parsing rules**, all of them deliberate:

- A line whose first non-blank character is `#` is a comment.
- A `#` **later** in a line starts a trailing comment: `ALGORITHM=dfs #kruskals`
  parses as `dfs`. Without this rule that value would silently become
  `"dfs #kruskals"` and algorithm selection would fail with no error at all.
- Keys are case-insensitive; whitespace around the key, the `=` and the value
  is ignored.
- Booleans accept `TRUE`, `true`, `True`, `1`, and their false counterparts.
- Blank lines are skipped.
- A **duplicate key** is an error, rather than a silent last-one-wins.
- An **empty value** is an error.
- An **unknown key** prints a warning and is ignored, so a config from a
  later version still runs.

Every error names the file, the line number and what is wrong, exits
non-zero, and never shows a traceback:

```
$ uv run a_maze_ing.py broken.txt
error: broken.txt:7: duplicate key WIDTH
```

### Example

```
WIDTH=15
HEIGHT=15
ENTRY=0,0
EXIT=14,14
OUTPUT_FILE=maze_out.txt
PERFECT=TRUE
ALGORITHM=dfs
# SEED=1
```

### Output file

The grid as uppercase hex digits, one digit per cell and one line per row,
then a blank line, then the entry cell, the exit cell, and the shortest path
as a string of `N`/`E`/`S`/`W` moves. Each digit is a bitmask of that cell's
closed walls: bit 0 = North, 1 = East, 2 = South, 3 = West, so `F` is a fully
walled cell.

```
D53953953D51557
B96C3AABC53C153
...

0,0
14,14
EESWSWSSSSSSSENN...
```

## Algorithms

**The maze is an edge set, not a grid of walls.** While it is being carved the
maze lives in `MazeGenerator` as a `set[frozenset[Coord]]` — one undirected
edge per opened wall. The per-cell bitmask grid is derived from it at the
boundary, in `edges_to_grid()`, and nowhere else. That makes it *structurally
impossible* for one cell to be open eastward while its neighbour is closed
westward: both masks are written from the same edge, in the same loop. Wall
coherence is a validity requirement of the subject and a classic source of
silent bugs, and choosing the representation removes the whole bug class
rather than testing for it afterwards.

**The "42" glyph is removed before anything is carved.** Fully-walled cells
are cells that are not in the graph at all. `pattern.py` centres the 7x5
glyph, and `MazeGenerator._free` is every cell outside it; `_neighbours()` —
the one function both algorithms use to look around — only ever returns cells
from `_free`, so to an algorithm the glyph simply does not exist. The other
order, walling the glyph in after carving, would tear holes in a finished
spanning tree and disconnect the maze. The mask has to pass three checks
before it is accepted: the maze must be at least 11x9 to hold the glyph plus a
one-cell margin, entry and exit must not fall inside it, and the cells left
over must still form one connected region (a flood fill, in
`pattern.splits_grid`). If any check fails the glyph is dropped and the reason
is handed back as a value through `pattern_skipped` — the library never
prints; the app does.

### Kruskal's algorithm (`ALGORITHM=kruskal`)

Randomised Kruskal over the free cells. Every wall between two free cells is
collected once (`if n < cell` keeps each pair from being added twice), the
list is shuffled, and then walked in that order: if the two cells belong to
different sets the wall is opened and the sets merged, otherwise it is left
standing. Randomised Kruskal has no weights and therefore needs no sort — the
shuffle *is* the weight assignment — so the `O(E log E)` of textbook Kruskal
collapses to a linear pass plus the union-find work.

**Union-find** is what makes "are these two cells already connected?" cheap.
Every cell starts as its own set, pointing at itself; `find_parent` walks the
parent chain up to the representative and halves the path on the way
(`parents[cell] = parents[parents[cell]]`), so repeated queries flatten the
tree as a side effect of asking. Without it the same question is a graph
search per wall — `O(V)` each, `O(V·E)` overall, the difference between
instant and unusable at 60x40. The implementation attaches one root to the
other without union by rank; path halving alone is enough for near-linear
behaviour at these grid sizes.

The result is a spanning tree: exactly `V - 1` walls are opened, because each
opening merges two sets and there are `V` sets to merge into one, and no
opening can ever close a cycle, because a wall inside one set is rejected. A
spanning tree over the grid *is* a perfect maze — one route between any two
cells, no loops, nothing unreachable.

### Iterative depth-first search (`ALGORITHM=dfs`)

The recursive backtracker, with an explicit stack in place of recursion. From
the entry cell: look at the neighbours not yet visited, pick one at random,
open the wall between them, push it. When a cell has no unvisited neighbours
left, pop it and carry on from the cell underneath. Each cell is entered
exactly once, and every opening joins a visited cell to an unvisited one, so
no opening can close a cycle — a spanning tree again, perfect again.

**Iterative rather than recursive, on purpose.** The stack depth grows with
the longest corridor, and DFS corridors are long: on a 60x40 maze the stack
routinely passes a thousand cells, which is Python's default recursion limit.
The recursive version raises `RecursionError` at exactly the sizes the project
has to handle.

### Why both

|  | Kruskal | DFS |
|---|---|---|
| Picks | a random wall anywhere on the grid | a random step from where it stands |
| Grows | many separate regions, fusing | one frontier, backtracking |
| Character | short branches, junctions spread evenly | long winding corridors, few junctions |
| Emits | `consider`, then `open` or `reject` | `visit`, `open`, `backtrack` |
| On screen | regions fuse all over the grid at once | a snake carves and retreats |

Both produce perfect mazes, so the choice is about the *character* of the maze
rather than its correctness. Because each emits its own vocabulary of step
events, the difference between them is visible while it happens instead of
being described afterwards — which is the main reason two algorithms are worth
having rather than one.

### Braiding — non-perfect mazes

`PERFECT=FALSE` runs a braiding pass over the finished spanning tree
(`constraints.braid`). It walks the cells in sorted order, finds every dead
end — a cell with exactly one open wall — and opens a second wall at random.
Every such opening adds a cycle, so the maze stops being perfect and more than
one route to the exit appears. The pass runs last, deliberately: braiding a
finished tree is well defined, whereas braiding *during* carving would fight
the algorithm's own connectivity invariant.

### The 3x3 constraint

No 3x3 block of cells may be fully open. The useful observation is that in
perfect mode this costs nothing at all:

> A 3x3 block has 9 cells and 12 internal edges. A spanning tree over 9 cells
> has exactly 8. So twelve open edges among nine cells implies at least one
> cycle — and a perfect maze has none. **Only braiding can violate the
> constraint.**

So the guard lives *inside* the braiding loop rather than in a post-pass over
the finished maze. `opens_3x3` probes the six 3x3 blocks that could contain
the candidate edge, and the braid skips any opening that would complete one; a
dead end whose every alternative would complete a 3x3 stays a dead end, so the
constraint wins over the braid. A global post-pass would instead have to
*undo* openings, and undoing an opening can re-isolate a region. Refusing one
up front cannot fail.

### Shortest path

`solver.shortest_path` is a breadth-first search from entry to exit across the
open edges, recording a parent per cell and walking that map back from the
exit. The subject asks for the *shortest* path, and BFS on an unweighted graph
is exactly that: the first time BFS reaches a cell it has reached it in the
fewest possible moves. A depth-first search would find *a* path, and on a
DFS-carved maze usually a comically bad one. Dijkstra or A\* would also be
correct, but every move costs one, so the priority queue would buy nothing
over a plain queue.

In a perfect maze the shortest path is also the only path, which makes the BFS
look redundant — it is not. Braided mazes have several routes, and only one of
them is the one written to the output file. The path is computed on first
access and cached, then turned into the `N`/`E`/`S`/`W` move string by looking
each consecutive pair up in `MOVE`.

### Determinism

One `random.Random`, seeded once in `__init__` and threaded through everything
that makes a choice: Kruskal's shuffle, DFS's neighbour pick, the braid's
option order. `SEED=` therefore reproduces a maze exactly. When it is absent a
seed is drawn from `random.SystemRandom` and *stored*, so `maze.seed` is
always a concrete integer and any maze that happens to look good can be
rebuilt later. `generate()` reseeds before consuming a single event — the
algorithms are Python generators, so no randomness has been drawn at the point
the seed is reset — which is what makes re-running it a replay rather than a
new maze.

### Cost

For `V = WIDTH x HEIGHT` cells and `E ≈ 2V` walls:

| Step | Cost |
|---|---|
| Kruskal | `O(E)` shuffle and walk, plus near-linear union-find |
| DFS | `O(V)` — every cell pushed and popped once |
| Braiding | `O(V)`, with a constant-size probe per dead end |
| BFS solve | `O(V + E)` |
| `grid` | `O(V)` |

Linear in the cell count, in practice as well as in theory: a 60x40 Kruskal
maze — 2400 cells, 9277 step events, solved — is built in about 8 ms. The two
and a half seconds it takes on screen are the animation's choice, not the
algorithm's.

## Reusable module

`mazegen` is the half of this project that can leave it. Pure standard
library, Python 3.10+, no dependency on `app/` and no dependency on anything
else: it never opens a file, never prints and never draws. Failures are
raised, not reported, and a skipped "42" glyph is a value (`pattern_skipped`)
rather than a message. That is the whole reason it can be dropped into another
program unchanged.

### Install

The built wheel is committed at the repository root:

```sh
pip install mazegen-0.1.0-py3-none-any.whl
```

`make build` rebuilds the wheel and the sdist from `mazegen/`. There is
nothing to resolve — it installs into an empty virtualenv, and
`from mazegen import MazeGenerator` then works from any directory.

### The API

```python
MazeGenerator(
    width, height,          # grid size in cells, at least 2x2
    entry, exit,            # (x, y) cells, x = column, y = row, origin top-left
    perfect=True,           # False braids the maze
    seed=None,              # int reproduces a maze; None draws one and keeps it
    algorithm="dfs",        # "dfs" or "kruskal"
)
```

The maze is carved in the constructor, so an instance is usable the moment it
exists. Invalid arguments raise `ValueError`: a maze smaller than 2x2, an
entry or exit off the grid, entry equal to exit, an unknown algorithm name.

| Member | Type | What it gives you |
|---|---|---|
| `.grid` | `list[list[int]]` | Row-major wall bitmasks, `grid[y][x]` |
| `.solution` | `list[Coord]` | Shortest path as cells, entry first, exit last |
| `.solution_string` | `str` | The same path as `N`/`E`/`S`/`W` moves |
| `.steps()` | `Iterator[Step]` | The carve, replayable as discrete events |
| `.pattern_cells` | `frozenset[Coord]` | The "42" cells, empty if the glyph was skipped |
| `.pattern_skipped` | `str \| None` | Why it was skipped, or `None` if it was drawn |
| `.seed` | `int` | Always concrete, even when `None` was passed |
| `.generate()` | `None` | Re-carve in place after changing `algorithm` or `perfect` |

Also exported: `BIT_NORTH`, `BIT_EAST`, `BIT_SOUTH`, `BIT_WEST`, `ALL_WALLS`
(`0xF`), `BIT` mapping a `(dx, dy)` step to its wall bit, `MOVE` mapping the
same step to its letter, and `edges_to_grid()`, which turns an edge set built
by some other means into the same bitmask grid.

### A worked example

```python
from mazegen import BIT_EAST, MazeGenerator

maze = MazeGenerator(
    width=20, height=15, entry=(0, 0), exit=(19, 14),
    seed=42, algorithm="kruskal",
)

print(maze.seed)                    # 42 -- pass it back to rebuild this maze
print(maze.grid[0][0])              # 9 -- north and west closed (1 | 8)
print(maze.grid[0][0] & BIT_EAST)   # 0 -- so (1, 0) is reachable from (0, 0)

if maze.pattern_skipped:
    print(f"'42' omitted: {maze.pattern_skipped}")
```

The solution comes out in either of two shapes — cells, or moves:

```python
print(len(maze.solution))     # 50
print(maze.solution[:3])      # [(0, 0), (0, 1), (0, 2)]
print(maze.solution_string)   # "SSEESSWSEESSSSSSESEE..."
```

`BIT` and `MOVE` are what make the move string walkable against the grid, and
this is the invariant the test suite checks: every move in the string crosses
a wall the grid reports as open, and the walk ends on the exit.

```python
from mazegen import BIT, MOVE

deltas = {letter: delta for delta, letter in MOVE.items()}
x, y = maze.entry
for move in maze.solution_string:
    dx, dy = deltas[move]
    assert not maze.grid[y][x] & BIT[(dx, dy)]
    x, y = x + dx, y + dy
assert (x, y) == maze.exit
```

To animate the carve rather than just its result, replay the step stream. A
`Step` carries `kind`, `a` and an optional `b`; an `open` step means the wall
between `a` and `b` came down. Replaying every `open` reconstructs the final
grid exactly, which is what keeps the animation and the maze from ever
disagreeing:

```python
for step in maze.steps():
    if step.kind == "open":
        draw_opening(step.a, step.b)
```

### How the app uses it

Exactly through the API above and nothing else: `a_maze_ing.py` constructs the
generator from the parsed config, `app/writer.py` formats `.grid` and
`.solution_string` into the output file, and the renderer replays `.steps()`
and draws `.solution` and `.pattern_cells`. Nothing reaches past that line,
which is why the maze can be generated headless — in the tests, or in any
other program — without a renderer anywhere in sight.

The full reference — every parameter, every member, the bit table — is
[mazegen/usage.md](mazegen/usage.md), which is also the wheel's long
description.

## Visual representation

The window is a MiniLibX window driven through the vendored Python wrapper.

**Drawing.** Every frame is assembled in a `bytearray` and pushed to the
image's `memoryview` in a single slice assignment, then blitted with one
`mlx_put_image_to_window` call. Nothing is ever drawn with `mlx_pixel_put`:
at 1280x720 that would be almost a million ctypes calls per frame. The
bits-per-pixel and `size_line` reported by `mlx_get_data_addr` are read at
runtime rather than assumed, because `size_line` usually includes padding.

The grid is sized to fit whatever `WIDTH` and `HEIGHT` ask for: the cell size
is derived from the window so cells tile the drawing area exactly with no
remainder, and wall thickness scales with it. A 5x5 maze and a 60x40 maze
both fill the window without any special-casing.

**Animation.** All animation state advances inside `mlx_loop_hook`, which
must return promptly every time — sleeping in it would freeze the window and
swallow key events. Time comes from `time.monotonic()` deltas rather than an
assumed frame interval, because MiniLibX does not provide one, and a delta is
capped so a stalled window pauses an animation instead of teleporting it.

Three animations run through one small scheduler in `app/animation.py`:

- **The generation animation** replays the step-event stream the generator
  records while carving. It is paced in *events per second* derived from a
  target duration, not one event per frame: a 15x15 maze (615 events) and a
  60x40 maze (9277 events) therefore both take about 2.5 seconds. Because the
  two algorithms emit different events, they look completely different on
  screen — DFS carves and retreats like a snake, with a solid uncarved block
  ahead of it, while Kruskal fuses separate regions all over the grid at once.
- **The path reveal** tweens the stripe from entry to exit. It is
  interruptible: pressing `P` mid-reveal reverses from the current progress
  rather than restarting, so the stripe folds back from where it actually is.
- **The palette cross-fade** interpolates every colour channel-wise, eased
  with smoothstep, and lands exactly on the destination scheme.

**Redrawing.** The carve and the path patch only the cells they touch —
roughly 0.02 ms per cell, against about 12 ms to repaint the whole frame.
That is what keeps the frame rate flat as the maze grows: a 60x40 carve runs
as smoothly as a 15x15 one. The cross-fade is the one animation that cannot
patch, because every colour on screen changes at once, so it repaints in
full.

**Colours.** Seven schemes — `dark`, `light`, `neon`, `spring`, `summer`,
`autumn`, `winter` — cycled with `C`. Each defines its own colour for the
background, walls, floor, entry, exit, path, legend, and a distinct one for
the "42" glyph, so the pattern reads as deliberate in every scheme.

## Bonuses

- **Multiple algorithms.** Kruskal and iterative DFS, selected with
  `ALGORITHM=`.
- **Generation animation.** Driven by a step-event stream the generator
  records, so the animation never drives generation — headless runs and the
  test suite get a maze without a renderer.
- **Live colour switching**, cross-faded rather than snapped.
- **Animated, interruptible path reveal.**
- **Replay** of the carve for the maze already on screen.

## Team & project management

| Role | Who | Owns |
|---|---|---|
| Algorithms & library | jkarl | `mazegen/`, the solver, packaging, the output writer |
| Visualization & app shell | aselezen | `app/`, the renderer, animations, config, CLI |

The split follows the library/app seam described above, agreed on day one as
a written contract — the `MazeGenerator` API, the wall-bit convention, and
the step-event stream — so that both halves could be built in parallel. A
stub generator satisfying that contract existed on day one, which is what
kept the renderer from ever being blocked on the algorithms.

### Planned vs actual — A (`aselezen`)

`PROJECT_PLAN.md` budgeted ~42h across ~10 working days for the app half.
Actual: **9 active days, 55 commits, spread over 14 calendar days**
(11–24 Aug). The effort estimate held; the calendar did not.

Project days below are A's active days, not calendar days:
D1 = 11 Aug · D2 = 13 · D3 = 14 · D4 = 15 · D5 = 16 · D6 = 18 · D7 = 22 ·
D8 = 23 · D9 = 24.

| # | Task | Planned | Actual | Δ |
|---|---|---|---|---|
| A1 | MLX spike — build, window, rectangle | D1 | D2 (13 Aug) | +1 |
| A10 | `config.py` — parser, validation, messages | D2–4 | D1 (11 Aug) | −1 |
| A2 | Framebuffer renderer — cells, walls, entry, exit | D2–4 | D3–4 (14–15 Aug) | on time |
| A3 | Geometry — fit any size, dynamic wall thickness | D2–4 | D4 (15 Aug) | on time |
| A11 | `a_maze_ing.py` — argv, wiring, exit codes | D8–9 | D5 (16 Aug) | −3 |
| A9 | Key hooks, `keys.py`, on-screen legend | D2–7 | D5 (16 Aug) | on time |
| A7a | Path reveal — static draw on `p` | D5–7 | D5 (16 Aug) | on time |
| A2b | 42 glyph colouring | D2–4 | D6 (18 Aug) | +2 |
| A4 | `palette.py` — 6 schemes, distinct 42 colour | D5–7 | D6 (18 Aug) | on time |
| A5 | `animation.py` — `Clock`, `Tween`, `EventStream`, easing | D5–7 | D9 (24 Aug) | +2 |
| A6 | Generation animation over J's step stream | D5–7 | D9 (24 Aug) | +2 |
| A7b | Path animation, reversible mid-flight | D5–7 | D9 (24 Aug) | +2 |
| A8 | Palette cross-fade | D5–7 | D9 (24 Aug) | +2 |
| A12 | Config and CLI error-path tests | D8–9 | D9 (24 Aug) | on time |
| A13 | README — app sections | D8–9 | D9 (24 Aug) | on time |

**Gates.** The Phase 1 gate (window shows a real maze from a real config)
was met on D5, one day past the planned D4. The Phase 2 gate (every
mandatory feature working, both algorithms visibly different when
animated) was met on D9 against a planned D7.

**Where the plan was wrong.**

- **Order flipped on day one.** The plan called for the MLX spike first,
  since it was named the top project risk. `config.py` got written first
  instead — it needed no unknowns. The spike then took two calendar days,
  which is roughly what the plan feared, so the risk call was right even
  though the sequencing was not.
- **Static rendering ran ahead.** D3–D5 covered A2, A3, A9, A11 and a
  static path — the whole Phase 1 scope plus part of Phase 2. Most of it
  landed in one long session on the night of 15–16 Aug (23:01 → 07:41).
  Wiring `a_maze_ing.py` three days early is what made everything after
  it testable end to end.
- **The animation stack slipped as a block.** A5–A8 were planned for
  D5–7 and all landed on D9. They share `Clock` and the loop hook, so
  none of them could ship before that engine existed — splitting them
  across four plan rows implied an independence they never had. They were
  rebased into one push, so the commit timestamps inside that batch are
  all identical and say nothing about the real order.
- **19–21 Aug is missing entirely.** Not a slip in effort, a gap in
  calendar. The plan's day numbers assumed consecutive working days and
  nothing in it flagged what happens when they are not.

**What worked.** The written contract from day one — the `MazeGenerator`
API, the wall-bit convention, the step-event stream — plus J's stub
generator meant the renderer was never blocked. The 42 glyph colouring
was the only task that waited on the other half, and only for two days.

### Planned vs actual — J (`jkarl`)

`PROJECT_PLAN.md` budgeted ~43h across ~10 working days for the library half.
Actual: **7 active days, 24 commits, spread over 15 calendar days**
(11–25 Aug). The effort estimate held; the calendar did not.

Project days below are J's active days, not calendar days:
D1 = 11 Aug · D2 = 14 · D3 = 16 · D4 = 17 · D5 = 18 · D6 = 19 · D7 = 25.
D2 and D4 are single housekeeping commits, but they are counted, because
skipping them would make every later row look further ahead than it was.

| # | Task | Planned | Actual | Δ |
|---|---|---|---|---|
| J1 | Stub generator meeting the §4 contract | D1 | D1 (11 Aug) | on time |
| J2 | Edge-set model + mask serialization | D2–4 | D1 (11 Aug) | −1 |
| J7 | Border walls + entry/exit validation | D2–4 | D1 (11 Aug) | −1 |
| J3 | Union-find + `kruskal()` | D2–4 | D3 (16 Aug) | on time |
| J9 | BFS solver → coords + move string | D2–4 | D3 (16 Aug) | on time |
| J4 | Iterative `dfs()` | D5–7 | D3 (16 Aug) | −2 |
| J5 | Step-event recording for both algorithms | D5–7 | D3 (16 Aug) | −2 |
| J6 | `pattern.py` — "42" mask, size and connectivity checks | D5–7 | D3 (16 Aug) | −2 |
| J10 | Seeded determinism, one RNG threaded through | D5–7 | D3 (16 Aug) | −2 |
| J8 | Braiding for `PERFECT=FALSE` + the 3x3 guard | D5–7 | D5 (18 Aug) | on time |
| J11 | `app/writer.py` — hex rows + metadata block | D2–4 | D5 (18 Aug) | +1 |
| J12 | Package: `pyproject.toml`, wheel build, clean-venv install | D8–9 | D6 (19 Aug) | −2 |
| J13 | `mazegen/usage.md` | D8–9 | D6 (19 Aug) | −2 |
| J14 | pytest invariant suite | D8–9 | D7 (25 Aug) | −1 |
| J15 | README — algorithms, reusable module | D8–9 | D7 (25 Aug) | −1 |
| — | Build and tooling: Makefile, deps, `.gitignore`, `uv.lock` | not in the plan | D1–D6, throughout | unplanned |

**Gates.** The Phase 0 gate — J's stub imports cleanly — was met on D1, as
planned. J's half of the Phase 1 gate came apart in two: correct mazes on D3
(16 Aug), but the valid output file only on D5 (18 Aug), one day past the
planned D4. The Phase 2 gate — DFS, step events, the 42 glyph, braiding, the
3x3 guard, `PERFECT` and seed plumbing — was complete on D5 (18 Aug) against
a planned D7. The Phase 3 gate (the wheel installs into a fresh virtualenv
and `from mazegen import MazeGenerator` works from an unrelated directory)
was met on D6 (19 Aug), two ahead of plan; the other Phase 3 item on J's
list, a green test suite, waited until D7 (25 Aug). Phase 4 is a reading day
and leaves no commits, so the history is silent on it.

**Where the plan was wrong.**

- **The library landed in one commit.** J2–J6, J9 and J10 — seven rows and
  about 22h of estimate — are a single commit on 16 Aug. Splitting them
  across seven plan rows implied checkpoints between them that never
  existed: the edge set, both algorithms, the step stream, the glyph and the
  solver were one design carried through in one sitting, largely because
  §7.1–§7.4 had already settled the hard questions on day one. The cost is
  that there was no intermediate state to hand over — until 16 Aug, A had
  the stub and nothing else, and the day the library existed it existed
  whole.
- **The writer was scheduled as a small row and was actually the Phase 1
  gate.** `app/writer.py` is 3h in the plan with no day attached, but the
  Phase 1 gate demands a valid output file by D4 and §7.9 says to run the
  subject's validation script "as soon as J11 exists — do not save it for
  Phase 3". It landed on 18 Aug, two days after the mazes themselves were
  correct, so for two days there were correct mazes that nothing could check
  against the required format.
- **Build and tooling were never in the estimate.** The layout in §3 assigns
  `Makefile` and `.gitignore` to A and `pyproject.toml` to "shared"; in
  practice J wrote the initial Makefile and `config.txt` on D1 and owned
  every build change afterwards — dependencies and the MLX wheel (16 Aug),
  the clean rule and the output file's gitignore entry (18 Aug), the
  `uv.lock` question twice (14 and 18 Aug), and the `build` target plus the
  package's own venv (19 Aug). Roughly a fifth of J's commits, none of them
  in the 43h. The same gap is why the wheel is `mazegen-0.1.0` rather than
  the `1.0.0` the §10 checklist names: the checklist picked a version before
  anyone had decided to build one.
- **The tests were scheduled after the code and stayed there.** J14 is the
  largest single row in the plan, and its note says "this is where the bugs
  actually are" — yet Phase 3 puts it after everything it tests. It landed
  on 25 Aug, six calendar days after the last library commit and a day after
  A had finished. The commit adds test files and changes no library code, so
  nothing was found late; that is the design holding rather than the
  schedule working. Written alongside J3–J6 the invariants would have been a
  design check. Written at the end they could only be a receipt.
- **The day-number axis was the wrong one.** J used 7 active days spread
  over 15, with the library finished on 19 Aug and the last two rows waiting
  until 25 Aug. Every Phase 3 task is therefore *early* by day index and
  *late* by date at the same time, which is the clearest sign that numbering
  ten consecutive working days was not how this project was ever going to
  run.

**What worked.** The §4.2 stub, 2h on day one, did exactly what the plan
claimed it would: A wired `a_maze_ing.py` to `mazegen` at 00:02 on 16 Aug
and had a non-hardcoded grid on screen the evening before that — both ahead
of the real generator, which landed at 12:21 on 16 Aug. A was never blocked.
Choosing the edge-set representation in the stub rather than after the fact
paid off in the same way: no commit in this history fixes a wall-coherence
bug, a disconnected maze or a 3x3 violation, because those bugs were removed
by construction in §7.1–§7.3 instead of found later. And the two rebalance
valves agreed in §5 — J takes `config.py`, or A takes `writer.py` and the
README assembly — were never needed; the only crossing of the seam in either
direction was a one-line type change in `app/config.py`.

**Tools used:** uv, flake8, mypy, pytest, MiniLibX, git.

## Resources

- [MiniLibX documentation](https://harm-smits.github.io/42docs/libs/minilibx)
- [DFS](https://dev.to/ziskand/maze-generation-with-dfs-3nem)
- [Kruskals algorithm](https://vishald.com/blog/kruskals-maze-generation/)
- Claude to get a better understanding of the algorithm logic

### AI usage

AI was used on the testing side of animation

- `app/palette.py` — the colour schemes are hand-picked, but codes of colors are added to script via AI
- `tests/test_animation.py`, `tests/test_config.py`, `tests/test_cli.py` —
  written with AI.
- `README.md` was written using AI

AI was also used on the generation side:

- The project plan was written using AI, all concepts come from us though
- `tests/frozen_generator.py` was partially written by AI to quickly have a stub for the animation side
- AI was used for testing and debugging the algorithms and the Mazegen class
- `mazegen/usage.md` was written using AI
