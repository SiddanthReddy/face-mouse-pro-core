"""Validated, platform-neutral values used by shared algorithms."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector2D:
    """Finite two-dimensional vector; values may be signed or unbounded."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("vector coordinates must be finite")


@dataclass(frozen=True)
class NormalizedPoint:
    """A finite point whose coordinates are within the closed unit square."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("normalized coordinates must be finite")
        if not (0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0):
            raise ValueError("normalized coordinates must be in [0, 1]")


@dataclass(frozen=True)
class Landmark:
    """A named normalized point supplied by a host landmark provider."""

    name: str
    point: NormalizedPoint

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("landmark name must not be empty")


@dataclass(frozen=True)
class TimestampedPoint:
    """A point observed at an explicit monotonic timestamp in seconds."""

    timestamp_seconds: float
    point: NormalizedPoint

    def __post_init__(self) -> None:
        if not math.isfinite(self.timestamp_seconds) or self.timestamp_seconds < 0:
            raise ValueError("timestamp_seconds must be finite and non-negative")
