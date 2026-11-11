# Windows Face Mouse Pro behavior analysis

This report is based on a read-only inspection of the sibling `../face-mouse-pro`
repository. The paths below are relative to that repository. “Verified” means
the behavior is present in source or test code; product prose and comments are
identified separately where implementation does not match the claim.

## Gesture detection

| Existing file and symbol | Current behavior (verified) | Reusable logic / proposed core location | Tests needed to preserve behavior |
|---|---|---|---|
| `src/core/gesture_detector.py` — `GestureAction`, `EyeState`, `GestureDetector.__init__`, `update_parameters`, `process` | Stateful per-frame detector. `process` accepts eye/mouth landmarks and optional `current_time`; absent time falls back to `time.perf_counter()`. It computes EAR/MAR and returns `NONE`, `LEFT_CLICK`, `RIGHT_CLICK`, `DOUBLE_CLICK`, or `DRAG_TOGGLE`; mouth-open is exposed as state. It logs from the algorithm module. | Extract action/event/state data to `gestures/types.py`; make a pure input value containing precomputed eye ratios, MAR and required timestamp (the host may use shared EAR/MAR helpers); type settings in `config.py`; detector state machine to `gestures/detection.py`. Keep default wall-clock acquisition and logging in the application adapter. | Deterministic timestamp-sequence tests; action enumeration; initial state; no-face handling policy; config update behavior; call-order and boundary behavior. Existing `tests/test_gesture_detector.py` covers natural bilateral suppression, delayed left click, double click, right click, and long-blink drag toggle. |
| `src/core/gesture_detector.py` — `process` bilateral blink handling | Both eyes below `blink_ear_threshold` on one frame are treated as a natural blink, and both eye states/counters reset without a click. The implemented predicate is simply both closed; the constructor accepts `both_eyes_natural_blink_ratio_diff=0.05` but this value is not read by `process`. | `gestures/detection.py`, once desired behavior is confirmed. Do not silently implement the unused ratio-difference option as if it were current behavior. | Bilateral closed frames suppress both click actions; test differing left/right EAR values to prove current code only checks threshold and does not use the ratio-difference value. |
| `src/core/gesture_detector.py` — `process` left-eye click/long blink | EAR is closed when `< threshold`; a left-eye close starts on first closed frame, frame count increments on subsequent closed frames. A long blink is checked on subsequent closed frames using elapsed timestamp and triggers `DRAG_TOGGLE` when duration `>=` configured duration and not in cooldown. On release, click is eligible if count is inclusive `min_frames <= frames <= max_frames`, not in cooldown, and not bilateral. Eligible first blink is buffered; a subsequent eligible blink within the configured window emits double click. Pending click emits left click when elapsed time is strictly `>` the window. | `gestures/detection.py` with explicit timestamps and frame count input or frame-by-frame observation state. Preserve inequalities carefully. | Below/equal/above threshold; exact min/max counts; exact duration; exact timeout boundary (`>`); cooldown boundary; pending-click clearing on drag/right click; timestamp gaps and repeated timestamps. |
| `src/core/gesture_detector.py` — `process` right-eye click and cooldown | A right-eye blink emits `RIGHT_CLICK` immediately on release for inclusive frame counts and when not in global cooldown; it clears pending left click. A click cooldown is based on timestamp delta from `last_action_time`. | Same gesture detector. | Right-eye blink duration/frame count boundaries; cooldown; interaction with pending left click; bilateral blink. |
| `src/core/gesture_detector.py` — mouth state in `process` | MAR is open when `>` `mouth_mar_threshold`. Consecutive open frames increment; `is_mouth_open` becomes true at `mouth_open_min_frames`. A closed frame resets count/state immediately. This does not produce a scroll action itself. | `gestures/detection.py` or typed gesture state/event if API semantics are agreed. Host application may map open state to scrolling. | MAR equality/threshold; exactly `mouth_open_min_frames`; reset after a closed frame; runtime settings update (currently update method omits `mouth_open_min_frames`). |
| `src/utils/helpers.py` — `euclidean_distance`, `calculate_ear`, `calculate_mar` | Euclidean distance sums coordinate deltas using `zip`. EAR/MAR both use the first six points and ratio `(distance(P2,P6)+distance(P3,P5))/(2*distance(P1,P4))`. Fewer than six points or horizontal distance `<= 1e-6` returns `0.0`. | `gestures/metrics.py` or `gestures/geometry.py`; accept typed points/sequences and remain pure. Confirm landmark ordering as part of public API. | Exact known geometries; 2D/3D distances; excess point truncation; fewer than six; zero and near-zero baseline; malformed/dimension mismatch input behavior. Existing `tests/test_helpers.py` covers typical EAR/MAR and distances, not all edge cases. |

