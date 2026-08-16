"""

Key bindings for the renderer.

"""

__all__ = ["ACTIONS", "LEGEND"]

KEY_ESC = 65307
KEY_SPACE = 32
KEY_C = 99
KEY_P = 112
KEY_Q = 113
KEY_R = 114

# keysym -> name of the Renderer method to call.
ACTIONS: dict[int, str] = {
    KEY_ESC: "quit",
    KEY_Q: "quit",
    KEY_R: "regenerate",
    KEY_P: "toggle_path",
    KEY_C: "cycle_palette",
    KEY_SPACE: "replay",
}

# What the on-screen legend spells out, in the order it is shown. Kept next
# to ACTIONS so a new binding and its hint are added in one place.
LEGEND: tuple[tuple[str, str], ...] = (
    ("R", "regenerate"),
    ("P", "path"),
    ("C", "colours"),
    ("SPACE", "replay"),
    ("ESC/Q", "quit"),
)
