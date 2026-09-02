# Key bindings for the renderer.

__all__ = ["ACTIONS", "LEGEND"]

KEY_ESC = 65307
KEY_SPACE = 32
KEY_C = 99
KEY_P = 112
KEY_Q = 113
KEY_R = 114

# keysym -> name of the Renderer method to call
ACTIONS: dict[int, str] = {
    KEY_ESC: "quit",
    KEY_Q: "quit",
    KEY_R: "regenerate",
    KEY_P: "toggle_path",
    KEY_C: "cycle_palette",
    KEY_SPACE: "replay",
}

# What the legend shows, in order. Next to ACTIONS so a new key and its
# hint get added in one place.
LEGEND: tuple[tuple[str, str], ...] = (
    ("R", "regen"),
    ("P", "path"),
    ("C", "colours"),
    ("SPC", "replay"),
    ("ESC+Q", "exit"),
)
