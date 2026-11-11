"""Typed structural interfaces between host applications and the core."""

from typing import Protocol, Sequence

from .models import Landmark, NormalizedPoint, TimestampedPoint


class LandmarkSource(Protocol):
    """An application-provided source of named face landmarks."""

    def get_landmarks(self) -> Sequence[Landmark]:
        """Return the landmarks for the host's current observation."""


class PointMapper(Protocol):
    """Map a normalized input point to a normalized cursor point."""

    def map_point(self, point: NormalizedPoint) -> NormalizedPoint:
        """Return a mapped point without relying on display dimensions."""


class PointSmoother(Protocol):
    """Smooth a point using an explicit observation timestamp."""

    def update(self, observation: TimestampedPoint) -> NormalizedPoint:
        """Return the filtered point for this observation."""