### Verified gesture timing and values

Values declared by `GestureDetector.__init__` are: EAR `0.21`, blink frame range
`2..14`, double-click window `0.40 s`, long-blink duration `0.80 s`, natural
blink ratio difference `0.05`, MAR threshold `0.45`, mouth-open minimum `3`
frames, and click cooldown `0.35 s`.

`src/config/config_manager.py`'s `DEFAULT_SETTINGS` and
`config/settings.json` both provide most of the same values, but blink max is
`14` in code defaults and `12` in the checked-in JSON. `src/core/gesture_detector.py`
uses constructor defaults only until `update_parameters` is called; app
initialization and settings callbacks provide the config section. `update_parameters`
does not update `both_eyes_natural_blink_ratio_diff` or
`mouth_open_min_frames`, despite both being configurable in defaults/JSON.
No runtime code consumes `both_eyes_natural_blink_ratio_diff` at all.

`GestureAction.SCROLL_UP` and `SCROLL_DOWN` are declared but are not returned by
`GestureDetector.process`. The actual scroll-mode contract is the
`is_mouth_open` flag plus a separate controller call.

## Calibration and input workflow

| Existing file and symbol | Current behavior (verified) | Reusable logic / proposed core location | Tests needed to preserve behavior |
|---|---|---|---|
| `src/core/calibration.py` — `CalibrationManager.__init__`, `calibrate_immediate` | Stores neutral x/y (defaults `0.5`, `0.5`), calibrated flag, list of collected samples, and sample target `10`. Immediate calibration casts both values to float, sets calibrated true and returns a tuple; logs the result. | `calibration/models.py` for neutral point/profile; pure operation in `calibration/algorithms.py` for setting/copying a neutral point. Logging belongs to app. | Immediate calibration return and state; numeric conversion; exact sample count; reset behavior; no storage. |
| `src/core/calibration.py` — `CalibrationManager.add_sample_and_calibrate` | Appends each nose point. Once sample list length is `>= 10`, computes arithmetic mean per axis over all accumulated samples, sets calibrated true, clears samples, logs, and returns true. Before that returns false. It does not reject outliers or validate ranges. | `calibration/algorithms.py` for mean calculation; collection/workflow may be a pure stateful accumulator if needed. Keep persistence separate. | Nine vs ten samples; average with non-identical values; additional calls after completion; sample clearing; reset before completion. |
| `src/core/calibration.py` — `get_relative_offset` | If uncalibrated returns `(0,0)`. Otherwise computes nose minus neutral per axis. If absolute delta is `<` deadzone, returns zero; at or beyond deadzone, subtracts deadzone magnitude while preserving sign. Defaults are `0.008` per axis. | `calibration/algorithms.py` or `cursor/mapping.py` (decision pending ownership): a pure neutral-offset/deadzone calculation over normalized points, with explicit deadzone settings. | Uncalibrated; inside/equal/outside deadzone; positive and negative axes independently; non-default deadzones; neutral center and boundary values. Existing `tests/test_calibration.py` covers basic inside/outside and uncalibrated. |
| `src/core/calibration.py` — `to_dict`; `main.py` calibration key handling | `to_dict` serializes calibrated flag and neutral coordinates. Main app triggers immediate calibration on Space only when tracking data exists; reset key `R` clears runtime calibrated flag and sample list. Main separately persists calibration values via `ConfigManager`. | Keep serialization, key handling, app state, and persistence in Windows adapter. Core may expose a typed neutral calibration value only. | Adapter integration tests for Space/no tracking, successful persistence, reset synchronization. These are Windows application tests, not shared-core unit tests. |
| `main.py` — `FaceMouseProApp.run` pipeline | For a detected face, extracts normalized nose and landmark arrays, calls gesture processing with loop `time.perf_counter()`, dispatches non-`NONE` actions to mouse controller. When calibrated, gets relative offsets from calibration. If mouth state is open, sends `dy` to scroll; otherwise sends `(dx,dy)` to cursor movement. | Shared algorithm owns pure transformations/detection; frame acquisition, orchestration, action dispatch, mode selection, HUD and key inputs remain in Windows app. | Adapter tests around order and mode routing; core tests separately verify pure deterministic steps. |

