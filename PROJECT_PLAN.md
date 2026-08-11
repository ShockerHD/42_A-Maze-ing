# A-Maze-ing — Project Plan

**Team:** J (algorithms & library) · A (visualization & app shell)
**Stack:** Python 3.10+, uv, MinilibX + its bundled Python wrapper
**Algorithms:** Kruskal (union-find) + iterative DFS (recursive backtracker)
**Visuals:** generation animation, path show/hide, multiple palettes, live colour switching

Day numbers assume ~10 working days. The *gates* between phases matter more than the
absolute dates.

---

## 1. The seam: library vs app

Everything in the split follows one architectural line, and it is worth stating up front
because it is what makes the division defensible at evaluation:

> **`mazegen/` never reads a file, never prints, never draws.** It takes typed
> parameters and hands back data structures. Everything that touches the filesystem,
> the terminal, or the screen lives in `app/`.

- **J owns the library layer** — generation, constraints, solving, and the data the
  renderer consumes.
- **A owns the app layer** — config parsing, CLI, error reporting, and the MLX window.

This is also the reusability requirement (Chapter VI) satisfied by construction: the
package is import-clean because it was never allowed to depend on the app.

---

## 2. Scope & choices

| Requirement | Our choice |
|---|---|
| Generation algorithms | **Kruskal** and **iterative DFS**, selectable via `ALGORITHM=` → also covers the "multiple algorithms" bonus |
| Rendering | **MinilibX** graphical window, via the wrapper vendored in [mlx/](mlx/) |
| Generation animation | **Required feature, not a bonus** — the generator emits a step-event stream that the renderer replays |
| Path display | Show/hide toggle, animated reveal, reversible mid-flight |
| Colours | ≥4 palettes, cycled live, cross-faded; the "42" glyph gets its own colour |
| Solver | BFS — the subject demands the *shortest* path, so DFS won't do |
| Non-perfect mode | Braiding pass over the spanning tree |

---

## 3. Repository layout

```
.
├── a_maze_ing.py                    # entry point — A
├── config.txt                       # default config — A
├── pyproject.toml                   # app deps (uv sync) — shared
├── Makefile / .gitignore            # A
├── README.md                        # assembled by J, both write sections
├── mazegen-1.0.0-py3-none-any.whl   # built artifact, committed at root — J
├── mazegen/                         # the reusable package — J
│   ├── __init__.py                  #   exports MazeGenerator
│   ├── generator.py                 #   MazeGenerator, orchestration, step events
│   ├── algorithms.py                #   kruskal(), dfs()
│   ├── pattern.py                   #   "42" glyph mask
│   ├── constraints.py               #   braiding + 3x3 open-area guard
│   ├── solver.py                    #   BFS shortest path
│   ├── pyproject.toml               #   package build metadata
│   └── USAGE.md                     #   module documentation
├── app/                             # not part of the package
│   ├── config.py                    #   KEY=VALUE parser + validation — A
│   ├── writer.py                    #   hex output file — J
│   ├── palette.py                   #   colour schemes — A
│   ├── animation.py                 #   tween/scheduler engine — A
│   ├── render.py                    #   window, framebuffer, draw loop — A
│   └── keys.py                      #   key hooks + HUD legend — A
├── mlx/                             # vendored MinilibX (upstream, do not edit)
└── tests/                           # pytest — J owns generator tests, A owns app tests
```

---

## 4. The shared contract — agree on this *before* splitting

Write this together on Day 1, commit it, and treat changes as requiring both sign-offs.
It is the only thing standing between you and two incompatible halves on Day 8.

