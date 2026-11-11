# Windows application integration plan

This plan describes the Milestone 4 adapter boundary between the shared core
and `../face-mouse-pro`. The Windows repository is on branch
`migration/mac-baseline` with pending, uncommitted Milestone 4 integration
changes. Separately, the shared-core repository is on `main` with its initial
project files untracked and no commits yet. These are distinct repository
statuses; the Windows integration is not described here as committed, pushed,
released, or fully verified. The sibling app remains a separate project and is
not vendored into this core.

## Current duplication and integration boundaries

| Windows symbol | Current responsibility | Integration decision |
|---|---|---|
| `src/core/gesture_detector.py:GestureDetector` | Computes EAR/MAR, holds the frame state machine, thresholds, click timing, mouth-open state, and logging. | Retain the class and constructor/method surface as a compatibility adapter. Delegate metric calculations and state transitions to `face_mouse_core`; translate core action enum values to the legacy enum. Preserve optional timestamp fallback only in the Windows adapter. |
| `src/core/calibration.py:CalibrationManager` | Holds neutral coordinates and calibration sample state; calculates ten-sample average and deadzone-adjusted offsets; logs. | Retain class/state and tuple return API. Delegate averaging, accumulation, validation, and offsets to core functions. Keep host JSON persistence and logging where they are. |
| `src/utils/helpers.py:calculate_ear`, `calculate_mar`, `OneEuroFilter1D/2D`, `ExponentialFilter` | Duplicates pure geometry and filtering. | Preserve import-compatible wrappers but delegate math/filter state to core. Keep a `time.perf_counter()` fallback in wrappers that are legacy app API; pass timestamps explicitly from the main loop to the actual controller path. |
| `src/core/mouse_controller.py:MouseController` | Combines movement transformation, pixel scaling, filtering, display bounds, PyAutoGUI dispatch, and mouse lifecycle. | Delegate signed power/sensitivity transformation and filtering to core. Keep screen dimensions, virtual cursor, pixel scaling, 4 px clamp, PyAutoGUI, fail-safe recovery, clicks, drag, scroll and pause state in the Windows class. |
| `main.py:FaceMouseProApp.run` | Acquires timestamps and runs camera → tracker → gesture → calibration → controller → HUD/key handling. | Keep orchestration and pass its `now` value to gesture processing. The cursor adapter obtains `perf_counter()` at the filter call, matching the legacy filter timing point. Retain the same no-face frame skip and action dispatch. |
| `src/core/face_tracker.py:FaceTracker.process_frame` | Converts OpenCV/MediaPipe output to coordinate arrays and rendering dictionaries. | Keep unchanged. It already returns six ordered feature points consumed by the core-backed adapter. Do not move MediaPipe/OpenCV into shared core. |
| `src/config/config_manager.py:ConfigManager` | JSON loading, persistence and settings merges. | Keep unchanged. Translate dictionaries to typed core configs at adapter construction/update boundaries. |

## Configuration mapping

| Windows JSON key | Core field | Notes |
|---|---|---|
| `gestures.blink_ear_threshold` | `GestureConfig.blink_ear_threshold` | Pass through unchanged. |
| `gestures.blink_min_frames` / `blink_max_frames` | `blink_min_frames` / `blink_max_frames` | Pass through app config. Constructor default stays 14; checked-in JSON value 12 stays 12. |
| `double_click_window_sec` | `double_click_window_seconds` | Unit conversion is identity: seconds. |
| `long_blink_duration_sec` | `long_blink_duration_seconds` | Unit conversion is identity: seconds. |
| `both_eyes_natural_blink_ratio_diff` | same named core field | Remains unused, preserving verified runtime behavior. |
| `mouth_mar_threshold` / `mouth_open_min_frames` | same named core fields | Both are passed at construction. The compatibility adapter preserves the legacy live-update behavior, which does not change `mouth_open_min_frames`. |
| `click_cooldown_sec` | `click_cooldown_seconds` | Unit conversion is identity: seconds. |
| `cursor.sensitivity_x/y`, `acceleration_curve`, `invert_x/y` | `CursorMappingConfig` | Core produces dimensionless mapped displacement; adapter multiplies by screen width/height after mapping. |
| `cursor.deadzone_x/y` | `CalibrationConfig` or `relative_offset` arguments | Preserve deadzone subtraction before mapping. Settings UI updates stay in host app. |
| One Euro runtime `min_cutoff=1.2`, `beta=0.04`, `d_cutoff=1.0` | `SmoothingConfig` | These values come from the actual Windows filter constructor/default. `cursor.smoothing_factor=0.65` is not consumed by the current controller; do not map it to any One Euro parameter. |
| `calibration.neutral_x/y`, `calibrated` | Windows `CalibrationManager` state | Core receives neutral point values for calculations; persistence and calibrated flag remain host-owned. |

