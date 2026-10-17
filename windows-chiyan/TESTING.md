# Validation for the 2026-10-17 motion update

Run from the repository root:

```powershell
python -m unittest discover -s windows-chiyan -v
```

42 tests cover:

- Per-frame durations, full one-shot completion, idle loops, long timer gaps,
  weighted selection without immediate repetition.
- Spring following, stale/slow versus fast release, bounded throws, floor
  friction, settling, negative screen origins and frame-rate comparisons.
- Real Qt mouse events for clicks, double-clicks and drag interruption;
  complete playback of the six action clips, rapid-transition opacity,
  gentle placement, pause/resize/reset, reduced motion and custom menu entries.
- Missing/corrupt optional manifests, invalid and overflowing timings,
  missing frames, traversal and forbidden built-in overrides.

Qt tests run offscreen using temporary INI files. They do not change installed
pets, Codex, the registry preferences or any running user application.

`render_preview.py` rendered 429 frames from the real Qt widget; preview.png and
motion-preview.gif are exports of the actual keyframe player, not video mocks.
The EXE is built with the existing PyQt5/PyInstaller environment on Windows.
An independent code reviewer checked the implementation and the overflow
finding was reproduced, fixed and covered by a passing regression test.

Packaged EXE SHA-256:
`EA81B83685BDC425E09948E1616BA4B175C4F709CF3E79657E5B7B2B2AEF84A7`.
The packaged process was responsive in the interactive Windows session. The
Windows automation helper did not expose the transparent Qt.Tool window, so
native-window screenshot/input verification could not be completed. Actual
widget rendering and mouse-event tests passed using Qt's offscreen platform.

Limits: continuous-video quality, cross-screen throws and multiple simultaneous
pet collisions are not implemented. Physical multi-monitor/DPI combinations
have not been exhaustively tested; physics tests cover negative coordinate
origins and screen bounds. Preview generation additionally requires Pillow.