```python
# mazegen/generator.py

Coord = tuple[int, int]          # (x, y), x = column, y = row, origin top-left

class MazeGenerator:
    def __init__(
        self,
        width: int,
        height: int,
        entry: Coord,
        exit: Coord,
        perfect: bool = True,
        seed: int | None = None,
        algorithm: str = "kruskal",   # "kruskal" | "dfs"
    ) -> None: ...

    def generate(self) -> None:
        """(Re)generate the maze. Deterministic for a fixed seed."""

    @property
    def grid(self) -> list[list[int]]:
        """Row-major wall bitmasks. Bit 0=N, 1=E, 2=S, 3=W. 1 = wall closed."""

    @property
    def solution(self) -> list[Coord]:
        """Shortest path as cells, entry first, exit last."""

    @property
    def solution_string(self) -> str:
        """The same path as an 'NESW...' move string."""

    @property
    def pattern_cells(self) -> frozenset[Coord]:
        """Cells forming the '42' glyph (all walls closed). Empty if skipped."""

    @property
    def seed(self) -> int:
        """The seed actually used — always a concrete int, even if None was passed."""

    def steps(self) -> Iterator[Step]:
        """Replay generation as discrete events, for the animation. See below."""
```

**Bit convention, written down once so nobody guesses:**

| Bit | Value | Direction | Delta (dx, dy) |
|---|---|---|---|
| 0 | 1 | North | (0, −1) |
| 1 | 2 | East | (+1, 0) |
| 2 | 4 | South | (0, +1) |
| 3 | 8 | West | (−1, 0) |

`1` = wall present (closed). A fully-walled cell is `0xF`.

### 4.1 The step-event stream (this is the interface that will bite you)

Because the generation animation is a required feature, it is a *contract* item, not
something A bolts on later. J emits events; A decides how to draw them. Neither side
needs to know the other's internals.

```python
@dataclass(frozen=True)
class Step:
    kind: Literal["open", "consider", "reject", "visit", "backtrack", "done"]
    a: Coord                  # the cell acted on
    b: Coord | None = None    # the neighbour, for edge events
```

- **Kruskal** emits `consider` (edge popped), then `open` (merged two trees) or
  `reject` (already the same tree). The animation looks like separate regions fusing.
- **DFS** emits `visit`, `open`, and `backtrack`. The animation looks like a snake
  carving and retreating.

The two algorithms therefore *look* completely different on screen. That is a genuinely
good thing to demo — it makes the algorithmic difference visible rather than described,
and it is excellent defense material for both of you.

**Design rule:** `steps()` must be replayable without re-randomising. Simplest correct
approach: `generate()` records the event list internally, `steps()` yields from it. Do
not make the animation drive generation — A must never be forced to run the renderer to
get a maze, or headless mode and the tests break.

### 4.2 Day-1 deliverable from J

A stub `MazeGenerator` that returns a hardcoded 5×5 maze plus a handful of fake steps,
satisfying the full contract. A builds the entire renderer against this stub and is
**never blocked on J**. This single artifact is what makes a parallel split work.

---

## 5. Work split

### J — algorithms, solver, library, packaging

| # | Task | Est. | Notes |
|---|---|---|---|
| J1 | Stub generator meeting §4 | 2h | Day 1, unblocks A entirely |
| J2 | Edge-set grid model + mask serialization | 3h | See §7.1 — kills the wall-coherence bug class |
| J3 | Union-find + `kruskal()` | 4h | Seeded shuffle of the edge list |
| J4 | Iterative `dfs()` | 3h | Explicit stack, no recursion limit |
| J5 | Step-event recording for both algorithms | 3h | §4.1 |
| J6 | `pattern.py` — "42" mask, size check, connectivity check | 4h | Runs *before* generation, see §7.2 |
| J7 | Border walls + entry/exit validation | 2h | Entry/exit are cells, not gaps |
| J8 | Braiding for `PERFECT=False` + 3×3 guard | 4h | §7.3 |
| J9 | BFS solver → coords + move string | 3h | |
| J10 | Seeded determinism, one RNG threaded through | 2h | §7.4 |
| J11 | `app/writer.py` — hex rows + metadata block | 3h | J owns the bit convention, so J owns the writer |
| J12 | Package: `pyproject.toml`, wheel build, clean-venv install test | 3h | |
| J13 | `mazegen/USAGE.md` | 2h | Instantiate / params / structure + solution |
| J14 | pytest invariant suite | 5h | §8 — this is where the bugs actually are |
| J15 | README: algorithms, why, reusable module + assembly | 3h | |
| | **Total** | **~43h** | |

