"""
The carving algorithms.

Each yields animation events as ``(kind, a, b)`` tuples; generator.py
turns them into Step objects and derives the open edges from them, so
the event stream and the maze can never disagree.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:
    from mazegen.generator import Coord, StepKind

    Neighbours = Callable[[Coord], list[Coord]]
    Event = tuple[StepKind, Coord, "Coord | None"]

__all__ = ["dfs", "kruskal"]


def dfs(
    start: Coord,
    neighbours: Neighbours,
    rng: random.Random,
) -> Iterator[Event]:
    """Randomised depth-first search from *start*.

    Yields a perfect maze over every cell reachable from *start*: each
    cell is entered exactly once, so the opened edges form a spanning
    tree with no cycles.
    """
    visited = {start}
    stack = [start]
    yield ("visit", start, None)

    while stack:
        cell = stack[-1]
        candidates = [n for n in neighbours(cell) if n not in visited]
        if not candidates:
            stack.pop()
            yield ("backtrack", cell, None)
            continue
        chosen = rng.choice(candidates)
        visited.add(chosen)
        yield ("open", cell, chosen)
        yield ("visit", chosen, None)
        stack.append(chosen)


def kruskal(
    cells: frozenset[Coord],
    neighbours: Neighbours,
    rng: random.Random,
) -> Iterator[Event]:
    """Randomised Kruskal over *cells*, merging disjoint sets.

    Shuffles every wall between two cells of *cells*, then walks them in
    order: opens the wall when it joins two different sets ("open"),
    otherwise leaves it ("reject").  Emits "consider" before deciding, so
    the animation can show the wall being weighed.
    """

    parents: dict[Coord, Coord] = {cell: cell for cell in cells}

    def find_parent(cell: Coord) -> Coord:
        """The representative of *cell*'s set, halving the path on the way."""
        while parents[cell] != cell:
            parents[cell] = parents[parents[cell]]
            cell = parents[cell]
        return cell

    def union(pa: Coord, pb: Coord) -> None:
        parents[pa] = pb

    walls: list[tuple[Coord, Coord]] = []
    for cell in cells:
        for n in neighbours(cell):
            if n < cell:
                walls.append((cell, n))
    rng.shuffle(walls)

    for a, b in walls:
        yield ("consider", a, b)
        pa, pb = find_parent(a), find_parent(b)
        if pa == pb:
            yield ("reject", a, b)
        else:
            union(pa, pb)
            yield ("open", a, b)
