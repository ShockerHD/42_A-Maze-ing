"""

Key bindings for the renderer.

"""

__all__ = ["ACTIONS"]

KEY_ESC = 65307
KEY_P = 112
KEY_Q = 113
KEY_R = 114

# keysym -> name of the Renderer method to call.
ACTIONS: dict[int, str] = {
    KEY_ESC: "quit",
    KEY_Q: "quit",
    KEY_R: "regenerate",
    KEY_P: "toggle_path",
}
