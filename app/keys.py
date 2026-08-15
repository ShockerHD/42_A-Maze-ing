"""

Key bindings for the renderer.

"""

__all__ = ["ACTIONS"]

KEY_ESC = 65307
KEY_Q = 113

# keysym -> name of the Renderer method to call.
ACTIONS: dict[int, str] = {
    KEY_ESC: "quit",
    KEY_Q: "quit",
}
