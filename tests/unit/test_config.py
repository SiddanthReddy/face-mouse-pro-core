import pytest

from face_mouse_core.config import (
    CalibrationConfig,
    CoreConfig,
    CursorConfig,
    CursorMappingConfig,
    GestureConfig,
    SmoothingConfig,
)


def test_core_config_has_verified_algorithm_defaults():
    config = CoreConfig()
    assert config.gestures.blink_ear_threshold == 0.21
    assert config.gestures.blink_max_frames == 14
    assert config.gestures.both_eyes_natural_blink_ratio_diff == 0.05
    assert config.calibration.sample_target == 10
    assert config.cursor.deadzone_x == 0.008
    assert config.cursor.mapping.sensitivity_x == 2.2
    assert config.cursor.smoothing.min_cutoff == 1.2
    assert config.cursor.smoothing.beta == 0.04


def test_json_app_can_supply_its_distinct_blink_cap():
    assert GestureConfig(blink_max_frames=12).blink_max_frames == 12


@pytest.mark.parametrize(
    "factory",
    [
        lambda: GestureConfig(blink_ear_threshold=float("nan")),
        lambda: GestureConfig(blink_min_frames=0),
        lambda: GestureConfig(blink_min_frames=4, blink_max_frames=3),
        lambda: GestureConfig(mouth_open_min_frames=0),
        lambda: CursorMappingConfig(sensitivity_y=float("inf")),
        lambda: CursorMappingConfig(acceleration_curve=-1.0),
        lambda: SmoothingConfig(derivative_cutoff=0.0),
        lambda: CursorConfig(deadzone_x=-0.1),
        lambda: CalibrationConfig(sample_target=0),
        lambda: CalibrationConfig(deadzone_y=float("nan")),
    ],
)
def test_invalid_configuration_is_rejected(factory):
    with pytest.raises(ValueError):
        factory()


def test_frozen_config_cannot_be_mutated():
    config = GestureConfig()
    with pytest.raises((AttributeError, TypeError)):
        config.blink_min_frames = 3
