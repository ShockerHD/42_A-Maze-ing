"""

Colour schemes for the renderer.

"""

from dataclasses import dataclass

__all__ = [
    "Palette", "DARK", "LIGHT", "NEON",
    "SPRING", "SUMMER", "AUTUMN", "WINTER",
    "PALETTES", "DEFAULT",
]


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

# The seasonal schemes come from ColorHunt, four colours each. Those four
# take the visible roles (walls, entry, exit, path); background, floor and
# legend are darker or lighter shades derived from them.

# colorhunt.co/palette/8b2626ef6905f1e5a1486c2f
AUTUMN = Palette(
    name="autumn",
    bg=0xFF3E1111,
    wall=0xFFF1E5A1,
    floor=0xFF681C1C,
    entry=0xFF73AC4B,
    exit=0xFFEF6905,
    path=0xFFD9A441,
    glyph=0xFFE4746B,
    legend=0xFFA8A070,
)

# colorhunt.co/palette/df301cff9100fff1d100b7cd
SUMMER = Palette(
    name="summer",
    bg=0xFFFFF1D1,
    wall=0xFF005B66,
    floor=0xFFFFFFFF,
    entry=0xFF00849A,
    exit=0xFFDF301C,
    path=0xFFCC6A00,
    glyph=0xFF9C2214,
    legend=0xFF4A4038,
)

# colorhunt.co/palette/5f8b4cffddabff9a9a945034
SPRING = Palette(
    name="spring",
    bg=0xFF422417,
    wall=0xFFFFDDAB,
    floor=0xFF683824,
    entry=0xFF8FBF6F,
    exit=0xFFFF9A9A,
    path=0xFF98DE7A,
    glyph=0xFFF09A6A,
    legend=0xFFCBB08A,
)

# colorhunt.co/palette/0c2c55296374629fadededce
# All four are cool, so entry and exit would be hard to tell apart -- the
# exit borrows a frost rose to keep the two endpoints distinct.
WINTER = Palette(
    name="winter",
    bg=0xFF081A30,
    wall=0xFFEDEDCE,
    floor=0xFF0C2C55,
    entry=0xFF629FAD,
    exit=0xFFC97B84,
    path=0xFF7FD4C4,
    glyph=0xFFB8CFE0,
    legend=0xFF9FB4C4,
)

# Cycling order for the C key.
PALETTES: tuple[Palette, ...] = (
    DARK, LIGHT, NEON, SPRING, SUMMER, AUTUMN, WINTER,
)
DEFAULT = DARK