### A — MLX renderer, animation, palettes, app shell

| # | Task | Est. | Notes |
|---|---|---|---|
| A1 | Build MinilibX, import the wrapper, open a window, draw a rectangle | 4h | Day 1 spike, see §7.5 — top project risk |
| A2 | Framebuffer renderer: walls, entry, exit, 42 cells | 6h | §7.6 — write into the image buffer, never pixel-by-pixel |
| A3 | Geometry: fit any WIDTH×HEIGHT into the window, integer cell size | 3h | Handle 5×5 and 60×40 without special-casing |
| A4 | `palette.py` — ≥4 schemes, distinct 42 colour | 3h | |
| A5 | `animation.py` — scheduler, dt from the loop hook, easing | 4h | §7.7 |
| A6 | **Generation animation** consuming J's step stream | 5h | Pace by events-per-frame, not per-frame-one-event |
| A7 | Path reveal/hide animation, interruptible | 4h | |
| A8 | Palette cross-fade | 2h | RGB lerp + smoothstep |
| A9 | Key hooks + on-screen legend | 3h | Regenerate / path / colours / replay / quit |
| A10 | `config.py` — parser, validation, clear messages | 4h | §7.8 — more traps than it looks |
| A11 | `a_maze_ing.py` — argv, wiring, exit codes, error paths | 3h | Never a traceback |
| A12 | Error-path tests | 2h | §8 |
| A13 | README: config format, visuals, controls, bonuses | 3h | |
| | **Total** | **~42h** | |

### Shared (both, together)

| Task | Est. | Notes |
|---|---|---|
| §4 contract + repo skeleton | 2h | Day 1, in one sitting, in person |
| Cross-review walkthroughs | 4h | Phase 4 — non-negotiable, see §6 |
| Team/planning README section | 1h | Roles, planned vs actual, tools |

**Balance notes.** The totals are within a couple of hours, but estimates lie, so agree
on these **rebalance valves** now rather than negotiating them at 2am on Day 8:

- If **A runs behind** (most likely — MLX is the unknown): J takes `config.py` (A10) and
  the error-path tests (A12). That moves ~6h and flips the split to roughly 49/36.
- If **J runs behind** (likely cause: the 42 glyph interacting badly with connectivity):
  A takes `writer.py` (J11) and the README assembly (part of J15), ~5h.
- The generation animation (A6) is the one feature where both are on the hook. If the
  step stream is late, A ships a placeholder that animates a plain flood-fill so the
  renderer is still exercised.

Raw algorithmic difficulty sits with J; fiddly-integration difficulty sits with A. Those
are different kinds of hard and they do not compress the same way — J's tasks are mostly
"think, then it works", A's are mostly "it works, but it flickers". Plan for A to spend
more wall-clock time debugging things that are not conceptually hard.

---

## 6. Phases & gates

### Phase 0 — Foundation (Day 1, together)
- Repo skeleton, flake8/mypy config, branch strategy, `uv sync` works for both
- Write and commit §4 (contract + step events)
- J ships the stub generator · A ships the MLX spike
- **Gate:** A can open a window and draw a rectangle; J's stub imports cleanly.
  *If the MLX spike fails, decide today* — this is the last cheap moment to fall back to
  ASCII rendering, which the subject accepts as an equal alternative.

### Phase 1 — Vertical slice (Days 2–4)
- J: edge-set grid, Kruskal, border walls, BFS solver → a real perfect maze
- A: config parser, static render of a real maze, key hook skeleton
- **Gate (end of Day 4):** `make run` writes a valid output file *and* opens a window
  showing that same maze. One algorithm, no animation, no 42.

