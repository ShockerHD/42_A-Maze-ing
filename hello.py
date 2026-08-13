from mlx import Mlx

WIDTH = 1280
HEIGHT = 720

EVENT_CLIENT_MESSAGE = 33  # X11 ClientMessage -> WM close button


class Spike:
    def __init__(self) -> None:
        self.m = Mlx()
        self.mlx = self.m.mlx_init()
        self.win = self.m.mlx_new_window(self.mlx, WIDTH, HEIGHT, "A-Maze-ing test")

    def on_close(self, _param: object) -> None:
        self.m.mlx_loop_exit(self.mlx)

    def run(self) -> None:
        self.m.mlx_hook(self.win, EVENT_CLIENT_MESSAGE, 0, self.on_close, None)
        self.m.mlx_loop(self.mlx)
        self.m.mlx_destroy_window(self.mlx, self.win)
        self.m.mlx_release(self.mlx)


if __name__ == "__main__":
    Spike().run()
