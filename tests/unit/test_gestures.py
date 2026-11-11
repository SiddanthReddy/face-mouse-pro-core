import pytest

from face_mouse_core.config import GestureConfig
from face_mouse_core.gestures import (
    GestureDetector,
    GestureType,
    calculate_ear,
    calculate_mar,
)


def eye_with_ear(ear):
    return [(0.0, 0.0), (0.3, ear / 2), (0.7, ear / 2), (1.0, 0.0), (0.7, -ear / 2), (0.3, -ear / 2)]


def mouth_with_mar(mar):
    return [(0.0, 0.0), (0.25, mar / 2), (0.75, mar / 2), (1.0, 0.0), (0.75, -mar / 2), (0.25, -mar / 2)]


def send(detector, t, left=0.4, right=0.4, mouth=0.1):
    return detector.process(
        eye_with_ear(left), eye_with_ear(right), mouth_with_mar(mouth), timestamp_seconds=t
    )


def test_metrics_match_six_point_windows_formula_and_short_input_behavior():
    points = eye_with_ear(0.2)
    assert calculate_ear(points) == pytest.approx(0.2)
    assert calculate_mar(mouth_with_mar(0.5)) == pytest.approx(0.5)
    assert calculate_ear(points[:5]) == 0.0
    assert calculate_mar([(0, 0)] * 6) == 0.0


def test_metrics_reject_nonfinite_and_mismatched_geometry():
    with pytest.raises(ValueError):
        calculate_ear([(0.0, 0.0)] * 5 + [(float("nan"), 0.0)])
    with pytest.raises(ValueError):
        calculate_mar([(0.0, 0.0)] * 5 + [(0.0, 0.0, 0.0)])


def test_left_click_is_delayed_until_strictly_after_double_click_window():
    detector = GestureDetector(GestureConfig(double_click_window_seconds=0.2))
    assert send(detector, 1.0, left=0.1) is GestureType.NONE
    assert send(detector, 1.03, left=0.1) is GestureType.NONE
    assert send(detector, 1.06) is GestureType.NONE
    assert detector.pending_left_click
    assert send(detector, 1.26) is GestureType.NONE  # Exact boundary is not expired.
    assert send(detector, 1.261) is GestureType.LEFT_CLICK


def test_second_eligible_left_blink_within_window_is_double_click():
    detector = GestureDetector(GestureConfig(double_click_window_seconds=0.4))
    send(detector, 1.0, left=0.1)
    send(detector, 1.03, left=0.1)
    send(detector, 1.06)
    send(detector, 1.15, left=0.1)
    send(detector, 1.18, left=0.1)
    assert send(detector, 1.21) is GestureType.DOUBLE_CLICK
    assert not detector.pending_left_click


def test_right_blink_emits_on_release_and_starts_global_cooldown():
    detector = GestureDetector(GestureConfig(click_cooldown_seconds=0.35))
    send(detector, 1.0, right=0.1)
    send(detector, 1.03, right=0.1)
    assert send(detector, 1.06) is GestureType.RIGHT_CLICK
    send(detector, 1.20, right=0.1)
    send(detector, 1.23, right=0.1)
    assert send(detector, 1.26) is GestureType.NONE


def test_bilateral_closure_is_suppressed_even_when_ratio_difference_setting_varies():
    for difference in (0.0, 0.05, 1.0):
        detector = GestureDetector(GestureConfig(both_eyes_natural_blink_ratio_diff=difference))
        assert send(detector, 1.0, left=0.1, right=0.15) is GestureType.NONE
        assert send(detector, 1.03, left=0.1, right=0.15) is GestureType.NONE
        assert send(detector, 1.06) is GestureType.NONE
        assert not detector.pending_left_click


def test_blink_frame_count_boundaries_are_inclusive():
    config = GestureConfig(blink_min_frames=2, blink_max_frames=3, long_blink_duration_seconds=10)
    for frame_count in (2, 3):
        detector = GestureDetector(config)
        t = 1.0
        for _ in range(frame_count):
            assert send(detector, t, left=0.1) is GestureType.NONE
            t += 0.03
        send(detector, t)
        assert detector.pending_left_click

    too_short = GestureDetector(config)
    send(too_short, 1.0, left=0.1)
    send(too_short, 1.03)
    assert not too_short.pending_left_click

    too_long = GestureDetector(config)
    for i in range(4):
        send(too_long, 1.0 + i * 0.03, left=0.1)
    send(too_long, 1.13)
    assert not too_long.pending_left_click


def test_long_blink_uses_timestamp_duration_inclusive_boundary():
    detector = GestureDetector(GestureConfig(long_blink_duration_seconds=0.5))
    send(detector, 1.0, left=0.1)
    assert send(detector, 1.5, left=0.1) is GestureType.DRAG_TOGGLE


def test_mouth_open_requires_consecutive_frames_and_resets_immediately():
    detector = GestureDetector(GestureConfig(mouth_open_min_frames=3))
    send(detector, 1.0, mouth=0.6)
    send(detector, 1.03, mouth=0.6)
    assert not detector.is_mouth_open
    send(detector, 1.06, mouth=0.6)
    assert detector.is_mouth_open
    send(detector, 1.09, mouth=0.45)
    assert not detector.is_mouth_open


def test_invalid_missing_landmarks_do_not_advance_state_or_trigger_clicks():
    detector = GestureDetector()
    send(detector, 1.0, left=0.1)
    count_before = detector.left_eye_state.closed_frame_count
    result = detector.process(eye_with_ear(0.1), None, mouth_with_mar(0.1), timestamp_seconds=1.03)
    assert result is GestureType.NONE
    assert not detector.last_input_valid
    assert detector.left_eye_state.closed_frame_count == count_before
    send(detector, 1.06)
    assert not detector.pending_left_click


@pytest.mark.parametrize("bad_group", [[], [(0.0, 0.0)] * 5, [(float("nan"), 0.0)] * 6])
def test_invalid_landmark_shapes_are_ignored(bad_group):
    detector = GestureDetector()
    result = detector.process(bad_group, eye_with_ear(0.4), mouth_with_mar(0.1), timestamp_seconds=1.0)
    assert result is GestureType.NONE
    assert not detector.last_input_valid


def test_detector_rejects_nonmonotonic_or_nonfinite_timestamps():
    detector = GestureDetector()
    send(detector, 2.0)
    with pytest.raises(ValueError):
        send(detector, 1.9)
    with pytest.raises(ValueError):
        send(detector, float("inf"))


def test_detector_reset_clears_temporal_state_but_retains_config():
    config = GestureConfig(blink_max_frames=12)
    detector = GestureDetector(config)
    send(detector, 1.0, left=0.1)
    detector.reset()
    assert detector.config is config
    assert detector.left_eye_state.closed_frame_count == 0
    assert detector._last_timestamp is None
