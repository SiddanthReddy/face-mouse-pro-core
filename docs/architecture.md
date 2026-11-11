# Architecture

## Responsibility boundary

`face_mouse_core` is shared by the Windows and future macOS applications. It
accepts plain typed values and returns values for host applications to consume.
The core owns no camera capture, computer-vision library, screen dimensions,
OS mouse API, GUI, keyboard handling, logging, or configuration persistence.
Runtime dependencies are limited to the Python standard library.

## Implemented behavior

- `gestures.metrics` computes Euclidean distance and six-point EAR/MAR ratios.
  Short groups and degenerate horizontal spans return `0.0` as in Windows;
  malformed dimensions and non-finite coordinates raise `ValueError`.
- `gestures.detection.GestureDetector` processes one landmark frame at a time
  with a required monotonic timestamp. It preserves inclusive blink frame
  bounds, strict pending-click timeout, bilateral suppression, delayed left
  click/double-click, right click, long-blink drag toggle, global cooldown and
  mouth-open consecutive-frame state.
- `calibration.algorithms` provides arithmetic mean, a fixed-sample accumulator
  and neutral-relative offsets with the Windows deadzone subtraction rule.
- `cursor.mapping.CursorMapper` maps normalized points with clipping/inversion
  and applies dimensionless signed power/sensitivity to relative offsets.
- `cursor.smoothing` provides EMA and 1D/2D One Euro filters. Timestamps are
  explicit; there is no wall-clock access.
- `config.py` defines frozen, validated settings and performs no file I/O.

Missing or malformed landmark groups are ignored without changing detector
state, matching the host loop's behavior when it skips frames without a face.
Detector timestamps must be finite, non-negative and monotonic; equal
timestamps are allowed, and each valid call still counts toward frame-based
thresholds. Normalized points are finite and constrained to `[0, 1]`.
`CursorMapper.map_coordinates` accepts finite out-of-range values and clamps
them at the boundary. Calibration rejects invalid normalized samples.

## Verified Windows behavior and decisions

`GestureConfig.blink_max_frames` defaults to 14, matching the detector
constructor and `DEFAULT_SETTINGS`; the Windows checked-in JSON contains 12,
which an adapter can pass explicitly. The bilateral ratio-difference setting
is kept for compatibility but remains unused, matching source behavior that
suppresses a frame whenever both EAR values are below threshold. The core
computes EAR/MAR using the verified six-point formula.

The Windows cursor JSON contains `smoothing_factor=0.65`, but the controller
does not consume it. Runtime smoothing is a One Euro filter configured with
`min_cutoff=1.2`, `beta=0.04`, and default `d_cutoff=1.0`. The core expresses
these runtime values in `SmoothingConfig` as `min_cutoff`, `beta`, and
`derivative_cutoff`; it does not reinterpret the unused factor. The separate
EMA class is independently configurable for consumers that choose it.

The core uses normalized space for point mapping and dimensionless values for
relative movement. Windows pixel scaling, virtual cursor state, display clamps,
scroll dispatch and mouse actions remain host responsibilities. The mapping
stage reproduces the signed power and sensitivity formula without multiplying
by display width or height.

## Package map

- `models.py`: immutable validated vectors, normalized points, landmarks and
  timestamped point observations.
- `config.py`: validated gesture, calibration, mapping and smoothing settings;
  no loading or saving.
- `protocols.py`: structural interfaces at host/core boundaries.
- `gestures/`: action values, EAR/MAR metrics and deterministic detector.
- `calibration/`: calibration sample/profile values and pure calculations.
- `cursor/`: normalized mapping, EMA and One Euro filters.
- `tests/unit/`: parity-oriented deterministic tests for boundaries and state.

## Integration guidance

Host applications should convert provider-specific landmark data into ordered
plain coordinate sequences, pass a monotonic timestamp to each detector call,
and translate returned `GestureType` values into their own OS events. Apps may
pass configuration overrides, including `blink_max_frames=12` for the current
Windows JSON value. The core does not determine a clock or persist any values.
