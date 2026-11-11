# Face Mouse Pro Windows integration publication checklist

This checklist covers the separate Windows application repository. It has not
been modified as part of this core release preparation.

## Before publishing the integration

- [ ] Review the complete Windows Git status and confirm each pending change is
  intended for the integration branch.
- [ ] Publish an approved core commit so CI's current `main` checkout resolves.
- [ ] Run the full Windows test suite on supported Python 3.10+ with its real
  dependencies installed.
- [ ] Run adapter and deterministic parity tests against the Windows baseline.
- [ ] Build and launch the PyInstaller executable on Windows; verify the core
  modules are bundled.
- [ ] Confirm the core installation source and version/commit pin used by CI
  and release builds.
- [ ] Review configuration mapping, timestamp conversion, gesture lifecycle,
  calibration behavior, and smoothing behavior against the integration docs.
- [ ] Review the Windows diff for unrelated features and generated files.
- [ ] Commit and push the Windows integration separately after approval.
- [ ] Publish the Windows application only after its supported-platform checks
  pass.

## Known preparation gaps

- The remote core `main` branch does not currently resolve.
- A supported Windows Python 3.10+ test and PyInstaller build have not been
  run in this preparation environment.
- The pending Windows integration working tree has not been committed.

No Windows publication action has been performed.
