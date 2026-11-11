"""Pure calibration calculations and a deterministic sample accumulator."""

import math
from collections.abc import Iterable
from typing import Optional

from ..models import NormalizedPoint, Vector2D


def mean_point(samples: Iterable[NormalizedPoint]) -> NormalizedPoint:
    """Return the arithmetic mean of a non-empty sample iterable."""
    points = tuple(samples)
    if not points:
        raise ValueError("at least one calibration sample is required")
    if any(not isinstance(point, NormalizedPoint) for point in points):
        raise TypeError("samples must be NormalizedPoint values")
    return NormalizedPoint(
        sum(point.x for point in points) / len(points),
        sum(point.y for point in points) / len(points),
    )


def relative_offset(
    point: NormalizedPoint,
    neutral: Optional[NormalizedPoint],
    deadzone_x: float = 0.008,
    deadzone_y: float = 0.008,
) -> Vector2D:
    """Return neutral-relative movement with legacy deadzone subtraction.

    Values strictly inside the deadzone become zero. At the boundary the
    threshold is subtracted, yielding exactly zero as in the Windows code.
    """
    for name, value in (("deadzone_x", deadzone_x), ("deadzone_y", deadzone_y)):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if neutral is None:
        return Vector2D(0.0, 0.0)
    raw_x = point.x - neutral.x
    raw_y = point.y - neutral.y
    dx = 0.0 if abs(raw_x) < deadzone_x else raw_x - (deadzone_x if raw_x > 0 else -deadzone_x)
    dy = 0.0 if abs(raw_y) < deadzone_y else raw_y - (deadzone_y if raw_y > 0 else -deadzone_y)
    return Vector2D(dx, dy)


class CalibrationAccumulator:
    """Collect a fixed count of normalized points and return their mean."""

    def __init__(self, sample_target: int = 10) -> None:
        if not isinstance(sample_target, int) or isinstance(sample_target, bool) or sample_target < 1:
            raise ValueError("sample_target must be a positive integer")
        self.sample_target = sample_target
        self._samples: list[NormalizedPoint] = []

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def samples(self) -> tuple[NormalizedPoint, ...]:
        """Return an immutable snapshot of the in-progress calibration batch."""
        return tuple(self._samples)

    def add_sample(self, point: NormalizedPoint) -> Optional[NormalizedPoint]:
        """Add one sample; return the mean and clear the batch when complete."""
        if not isinstance(point, NormalizedPoint):
            raise TypeError("point must be a NormalizedPoint")
        self._samples.append(point)
        if len(self._samples) < self.sample_target:
            return None
        result = mean_point(self._samples)
        self._samples.clear()
        return result

    def reset(self) -> None:
        """Discard incomplete samples."""
        self._samples.clear()
