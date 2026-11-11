"""Platform-independent shared primitives for Face Mouse Pro."""

from .config import (
    CalibrationConfig,
    CoreConfig,
    CursorConfig,
    CursorMappingConfig,
    GestureConfig,
    SmoothingConfig,
)
from .models import Landmark, NormalizedPoint, TimestampedPoint, Vector2D

__all__ = [
    "CalibrationConfig",
    "CoreConfig",
    "CursorConfig",
    "CursorMappingConfig",
    "GestureConfig",
    "Landmark",
    "NormalizedPoint",
    "SmoothingConfig",
    "TimestampedPoint",
    "Vector2D",
]
