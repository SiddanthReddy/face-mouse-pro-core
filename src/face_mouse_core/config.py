"""Validated shared algorithm settings; persistence belongs to host apps."""

import math
from dataclasses import dataclass


def _finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class GestureConfig:
    """Gesture thresholds and timing settings, in monotonic seconds/frames."""

    blink_ear_threshold: float = 0.21
    blink_min_frames: int = 2
    # Verified detector constructor and DEFAULT_SETTINGS fallback; app JSON has 12.
    blink_max_frames: int = 14
    double_click_window_seconds: float = 0.40
    long_blink_duration_seconds: float = 0.80
    both_eyes_natural_blink_ratio_diff: float = 0.05  # Accepted but intentionally unused.
    mouth_mar_threshold: float = 0.45
    mouth_open_min_frames: int = 3
    click_cooldown_seconds: float = 0.35

    def __post_init__(self) -> None:
        for name in ("blink_min_frames", "blink_max_frames", "mouth_open_min_frames"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{name} must be an integer")
        for name in (
            "blink_ear_threshold",
            "double_click_window_seconds",
            "long_blink_duration_seconds",
            "both_eyes_natural_blink_ratio_diff",
            "mouth_mar_threshold",
            "click_cooldown_seconds",
        ):
            value = getattr(self, name)
            _finite(name, value)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.blink_min_frames < 1 or self.blink_max_frames < self.blink_min_frames:
            raise ValueError("blink frame range must satisfy 1 <= min <= max")
        if self.mouth_open_min_frames < 1:
            raise ValueError("mouth_open_min_frames must be at least 1")


@dataclass(frozen=True)
class CursorMappingConfig:
    """Dimensionless response for relative face movement and point mapping."""

    sensitivity_x: float = 2.2
    sensitivity_y: float = 2.0
    acceleration_curve: float = 1.2
    invert_x: bool = False
    invert_y: bool = False

    def __post_init__(self) -> None:
        if not all(isinstance(value, bool) for value in (self.invert_x, self.invert_y)):
            raise ValueError("invert flags must be bool values")
        for name in ("sensitivity_x", "sensitivity_y", "acceleration_curve"):
            value = getattr(self, name)
            _finite(name, value)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class SmoothingConfig:
    """One Euro filter parameters; these are distinct from legacy smoothing_factor."""

    min_cutoff: float = 1.2
    beta: float = 0.04
    derivative_cutoff: float = 1.0

    def __post_init__(self) -> None:
        for name in ("min_cutoff", "beta", "derivative_cutoff"):
            value = getattr(self, name)
            _finite(name, value)
            if value < 0 or (name != "beta" and value == 0):
                raise ValueError(f"{name} must be positive" if name != "beta" else f"{name} must be non-negative")


@dataclass(frozen=True)
class CursorConfig:
    """Cursor response, deadzones and smoothing settings."""

    mapping: CursorMappingConfig = CursorMappingConfig()
    smoothing: SmoothingConfig = SmoothingConfig()
    deadzone_x: float = 0.008
    deadzone_y: float = 0.008

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, CursorMappingConfig) or not isinstance(self.smoothing, SmoothingConfig):
            raise TypeError("mapping and smoothing must use their corresponding config types")
        for name in ("deadzone_x", "deadzone_y"):
            value = getattr(self, name)
            _finite(name, value)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class CalibrationConfig:
    """Calibration calculation defaults, independent of persistence/workflow UI."""

    sample_target: int = 10
    deadzone_x: float = 0.008
    deadzone_y: float = 0.008

    def __post_init__(self) -> None:
        if not isinstance(self.sample_target, int) or isinstance(self.sample_target, bool) or self.sample_target < 1:
            raise ValueError("sample_target must be at least 1")
        for name in ("deadzone_x", "deadzone_y"):
            value = getattr(self, name)
            _finite(name, value)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class CoreConfig:
    """Aggregate immutable settings. Applications own loading and saving."""

    gestures: GestureConfig = GestureConfig()
    cursor: CursorConfig = CursorConfig()
    calibration: CalibrationConfig = CalibrationConfig()

    def __post_init__(self) -> None:
        if not isinstance(self.gestures, GestureConfig):
            raise TypeError("gestures must be GestureConfig")
        if not isinstance(self.cursor, CursorConfig):
            raise TypeError("cursor must be CursorConfig")
        if not isinstance(self.calibration, CalibrationConfig):
            raise TypeError("calibration must be CalibrationConfig")
