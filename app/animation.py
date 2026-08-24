"""

Animation primitives: a frame clock, easing, and the two things that move.

"""

import time
from collections.abc import Callable, Sequence
from typing import Generic, TypeVar

__all__ = ["Clock", "EventStream", "Tween", "lerp_color", "smoothstep"]

T = TypeVar("T")

# A stalled window (dragged, or a slow regenerate) hands the loop hook a
# huge dt. Capping it makes an animation pause rather than teleport.
MAX_DT = 0.1


def clamp(value: float) -> float:
    """*value* squeezed into [0, 1]."""
    return min(1.0, max(0.0, value))


def smoothstep(t: float) -> float:
    """Ease *t* in and out. Cheap, and much nicer than linear."""
    return t * t * (3.0 - 2.0 * t)


def lerp_color(a: int, b: int, t: float) -> int:
    """Blend two 0xAARRGGBB colours one channel at a time.

    Blending the packed ints directly would let a channel's overflow
    bleed into its neighbour, so each byte is mixed on its own.
    """
    out = 0
    for shift in (0, 8, 16, 24):
        channel_a = (a >> shift) & 0xFF
        channel_b = (b >> shift) & 0xFF
        out |= round(channel_a + (channel_b - channel_a) * t) << shift
    return out


class Clock:
    """Wall-clock deltas for the loop hook.

    MLX gives no fixed frame interval, so the time between two hook calls
    has to be measured rather than assumed.
    """

    def __init__(self) -> None:
        self._last = time.monotonic()

    def tick(self) -> float:
        """Seconds since the previous tick, capped at MAX_DT."""
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        return min(dt, MAX_DT)


class Tween:
    """A 0 -> 1 ramp over *duration* seconds, reversible mid-flight."""

    def __init__(
        self,
        duration: float,
        progress: float = 0.0,
        forward: bool = True,
    ) -> None:
        # Guard against a zero duration dividing by zero in update().
        self.duration = max(duration, 1e-6)
        self.progress = clamp(progress)
        self.forward = forward

    @property
    def done(self) -> bool:
        """True once the ramp has reached the end it is heading for."""
        return self.progress >= 1.0 if self.forward else self.progress <= 0.0

    @property
    def eased(self) -> float:
        """Progress with smoothstep applied."""
        return smoothstep(self.progress)

    def reverse(self) -> None:
        """Flip direction without resetting.

        Pressing the toggle halfway through a reveal has to fold back from
        where it actually is, not restart from the far end.
        """
        self.forward = not self.forward

    def update(self, dt: float) -> bool:
        """Advance the ramp. True once finished."""
        step = dt / self.duration
        self.progress = clamp(
            self.progress + (step if self.forward else -step)
        )
        return self.done


class EventStream(Generic[T]):
    """Play *events* evenly across *duration* seconds.

    Paced by how much of the duration has passed rather than one event
    per frame, so a 15x15 maze (615 events) and a 60x40 one (9277) take
    the same time to draw. One per frame looks right at the small size
    and takes forever at the large one.
    """

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
        """How much of the list has been played."""
        return self.index / len(self.events) if self.events else 1.0

    @property
    def done(self) -> bool:
        return self.index >= len(self.events)

    def update(self, dt: float) -> bool:
        """Play whatever events the time so far has earned.

        How far through the duration are we? Play up to that share of the
        list. Counting from elapsed time rather than per-frame leftovers
        means a frame too short for a whole event still adds up.
        """
        self.elapsed += dt
        share = clamp(self.elapsed / self.duration)
        upto = round(share * len(self.events))
        while self.index < upto:
            self.apply(self.events[self.index])
            self.index += 1
        return self.done