### Phase 2 — Feature complete (Days 5–7)
- J: DFS, step events, 42 pattern, braiding, 3×3 guard, `PERFECT`, seed plumbing
- A: palettes, animation engine, generation animation, path reveal/hide, cross-fade
- **Gate (end of Day 7):** every mandatory requirement demonstrably works, both
  algorithms selectable and visibly different when animated, 42 visible in a distinct
  colour, non-perfect mode passes the constraint checks.

### Phase 3 — Packaging & hardening (Days 8–9)
- J: wheel build, clean-venv install test, `USAGE.md`, test suite green
- A: error paths (malformed config, missing file, impossible dimensions, entry == exit,
  entry inside the glyph, unwritable output), README sections
- Both: `make lint` clean, then try `make lint-strict`
- **Gate:** the wheel installs into a fresh virtualenv and `from mazegen import
  MazeGenerator` works from an unrelated directory.

### Phase 4 — Cross-review & defense prep (Day 10)
The evaluation can ask *either* of you about *any* file, and "my partner wrote that" is
a failing answer. Budget the whole day.

- **J walks A through:** union-find, why Kruskal needs it, the braiding pass, the 3×3
  argument in §7.3, BFS vs DFS for shortest path
- **A walks J through:** the config parser, the framebuffer write path, the loop-hook
  timing model, how an animation is interrupted mid-flight
- Rehearse the "small modification" step (Chapter IX): add a palette, rebind a key, add a
  config key, change the solver's tie-breaking, invert the 42 glyph colour
- Final checklist (§10)

---

## 7. Technical notes & known traps

### 7.1 Store edges, derive masks
Keep the maze internally as `open_edges: set[frozenset[Coord]]` — undirected edges
between adjacent cells. Serialize to per-cell bitmasks only at the boundary (the `grid`
property and the writer). It is then *structurally impossible* for cell A to be open
eastward while cell B is closed westward, which is an explicit validity requirement and
a classic source of silent, hard-to-find bugs.

### 7.2 Carve the "42" *before* generating
Fully-closed cells are cells removed from the graph. Carving them afterwards tears holes
in the spanning tree and breaks connectivity. Order of operations:

1. Compute the glyph mask.
2. If `WIDTH`/`HEIGHT` are too small, print the error and use an empty mask — the subject
   explicitly permits skipping the pattern.
3. Verify entry and exit are outside the mask, and that the *unmasked* cells are still
   connected — a badly placed glyph can cut the grid in two.
4. Run Kruskal/DFS over the unmasked cells only.

Start by requiring roughly `WIDTH ≥ 11` and `HEIGHT ≥ 9` (a 7×5 glyph plus a 1-cell
margin) and tune once the glyph is drawn.

### 7.3 The 3×3 constraint is free in perfect mode
A 3×3 fully-open block has 9 cells and 12 internal open edges. A spanning tree over 9
cells has exactly 8. So any 3×3 open area implies a cycle, and a perfect maze has none.
**Only braiding can violate the constraint.** Implement the detector as a guard *inside*
the braiding loop — reject any wall removal that would complete a 3×3 opening — rather
than as a global post-pass. Simpler, and it cannot fail. Know this argument for the
defense; it is the kind of reasoning evaluators like to poke at.

### 7.4 Seeding
One `random.Random(seed)` created in `__init__`, passed to everything that makes a
choice: edge shuffling, DFS neighbour order, braiding. If `seed is None`, draw one from
`random.SystemRandom` and **store it**, so the UI can display it and a good-looking maze
can be reproduced afterwards. `SEED=` and `ALGORITHM=` are optional config keys.

### 7.5 MLX: what is actually vendored here
[mlx/](mlx/) is the official MinilibX with a Python wrapper at
`mlx/python/src/mlx/mlx.py`, exposing the classic API: `mlx_init`, `mlx_new_window`,
`mlx_new_image`, `mlx_get_data_addr`, `mlx_put_image_to_window`, `mlx_loop_hook`,
`mlx_key_hook`, `mlx_loop`, `mlx_loop_exit`. There is no ctypes work to do — that job is
already done, which removes what would otherwise be the project's biggest risk.

