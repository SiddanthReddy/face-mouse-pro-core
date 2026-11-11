"""Deterministic EMA and One Euro filters with explicit timestamps."""

import math
from typing import Optional

from ..config import SmoothingConfig
from ..models import NormalizedPoint, TimestampedPoint, Vector2D


class ExponentialSmoother:
    """Two-dimensional exponential moving average; first sample passes through."""

    def __init__(self, alpha: float = 0.6) -> None:
        if not math.isfinite(alpha) or not 0.01 <= alpha <= 0.99:
            raise ValueError("alpha must be finite and in [0.01, 0.99]")
        self.alpha = alpha
        self._previous: Optional[Vector2D] = None

    def update(self, value: Vector2D) -> Vector2D:
        if not isinstance(value, Vector2D):
            raise TypeError("value must be a Vector2D")
        if self._previous is None:
            self._previous = value
        else:
            a = self.alpha
            self._previous = Vector2D(
                a * value.x + (1.0 - a) * self._previous.x,
                a * value.y + (1.0 - a) * self._previous.y,
            )
        return self._previous

    def reset(self) -> None:
        self._previous = None


class _LowPass:
    def __init__(self) -> None:
        self.previous: Optional[float] = None

    def update(self, value: float, alpha: float) -> float:
        if self.previous is None:
            self.previous = value
        else:
            self.previous = alpha * value + (1.0 - alpha) * self.previous
        return self.previous

    def reset(self) -> None:
        self.previous = None


class OneEuroFilter1D:
    """Adaptive 1D low-pass filter; callers must supply monotonic seconds."""

    def __init__(self, config: SmoothingConfig = SmoothingConfig()) -> None:
        self.config = config
        self._value_filter = _LowPass()
        self._derivative_filter = _LowPass()
        self._last_timestamp: Optional[float] = None

    @staticmethod
    def _alpha(rate: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / rate
        return 1.0 / (1.0 + tau / te)

    def filter(self, value: float, timestamp_seconds: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        if not math.isfinite(timestamp_seconds) or timestamp_seconds < 0:
            raise ValueError("timestamp_seconds must be finite and non-negative")

        if self._last_timestamp is None or self._last_timestamp >= timestamp_seconds:
            # Match the verified Windows filter: non-increasing times make the
            # current value pass through and set the new time baseline.
            self._last_timestamp = timestamp_seconds
            return self._value_filter.update(value, 1.0)

        dt = timestamp_seconds - self._last_timestamp
        self._last_timestamp = timestamp_seconds
        rate = 1.0 / max(dt, 1e-5)
        previous_value = self._value_filter.previous
        derivative = (value - (previous_value if previous_value is not None else value)) * rate
        derivative_alpha = self._alpha(rate, self.config.derivative_cutoff)
        filtered_derivative = self._derivative_filter.update(derivative, derivative_alpha)
        cutoff = self.config.min_cutoff + self.config.beta * abs(filtered_derivative)
        return self._value_filter.update(value, self._alpha(rate, cutoff))

    def reset(self) -> None:
        self._value_filter.reset()
        self._derivative_filter.reset()
        self._last_timestamp = None


class OneEuroFilter2D:
    """Independent x/y One Euro filters sharing one explicit timestamp."""

    def __init__(self, config: SmoothingConfig = SmoothingConfig()) -> None:
        self.filter_x = OneEuroFilter1D(config)
        self.filter_y = OneEuroFilter1D(config)

    def filter(self, point: Vector2D, timestamp_seconds: float) -> Vector2D:
        if not isinstance(point, Vector2D):
            raise TypeError("point must be a Vector2D")
        return Vector2D(
            self.filter_x.filter(point.x, timestamp_seconds),
            self.filter_y.filter(point.y, timestamp_seconds),
        )

    def update(self, observation: TimestampedPoint) -> NormalizedPoint:
        if not isinstance(observation, TimestampedPoint):
            raise TypeError("observation must be a TimestampedPoint")
        result = self.filter(
            Vector2D(observation.point.x, observation.point.y), observation.timestamp_seconds
        )
        return NormalizedPoint(result.x, result.y)

    def reset(self) -> None:
        self.filter_x.reset()
        self.filter_y.reset()
