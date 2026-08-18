"""

Logic for making imperfect maze

"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:
    from mazegen.generator import Coord, StepKind

    Neighbours = Callable[[Coord], list[Coord]]
    Edges = set[frozenset[Coord]]
    Event = tuple[StepKind, Coord, "Coord | None"]

__all__ = ["braid", "opens_3x3"]


def _block_is_open(top_left: Coord, edges: Edges) -> bool:
    """True if the 3x3 block at *top_left* has all twelve edges open."""
    x0, y0 = top_left
    for y in range(y0, y0 + 3):
        for x in range(x0, x0 + 3):
            right = frozenset(((x, y), (x + 1, y)))
            below = frozenset(((x, y), (x, y + 1)))
            if x + 1 < x0 + 3 and right not in edges:
                return False
            if y + 1 < y0 + 3 and below not in edges:
                return False
    return True


def opens_3x3(edge: frozenset[Coord], edges: Edges) -> bool:
    """True if adding *edge* to *edges* completes a fully open 3x3 block."""
    (ax, ay), (bx, by) = tuple(edge)
    probe = edges | {edge}
    for y0 in range(max(ay, by) - 2, min(ay, by) + 1):
        for x0 in range(max(ax, bx) - 2, min(ax, bx) + 1):
            if _block_is_open((x0, y0), probe):
                return True
    return False


def braid(
    cells: frozenset[Coord],
    neighbours: Neighbours,
    edges: Edges,
    rng: random.Random,
) -> Iterator[Event]:
    """Open a second wall at every dead end of the maze in *edges*."""
    for cell in sorted(cells):
        linked = [n for n in neighbours(cell) if frozenset((cell, n)) in edges]
        if len(linked) != 1:
            continue
        options = [n for n in neighbours(cell) if n != linked[0]]
        rng.shuffle(options)
        for neighbour in options:
            edge = frozenset((cell, neighbour))
            if opens_3x3(edge, edges):
                continue
            edges.add(edge)
            yield ("open", cell, neighbour)
            break
