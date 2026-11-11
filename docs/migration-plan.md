# Windows-to-core migration plan

This is a migration proposal only. The Windows sibling repository remains
read-only, and no shared-core algorithms or models are changed by this plan.
Every port should retain the existing Windows behavior unless a deliberate
behavior change is separately approved and tested.

## Source-to-core mapping

| Existing Windows path and symbol | Behavior to extract | Proposed shared-core destination | Keep in Windows application |
|---|---|---|---|
| `src/utils/helpers.py` — `euclidean_distance`, `calculate_ear`, `calculate_mar` | Pure Euclidean metric and six-point EAR/MAR ratio calculations, including current short-input and degenerate denominator returns. | `face_mouse_core/gestures/metrics.py` (new module) | Landmark index selection, MediaPipe extraction, coordinate packaging. |
| `src/core/gesture_detector.py` — `GestureAction` | Action vocabulary: no action, left/right/double click, drag toggle, scroll up/down. | Expand `gestures/types.py` with an enum matching all actions or typed gesture events. Current core has only BLINK and DWELL; migration must resolve naming and meanings first. | Convert returned action/event into OS mouse events. |
| `src/core/gesture_detector.py` — `EyeState`, `GestureDetector.process` | Per-eye frame state, EAR/MAR thresholds, bilateral suppression, left-click pending window, double-click, right click, long-blink drag toggle, cooldown, mouth-open state. | `gestures/detection.py`; explicit timestamp and metrics in a typed observation. | Default wall-clock clock acquisition, logging, reading app dict configuration, tracking/display of current HUD metrics. |
| `src/core/gesture_detector.py` — `update_parameters` | Live threshold updates from gesture settings. | Typed immutable `GestureConfig` passed at construction or explicit typed reconfiguration API in `gestures/detection.py`. | UI callback and persistence; dynamic reconfiguration trigger. |
| `src/core/calibration.py` — `CalibrationManager` | Immediate neutral capture; 10-sample arithmetic mean; calibrated flag transitions; relative offsets with axis deadzones. | `calibration/models.py` and `calibration/algorithms.py`. Consider a pure `mean_point(samples)` and `relative_offset(point, neutral, deadzone)` first. | Space/R key handling, status display, samples tied to face-tracking frames, persistent calibration state/JSON. |
| `src/utils/helpers.py` — `LowPassFilter`, `OneEuroFilter1D`, `OneEuroFilter2D` | Stateful EMA low-pass and adaptive One Euro filter. | `cursor/smoothing.py`. Preserve explicit timestamp behavior and state reset semantics with unit tests. | Choosing wall clock, calling the filter at camera frame cadence, and screen pixel adaptation. |
| `src/core/mouse_controller.py` — first half of `move_cursor_relative` | Axis inversion, signed exponent/acceleration, axis sensitivity scaling. | `cursor/mapping.py`, but refactor interface to avoid screen-size dependency (for example normalized input/output plus an explicit mapping config). | Pixel multiplication by screen width/height and stateful absolute cursor position. |
| `src/core/mouse_controller.py` — later `move_cursor_relative` | One Euro filtered screen deltas, virtual cursor addition, 4 px margin clamp, `pyautogui.moveTo`, fail-safe recovery. | Smoothing mathematics may be shared. | All screen discovery, pixel boundary logic, absolute position, PyAutoGUI invocation, failsafe and error handling. |
| `src/core/mouse_controller.py` — `handle_scroll` | Sign/deadzone/fixed scroll magnitude math may be reusable. | Optional pure `cursor/scroll.py` only if both applications share the behavior. | `perf_counter`, cooldown scheduling, OS scroll call, logging and failure behavior. |
| `src/config/config_manager.py` — `DEFAULT_SETTINGS`, `ConfigManager` | Values/defaults may inform typed core config after conflicts are resolved. | Expand `config.py` with typed gesture, calibration, mapping, smoothing config dataclasses; standard-library only. | JSON schema, file paths, load/save, merge/recovery, UI and device settings. |
| `main.py` — `FaceMouseProApp.run`, `on_settings_changed` | Provides integration ordering: landmarks → gesture event → action dispatch; calibration-relative offset → mouth-scroll or cursor mapping. | No direct main-loop migration; call the shared package from an adapter. | Camera/render loop, mode orchestration, UI, input keys, state persistence, shutdown. |

## Recommended migration sequence

1. **Freeze a behavior reference.** Treat the observed code paths and current
   Windows tests as baseline. Add missing Windows characterization tests in
   the Windows repository only through a separate authorized task; this
   analysis did not modify it. Record exact frame/timestamp sequences for
   threshold boundaries and unusual ordering before porting.
2. **Resolve source-of-truth configuration.** Reconcile constructor defaults,
   `DEFAULT_SETTINGS`, and `config/settings.json`. Current known conflict:
   `blink_max_frames` is 14 in constructor/defaults and 12 in checked-in JSON.
   Decide whether shared defaults represent app config defaults or detector
   fallback defaults. Also decide what to do with the unused
   `both_eyes_natural_blink_ratio_diff` and `smoothing_factor` settings.
3. **Define typed input/output contracts.** Replace implicit timing with
   required explicit timestamps for deterministic stateful logic; define the
   clock unit as monotonic seconds. Preserve the existing behavior that blink
   eligibility also depends on frame counts. A timestamp-only redesign changes
   semantics if frame rate varies, so do not discard frame-count rules without
   an explicit product decision.
