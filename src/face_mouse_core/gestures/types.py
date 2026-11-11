"""Typed gesture names and emitted event values."""

import math
from dataclasses import dataclass
from enum import Enum


class GestureType(str, Enum):
    NONE = "none"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    DRAG_TOGGLE = "drag_toggle"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"


@dataclass(frozen=True)
class GestureEvent:
    """A recognized gesture at an explicit monotonic timestamp in seconds."""

    gesture: GestureType
    timestamp_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.gesture, GestureType):
            raise TypeError("gesture must be a GestureType")
        if not math.isfinite(self.timestamp_seconds) or self.timestamp_seconds < 0:
            raise ValueError("timestamp_seconds must be finite and non-negative")
