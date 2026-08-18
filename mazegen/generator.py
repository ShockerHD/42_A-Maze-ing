"""
MazeGenerator: orchestration, the shared vocabulary and step events.
"""

import random
from dataclasses import dataclass
from typing import Iterator, Literal

from mazegen import algorithms, constraints, solver
from mazegen.pattern import glyph_cells, splits_grid

__all__ = [
    "Coord", "Event", "Step", "StepKind", "MazeGenerator",
    "BIT", "BIT_NORTH", "BIT_EAST", "BIT_SOUTH", "BIT_WEST", "ALL_WALLS",
    "MOVE", "edges_to_grid",
]

Coord = tuple[int, int]          # (x, y), x = column, y = row, origin top-left
StepKind = Literal[
    "open", "consider", "reject", "visit", "backtrack", "done"
]

Event = tuple[StepKind, Coord, "Coord | None"]

BIT_NORTH = 1
BIT_EAST = 2
BIT_SOUTH = 4
BIT_WEST = 8
ALL_WALLS = 0xF

# Wall bit per (dx, dy) step. 1 = wall closed.
BIT: dict[Coord, int] = {
    (0, -1): BIT_NORTH,
    (1, 0): BIT_EAST,
    (0, 1): BIT_SOUTH,
    (-1, 0): BIT_WEST,
}
MOVE: dict[Coord, str] = {
    (0, -1): "N",
    (1, 0): "E",
    (0, 1): "S",
    (-1, 0): "W",
}
_DELTAS: tuple[Coord, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def edges_to_grid(
    width: int,
    height: int,
    edges: set[frozenset[Coord]],
) -> list[list[int]]:
    """Row-major wall bitmasks with *edges* opened. 1 = closed.
    """
    rows = [[ALL_WALLS] * width for _ in range(height)]
    for edge in edges:
        (ax, ay), (bx, by) = tuple(edge)
        rows[ay][ax] &= ~BIT[(bx - ax, by - ay)]
        rows[by][bx] &= ~BIT[(ax - bx, ay - by)]
    return rows


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
        algorithm: str = "dfs",   # "kruskal" | "dfs"
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
        self._seed = (
            random.SystemRandom().randrange(2 ** 32) if seed is None else seed
        )
        self._rng = random.Random(self._seed)
        self._open: set[frozenset[Coord]] = set()
        self._steps: list[Step] = []
        self._solution: list[Coord] | None = None
        self._pattern = self._glyph_mask()
        self._free = frozenset(
            (x, y)
            for y in range(height)
            for x in range(width)
            if (x, y) not in self._pattern
        )
        self.generate()

    @staticmethod
    def _inside(cell: Coord, width: int, height: int) -> bool:
        """Return True if `cell` lies within a width x height grid."""
        x, y = cell
        return 0 <= x < width and 0 <= y < height

    def _glyph_mask(self) -> frozenset[Coord]:
        """The '42' cells to keep out of the maze"""
        mask = glyph_cells(self.width, self.height)
        if mask & {self.entry, self.exit}:
            return frozenset()
        if splits_grid(self.width, self.height, mask, self.entry, self.exit):
            return frozenset()
        return mask

    def _neighbours(self, cell: Coord) -> list[Coord]:
        """The in-grid, non-glyph cells orthogonally adjacent to *cell*.

        The single place the glyph is consulted while carving: to an
        algorithm those cells simply do not exist.
        """
        x, y = cell
        return [
            neighbour
            for dx, dy in _DELTAS
            if (neighbour := (x + dx, y + dy)) in self._free
        ]

    def _linked(self, cell: Coord) -> list[Coord]:
        """The neighbours of *cell* reachable through an open wall."""
        return [
            neighbour
            for neighbour in self._neighbours(cell)
            if frozenset((cell, neighbour)) in self._open
        ]

    def _apply(self, events: Iterator[Event]) -> None:
        """Record *events* as steps, opening the walls they announce."""
        for kind, a, b in events:
            self._steps.append(Step(kind, a, b))
            if kind == "open" and b is not None:
                self._open.add(frozenset((a, b)))

    def generate(self) -> None:
        """(Re)generate the maze. Deterministic for a fixed seed."""
        if self.algorithm == "dfs":
            events = algorithms.dfs(self.entry, self._neighbours, self._rng)
        elif self.algorithm == "kruskal":
            events = algorithms.kruskal(
                self._free, self._neighbours, self._rng
            )
        else:
            raise ValueError(f"unknown algorithm {self.algorithm}")

        self._rng.seed(self._seed)
        self._open.clear()
        self._steps.clear()
        self._solution = None

        self._apply(events)
        if not self.perfect:
            self._apply(constraints.braid(
                self._free, self._neighbours, self._open, self._rng
            ))
        self._steps.append(Step("done", self.exit))

    def steps(self) -> Iterator[Step]:
        """Replay the last generation as discrete animation events."""
        return iter(self._steps)

    @property
    def grid(self) -> list[list[int]]:
        """Row-major wall bitmasks. Bit 0=N, 1=E, 2=S, 3=W. 1 = closed."""
        return edges_to_grid(self.width, self.height, self._open)

    @property
    def solution(self) -> list[Coord]:
        """Shortest path as cells, entry first, exit last."""
        if self._solution is None:
            self._solution = solver.shortest_path(
                self.entry, self.exit, self._linked
            )
        return self._solution

    @property
    def solution_string(self) -> str:
        """Solution as a NESW string"""
        path = self.solution
        return "".join(
            MOVE[(b[0] - a[0], b[1] - a[1])]
            for a, b in zip(path, path[1:])
        )

    @property
    def pattern_cells(self) -> frozenset[Coord]:
        """Cells forming the '42' glyph. Empty if the glyph was skipped."""
        return self._pattern

    @property
    def seed(self) -> int:
        """The seed actually used -- always a concrete int."""
        return self._seed
