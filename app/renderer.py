# MLX renderer: draws a generated maze in a window.

from collections.abc import Callable
from math import ceil

from mlx import Mlx

from app.animation import Clock, EventStream, Tween
from app.font import GLYPH_H, GLYPH_W, Font
from app.keys import ACTIONS, LEGEND
from app.palette import DEFAULT, PALETTES, Palette, blend
from mazegen import ALL_WALLS, BIT, Coord, MazeGenerator, Step

WIDTH = 1280
HEIGHT = 720
MARGIN = 40
WALL_RATIO = 8  # wall thickness = cell // WALL_RATIO, so it scales

# wall bits from MazeGenerator.grid, 1 = closed
WALL_N = 1
WALL_E = 2
WALL_S = 4
WALL_W = 8

EVENT_CLIENT_MESSAGE = 33  # X11 ClientMessage, the window close button

# MLX calls the loop hook as fast as it can, way more often than a repaint
# is worth. Batch frames to this interval; the dt still adds up, so the
# animations keep real-time pace anyway.
FRAME = 1.0 / 60.0

# how long the carve replay takes, whatever the maze size
GENERATION_SECONDS = 2.5

# how long the solution takes to draw itself in
PATH_SECONDS = 0.8

# how long one colour scheme takes to become the next
FADE_SECONDS = 0.45

