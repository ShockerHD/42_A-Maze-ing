from mlx import Mlx

WIDTH = 1280
HEIGHT = 720

EVENT_CLIENT_MESSAGE = 33


class Spike:
    def __init__(self) -> None:
        self.m = Mlx()
        self.mlx = self.m.mlx_init()
        self.win = self.m.mlx_new_window(self.mlx, WIDTH, HEIGHT, "A-Maze-ing test")
        self.img = self.m.mlx_new_image(self.mlx, WIDTH, HEIGHT)
        self.buf, self.bpp, self.size_line, self.fmt = self.m.mlx_get_data_addr(self.img)
        # Measured, not assumed: size_line usually carries row padding.
        print(f"bpp={self.bpp} size_line={self.size_line} "
              f"(width*4={WIDTH * 4}) fmt={self.fmt}")
        if self.bpp != 32:
            raise SystemExit(f"expected 32 bpp, got {self.bpp}")
        self.px_bytes = self.bpp // 8
        self.frame = bytearray(self.size_line * HEIGHT)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Paint one rectangle into the frame, a row-slice at a time."""
        row = color.to_bytes(self.px_bytes, "little") * w
        for j in range(y, y + h):
            start = j * self.size_line + x * self.px_bytes
            self.frame[start:start + len(row)] = row

    def draw(self) -> None:
        self.fill_rect(440, 210, 400, 300, 0xFFFFFFFF)
        self.buf[:] = self.frame

    def on_expose(self, _param: object) -> None:
        print("expose", flush=True)
        self.m.mlx_put_image_to_window(self.mlx, self.win, self.img, 0, 0)

    def on_close(self, _param: object) -> None:
        self.m.mlx_loop_exit(self.mlx)

    def run(self) -> None:
        self.draw()
        self.m.mlx_expose_hook(self.win, self.on_expose, None)
        self.m.mlx_hook(self.win, EVENT_CLIENT_MESSAGE, 0, self.on_close, None)
        self.m.mlx_loop(self.mlx)
        self.m.mlx_destroy_image(self.mlx, self.img)
        self.m.mlx_destroy_window(self.mlx, self.win)
        self.m.mlx_release(self.mlx)


if __name__ == "__main__":
    Spike().run()