## Timestamp, event and coordinate lifecycle

`main.py` already captures `time.perf_counter()` once per camera frame and
passes that monotonic-seconds value to the gesture adapter. The controller
adapter obtains `perf_counter()` immediately before the One Euro filter, which
matches the legacy filter's timing point (after tracking and mapping work) and
keeps the core call explicit. The detector returns at most one `GestureType`;
the Windows adapter maps it to the existing `GestureAction`, and
`MouseController.execute_gesture` remains the OS event boundary. Mouth-open
remains a detector state flag; `main.py` routes the calibrated vertical offset
to `handle_scroll` when that flag is set.

FaceTracker returns ordered normalized x/y tuples for each of six eye and mouth
landmarks plus normalized nose coordinates. The adapter passes eye/mouth
sequences directly to the core. Calibration wraps nose coordinates as
`NormalizedPoint`, applies deadzone offsets, then returns the existing `(dx,
dy)` tuple. Core cursor mapping applies signed power, sensitivity and inversion
to this offset; the host scales by screen size, runs the One Euro filter on
pixel deltas to preserve current feel, updates virtual position, clamps, and
dispatches PyAutoGUI.

If a required landmark group is malformed, the core deliberately emits no
gesture and holds its last state. This prevents bad/missing input from being
interpreted as eye closure. The normal Windows no-face path already skips the
detector call entirely.

## Behavior parity gates

Before switching each path, run the existing Windows regression tests plus
adapter tests. Characterize thresholds and timing with the current Windows
test vectors: left/right click, double click, bilateral blink suppression,
long blink drag toggle, calibration mean/deadzone, and One Euro outputs. Compare
legacy helper outputs with core outputs for fixed 2D/3D geometry and timestamp
sequences. Keep original behavior available in Git history and do not remove a
path until its replacement passes those parity checks.

Known deliberate differences to investigate/document: normalized coordinates
are validated in `[0,1]`; malformed groups are ignored (the old helper returned
EAR/MAR zero for short arrays); core timestamps reject backward values whereas
the old gesture detector accepted them; the core One Euro implementation
preserves the Windows non-increasing timestamp pass-through behavior. The
core's explicit handling of a closure starting at exactly `0.0` also corrects
the old detector's `timestamp or current_time` duration calculation edge case.

## Installation and distribution

For a sibling checkout during development, install the core into the Windows
application's Python environment with:

```powershell
python -m pip install -e ..\face-mouse-pro-core
python -m pip install -r requirements.txt
```

The Windows app currently requires Python 3.10+, while the core supports 3.9+.
For executable builds, install the core in the build environment before
running the app's PyInstaller build; the imported package should then be
collected as an installed Python dependency. A portable pinned Git/package
dependency cannot be declared until the separate core repository has an
approved commit or release. Do not add a machine-specific absolute path to app
metadata or combine the repositories.

## Validation scope and environment note

The local execution environment inspected for this plan is Python 3.9.6 and
does not have the Windows app's OpenCV, MediaPipe, PyAutoGUI, or CustomTkinter
dependencies installed. It therefore cannot run the Windows app's full suite
as configured (`requires-python >=3.10`) or exercise real PyAutoGUI behavior.
Pure core parity and mock-based adapter tests can run here; final application
and executable validation still needs the app's supported Windows environment.
