"""

The font sheet the renderer draws its text with.


"""

from pathlib import Path
from typing import Any

__all__ = ["GLYPH_W", "GLYPH_H", "Font"]

SHEET = Path(__file__).resolve().parent.parent / "assets" / "font.png"

GLYPH_W = 10
GLYPH_H = 20
SLOT_W = 12  # the cell a glyph sits in, wider than the glyph itself

FIRST = 32  # the sheet starts at space
COUNT = 95  # ... and runs to '~'
FALLBACK = ord("?")  # what stands in for anything that is not on the sheet

INK = 0  # the sheet is grey, so any colour byte of a pixel will do


class Font:

    def __init__(self, m: Any, mlx: Any) -> None:
        img, width, height = m.mlx_png_file_to_image(mlx, str(SHEET))
        if img is None:
            raise SystemExit(f"cannot read the font sheet {SHEET}")
        if width < COUNT * SLOT_W or height < GLYPH_H:
            raise SystemExit(f"{SHEET} is {width}x{height}, too small")
        sheet, bpp, size_line, _fmt = m.mlx_get_data_addr(img)
        px_bytes = bpp // 8
        self.masks = [
            cut(sheet, size_line, px_bytes, index) for index in range(COUNT)
        ]
        # The masks are plain bytes now, so the image itself can go.
        m.mlx_destroy_image(mlx, img)

    def coverage(self, char: str) -> bytes:
        code = ord(char)
        if not FIRST <= code < FIRST + COUNT:
            code = FALLBACK
        return self.masks[code - FIRST]


def cut(sheet: Any, size_line: int, px_bytes: int, index: int) -> bytes:
    mask = bytearray()
    for row in range(GLYPH_H):
        start = row * size_line + index * SLOT_W * px_bytes
        for col in range(GLYPH_W):
            mask.append(sheet[start + col * px_bytes + INK])
    return bytes(mask)
