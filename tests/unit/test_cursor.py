import pytest

from face_mouse_core.config import CursorMappingConfig, SmoothingConfig
from face_mouse_core.cursor import (
    CursorMapper,
    ExponentialSmoother,
    OneEuroFilter1D,
    OneEuroFilter2D,
)
from face_mouse_core.models import NormalizedPoint, TimestampedPoint, Vector2D


def test_normalized_mapping_is_identity_by_default_and_clamps_boundaries():
    mapper = CursorMapper()
    assert mapper.map_point(NormalizedPoint(0.25, 0.75)) == NormalizedPoint(0.25, 0.75)
    assert mapper.map_coordinates(-0.2, 1.2) == NormalizedPoint(0.0, 1.0)


def test_normalized_mapping_inversion_is_independent_per_axis():
    mapper = CursorMapper(CursorMappingConfig(invert_x=True, invert_y=False))
    assert mapper.map_point(NormalizedPoint(0.2, 0.7)) == NormalizedPoint(0.8, 0.7)


def test_offset_mapping_uses_signed_power_curve_and_sensitivity():
    mapper = CursorMapper(CursorMappingConfig(sensitivity_x=2.0, sensitivity_y=3.0, acceleration_curve=2.0))
    assert mapper.map_offset(Vector2D(0.5, -0.5)) == Vector2D(0.5, -0.75)


def test_mapping_rejects_invalid_coordinates_and_models_reject_out_of_bounds():
    with pytest.raises(ValueError):
        CursorMapper().map_coordinates(float("nan"), 0.5)
    with pytest.raises(ValueError):
        NormalizedPoint(1.01, 0.5)


def test_exponential_smoother_first_sample_and_weighting_match_ema():
    smoother = ExponentialSmoother(alpha=0.5)
    assert smoother.update(Vector2D(10.0, 10.0)) == Vector2D(10.0, 10.0)
    assert smoother.update(Vector2D(20.0, 20.0)) == Vector2D(15.0, 15.0)
    smoother.reset()
    assert smoother.update(Vector2D(-3.0, 4.0)) == Vector2D(-3.0, 4.0)


def test_one_euro_first_sample_and_timestamped_2d_smoothing():
    smoother = OneEuroFilter2D(SmoothingConfig(min_cutoff=1.0, beta=0.01))
    first = smoother.update(TimestampedPoint(10.0, NormalizedPoint(0.3, 0.4)))
    second = smoother.update(TimestampedPoint(10.033, NormalizedPoint(0.8, 0.9)))
    assert first == NormalizedPoint(0.3, 0.4)
    assert 0.3 < second.x < 0.8
    assert 0.4 < second.y < 0.9


def test_one_euro_1d_handles_nonincreasing_time_like_verified_runtime():
    smoother = OneEuroFilter1D()
    assert smoother.filter(2.0, 1.0) == 2.0
    assert smoother.filter(3.0, 1.0) == 3.0
    assert smoother.filter(4.0, 0.5) == 4.0
    assert smoother.filter(5.0, 0.6) < 5.0


def test_smoothing_and_mapping_configuration_validation():
    with pytest.raises(ValueError):
        SmoothingConfig(min_cutoff=0.0)
    with pytest.raises(ValueError):
        SmoothingConfig(beta=-1.0)
    with pytest.raises(ValueError):
        CursorMappingConfig(acceleration_curve=-0.1)
    with pytest.raises(ValueError):
        ExponentialSmoother(alpha=1.0)
