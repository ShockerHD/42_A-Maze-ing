"""
MLX renderer: draw a generated maze.

Grid size comes from the maze, not from config yet.

"""

from collections.abc import Callable

from mlx import Mlx

from app.keys import ACTIONS
from mazegen import Coord, MazeGenerator

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

COLOR_BG = 0xFF1E1E28
COLOR_WALL = 0xFFE0E0E8
COLOR_FLOOR = 0xFF2A2A38
COLOR_ENTRY = 0xFF4CAF50
COLOR_EXIT = 0xFFE05252
COLOR_PATH = 0xFF3A6EA5


class Renderer:
    def __init__(
        self,
        maze: MazeGenerator,
        make_maze: Callable[[], MazeGenerator] | None = None,
        title: str = "A-Maze-ing",
    ) -> None:
        self.maze = maze
        # Build a replacement maze when R is pressed. Without one the
        # renderer still works, it just cannot regenerate.
        self.make_maze = make_maze
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
        self.fit()

    def fit(self) -> None:
        """Size and centre the grid for the current maze."""
        self.cols = self.maze.width
        self.rows = self.maze.height
        # Cell size derived from the grid, so the cells tile the square
        # exactly instead of leaving a remainder.
        room_w = WIDTH - 2 * MARGIN
        room_h = HEIGHT - 2 * MARGIN
        # Wall thickness depends on cell size, and the outer frame eats into
        # the room the cells get -- so size the cells, then correct once.
        self.cell = min(room_w // self.cols, room_h // self.rows)
        self.wall = max(1, self.cell // WALL_RATIO)
        self.cell = min(
            (room_w - 2 * self.wall) // self.cols,
            (room_h - 2 * self.wall) // self.rows,
        )
        self.wall = max(1, self.cell // WALL_RATIO)
        if self.cell < 3:
            raise SystemExit(
                f"{self.cols}x{self.rows} is too large for this window"
            )
        self.grid_w = self.cell * self.cols
        self.grid_h = self.cell * self.rows
        self.side_w = self.grid_w + 2 * self.wall
        self.side_h = self.grid_h + 2 * self.wall
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
            x + self.wall, y + self.wall,
            self.grid_w, self.grid_h, COLOR_FLOOR,
        )
        grid = self.maze.grid
        for row in range(self.rows):
            for col in range(self.cols):
                self.draw_cell(col, row, grid[row][col])
        self.draw_path()
        # Painted after the path so entry and exit stay their own colours.
        self.fill_floor(*self.maze.entry, COLOR_ENTRY)
        self.fill_floor(*self.maze.exit, COLOR_EXIT)
        self.buf[:] = self.frame

    def draw_path(self) -> None:
        """Tint the floors along the entry-to-exit route, openings included."""
        path = self.maze.solution
        for col, row in path:
            self.fill_floor(col, row, COLOR_PATH)
        # fill_floor stops at the wall ring, so consecutive cells would read
        # as separate tiles. Tint the gap between each pair as well.
        for before, after in zip(path, path[1:]):
            self.fill_gap(before, after, COLOR_PATH)

    def fill_gap(self, before: Coord, after: Coord, color: int) -> None:
        """Tint the opening shared by two neighbouring cells."""
        col = min(before[0], after[0])
        row = min(before[1], after[1])
        x = self.origin_x + self.wall + col * self.cell
        y = self.origin_y + self.wall + row * self.cell
        inner = self.cell - 2 * self.wall
        span = 2 * self.wall
        if before[0] != after[0]:  # side by side
            self.fill_rect(x + self.wall + inner, y + self.wall,
                           span, inner, color)
        else:  # one above the other
            self.fill_rect(x + self.wall, y + self.wall + inner,
                           inner, span, color)

    def fill_floor(self, col: int, row: int, color: int) -> None:
        """Recolour a cell's floor, leaving its four walls as they are."""
        x = self.origin_x + self.wall + col * self.cell
        y = self.origin_y + self.wall + row * self.cell
        inner = self.cell - 2 * self.wall
        self.fill_rect(x + self.wall, y + self.wall, inner, inner, color)

    def draw_cell(self, col: int, row: int, bits: int) -> None:
        """One cell: floor, then only the walls the maze says are closed."""
        x = self.origin_x + self.wall + col * self.cell
        y = self.origin_y + self.wall + row * self.cell
        size, t = self.cell, self.wall
        self.fill_rect(x, y, size, size, COLOR_FLOOR)
        if bits & WALL_N:
            self.fill_rect(x, y, size, t, COLOR_WALL)
        if bits & WALL_S:
            self.fill_rect(x, y + size - t, size, t, COLOR_WALL)
        if bits & WALL_W:
            self.fill_rect(x, y, t, size, COLOR_WALL)
        if bits & WALL_E:
            self.fill_rect(x + size - t, y, t, size, COLOR_WALL)

    def show(self) -> None:
        """Push the current image to the window."""
        self.m.mlx_put_image_to_window(self.mlx, self.win, self.img, 0, 0)

    def refresh(self) -> None:
        """Rebuild the frame and show it -- for anything that changes state."""
        self.paint()
        self.show()

    def on_expose(self, _param: object) -> None:
        # The first paint has to reach the window from inside the loop.
        self.show()

    def on_close(self, _param: object) -> None:
        self.m.mlx_loop_exit(self.mlx)

    def on_key(self, keycode: int, _param: object) -> None:
        """Dispatch a keysym to the matching method, ignore the rest."""
        action = ACTIONS.get(keycode)
        if action is not None:
            getattr(self, action)()

    def quit(self) -> None:
        # Ctrl-C cannot interrupt mlx_loop from Python, so a key must.
        self.m.mlx_loop_exit(self.mlx)

    def regenerate(self) -> None:
        """Build a fresh maze and redraw. Repaints only if none is wired."""
        if self.make_maze is None:
            print("regenerate: no generator wired, repainting", flush=True)
        else:
            self.maze = self.make_maze()
            # A replacement maze may be a different shape, so re-fit first.
            self.fit()
        self.refresh()

    def toggle_path(self) -> None:
        # Drawing maze.solution comes next; this only proves the key routes
        # here and that a redraw follows.
        print("path: not drawn yet, repainting", flush=True)
        self.refresh()

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
        width=5, height=5, entry=(0, 0), exit=(4, 4), seed=42
    )
    Renderer(demo).run()
