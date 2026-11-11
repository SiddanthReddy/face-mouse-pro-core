from dataclasses import FrozenInstanceError

import pytest

from face_mouse_core import CoreConfig, GestureConfig, NormalizedPoint, TimestampedPoint
from face_mouse_core.calibration.models import CalibrationProfile, CalibrationSample
from face_mouse_core.gestures.types import GestureEvent, GestureType


def test_default_configuration_is_available_without_persistence():
    config = CoreConfig()

    assert config.gestures == GestureConfig()
    assert config.cursor.smoothing.min_cutoff == 1.2


def test_timestamped_point_preserves_explicit_timestamp():
    observation = TimestampedPoint(12.5, NormalizedPoint(0.2, 0.7))

    assert observation.timestamp_seconds == 12.5


def test_gesture_event_is_deterministic_value_data():
    event = GestureEvent(GestureType.LEFT_CLICK, 3.25)

    assert event.gesture is GestureType.LEFT_CLICK
    assert event.timestamp_seconds == 3.25


def test_calibration_profile_contains_only_supplied_samples():
    sample = CalibrationSample(NormalizedPoint(0.1, 0.2), NormalizedPoint(0.8, 0.9))
    profile = CalibrationProfile((sample,))

    assert profile.samples == (sample,)


def test_models_are_immutable():
    point = NormalizedPoint(0.0, 1.0)

    with pytest.raises(FrozenInstanceError):
        point.x = 0.5
