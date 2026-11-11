# Face Mouse Pro Core 0.1.0 — draft release notes

**Status:** prepared for review; not committed, tagged, or published.

## Overview

The initial shared engine package provides platform-independent components for
the Windows and future macOS Face Mouse Pro applications. Runtime dependencies
are limited to the Python standard library, and Python 3.9 or later is
supported.

## Included APIs

- Gesture action values, deterministic `GestureDetector`, EAR/MAR, and
  Euclidean distance helpers.
- Calibration sample models, arithmetic mean, fixed-size sample accumulator,
  and neutral-relative deadzone offsets.
- Normalized point mapping, dimensionless cursor movement transforms,
  exponential smoothing, and 1D/2D One Euro filters.
- Typed, immutable configuration and coordinate models.

## Compatibility notes

- The default maximum blink count is 14 frames, matching the verified Windows
  detector constructor. Windows settings may explicitly supply 12.
- The bilateral eye-ratio difference option is retained but inert, matching
  current Windows behavior.
- The Windows JSON `smoothing_factor=0.65` is not treated as active runtime
  behavior. One Euro parameters reflect the controller's verified values.
- The package performs no camera capture, UI, screen sizing, OS mouse control,
  logging, or settings persistence.

## Installation

Local development uses `python -m pip install -e ".[test]"`. Git installation
requires a published commit or tag; none is available yet. The package includes
MIT license metadata and its license file.

## Validation performed

The shared-core suite currently passes 50 tests on Python 3.9.6. The full
Windows application suite/build still needs validation in its supported
Python 3.10+ Windows environment. See the integration plan and Windows
repository report for details.
