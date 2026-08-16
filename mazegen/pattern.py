"""
The "42" glyph mask
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mazegen.generator import Coord

__all__ = [
    "GLYPH", "GLYPH_WIDTH", "GLYPH_HEIGHT", "MARGIN",
    "MIN_WIDTH", "MIN_HEIGHT",
    "fits", "glyph_cells", "splits_grid",
]

# '#' = wall cell removed from the graph, '.' = ordinary maze cell.
#
# No '.' may be fully enclosed by '#'.
# If fully enclosed, it won't be drawn.

GLYPH = (
    "#.#.###",
    "#.#...#",
    "###.###",
    "..#.#..",
    "..#.###",
)

# GLYPH = (
#     "###.###",
#     "..#.###",
#     "###.###",
#     "#...###",
#     "###.###",
# )

GLYPH_WIDTH = len(GLYPH[0])
GLYPH_HEIGHT = len(GLYPH)


MARGIN = 2
MIN_WIDTH = GLYPH_WIDTH + 2 * MARGIN
MIN_HEIGHT = GLYPH_HEIGHT + 2 * MARGIN


def fits(width: int, height: int) -> bool:
    """Return True if a width x height maze has room for the glyph."""
    return width >= MIN_WIDTH and height >= MIN_HEIGHT


def glyph_cells(width: int, height: int) -> frozenset[Coord]:
    """The centred glyph cells, or an empty mask if the maze is too small."""
    if not fits(width, height):
        return frozenset()
    origin_x = (width - GLYPH_WIDTH) // 2
    origin_y = (height - GLYPH_HEIGHT) // 2
    return frozenset(
        (origin_x + x, origin_y + y)
        for y, row in enumerate(GLYPH)
        for x, char in enumerate(row)
        if char == "#"
    )


def splits_grid(
    width: int,
    height: int,
    mask: frozenset[Coord],
    entry: Coord,
    exit: Coord,
) -> bool:
    """Return True if *mask* cuts the remaining cells into separate pieces.

    Denies applying a mask if the glyph encloses any maze cells fully.
    Irrelevant for default 42 logo
    """
    free = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in mask
    }
    if entry not in free or exit not in free:
        return True

    seen = {entry}
    stack = [entry]
    while stack:
        x, y = stack.pop()
        for neighbour in ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)):
            if neighbour in free and neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)

    return seen != free
