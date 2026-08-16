"""
Shortest path through a finished maze.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from mazegen.generator import Coord

    Linked = Callable[[Coord], list[Coord]]

__all__ = ["shortest_path"]


def shortest_path(start: Coord, goal: Coord, linked: Linked) -> list[Coord]:
    """
    Breadth-first search to get shortest path from entry to exit.

    Raises ValueError if *goal* cannot be reached.
    """
    parents: dict[Coord, Coord | None] = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        for neighbour in linked(cell):
            if neighbour not in parents:
                parents[neighbour] = cell
                queue.append(neighbour)

    if goal not in parents:
        raise ValueError(f"{goal} is unreachable from {start}")

    path: list[Coord] = []
    cursor: Coord | None = goal
    while cursor is not None:
        path.append(cursor)
        cursor = parents[cursor]
    path.reverse()
    return path
