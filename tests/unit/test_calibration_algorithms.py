import pytest

from face_mouse_core.calibration import (
    CalibrationAccumulator,
    mean_point,
    relative_offset,
)
from face_mouse_core.models import NormalizedPoint


def test_mean_point_matches_ten_sample_arithmetic_calibration():
    samples = [NormalizedPoint(0.4 + i * 0.01, 0.6 - i * 0.01) for i in range(10)]
    result = mean_point(samples)
    assert result.x == pytest.approx(0.445)
    assert result.y == pytest.approx(0.555)


def test_mean_point_requires_nonempty_valid_samples():
    with pytest.raises(ValueError):
        mean_point([])
    with pytest.raises(TypeError):
        mean_point(["bad"])


def test_accumulator_finishes_at_target_clears_samples_and_can_restart():
    accumulator = CalibrationAccumulator(sample_target=2)
    assert accumulator.add_sample(NormalizedPoint(0.4, 0.6)) is None
    result = accumulator.add_sample(NormalizedPoint(0.6, 0.8))
    assert result == NormalizedPoint(0.5, 0.7)
    assert accumulator.sample_count == 0
    assert accumulator.samples == ()
    assert accumulator.add_sample(NormalizedPoint(0.2, 0.2)) is None
    assert accumulator.samples == (NormalizedPoint(0.2, 0.2),)
    accumulator.reset()
    assert accumulator.sample_count == 0


def test_relative_offset_matches_windows_deadzone_subtraction_boundaries():
    neutral = NormalizedPoint(0.5, 0.5)
    inside = relative_offset(NormalizedPoint(0.507, 0.493), neutral)
    edge = relative_offset(NormalizedPoint(0.508, 0.492), neutral)
    outside = relative_offset(NormalizedPoint(0.528, 0.472), neutral)
    uncalibrated = relative_offset(NormalizedPoint(0.9, 0.1), None)
    assert (inside.x, inside.y) == pytest.approx((0.0, 0.0))
    assert (edge.x, edge.y) == pytest.approx((0.0, 0.0))
    assert (outside.x, outside.y) == pytest.approx((0.02, -0.02))
    assert (uncalibrated.x, uncalibrated.y) == pytest.approx((0.0, 0.0))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.1])
def test_calibration_points_validate_normalized_range_and_finiteness(bad):
    with pytest.raises(ValueError):
        NormalizedPoint(bad, 0.5)


def test_deadzone_configuration_is_validated():
    with pytest.raises(ValueError):
        relative_offset(NormalizedPoint(0.5, 0.5), NormalizedPoint(0.5, 0.5), deadzone_x=-0.01)