4. **Port metric helpers.** Port distance/EAR/MAR into pure typed functions.
   Preserve current six-point ordering and degenerate-input behavior at first.
   Keep MediaPipe indices and frame pixel conversion in the Windows adapter.
5. **Port calibration math.** Separate mean/neutral-offset calculations from
   sample collection UI and JSON persistence. Retain the current ten-sample
   arithmetic mean and deadzone “subtract threshold after crossing” semantics.
6. **Port cursor transforms and smoothing.** Decide which transform stages are
   dimensionless. Test signs, inversion, exponent and filter parameters. Keep
   pixel scale, screen center, clamps and OS input in the adapter. Do not map
   the existing `smoothing_factor=0.65` to a One Euro parameter without
   evidence; it is currently unused by the controller.
7. **Port gesture state machine.** Implement against typed observations and
   explicit configuration; use test vectors created from the current behavior.
   Keep logger calls out of shared code. Reconcile `GestureAction` with
   proposed `GestureType`; do not assume the current `BLINK`/`DWELL` scaffold
   enum covers click intent or timing.
8. **Add Windows adapter.** Translate MediaPipe landmarks and the application's
   monotonic clock to core values; translate returned actions back to existing
   `MouseController` commands. Keep old path available while comparing results
   on recorded deterministic input sequences.
9. **Compare and release separately.** Require exact parity on characterization
   sequences before switching the Windows app. Then repeat adapter integration
   on Windows and macOS. This plan does not authorize changes in either host
   application.

## Compatibility and migration risks

| Risk | Evidence / impact | Mitigation |
|---|---|---|
| Configuration conflicts | Detector constructor and `DEFAULT_SETTINGS` use max blink frames 14; tracked JSON uses 12. Different initialization paths may yield different accepted blink lengths. | Decide canonical per-app typed values; characterize both startup paths before migration. |
| Declared but unused settings | `both_eyes_natural_blink_ratio_diff` is accepted but bilateral suppression only tests both eyes closed. `smoothing_factor` exists in config/UI but is not used in cursor filter construction. `update_parameters` omits natural-blink ratio and mouth-open min frames. | Preserve actual behavior first; mark unused controls clearly; avoid silently activating or dropping settings. |
| Frame-rate dependence | Blink validity uses number of frames, while long blink and click windows use seconds. Replacing all timing with durations changes behavior at varying frame rate. | Keep explicit timestamps plus frame count semantics in first port; consider time-only calibration as a separate behavior change. |
| Time handling edge cases | `process` has an optional implicit clock; One Euro also accepts optional implicit timestamps. The One Euro filter treats non-increasing times as a direct update/reset-time path. | Core must receive explicit monotonic seconds; characterize duplicate/decreasing timestamp behavior and document invalid-input policy. |
| State-machine ordering | Pending single left click may be emitted at start of a frame while later code can also process another state path; early returns occur for drag/double/right click. Cooldown derives from a global last action. Small refactors can reorder outcomes. | Keep transition-focused tests and match action priority and pending/cooldown state effects explicitly. |
| Coordinate units differ | Calibration deltas are normalized nose coordinates. Mouse controller scales powered deltas by screen width/height before filtering; filter values are pixels. A normalized-only core filter will alter smoothing feel. | Keep transform stages explicit and compare output traces across representative display sizes. |
| Landmark geometry contracts | EAR/MAR depend on exact six-point order; face tracker supplies MediaPipe indices and normalized x/y/z tuples. | Put named typed metric input contracts in core; keep provider-specific index order mapping in each app adapter. |
| Adapter/platform behavior | Screen enumeration, 4 px clamp, PyAutoGUI fail-safe, drag release, camera, GUI and config storage are Windows-host behavior. | Leave all these in host adapter; test them with mocks in the Windows repository. |
| Error/input behavior | Helper functions return zero for fewer than six points or degenerate width; calibration accepts arbitrary floats; no validation for non-finite values. Adding model validation can change outcomes or raise new exceptions. | Match old behavior in parity layer first, then approve validation as a separately documented change. |
| Current scaffold mismatch | Core scaffold currently defines `GestureType.BLINK/DWELL`, simple `GestureConfig`, generic point mapping/smoothing protocols, and calibration sample/profile values. This does not represent the Windows action enum, thresholds, or mapping contract. | Treat the current scaffold as provisional public API. Review/bump its API before adding engine code; do not force a lossy adapter. |

## Test parity matrix

Before switching the Windows host to the shared package, the shared-core suite
should include these deterministic groups:

- EAR/MAR known points, insufficient landmarks and zero horizontal span.
- Gesture state: unilateral left/right; bilateral blink; blink frame-count
  min/max; overlong blink; double-click within/equal/outside window; pending
  single click after strictly exceeding timeout; cooldown; long blink at exact
  duration; mouth-open consecutive frame threshold and immediate close reset.
- Calibration: uncalibrated offset, immediate calibration, 9/10-sample
  boundary, arithmetic mean, reset, signed deadzone inside/equal/outside.
- Mapping: positive/negative directions, inversion, acceleration exponent,
  per-axis sensitivities, scale-independent behavior and boundary conversion
  in host adapter.
- Smoothing: first point, stable input, movement response, explicit timestamps,
  duplicate/backward time, parameter values, reset, and parity trace for
  1D/2D filtering.
- Windows adapter: normalized-to-pixel scaling, screen clamp, pause, OS action
  mapping, drag cleanup, scroll cooldown and dispatch error paths (mock OS API).