## Cursor mapping and smoothing

| Existing file and symbol | Current behavior (verified) | Reusable logic / proposed core location | Tests needed to preserve behavior |
|---|---|---|---|
| `src/utils/helpers.py` — `LowPassFilter`, `OneEuroFilter1D`, `OneEuroFilter2D` | One Euro filter uses `tau=1/(2π cutoff)`, `alpha=1/(1+tau/te)`, derivative estimate from previous filtered x, derivative low-pass at `d_cutoff`, adaptive cutoff `min_cutoff + beta*abs(filtered derivative)`, and value low-pass. On first or non-increasing timestamp it resets time and calls x filter with alpha 1.0. Missing timestamps call `time.perf_counter()`. The 2D filter applies independent 1D filters with shared timestamp. | `cursor/smoothing.py`. Require explicit timestamps in core entry points for deterministic replay; test/review what to do with non-increasing timestamps rather than accidentally changing current reset-like behavior. Keep filters dimension-agnostic or normalized-coordinate based. | First sample; stationary and moving signals; irregular timestamp; duplicate/decreasing time; reset; parameter validation; 1D/2D equivalence. Existing test checks one 2D movement case only. |
| `src/core/mouse_controller.py` — `MouseController.__init__`, `move_cursor_relative` | Uses `OneEuroFilter2D(min_cutoff=1.2, beta=0.04)`; filter `d_cutoff` remains default `1.0`. Input deltas optionally invert, then signed power curve `abs(delta)**acceleration_curve`, multiplied by axis sensitivity and screen width/height. Filter runs on screen-pixel deltas. Adds the filtered result to virtual cursor position initialized at screen center; clamps target to a 4 px screen margin. Paused mode returns current integer cursor coordinates. | Extract inversion, signed power response, and dimensionless normalized mapping to `cursor/mapping.py` if desired. Keep screen-size conversion, virtual position based on display, clamping, pause, PyAutoGUI dispatch and failsafe in host app adapter. Smoothing can be reused only after agreeing whether filter inputs/units remain pixels or change to normalized coordinates. | Sign, inversion, exponents, axis sensitivity, scale/units, initial point assumptions, clamping at display adapter, pause behavior, filter's first movement. The controller tests cover init, pause and relative clamping, not all mapping outputs. |
| `src/core/mouse_controller.py` — `handle_scroll` | Uses monotonic time internally; drops calls inside `scroll_cooldown_sec` (`0.08` default), ignores `abs(dy) < scroll_deadzone_y` (`0.02`), then produces fixed-magnitude integer `±scroll_speed` (`30`) based on the sign of `dy`; negative image y maps to positive scroll. OS dispatch and cooldown timestamp update happen on successful call only. | The sign/deadzone/amount math can be pure in a scroll mapping helper, but app-specific scroll APIs, timing source/cooldown orchestration remain outside unless explicitly designed into a core event contract. Scroll direction is not screen-independent behavior? Its sign convention is. | Exact threshold; signs; speed; failed dispatch must not update timer; cooldown boundaries, tested in app adapter. |
| `src/core/mouse_controller.py` — `execute_gesture`, `toggle_pause`, `cleanup` | Dispatches PyAutoGUI clicks, holds/releases mouse for drag toggle, pause releases an active drag, cleanup releases held mouse. These methods depend directly on OS mouse API and app lifecycle. | Remain outside core. Core can return typed gesture actions only. | Windows adapter tests with a mocked mouse API; core tests assert returned events, not OS effects. |

