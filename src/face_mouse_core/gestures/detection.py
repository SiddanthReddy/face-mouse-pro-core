"""Deterministic, stateful gesture recognition over per-frame landmarks."""

import math
from collections.abc import Sequence
from typing import Optional

from ..config import GestureConfig
from .metrics import calculate_ear, calculate_mar
from .types import GestureType

LandmarkSequence = Sequence[Sequence[float]]


class _EyeState:
    def __init__(self) -> None:
        self.is_closed = False
        self.close_start_time: Optional[float] = None
        self.closed_frame_count = 0
        self.last_blink_release_time = 0.0

    def reset(self) -> None:
        self.is_closed = False
        self.closed_frame_count = 0
        self.close_start_time = None


class GestureDetector:
    """Detect Windows-compatible click and mouth states with explicit time.

    A frame is ignored without changing detector state if any of its three
    landmark groups is missing, short, malformed, or non-finite. Timestamps
    must be finite, non-negative, monotonic seconds. Equal timestamps are
    allowed and frame-count thresholds still advance once per valid call.
    """

    def __init__(self, config: GestureConfig = GestureConfig()) -> None:
        self.config = config
        self.left_eye_state = _EyeState()
        self.right_eye_state = _EyeState()
        self.mouth_open_frames = 0
        self.is_mouth_open = False
        self.last_action_time = 0.0
        self.pending_left_click = False
        self.pending_left_click_time = 0.0
        self.current_left_ear = 0.0
        self.current_right_ear = 0.0
        self.current_mar = 0.0
        self.last_input_valid = True
        self._last_timestamp: Optional[float] = None

    def update_config(self, config: GestureConfig) -> None:
        """Replace thresholds atomically; state is preserved."""
        self.config = config

    @staticmethod
    def _is_landmark_group_valid(points: Optional[LandmarkSequence]) -> bool:
        if points is None:
            return False
        try:
            if len(points) < 6:
                return False
            selected = points[:6]
            dimensions = {len(point) for point in selected}
            if len(dimensions) != 1 or next(iter(dimensions)) not in (2, 3):
                return False
            return all(math.isfinite(value) for point in selected for value in point)
        except (TypeError, ValueError, OverflowError):
            return False

    def process(
        self,
        left_eye_landmarks: Optional[LandmarkSequence],
        right_eye_landmarks: Optional[LandmarkSequence],
        mouth_landmarks: Optional[LandmarkSequence],
        *,
        timestamp_seconds: float,
    ) -> GestureType:
        """Process one observation and return at most one gesture action."""
        if not math.isfinite(timestamp_seconds) or timestamp_seconds < 0:
            raise ValueError("timestamp_seconds must be finite and non-negative")
        if self._last_timestamp is not None and timestamp_seconds < self._last_timestamp:
            raise ValueError("timestamps must be monotonic")

        groups = (left_eye_landmarks, right_eye_landmarks, mouth_landmarks)
        if not all(self._is_landmark_group_valid(group) for group in groups):
            self.last_input_valid = False
            return GestureType.NONE

        # Validation above guarantees six well-formed points for each group.
        assert left_eye_landmarks is not None
        assert right_eye_landmarks is not None
        assert mouth_landmarks is not None
        try:
            left_ear = calculate_ear(left_eye_landmarks)
            right_ear = calculate_ear(right_eye_landmarks)
            mar = calculate_mar(mouth_landmarks)
        except (TypeError, ValueError, OverflowError):
            self.last_input_valid = False
            return GestureType.NONE

        self._last_timestamp = timestamp_seconds
        self.last_input_valid = True
        self.current_left_ear = left_ear
        self.current_right_ear = right_ear
        self.current_mar = mar

        left_closed = left_ear < self.config.blink_ear_threshold
        right_closed = right_ear < self.config.blink_ear_threshold
        mouth_open = mar > self.config.mouth_mar_threshold
        if mouth_open:
            self.mouth_open_frames += 1
            if self.mouth_open_frames >= self.config.mouth_open_min_frames:
                self.is_mouth_open = True
        else:
            self.mouth_open_frames = 0
            self.is_mouth_open = False

        # Verified runtime behavior: simply both below threshold; the
        # configured ratio-difference value is intentionally not consulted.
        natural_bilateral_blink = left_closed and right_closed

        triggered_action = GestureType.NONE
        if self.pending_left_click and (
            timestamp_seconds - self.pending_left_click_time > self.config.double_click_window_seconds
        ):
            self.pending_left_click = False
            triggered_action = GestureType.LEFT_CLICK
            self.last_action_time = timestamp_seconds

        in_cooldown = timestamp_seconds - self.last_action_time < self.config.click_cooldown_seconds

        if left_closed and not natural_bilateral_blink:
            if not self.left_eye_state.is_closed:
                self.left_eye_state.is_closed = True
                self.left_eye_state.close_start_time = timestamp_seconds
                self.left_eye_state.closed_frame_count = 1
            else:
                self.left_eye_state.closed_frame_count += 1
                start = self.left_eye_state.close_start_time
                duration = timestamp_seconds - start if start is not None else 0.0
                if duration >= self.config.long_blink_duration_seconds and not in_cooldown:
                    self.left_eye_state.reset()
                    self.last_action_time = timestamp_seconds
                    self.pending_left_click = False
                    return GestureType.DRAG_TOGGLE
        elif self.left_eye_state.is_closed:
            frames = self.left_eye_state.closed_frame_count
            self.left_eye_state.reset()
            if not natural_bilateral_blink and not in_cooldown and (
                self.config.blink_min_frames <= frames <= self.config.blink_max_frames
            ):
                time_since_last = timestamp_seconds - self.left_eye_state.last_blink_release_time
                self.left_eye_state.last_blink_release_time = timestamp_seconds
                if self.pending_left_click and time_since_last <= self.config.double_click_window_seconds:
                    self.pending_left_click = False
                    self.last_action_time = timestamp_seconds
                    return GestureType.DOUBLE_CLICK
                self.pending_left_click = True
                self.pending_left_click_time = timestamp_seconds

        if right_closed and not natural_bilateral_blink:
            if not self.right_eye_state.is_closed:
                self.right_eye_state.is_closed = True
                self.right_eye_state.close_start_time = timestamp_seconds
                self.right_eye_state.closed_frame_count = 1
            else:
                self.right_eye_state.closed_frame_count += 1
        elif self.right_eye_state.is_closed:
            frames = self.right_eye_state.closed_frame_count
            self.right_eye_state.reset()
            if not natural_bilateral_blink and not in_cooldown and (
                self.config.blink_min_frames <= frames <= self.config.blink_max_frames
            ):
                self.last_action_time = timestamp_seconds
                self.pending_left_click = False
                return GestureType.RIGHT_CLICK

        if natural_bilateral_blink:
            self.left_eye_state.reset()
            self.right_eye_state.reset()

        return triggered_action

    def reset(self) -> None:
        """Clear temporal detector state without changing configuration."""
        self.left_eye_state.reset()
        self.right_eye_state.reset()
        self.left_eye_state.last_blink_release_time = 0.0
        self.right_eye_state.last_blink_release_time = 0.0
        self.mouth_open_frames = 0
        self.is_mouth_open = False
        self.last_action_time = 0.0
        self.pending_left_click = False
        self.pending_left_click_time = 0.0
        self._last_timestamp = None
        self.current_left_ear = self.current_right_ear = self.current_mar = 0.0
        self.last_input_valid = True
