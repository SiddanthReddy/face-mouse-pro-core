"""Calibration values with no persistence or logging behavior."""

from dataclasses import dataclass

from ..models import NormalizedPoint


@dataclass(frozen=True)
class CalibrationSample:
    """A normalized input point paired with a normalized target point."""

    input_point: NormalizedPoint
    target_point: NormalizedPoint

    def __post_init__(self) -> None:
        if not isinstance(self.input_point, NormalizedPoint) or not isinstance(self.target_point, NormalizedPoint):
            raise TypeError("calibration sample points must be NormalizedPoint values")


@dataclass(frozen=True)
class CalibrationProfile:
    """An application-neutral collection of calibration samples."""

    samples: tuple[CalibrationSample, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.samples, tuple):
            raise TypeError("samples must be an immutable tuple")
        if any(not isinstance(sample, CalibrationSample) for sample in self.samples):
            raise TypeError("samples must contain CalibrationSample values")