Two things that *are* still risks:

- **It is Linux-only.** The wrapper loads `libmlx.so`, and upstream requires vulkan, xcb,
  xcb-keysyms, bsd and zip. It is not built yet in this repo, and it will not build or
  load on macOS. Plan to develop the renderer on a school machine, or keep the ASCII
  renderer as the path of record and treat MLX as the bonus.
- **Import path.** [a_maze_ing.py](a_maze_ing.py) currently does
  `from mlx.python.src.mlx import Mlx`, which reaches into the vendored tree. Upstream
  intends `pip install mlx-2.2-py3-none-any.whl` (built by `mlx/pybuild.sh`) and then
  `from mlx import Mlx`. Pick one on Day 1 and write it down — if you go the wheel route,
  it belongs in `pyproject.toml` so `uv sync` handles it.

Also: `Ctrl-C` does not interrupt `mlx_loop` from Python (upstream notes this — use
`Ctrl-\`). Make sure a key binding exits cleanly via `mlx_loop_exit`, or every test run
becomes a fight with the terminal.

### 7.6 Drawing: write into the image buffer
`mlx_get_data_addr` returns `(memoryview, bits_per_pixel, size_line, format)` — a
writable `memoryview` over the image's pixels. That is the fast path, and it is nicer
than the C version: build each frame as a `bytearray` and assign it in one slice, or
write row slices. Never draw with `mlx_pixel_put` per pixel — one ctypes call per pixel
over a 600×600 window is 360,000 calls a frame and will not hold any usable frame rate.

Sketch:

```python
buf, bpp, size_line, fmt = mlx.mlx_get_data_addr(img)
frame = bytearray(size_line * height)   # rebuild or patch each frame
# ... paint into frame ...
buf[:] = frame                          # single bulk copy
mlx.mlx_put_image_to_window(mlx_ptr, win, img, 0, 0)
```

Confirm `bits_per_pixel` and `size_line` at runtime rather than assuming 32bpp and
`width * 4` — `size_line` frequently includes padding.

### 7.7 Animation model
All animation state advances inside `mlx_loop_hook`. A `time.sleep()` in a hook freezes
the window and drops key events — the hook must return promptly, every time.

Model each animation as an object with `update(dt: float) -> bool` (returns `True` when
finished) and `progress` in `[0, 1]`. Keep a list of active animations in renderer state.

- **Generation:** consume `steps()` at *N events per frame*, computed from a target
  duration, so a 20×15 maze and a 60×40 maze both finish in about the same wall-clock
  time. One event per frame looks fine at 20×15 and takes forever at 60×40.
- **Path reveal:** `visible = ceil(progress * len(path))`. Hiding runs the same tween
  backwards. Make it interruptible — pressing the toggle mid-reveal must invert from the
  *current* progress, not restart from the end.
- **Palette fade:** lerp each channel, ease `t` with smoothstep (`t*t*(3-2*t)`). Looks
  noticeably better than linear for very little work.
- Keep a `dt` clock from `time.monotonic()` inside the hook. Do not assume a fixed frame
  interval; MLX will not give you one.

### 7.8 Config parsing traps
The current [config.txt](config.txt) already contains one:

```
ALGORITHM=dfs #kruskals
```

The subject only defines lines *starting* with `#` as comments. Parsed naively, that
value is `"dfs #kruskals"` and algorithm selection silently fails. Decide explicitly
whether trailing comments are supported — if yes, strip at the first unescaped `#` and
document it in the README; if no, remove it from the default config. Either is fine;
silently doing neither is not. Other cases to pin down: `PERFECT=TRUE` vs `True` vs `1`
(accept case-insensitively), whitespace around `=`, empty values, duplicate keys,
unknown keys (warn, don't crash), and blank lines.

### 7.9 Output file details that get missed
- A blank line separates the grid from the three metadata lines.
- Entry and exit are written as `x,y`, each on its own line.
- The path is the `NESW` move string, not coordinates.
- Every line ends with `\n`, including the last.
- Hex digits uppercase, one per cell, one row per line, no separators.

Run the validation script shipped with the subject as soon as J11 exists — do not save it
for Phase 3.

---

## 8. Test plan (pytest — not graded, but this is where the bugs are)

**Generator invariants (J), across many seeds and sizes:**
- Wall coherence: adjacent cells always agree about the wall between them
- Border: every outer wall closed
- Connectivity: every non-pattern cell reachable from entry
- Perfect mode: exactly one simple path entry→exit (or assert `edges == cells - 1` on the
  connected component)
- No 3×3 fully-open block, in both perfect and braided modes
- Determinism: same seed + params ⇒ byte-identical output file
- Solver: path crosses no walls, and its length equals the BFS distance
- Step stream: replaying every `open` event reconstructs exactly the final edge set —
  this one test catches nearly every possible animation/generation divergence

**App error paths (A):** missing file, unreadable file, missing key, duplicate key,
non-integer value, `WIDTH=0`, negative dimensions, entry out of bounds, entry == exit,
entry inside the glyph, unknown algorithm name, unwritable output path. Each must print a
clear message and exit non-zero, with no traceback.

---

## 9. README.md outline (maps 1:1 to Chapter VII)

```markdown
*This project has been created as part of the 42 curriculum by <login-J>, <login-A>.*

# A-Maze-ing
## Description
## Instructions            (uv, make install / run / lint, controls)
## Configuration file      (every key, types, defaults, comment rules, full example)
## Algorithms              (Kruskal, DFS — and why we chose them)          [J]
## Reusable module         (mazegen: install, API, example, solution access) [J]
## Visual representation   (MLX, palettes, animations, key bindings)       [A]
## Bonuses                 (multiple algorithms, generation animation)     [A]
## Team & project management
    - Roles (J: algorithms/library · A: visualization/app)
    - Planned vs actual schedule
    - What worked / what to improve
    - Tools used (uv, flake8, mypy, MinilibX)
## Resources               (references + explicit AI usage: which tasks, which files)
```

The AI-usage disclosure is mandatory and must be specific — name the tasks and the files.
Vagueness there reads badly at the defense.

---

## 10. Submission checklist

- [ ] `a_maze_ing.py` at repo root, exact filename
- [ ] `config.txt` default config committed and actually parseable
- [ ] `mazegen-1.0.0-py3-none-any.whl` (or `.tar.gz`) at repo root
- [ ] Everything needed to rebuild the wheel from source, in-repo
- [ ] `Makefile` with `install`, `run`, `debug`, `clean`, `lint`, `lint-strict`
- [ ] `.gitignore` excludes `__pycache__`, `.mypy_cache`, `.venv`, `dist/`, `build/`, `*.egg-info`
- [ ] `README.md` complete, first line italicised and exact
- [ ] `make lint` clean
- [ ] Output file passes the provided validation script
- [ ] Fresh clone → `make install` → `make run` works
- [ ] Fresh venv → `pip install ./mazegen-*.whl` → import from an unrelated directory
- [ ] Both of you can explain **every** file

---

## 11. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| `libmlx.so` won't build/load on the dev machine (macOS) | **High** | Day-1 spike; develop on a school Linux box, or make ASCII the path of record |
| Generation animation contract lands late | High | It's in §4 on Day 1, not negotiated in Phase 2 |
| Python render loop too slow | Medium | Buffer + single slice copy from the start, not as a later optimisation |
| 42 glyph disconnects the maze | Medium | Connectivity check on the unmasked graph *before* generating |
| Braiding violates the 3×3 rule | Medium | Guard inside the braid loop, not a post-pass |
| Config parser accepts the trailing-`#` value silently | Low | §7.8 — decide the rule and test it |
| One person can't explain the other's code | **High** | Phase 4 cross-review is non-negotiable |
| Contract drift between J and A | Medium | §4 is committed; changes need both signatures |
