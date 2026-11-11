"""Pure facial geometry metrics compatible with the Windows point ordering."""

import math
from collections.abc import Sequence


def euclidean_distance(point_a: Sequence[float], point_b: Sequence[float]) -> float:
    """Return Euclidean distance for matching 2D or 3D coordinates."""
    if len(point_a) != len(point_b) or len(point_a) not in (2, 3):
        raise ValueError("points must have matching 2D or 3D coordinates")
    if not all(math.isfinite(value) for value in (*point_a, *point_b)):
        raise ValueError("point coordinates must be finite")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(point_a, point_b)))


def _aspect_ratio(points: Sequence[Sequence[float]]) -> float:
    """Compute the shared six-point EAR/MAR ratio; short input matches legacy 0."""
    if len(points) < 6:
        return 0.0
    selected = points[:6]
    dimensions = {len(point) for point in selected}
    if len(dimensions) != 1 or next(iter(dimensions)) not in (2, 3):
        raise ValueError("each of the first six points must have matching 2D or 3D coordinates")
    if not all(math.isfinite(value) for point in selected for value in point):
        raise ValueError("point coordinates must be finite")
    vertical_a = euclidean_distance(selected[1], selected[5])
    vertical_b = euclidean_distance(selected[2], selected[4])
    horizontal = euclidean_distance(selected[0], selected[3])
    if horizontal <= 1e-6:
        return 0.0
    return (vertical_a + vertical_b) / (2.0 * horizontal)


def calculate_ear(eye_landmarks: Sequence[Sequence[float]]) -> float:
    """Calculate EAR using outer corner, upper points, inner corner, lower points."""
    return _aspect_ratio(eye_landmarks)


def calculate_mar(mouth_landmarks: Sequence[Sequence[float]]) -> float:
    """Calculate MAR using the established six-point lip ordering."""
    return _aspect_ratio(mouth_landmarks)