The settings file includes cursor values `sensitivity_x=2.2`,
`sensitivity_y=2.0`, `smoothing_factor=0.65`, deadzones `0.008`, acceleration
curve `1.2`, and false inversion flags. `smoothing_factor` is not read by
`MouseController`; smoothing is fixed at `min_cutoff=1.2`, `beta=0.04`,
`d_cutoff=1.0`. Scroll defaults are speed `30`, deadzone `0.02`, cooldown
`0.08 s`.

## Application-specific functionality to keep outside shared core

| Existing file and symbol | Verified application-specific behavior | Keep outside core | Tests needed |
|---|---|---|---|
| `src/core/camera.py` — `Camera` | Owns OpenCV camera creation, capture, retry, FPS and frame lifecycle. | Entire camera module and device configuration. | Mocked camera lifecycle, failed open/read, reconnect and stop tests in host repository. |
| `src/core/face_tracker.py` — `FaceTracker.process_frame`, `close` | Owns OpenCV color conversion, MediaPipe Face Mesh, landmark index selection, image dimensions, pixel-space landmarks, and rendering-oriented result dictionaries. | Provider library, index constants, frame and pixel conversion, MediaPipe resource lifecycle. | Adapter tests for landmark index/order mapping, normalized coordinate output, absent face and pixel conversion using mocked provider/frame. |
| `src/core/mouse_controller.py` — `MouseController.move_cursor_relative`, `execute_gesture`, `handle_scroll`, `toggle_pause`, `cleanup` | Owns PyAutoGUI screen discovery, cursor dispatch, click/drag/scroll actions, failsafe handling, safe pixel margins, pause state and cleanup. | OS mouse API and screen-specific behavior. | Mock PyAutoGUI tests for dispatch, clamps, fail-safe recovery, pause drag release, scroll cooldown and cleanup. |
| `src/ui/overlay.py` — `HUDOverlay`; `src/ui/settings_window.py` — `SettingsPanel`, `launch_settings_async` | Owns OpenCV rendering, CustomTkinter/Tk UI, widgets and settings interactions. | UI code, event loop and rendering state. | Host GUI tests for rendering inputs and settings callback wiring where practical; no core unit tests. |
| `src/config/config_manager.py` — `ConfigManager` | Owns JSON paths, load/save, default merging, corruption recovery and logging. | Persistence, filesystem paths, migration of old user settings. | Host config tests for default merge, load/save, corrupt JSON recovery, reset and backward-compatible user settings. |
| `main.py` — `FaceMouseProApp.run`, `on_settings_changed`, `shutdown` | Owns loop orchestration, key bindings, menu/settings launch, current mode routing, persistence updates and shutdown. | Host application flow and lifecycle. | Adapter integration tests for event ordering, calibration shortcut behavior, routing, live settings updates and cleanup. |
| `src/utils/logger.py` — `setup_logger`; logging calls in algorithm classes | Configures application logging and emits operational messages. | Logger creation, file/console handlers, algorithm logs. Core functions should return values or raise documented input errors. | Host logging/configuration tests; core tests should assert return/state rather than logs. |

The core should not import OpenCV, MediaPipe, PyAutoGUI, Tkinter, or
CustomTkinter. Landmark index conventions and image-specific coordinate
extraction should be supplied by host adapters.

## Evidence and caveats

Source inspection included `src/core/gesture_detector.py`,
`src/core/calibration.py`, `src/core/mouse_controller.py`,
`src/utils/helpers.py`, `src/config/config_manager.py`,
`src/core/face_tracker.py`, `main.py`, `config/settings.json`, and relevant
tests. `README.md` and `docs/ARCHITECTURE.md` describe intended capabilities,
but when their claims differ from executable code this report treats the source
as the verified current behavior. In particular, do not assume features listed
as future or planned in product prose are implemented.
