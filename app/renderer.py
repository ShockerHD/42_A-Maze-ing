"""
MLX renderer: draw a square outlined in walls.

No cells, no maze, no config yet.

"""

from mlx import Mlx

WIDTH = 1280
HEIGHT = 720
MARGIN = 40
WALL = 6
CELL = 60

EVENT_CLIENT_MESSAGE = 33  # X11 ClientMessage -> WM close button
KEY_ESC = 65307  # XK_Escape: the backend reports keysyms, not raw keycodes

COLOR_BG = 0xFF1E1E28
COLOR_WALL = 0xFFE0E0E8
COLOR_FLOOR = 0xFF2A2A38
COLOR_CELL = 0xFF4CAF50


class Renderer:
    def __init__(self, title: str = "A-Maze-ing") -> None:
        self.m = Mlx()
        self.mlx = self.m.mlx_init()
        self.win = self.m.mlx_new_window(self.mlx, WIDTH, HEIGHT, title)
        self.img = self.m.mlx_new_image(self.mlx, WIDTH, HEIGHT)
        self.buf, self.bpp, self.size_line, self.fmt = \
            self.m.mlx_get_data_addr(self.img)
        if self.bpp != 32:
            raise SystemExit(f"expected 32 bpp, got {self.bpp}")
        self.px_bytes = self.bpp // 8
        self.frame = bytearray(self.size_line * HEIGHT)
        # Largest square that fits the window, centred.
        self.side = min(WIDTH, HEIGHT) - 2 * MARGIN
        self.origin_x = (WIDTH - self.side) // 2
        self.origin_y = (HEIGHT - self.side) // 2

    def clear(self, color: int) -> None:
        """Repaint the whole frame in one slice assignment."""
        px = color.to_bytes(self.px_bytes, "little")
        self.frame[:] = px * (len(self.frame) // self.px_bytes)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Paint one rectangle into the frame, a row-slice at a time."""
        row = color.to_bytes(self.px_bytes, "little") * w
        for j in range(y, y + h):
            start = j * self.size_line + x * self.px_bytes
            self.frame[start:start + len(row)] = row

    def paint(self) -> None:
        """The outer square, plus two test cells to check placement."""
        self.clear(COLOR_BG)
        x, y, side = self.origin_x, self.origin_y, self.side
        self.fill_rect(x, y, side, side, COLOR_WALL)
        self.fill_rect(
            x + WALL, y + WALL, side - 2 * WALL, side - 2 * WALL, COLOR_FLOOR
        )
        # Top-left cell: tucked against the inside of the wall.
        self.fill_rect(x + WALL, y + WALL, CELL, CELL, COLOR_CELL)
        # Centre cell: same centre as the square itself.
        middle = (side - CELL) // 2
        self.fill_rect(x + middle, y + middle, CELL, CELL, COLOR_CELL)
        self.buf[:] = self.frame

    def on_expose(self, _param: object) -> None:
        # The first paint has to reach the window from inside the loop.
        self.m.mlx_put_image_to_window(self.mlx, self.win, self.img, 0, 0)

    def on_close(self, _param: object) -> None:
        self.m.mlx_loop_exit(self.mlx)

    def on_key(self, keycode: int, _param: object) -> None:
        # Ctrl-C cannot interrupt mlx_loop from Python, so a key must.
        if keycode == KEY_ESC:
            self.m.mlx_loop_exit(self.mlx)

    def run(self) -> None:
        self.paint()
        self.m.mlx_expose_hook(self.win, self.on_expose, None)
        self.m.mlx_key_hook(self.win, self.on_key, None)
        self.m.mlx_hook(self.win, EVENT_CLIENT_MESSAGE, 0, self.on_close, None)
        self.m.mlx_loop(self.mlx)
        self.m.mlx_destroy_image(self.mlx, self.img)
        self.m.mlx_destroy_window(self.mlx, self.win)
        self.m.mlx_release(self.mlx)


if __name__ == "__main__":
    Renderer().run()
