"""Timing and easing behaviour of app/animation.py."""

from app.animation import Tween, lerp_color, smoothstep


def test_tween_runs_to_completion() -> None:
    tween = Tween(duration=1.0)
    assert not tween.update(0.5)
    assert tween.progress == 0.5
    assert tween.update(0.5)
    assert tween.done


def test_tween_clamps_overshoot() -> None:
    tween = Tween(duration=0.1)
    assert tween.update(10.0)
    assert tween.progress == 1.0


def test_reverse_folds_back_from_current_progress() -> None:
    """The interruptible-toggle rule: invert, never restart."""
    tween = Tween(duration=1.0)
    tween.update(0.25)
    tween.reverse()
    assert not tween.done
    tween.update(0.1)
    assert tween.progress == 0.15
    assert tween.update(0.5)
    assert tween.progress == 0.0


def test_easing_is_symmetric() -> None:
    assert smoothstep(0.0) == 0.0
    assert smoothstep(0.5) == 0.5
    assert smoothstep(1.0) == 1.0


def test_colours_blend_per_channel() -> None:
    black, white = 0xFF000000, 0xFFFFFFFF
    assert lerp_color(black, white, 0.0) == black
    assert lerp_color(black, white, 1.0) == white
    # No channel may carry into the next one.
    assert lerp_color(0xFF0000FF, 0xFF00FF00, 0.5) == 0xFF008080
