"""

MLX renderer: draw a generated maze.

"""

from collections.abc import Callable
from math import ceil

from mlx import Mlx

from app.animation import Clock, Tween
from app.font import GLYPH_H, GLYPH_W, Font
from app.keys import ACTIONS, LEGEND
from app.palette import DEFAULT, PALETTES, Palette
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

# MLX calls the loop hook as fast as it can, which is far more often than a
# repaint is worth. Frames are batched up to this interval instead; the dt
# still adds up, so animations keep real-time pace either way.
FRAME = 1.0 / 60.0

# How long the solution takes to draw itself in, entry to exit.
PATH_SECONDS = 0.8

# The legend is drawn into the frame, so the only cap left is the frame's own
# width -- mlx_string_put() used to cost one draw call per character, and the
# backend has 64 per frame for the whole screen.
MAX_TEXT = (WIDTH - MARGIN) // GLYPH_W


class Renderer:
    def __init__(
        self,
        maze: MazeGenerator,
        make_maze: Callable[[], MazeGenerator] | None = None,
        palette: Palette = DEFAULT,
        title: str = "A-Maze-ing",
    ) -> None:
        self.maze = maze
        self.palette = palette
        # Build a replacement maze when R is pressed. Without one the
        # renderer still works, it just cannot regenerate.
        self.make_maze = make_maze
        # The stripe is a tween rather than a flag: hidden at 0, shown at
        # 1, and reversible from wherever it happens to be.
        self.path = Tween(PATH_SECONDS, progress=0.0, forward=False)
        # How many cells of the stripe are on screen, so a frame can
        # extend or trim it instead of redrawing the whole route.
        self.path_drawn = 0
        self.clock = Clock()
        self._elapsed = 0.0
        self.m = Mlx()
        self.mlx = self.m.mlx_init()
        self.win = self.m.mlx_new_window(self.mlx, WIDTH, HEIGHT, title)
        self.font = Font(self.m, self.mlx)
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
        """One whole frame: the maze, the legend on top, then out to MLX."""
        self.draw_maze()
        self.draw_legend()
        self.buf[:] = self.frame

    def draw_maze(self) -> None:
        """The outer square, filled with a full grid of walled cells."""
        self.clear(self.palette.bg)
        x, y = self.origin_x, self.origin_y
        self.fill_rect(x, y, self.side_w, self.side_h, self.palette.wall)
        self.fill_rect(
            x + self.wall, y + self.wall,
            self.grid_w, self.grid_h, self.palette.floor,
        )
        grid = self.maze.grid
        for row in range(self.rows):
            for col in range(self.cols):
                self.draw_cell(col, row, grid[row][col])
        for cell in self.maze.pattern_cells:
            self.fill_floor(*cell, self.palette.glyph)
        if self.path.progress > 0.0:
            self.draw_path()
        # Painted after the path so entry and exit stay their own colours.
        self.fill_floor(*self.maze.entry, self.palette.entry)
        self.fill_floor(*self.maze.exit, self.palette.exit)

    def repaint_cell(self, cell: Coord) -> None:
        """Redraw one cell in place, erasing anything drawn over it."""
        col, row = cell
        self.draw_cell(col, row, self.maze.grid[row][col])
        if cell in self.maze.pattern_cells:
            self.fill_floor(col, row, self.palette.glyph)
        elif cell == self.maze.entry:
            self.fill_floor(col, row, self.palette.entry)
        elif cell == self.maze.exit:
            self.fill_floor(col, row, self.palette.exit)

    def centre(self, cell: Coord) -> Coord:
        """Pixel centre of a cell."""
        col, row = cell
        return (
            self.origin_x + self.wall + col * self.cell + self.cell // 2,
            self.origin_y + self.wall + row * self.cell + self.cell // 2,
        )

    def path_length(self) -> int:
        """How many cells of the solution the tween is asking for."""
        return ceil(self.path.eased * len(self.maze.solution))

    def draw_path(self) -> None:
        """The stripe, drawn as far as the tween has got."""
        self.path_drawn = self.path_length()
        self.draw_path_segments(1, self.path_drawn)

    def draw_path_segments(self, first: int, last: int) -> None:
        """Stripe the route from cell *first* - 1 up to cell *last* - 1.

        One rect per step, centre to centre. Each covers both endpoints,
        so turns join up without a separate corner piece.
        """
        path = self.maze.solution
        width = max(2, self.cell // 6)
        half = width // 2
        for index in range(first, last):
            ax, ay = self.centre(path[index - 1])
            bx, by = self.centre(path[index])
            x, y = min(ax, bx), min(ay, by)
            self.fill_rect(
                x - half, y - half,
                abs(bx - ax) + width, abs(by - ay) + width, self.palette.path,
            )

    def advance_path(self) -> None:
        """Extend or trim the stripe in place to match the tween."""
        want = self.path_length()
        if want > self.path_drawn:
            # Only the newly revealed steps -- the rest is already drawn.
            self.draw_path_segments(max(self.path_drawn, 1), want)
        elif want < self.path_drawn:
            # Cells tile the grid exactly, so repainting the ones that
            # lost the stripe erases it, gap between cells included.
            for cell in self.maze.solution[want:self.path_drawn]:
                self.repaint_cell(cell)
        self.path_drawn = want

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
        self.fill_rect(x, y, size, size, self.palette.floor)
        if bits & WALL_N:
            self.fill_rect(x, y, size, t, self.palette.wall)
        if bits & WALL_S:
            self.fill_rect(x, y + size - t, size, t, self.palette.wall)
        if bits & WALL_W:
            self.fill_rect(x, y, t, size, self.palette.wall)
        if bits & WALL_E:
            self.fill_rect(x + size - t, y, t, size, self.palette.wall)

    def show(self) -> None:
        """Push the frame to the window -- one draw call for the lot."""
        self.m.mlx_put_image_to_window(self.mlx, self.win, self.img, 0, 0)

    def draw_glyph(self, x: int, y: int, char: str, color: int) -> None:
        """One character, blended into the frame and clipped to the window."""
        ink = color.to_bytes(self.px_bytes, "little")
        mask = self.font.coverage(char)
        for row in range(max(0, -y), min(GLYPH_H, HEIGHT - y)):
            line = (y + row) * self.size_line
            for col in range(max(0, -x), min(GLYPH_W, WIDTH - x)):
                alpha = mask[row * GLYPH_W + col]
                at = line + (x + col) * self.px_bytes
                if alpha == 0xFF:
                    self.frame[at:at + self.px_bytes] = ink
                elif alpha:
                    # An antialiased edge: mix ink into what is underneath.
                    rest = 0xFF - alpha
                    for byte in range(self.px_bytes):
                        self.frame[at + byte] = (
                            ink[byte] * alpha + self.frame[at + byte] * rest
                        ) // 0xFF

    def draw_text(self, x: int, y: int, text: str, color: int) -> None:
        """A string, left to right from its top-left corner."""
        for char in text:
            self.draw_glyph(x, y, char, color)
            x += GLYPH_W

    def draw_legend(self) -> None:
        """
        Key hints at the bottom.

        """
        keys = " ".join(f"[{key}] {hint}" for key, hint in LEGEND)
        text = f"{self.status()} {keys}"[:MAX_TEXT]
        y = min(
            self.origin_y + self.side_h + (MARGIN - GLYPH_H) // 2,
            HEIGHT - GLYPH_H,
        )
        # The band is wiped first: an animating status redraws this every
        # frame, and glyphs blended over their own leftovers turn to mush.
        self.fill_rect(0, y, WIDTH, GLYPH_H, self.palette.bg)
        centred = self.origin_x + (self.side_w - len(text) * GLYPH_W) // 2
        x = max(
            MARGIN // 2,
            min(centred, WIDTH - MARGIN // 2 - len(text) * GLYPH_W),
        )
        self.draw_text(x, y, text, self.palette.legend)

    def status(self) -> str:
        """What the view is showing, ahead of the key hints."""
        path = "on" if self.path.forward else "off"
        return f"{self.cols}x{self.rows} {self.palette.name} path:{path}"

    def refresh(self) -> None:
        """Rebuild the frame and show it -- for anything that changes state."""
        self.paint()
        self.show()

    def on_expose(self, _param: object) -> None:
        # The first paint has to reach the window from inside the loop.
        self.show()

    def advance(self, dt: float) -> bool:
        """Move the running animation on by *dt* seconds.

        Returns True if it ran, which is the same as asking whether the
        window needs drawing again.
        """
        if self.path.done:
            return False
        self.path.update(dt)
        return True

    def on_frame(self, _param: object) -> None:
        """Advance the animations. Must return promptly, every time.

        Sleeping in here would freeze the window and swallow key events,
        so an idle frame does nothing but read the clock.
        """
        self._elapsed += self.clock.tick()
        if self._elapsed < FRAME:
            return
        dt, self._elapsed = self._elapsed, 0.0
        if not self.advance(dt):
            return
        self.advance_path()
        # The stripe patched the cells it touched, so the rest of the
        # frame still stands: only the legend and the blit are left.
        self.draw_legend()
        self.buf[:] = self.frame
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
        """Reveal or hide the solution.

        Reverses from the current progress rather than restarting, so a
        toggle pressed mid-reveal folds the stripe back from where it
        actually is instead of snapping to the far end first.
        """
        self.path.reverse()

    def cycle_palette(self) -> None:
        """Step to the next colour scheme and redraw."""
        nxt = (PALETTES.index(self.palette) + 1) % len(PALETTES)
        self.palette = PALETTES[nxt]
        self.refresh()

    def replay(self) -> None:
        # Replaying maze.steps() as an animation This function requires
        # animation, which is in further steps in our plan
        steps = sum(1 for _ in self.maze.steps())
        print(f"replay: {steps} steps recorded, ano animation yet ;(",
              flush=True)

    def run(self) -> None:
        self.paint()
        self.m.mlx_expose_hook(self.win, self.on_expose, None)
        self.m.mlx_key_hook(self.win, self.on_key, None)
        self.m.mlx_loop_hook(self.mlx, self.on_frame, None)
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
