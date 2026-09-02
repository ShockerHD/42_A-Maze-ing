# Animation helpers: a frame clock, easing, and the two moving things.

import time
from collections.abc import Callable, Sequence
from typing import Generic, TypeVar

__all__ = ["Clock", "EventStream", "Tween", "lerp_color", "smoothstep"]

T = TypeVar("T")

# A stalled window (dragged, or a slow regenerate) gives a huge dt.
# Capping it makes an animation pause instead of teleporting.
MAX_DT = 0.1


def clamp(value: float) -> float:
    # squeeze value into [0, 1]
    return min(1.0, max(0.0, value))


def smoothstep(t: float) -> float:
    # ease t in and out, much nicer than linear
    return t * t * (3.0 - 2.0 * t)


def lerp_color(a: int, b: int, t: float) -> int:
    # Blend two 0xAARRGGBB colours one channel at a time: mixing the packed
    # ints would let one channel overflow into its neighbour.
    out = 0
    for shift in (0, 8, 16, 24):
        channel_a = (a >> shift) & 0xFF
        channel_b = (b >> shift) & 0xFF
        out |= round(channel_a + (channel_b - channel_a) * t) << shift
    return out


class Clock:
    # Wall-clock deltas for the loop hook. MLX has no fixed frame interval,
    # so the gap between two calls has to be measured, not assumed.

    def __init__(self) -> None:
        self._last = time.monotonic()

    def tick(self) -> float:
        # seconds since the last tick, capped at MAX_DT
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        return min(dt, MAX_DT)


class Tween:
    # a 0 -> 1 ramp over duration seconds, reversible mid-flight

    def __init__(
        self,
        duration: float,
        progress: float = 0.0,
        forward: bool = True,
    ) -> None:
        # guard against a zero duration dividing by zero in update()
        self.duration = max(duration, 1e-6)
        self.progress = clamp(progress)
        self.forward = forward

    @property
    def done(self) -> bool:
        # True once the ramp reached the end it is heading for
        return self.progress >= 1.0 if self.forward else self.progress <= 0.0

    @property
    def eased(self) -> float:
        # progress with smoothstep applied
        return smoothstep(self.progress)

    def reverse(self) -> None:
        # Flip direction without resetting: toggling halfway through a
        # reveal folds back from where it is, not from the far end.
        self.forward = not self.forward

    def update(self, dt: float) -> bool:
        # advance the ramp, True once finished
        step = dt / self.duration
        self.progress = clamp(
            self.progress + (step if self.forward else -step)
        )
        return self.done


class EventStream(Generic[T]):
    # Play events evenly across duration seconds. Paced by elapsed time and
    # not one event per frame, so a 15x15 maze (615 events) and a 60x40 one
    # (9277) take the same time. One per frame is way too slow when big.

    def __init__(
        self,
        events: Sequence[T],
        duration: float,
        apply: Callable[[T], None],
    ) -> None:
        self.events = events
        self.duration = max(duration, 1e-6)
        self.apply = apply
        self.elapsed = 0.0
        self.index = 0

    @property
    def progress(self) -> float:
        # how much of the list has been played
        return self.index / len(self.events) if self.events else 1.0

    @property
    def done(self) -> bool:
        return self.index >= len(self.events)

    def update(self, dt: float) -> bool:
        # Play up to the share of the list the elapsed time has earned.
        # Counting from elapsed time means a frame too short for a whole
        # event still adds up instead of being lost.
        self.elapsed += dt
        share = clamp(self.elapsed / self.duration)
        upto = round(share * len(self.events))
        while self.index < upto:
            self.apply(self.events[self.index])
            self.index += 1
        return self.done
