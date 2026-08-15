"""
MLX renderer: draw a generated maze.

Grid size comes from the maze, not from config yet.

"""

from mlx import Mlx

from mazegen import MazeGenerator

WIDTH = 1280
HEIGHT = 720
MARGIN = 40
WALL_RATIO = 8  # wall thickness = cell // WALL_RATIO, so it scales with zoom

# Wall bits as produced by MazeGenerator.grid. 1 = closed.
WALL_N = 1
WALL_E = 2
WALL_S = 4
WALL_W = 8

EVENT_CLIENT_MESSAGE = 33  # X11 ClientMessage -> WM close button
KEY_ESC = 65307  # XK_Escape: the backend reports keysyms, not raw keycodes

COLOR_BG = 0xFF1E1E28
COLOR_WALL = 0xFFE0E0E8
COLOR_FLOOR = 0xFF2A2A38
COLOR_ENTRY = 0xFF4CAF50
COLOR_EXIT = 0xFFE05252


class Renderer:
    def __init__(self, maze: MazeGenerator, title: str = "A-Maze-ing") -> None:
        self.maze = maze
        self.cols = maze.width
        self.rows = maze.height
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
        # Cell size derived from the grid, so the cells tile the square
        # exactly instead of leaving a remainder.
        room_w = WIDTH - 2 * MARGIN - 2 * WALL
        room_h = HEIGHT - 2 * MARGIN - 2 * WALL
        self.cell = min(room_w // self.cols, room_h // self.rows)
        if self.cell < 3:
            raise SystemExit(
                f"{self.cols}x{self.rows} is too large for this window"
            )
        self.grid_w = self.cell * self.cols
        self.grid_h = self.cell * self.rows
        self.side_w = self.grid_w + 2 * WALL
        self.side_h = self.grid_h + 2 * WALL
        self.origin_x = (WIDTH - self.side_w) // 2
        self.origin_y = (HEIGHT - self.side_h) // 2

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
        """The outer square, filled with a full grid of walled cells."""
        self.clear(COLOR_BG)
        x, y = self.origin_x, self.origin_y
        self.fill_rect(x, y, self.side_w, self.side_h, COLOR_WALL)
        self.fill_rect(
            x + WALL, y + WALL, self.grid_w, self.grid_h, COLOR_FLOOR
        )
        grid = self.maze.grid
        for row in range(self.rows):
            for col in range(self.cols):
                self.draw_cell(col, row, grid[row][col])
        # Painted after the grid so the walls around them stay untouched.
        self.fill_floor(*self.maze.entry, COLOR_ENTRY)
        self.fill_floor(*self.maze.exit, COLOR_EXIT)
        self.buf[:] = self.frame

    def fill_floor(self, col: int, row: int, color: int) -> None:
        """Recolour a cell's floor, leaving its four walls as they are."""
        x = self.origin_x + WALL + col * self.cell
        y = self.origin_y + WALL + row * self.cell
        inner = self.cell - 2 * WALL
        self.fill_rect(x + WALL, y + WALL, inner, inner, color)

    def draw_cell(self, col: int, row: int, bits: int) -> None:
        """One cell: floor, then only the walls the maze says are closed."""
        x = self.origin_x + WALL + col * self.cell
        y = self.origin_y + WALL + row * self.cell
        size = self.cell
        self.fill_rect(x, y, size, size, COLOR_FLOOR)
        if bits & WALL_N:
            self.fill_rect(x, y, size, WALL, COLOR_WALL)
        if bits & WALL_S:
            self.fill_rect(x, y + size - WALL, size, WALL, COLOR_WALL)
        if bits & WALL_W:
            self.fill_rect(x, y, WALL, size, COLOR_WALL)
        if bits & WALL_E:
            self.fill_rect(x + size - WALL, y, WALL, size, COLOR_WALL)

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
    demo = MazeGenerator(
        width=21, height=30, entry=(0, 0), exit=(20, 12), seed=42
    )
    Renderer(demo).run()
