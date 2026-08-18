"""

Colour schemes for the renderer.

"""

from dataclasses import dataclass

__all__ = ["Palette", "DARK", "LIGHT", "NEON", "PALETTES", "DEFAULT"]


@dataclass(frozen=True)
class Palette:
    """One colour scheme. Every element on screen takes its colour here."""

    name: str
    bg: int
    wall: int
    floor: int
    entry: int
    exit: int
    path: int
    glyph: int
    legend: int


DARK = Palette(
    name="dark",
    bg=0xFF1E1E28,
    wall=0xFFE0E0E8,
    floor=0xFF2A2A38,
    entry=0xFF4CAF50,
    exit=0xFFE05252,
    path=0xFF3A6EA5,
    glyph=0xFF3FA796,
    legend=0xFFA0A0B0,
)

LIGHT = Palette(
    name="light",
    bg=0xFFF4F4F2,
    wall=0xFF2E3440,
    floor=0xFFFFFFFF,
    entry=0xFF2E7D32,
    exit=0xFFC62828,
    path=0xFF1565C0,
    glyph=0xFF00796B,
    legend=0xFF55555F,
)

NEON = Palette(
    name="neon",
    bg=0xFF07070F,
    wall=0xFF00F5FF,
    floor=0xFF12122A,
    entry=0xFF39FF14,
    exit=0xFFFF2079,
    path=0xFFFFD400,
    glyph=0xFFB026FF,
    legend=0xFF00F5FF,
)

PALETTES: tuple[Palette, ...] = (DARK, LIGHT, NEON)
DEFAULT = DARK