# the legend is drawn into the frame, so the only limit is the window width
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
        self.make_maze = make_maze
        self.path = Tween(PATH_SECONDS, progress=0.0, forward=False)
        self.path_drawn = 0
        self.palette_index = PALETTES.index(palette) if palette in PALETTES \
            else 0
        self.fade_from = palette
        self.fade: Tween | None = None
        self.clock = Clock()
        self._elapsed = 0.0
        self.live: list[list[int]] | None = None
        self.head: Coord | None = None
        self.generation: EventStream[Step] | None = None
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
        # size and centre the grid for the current maze
        self.cols = self.maze.width
        self.rows = self.maze.height
        # cell size comes from the grid so the cells tile it exactly
        room_w = WIDTH - 2 * MARGIN
        room_h = HEIGHT - 2 * MARGIN
        # wall thickness depends on the cell size and the frame eats into
        # the room, so size the cells then correct once
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
        # repaint the whole frame in one slice assignment
        px = color.to_bytes(self.px_bytes, "little")
        self.frame[:] = px * (len(self.frame) // self.px_bytes)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        # paint one rectangle into the frame, a row-slice at a time
        row = color.to_bytes(self.px_bytes, "little") * w
        for j in range(y, y + h):
            start = j * self.size_line + x * self.px_bytes
            self.frame[start:start + len(row)] = row

    def paint(self) -> None:
        # one whole frame: maze, legend on top, then out to MLX
        self.draw_maze()
        self.draw_legend()
        self.buf[:] = self.frame

    def draw_maze(self) -> None:
        # the outer square, filled with a full grid of walled cells
        self.clear(self.palette.bg)
        x, y = self.origin_x, self.origin_y
        self.fill_rect(x, y, self.side_w, self.side_h, self.palette.wall)
        self.fill_rect(
            x + self.wall, y + self.wall,
            self.grid_w, self.grid_h, self.palette.floor,
        )
        grid = self.grid_now()
        for row in range(self.rows):
            for col in range(self.cols):
                self.draw_cell(col, row, grid[row][col])
        for cell in self.maze.pattern_cells:
            self.fill_floor(*cell, self.palette.glyph)
        # mid-carve there is no maze to solve yet, so the stripe waits
        if self.live is None and self.path.progress > 0.0:
            self.draw_path()
        # after the path, so entry and exit keep their own colours
        self.fill_floor(*self.maze.entry, self.palette.entry)
        self.fill_floor(*self.maze.exit, self.palette.exit)
        if self.head is not None:
            self.fill_floor(*self.head, self.palette.path)

    def grid_now(self) -> list[list[int]]:
        # the walls to draw: the carve so far, or the finished maze
        return self.maze.grid if self.live is None else self.live

    def repaint_cell(self, cell: Coord, accent: int | None = None) -> None:
        # redraw one cell in place
        col, row = cell
        self.draw_cell(col, row, self.grid_now()[row][col])
        if accent is not None:
            self.fill_floor(col, row, accent)
        elif cell in self.maze.pattern_cells:
            self.fill_floor(col, row, self.palette.glyph)
        elif cell == self.maze.entry:
            self.fill_floor(col, row, self.palette.entry)
        elif cell == self.maze.exit:
            self.fill_floor(col, row, self.palette.exit)

    def centre(self, cell: Coord) -> Coord:
        # pixel centre of a cell
        col, row = cell
        return (
            self.origin_x + self.wall + col * self.cell + self.cell // 2,
            self.origin_y + self.wall + row * self.cell + self.cell // 2,
        )

    def path_length(self) -> int:
        # how many cells of the solution the tween is asking for
        return ceil(self.path.eased * len(self.maze.solution))

    def draw_path(self) -> None:
        # the stripe, drawn as far as the tween has got
        self.path_drawn = self.path_length()
        self.draw_path_segments(1, self.path_drawn)

    def draw_path_segments(self, first: int, last: int) -> None:
        # stripe the route from cell first - 1 up to cell last - 1
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
        # extend or trim the stripe in place to match the tween
        want = self.path_length()
        if want > self.path_drawn:
            # only the new steps, the rest is already drawn
            self.draw_path_segments(max(self.path_drawn, 1), want)
        elif want < self.path_drawn:
            # cells tile the grid exactly, so repainting the ones that
            # lost the stripe erases it, gaps included
            for cell in self.maze.solution[want:self.path_drawn]:
                self.repaint_cell(cell)
        self.path_drawn = want

    def fill_floor(self, col: int, row: int, color: int) -> None:
        # recolour a cell floor, leave its four walls alone
        x = self.origin_x + self.wall + col * self.cell
        y = self.origin_y + self.wall + row * self.cell
        inner = self.cell - 2 * self.wall
        self.fill_rect(x + self.wall, y + self.wall, inner, inner, color)

    def draw_cell(self, col: int, row: int, bits: int) -> None:
        # one cell: floor, then only the walls that are closed
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

    def animate_generation(self) -> None:
        # replay the carve from an all-walls-closed grid
        self.live = [[ALL_WALLS] * self.cols for _ in range(self.rows)]
        self.head = None
        # steps() replays without re-randomising, so this can be restarted
        # as often as the user likes without changing the maze
        self.generation = EventStream(
            list(self.maze.steps()), GENERATION_SECONDS, self.apply_step,
        )
        self.refresh()

    def end_generation(self) -> None:
        # drop back to showing the finished maze
        self.generation = None
        self.live = None
        self.head = None
        self.paint()

    def carve(self, a: Coord, b: Coord) -> None:
        # open the wall between two cells in the live grid
        if self.live is None:
            return
        (ax, ay), (bx, by) = a, b
        self.live[ay][ax] &= ~BIT[(bx - ax, by - ay)]
        self.live[by][bx] &= ~BIT[(ax - bx, ay - by)]
        self.repaint_cell(a)
        self.repaint_cell(b)

    @staticmethod
    def head_of(step: Step) -> Coord | None:
        # The cell to highlight for this step. Kruskal consider/reject and
        # DFS visit/backtrack move the highlight even though they open
        # nothing -- that is what makes the two look different.
        if step.kind == "done":
            return None
        if step.kind == "backtrack":
            return step.a
        return step.a if step.b is None else step.b

    def apply_step(self, step: Step) -> None:
        # one generation event: carve it, then move the highlight
        if step.kind == "open" and step.b is not None:
            self.carve(step.a, step.b)
        stale, self.head = self.head, self.head_of(step)
        if stale is not None and stale != self.head:
            self.repaint_cell(stale)
        if self.head is not None:
            self.repaint_cell(self.head, self.palette.path)

    def show(self) -> None:
        # push the frame to the window, one draw call for the lot
        self.m.mlx_put_image_to_window(self.mlx, self.win, self.img, 0, 0)

    def draw_glyph(self, x: int, y: int, char: str, color: int) -> None:
        # one character, blended into the frame and clipped to the window
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
                    # antialiased edge: mix ink into what is underneath
                    rest = 0xFF - alpha
                    for byte in range(self.px_bytes):
                        self.frame[at + byte] = (
                            ink[byte] * alpha + self.frame[at + byte] * rest
                        ) // 0xFF

    def draw_text(self, x: int, y: int, text: str, color: int) -> None:
        # a string, left to right from its top-left corner
        for char in text:
            self.draw_glyph(x, y, char, color)
            x += GLYPH_W

    def draw_legend(self) -> None:
        # key hints at the bottom
        keys = " ".join(f"[{key}] {hint}" for key, hint in LEGEND)
        text = f"{self.status()} {keys}"[:MAX_TEXT]
        y = min(
            self.origin_y + self.side_h + (MARGIN - GLYPH_H) // 2,
            HEIGHT - GLYPH_H,
        )
        # wipe the band first: the status redraws every frame and glyphs
        # blended over their own leftovers turn to mush
        self.fill_rect(0, y, WIDTH, GLYPH_H, self.palette.bg)
        centred = self.origin_x + (self.side_w - len(text) * GLYPH_W) // 2
        x = max(
            MARGIN // 2,
            min(centred, WIDTH - MARGIN // 2 - len(text) * GLYPH_W),
        )
        self.draw_text(x, y, text, self.palette.legend)

    def status(self) -> str:
        # what the view is showing, in front of the key hints
        head = f"{self.cols}x{self.rows} {self.palette.name}"
        if self.generation is not None:
            return (f"{head} {self.maze.algorithm} "
                    f"{self.generation.progress:.0%}")
        path = "on" if self.path.forward else "off"
        return f"{head} path:{path}"

    def refresh(self) -> None:
        # rebuild the frame and show it, after any state change
        self.paint()
        self.show()

    def on_expose(self, _param: object) -> None:
        # the first paint has to reach the window from inside the loop
        self.show()

    def advance(self, dt: float) -> bool:
        # Move the running animations on by dt seconds. True if any ran,
        # which is the same as asking whether to redraw. One that finishes
        # on this frame counts too: its last state must reach the screen.
        running = False
        for animation in (self.generation, self.path, self.fade):
            if animation is not None and not animation.done:
                animation.update(dt)
                running = True
        return running

    def on_frame(self, _param: object) -> None:
        # Advance the animations. Has to return fast every time: sleeping
        # here would freeze the window and swallow key events, so an idle
        # frame only reads the clock.
        self._elapsed += self.clock.tick()
        if self._elapsed < FRAME:
            return
        dt, self._elapsed = self._elapsed, 0.0
        if not self.advance(dt):
            return
        if self.generation is not None and self.generation.done:
            self.end_generation()
        elif self.fade is not None:
            self.advance_fade()
        else:
            if self.live is None:
                self.advance_path()
            # the animation already patched every cell it touched, so only
            # the legend and the blit are left
            self.draw_legend()
            self.buf[:] = self.frame
        self.show()

    def on_close(self, _param: object) -> None:
        self.m.mlx_loop_exit(self.mlx)

    def on_key(self, keycode: int, _param: object) -> None:
        # dispatch a keysym to the matching method, ignore the rest
        action = ACTIONS.get(keycode)
        if action is not None:
            getattr(self, action)()

    def quit(self) -> None:
        # Ctrl-C cannot interrupt mlx_loop from Python, so a key has to
        self.m.mlx_loop_exit(self.mlx)

    def regenerate(self) -> None:
        # build a fresh maze and redraw, or just repaint if none is wired
        if self.make_maze is None:
            print("regenerate: no generator wired, repainting", flush=True)
        else:
            self.maze = self.make_maze()
            # the new maze may be a different shape, so re-fit first
            self.fit()
            self.animate_generation()
            return
        self.refresh()

    def toggle_path(self) -> None:
        # reveal or hide the solution
        self.path.reverse()

    def cycle_palette(self) -> None:
        # cross-fade to the next colour scheme
        self.fade_from = self.palette
        self.palette_index = (self.palette_index + 1) % len(PALETTES)
        self.fade = Tween(FADE_SECONDS)

    def advance_fade(self) -> None:
        # recolour everything to the current point of the fade
        if self.fade is None:
            return
        target = PALETTES[self.palette_index]
        if self.fade.done:
            self.palette, self.fade = target, None
        else:
            self.palette = blend(self.fade_from, target, self.fade.eased)
        self.paint()

    def replay(self) -> None:
        # watch the same maze being carved again
        self.animate_generation()

    def run(self) -> None:
        self.animate_generation()
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
