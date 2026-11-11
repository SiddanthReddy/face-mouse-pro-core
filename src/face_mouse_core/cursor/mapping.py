"""Screen-independent mappings for normalized points and relative vectors."""

import math

from ..config import CursorMappingConfig
from ..models import NormalizedPoint, Vector2D


class CursorMapper:
    """Map normalized input points and movement vectors without display APIs."""

    def __init__(self, config: CursorMappingConfig = CursorMappingConfig()) -> None:
        self.config = config

    def map_coordinates(self, x: float, y: float) -> NormalizedPoint:
        """Clamp finite coordinates to [0, 1], then apply configured inversion."""
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("cursor coordinates must be finite")
        x = min(1.0, max(0.0, x))
        y = min(1.0, max(0.0, y))
        if self.config.invert_x:
            x = 1.0 - x
        if self.config.invert_y:
            y = 1.0 - y
        return NormalizedPoint(x, y)

    def map_point(self, point: NormalizedPoint) -> NormalizedPoint:
        """Map a normalized input point into normalized cursor coordinates."""
        if not isinstance(point, NormalizedPoint):
            raise TypeError("point must be a NormalizedPoint")
        return self.map_coordinates(point.x, point.y)

    def map_offset(self, offset: Vector2D) -> Vector2D:
        """Apply the Windows signed power response and axis sensitivity.

        No screen width, height, cursor position, clamping to a display, or OS
        mouse operation is involved. Result components remain dimensionless.
        """
        if not isinstance(offset, Vector2D):
            raise TypeError("offset must be a Vector2D")
        x = -offset.x if self.config.invert_x else offset.x
        y = -offset.y if self.config.invert_y else offset.y
        mapped_x = math.copysign(abs(x) ** self.config.acceleration_curve, x) * self.config.sensitivity_x
        mapped_y = math.copysign(abs(y) ** self.config.acceleration_curve, y) * self.config.sensitivity_y
        if not math.isfinite(mapped_x) or not math.isfinite(mapped_y):
            raise ValueError("mapped movement must remain finite")
        return Vector2D(mapped_x, mapped_y)
