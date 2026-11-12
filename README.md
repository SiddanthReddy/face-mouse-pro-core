# Face Mouse Pro Core

**Version 0.1.0 · published source revision (no tagged release yet)**

Face Mouse Pro Core is a platform-independent Python engine shared by the
Face Mouse Pro Windows and macOS applications. It contains reusable gesture,
calibration, cursor mapping, and smoothing algorithms. Camera access, facial
landmark providers, screen geometry, mouse control, GUI code, logging, and
configuration persistence remain application responsibilities.

## Capabilities

- Deterministic gesture detection over ordered landmark coordinates and
  explicit monotonic timestamps.
- Eye Aspect Ratio (EAR), Mouth Aspect Ratio (MAR), and Euclidean distance
  calculations.
- Immediate calibration helpers, fixed-size sample averaging, and
  neutral-relative offsets with deadzone compensation.
- Normalized point mapping and dimensionless relative cursor movement
  transforms.
- Exponential moving average and 1D/2D One Euro smoothing filters.
- Frozen, validated configuration and data models.

Runtime code uses only the Python standard library. Python 3.9 or later is
required.

## Installation

### Local development

From a cloned core repository:

```sh
python -m pip install -e ".[test]"
python -m pytest
```

For the Windows app's sibling development checkout, install the core in the
same environment before installing/running the Windows application:

```powershell
python -m pip install -e ..\face-mouse-pro-core
```

### Install from the published Git commit

The source is published on `main` at commit
`7ae514e29578f09a819ae4f5bb84218049e338e5`. No version tag or GitHub Release
has been published yet. Install the immutable source revision with:

```sh
python -m pip install "face-mouse-pro-core @ git+https://github.com/SiddanthReddy/face-mouse-pro-core.git@7ae514e29578f09a819ae4f5bb84218049e338e5"
```

Use this immutable commit for reproducible application builds. The Windows app pins the same SHA in `requirements.txt` and its CI workflow.

## Quick example

The host application supplies the six ordered points for each feature and an
explicit monotonic timestamp in seconds:

```python
from face_mouse_core.config import GestureConfig
from face_mouse_core.gestures import GestureDetector, GestureType

detector = GestureDetector(GestureConfig(blink_max_frames=12))
action = detector.process(
    left_eye_landmarks=left_eye_points,
    right_eye_landmarks=right_eye_points,
    mouth_landmarks=mouth_points,
    timestamp_seconds=frame_time_seconds,
)

if action is GestureType.LEFT_CLICK:
    handle_left_click_in_the_host_application()
```

The core returns gesture values and does not emit OS events. Missing, short,
malformed, or non-finite landmark groups are ignored without advancing
detector state. Timestamps must be finite, non-negative, and monotonic; equal
timestamps are allowed.

## Windows behavior compatibility

The detector's default maximum blink length is 14 frames, matching the
verified Windows constructor and configuration defaults. The checked-in
Windows JSON sets 12, so the Windows adapter passes that configured value.
The bilateral blink ratio-difference setting is represented for compatibility
but remains unused because the verified Windows detector suppresses a frame
whenever both eyes are below the EAR threshold.

The Windows `smoothing_factor=0.65` setting is not consumed by its controller.
The shared core exposes the verified runtime One Euro settings separately:
`min_cutoff=1.2`, `beta=0.04`, and `derivative_cutoff=1.0`.

## Platform boundary

The shared package does not import or control OpenCV, MediaPipe, PyAutoGUI,
Tkinter, CustomTkinter, cameras, displays, keyboards, or mouse devices. Each
host application converts provider output to plain coordinates, supplies
timestamps/configuration, and translates core values to its own OS actions.
See [the architecture](docs/architecture.md), [Windows behavior analysis](docs/windows-behavior-analysis.md), and [the Windows integration plan](docs/windows-integration-plan.md).

## Tests

Install the test extra and run the unit suite:

```sh
python -m pip install -e ".[test]"
python -m pytest
```

The tests cover gesture state/timing boundaries, invalid inputs, calibration,
cursor mapping, smoothing, and configuration validation. Windows adapter
instructions and application-specific checks are documented in the Windows
repository's `docs/WINDOWS_CORE_INTEGRATION.md`.

## Release status and license

Version `0.1.0` is present in the published source and package metadata. It has not yet been tagged or published as a GitHub Release. Face Mouse Pro Core is distributed under the MIT License; see
[`LICENSE`](LICENSE). The copyright attribution follows the existing
Face Mouse Pro application repository's license notice.
