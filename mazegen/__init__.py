"""Maze generation"""

from mazegen.generator import (
    ALL_WALLS,
    BIT,
    BIT_EAST,
    BIT_NORTH,
    BIT_SOUTH,
    BIT_WEST,
    MOVE,
    Coord,
    MazeGenerator,
    Step,
    StepKind,
    edges_to_grid,
)

__all__ = [
    "ALL_WALLS", "BIT", "BIT_EAST", "BIT_NORTH", "BIT_SOUTH", "BIT_WEST",
    "MOVE", "Coord", "MazeGenerator", "Step", "StepKind", "edges_to_grid",
]
__version__ = "0.1.0"
