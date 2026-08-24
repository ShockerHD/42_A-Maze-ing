"""Timing and easing behaviour of app/animation.py."""

from app.animation import EventStream, Tween, lerp_color, smoothstep


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


def test_event_stream_paces_by_duration_not_by_frame() -> None:
    seen: list[int] = []
    stream = EventStream(list(range(100)), duration=1.0, apply=seen.append)
    # A tenth of the run buys a tenth of the events, however many frames
    # it took to get there.
    stream.update(0.1)
    assert len(seen) == 10
    for _ in range(10):
        stream.update(0.01)
    assert len(seen) == 20


def test_event_stream_accumulates_partial_frames() -> None:
    """Frames too short for one whole event must still add up."""
    seen: list[int] = []
    stream = EventStream(list(range(10)), duration=1.0, apply=seen.append)
    for _ in range(5):
        stream.update(0.02)  # 0.2 events each
    assert len(seen) == 1
    assert stream.progress == 0.1


def test_event_stream_finishes_and_reports_done() -> None:
    seen: list[int] = []
    stream = EventStream(list(range(10)), duration=1.0, apply=seen.append)
    assert stream.update(5.0)
    assert seen == list(range(10))
    assert stream.progress == 1.0


def test_empty_stream_is_done_immediately() -> None:
    stream: EventStream[int] = EventStream(
        [], duration=1.0, apply=lambda _: None
    )
    assert stream.done
    assert stream.progress == 1.0
    assert stream.update(0.1)
