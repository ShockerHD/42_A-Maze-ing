*This project has been created as part of the 42 curriculum by TODO-LOGIN-J, TODO-LOGIN-A.*

<!-- ^ Chapter VII requires this exact line, italicised, with real 42
     logins. Replace both placeholders before turning the project in. -->

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
| `ALGORITHM` | `kruskal` or `dfs` | no | `kruskal` | Which algorithm carves the maze |

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

<!-- TODO (J): Kruskal and iterative DFS, why each was chosen, union-find,
     the braiding pass, the 3x3 open-area argument, and BFS for the
     shortest path. -->

## Reusable module

<!-- TODO (J): installing the wheel, the MazeGenerator API, a worked
     example, and how to get at the solution. See mazegen/usage.md, which
     already covers this ground. -->

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
| Algorithms & library | TODO-LOGIN-J | `mazegen/`, the solver, packaging, the output writer |
| Visualization & app shell | TODO-LOGIN-A | `app/`, the renderer, animations, config, CLI |

The split follows the library/app seam described above, agreed on day one as
a written contract — the `MazeGenerator` API, the wall-bit convention, and
the step-event stream — so that both halves could be built in parallel. A
stub generator satisfying that contract existed on day one, which is what
kept the renderer from ever being blocked on the algorithms.

<!-- TODO (both): planned vs actual schedule, what worked, what to
     improve. -->

**Tools used:** uv, flake8, mypy, pytest, MiniLibX, git.

## Resources

- [MiniLibX documentation](https://harm-smits.github.io/42docs/libs/minilibx)
- Kruskal's algorithm and union-find <!-- TODO (J): the references you used -->

### AI usage

<!-- This disclosure is mandatory and must be specific: which tasks, which
     files. Extend it with J's usage before turning in. -->

AI was used on the testing side of animation

- `app/palette.py` — the colour schemes are hand-picked, but codes of colors are added to script via AI
- `tests/test_animation.py`, `tests/test_config.py`, `tests/test_cli.py` —
  written with AI.
- `README.md` was written using AI

<!-- TODO (J): your own AI usage, or a line stating you used none. -->
