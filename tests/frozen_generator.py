"""Frozen copy of ``mazegen/generator.py`` -- a TEST FIXTURE, not app code.

Pinned to commit b4b36cd ("stub mazegenerator with fixed logic").  It
exists so the app-layer tests keep a generator with known, unchanging
behaviour even while the real one is being rewritten with Kruskal and DFS.

Do not import this from ``app/`` or from ``a_maze_ing.py``.  Those must
import ``mazegen`` so that any drift between the contract and the real
generator shows up immediately instead of hiding behind this snapshot.

Refresh it deliberately, never by accident:

    cp mazegen/generator.py tests/frozen_generator.py   # then re-add this
                                                        # header

Original module docstring follows.

    Stub with fixed maze generation.
    Body of generate() to be replaced with kruskal / dfs
"""

from dataclasses import dataclass
from typing import Iterator, Literal

Coord = tuple[int, int]
StepKind = Literal[
    "open", "consider", "reject", "visit", "backtrack", "done"
]

# Wall bit per (dx, dy) step. 1 = wall closed.
_BIT: dict[Coord, int] = {
    (0, -1): 1,   # North
    (1, 0): 2,    # East
    (0, 1): 4,    # South
    (-1, 0): 8,   # West
}
_MOVE: dict[Coord, str] = {
    (0, -1): "N",
    (1, 0): "E",
    (0, 1): "S",
    (-1, 0): "W",
}
_ALL_WALLS = 0xF


@dataclass(frozen=True)
class Step:
    """One event in the generation animation stream."""

    kind: StepKind
    a: Coord
    b: Coord | None = None


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
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError("maze must be at least 2x2")
        if not self._inside(entry, width, height):
            raise ValueError(f"entry {entry} is outside the maze")
        if not self._inside(exit, width, height):
            raise ValueError(f"exit {exit} is outside the maze")
        if entry == exit:
            raise ValueError("entry and exit must be different cells")

        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.perfect = perfect
        self.algorithm = algorithm
        self._seed = 0 if seed is None else seed
        self._open: set[frozenset[Coord]] = set()
        self._steps: list[Step] = []
        self._order: list[Coord] = []
        self.generate()

    @staticmethod
    def _inside(cell: Coord, width: int, height: int) -> bool:
        """Return True if `cell` lies within a width x height grid."""
        x, y = cell
        return 0 <= x < width and 0 <= y < height

    def _serpentine(self) -> list[Coord]:
        """Return every cell in boustrophedon order (a Hamiltonian path)."""
        cells: list[Coord] = []
        for y in range(self.height):
            xs = list(range(self.width))
            if y % 2:
                xs.reverse()
            cells.extend((x, y) for x in xs)
        return cells

    def generate(self) -> None:
        self._open.clear()
        self._steps.clear()
        self._order = self._serpentine()

        previous = self._order[0]
        self._steps.append(Step("visit", previous))
        for cell in self._order[1:]:
            self._steps.append(Step("visit", cell))
            self._open.add(frozenset((previous, cell)))
            self._steps.append(Step("open", previous, cell))
            previous = cell
        self._steps.append(Step("done", self.exit))

    def steps(self) -> Iterator[Step]:
        """Replay the last generation as discrete animation events."""
        return iter(self._steps)

    @property
    def grid(self) -> list[list[int]]:
        """Row-major wall bitmasks. Bit 0=N, 1=E, 2=S, 3=W. 1 = closed."""
        rows = [[_ALL_WALLS] * self.width for _ in range(self.height)]
        for edge in self._open:
            (ax, ay), (bx, by) = tuple(edge)
            rows[ay][ax] &= ~_BIT[(bx - ax, by - ay)]
            rows[by][bx] &= ~_BIT[(ax - bx, ay - by)]
        return rows

    @property
    def solution(self) -> list[Coord]:
        """Shortest path as cells, entry first, exit last."""
        start = self._order.index(self.entry)
        end = self._order.index(self.exit)
        if start <= end:
            return self._order[start:end + 1]
        return self._order[end:start + 1][::-1]

    @property
    def solution_string(self) -> str:
        """The same path as an 'NESW...' move string."""
        path = self.solution
        return "".join(
            _MOVE[(b[0] - a[0], b[1] - a[1])]
            for a, b in zip(path, path[1:])
        )

    @property
    def pattern_cells(self) -> frozenset[Coord]:
        """Cells forming the '42' glyph. Always empty in the stub."""
        return frozenset()

    @property
    def seed(self) -> int:
        """The seed actually used -- always a concrete int."""
        return self._seed
