# Plan: Cross-platform automated testing suite for Custom2kinter

## Context

Custom2kinter is a Tkinter-based GUI library whose entire value proposition is *looking
native and rendering correctly across every desktop environment*: Linux/Windows/macOS,
low/high DPI, single/multi-monitor, Tcl/Tk 8.6 and 9.0, and several Python versions.
Today the project has essentially no automated testing:

- `test/unit_tests/` — 5 class-based scripts (`TestCTk`, etc.) with `main()`/`execute_tests()`
  that open **real Tk windows**, schedule checks via `after()`, and use bare `assert`. No runner,
  no CI, require a live display.
- `test/manual_integration_tests/` — ~32 human-watched scripts, **no assertions**.
- No `conftest.py`, no pytest/tox config, no `.github/workflows/`, no screenshot/visual-diff code.

The hard part is that many rendering glitches only appear in *specific* environments (the macOS
Tk 9.0 transparency bug is the canonical example — see memory `project_macos_tk9_transparency.md`),
and macOS doesn't use native Cocoa so its rendering diverges most. The goal is to catch these
regressions automatically where possible and generate human-reviewable artifacts where full
automation isn't feasible.

**Decisions confirmed with the user:**
- Framework: **pytest** (convert existing tests incrementally).
- Model: **phased** — human-reviewed screenshot/recording artifacts first, then layer automated
  pixel/perceptual-diff regression on committed baselines.
- Infra: **GitHub-hosted runners + self-hosted runners** (real Macs/Windows/Linux for multi-monitor,
  real DPI, and Tk 9 on macOS).
- Matrix axes (all must-have): **OS, Tk 8 vs Tk 9, DPI/scaling, multi-monitor**.

## What makes this tractable (knobs found during exploration)

Rendering is fully controllable programmatically, so we can produce deterministic scenes on any host:

- **Appearance**: `set_appearance_mode("light"|"dark")` (`customtkinter/__init__.py`) bypasses `darkdetect`.
- **Scaling/DPI**: `deactivate_automatic_dpi_awareness()` + `set_widget_scaling()` / `set_window_scaling()`
  (`scaling/scaling_tracker.py`) let us force exact factors regardless of host DPI.
- **Drawing method**: `BaseShape.preferred_drawing_method = "polygons"|"font"|"circles"`
  (`core_rendering/draw_engine.py`, default chosen by `sys.platform` in `core_rendering/__init__.py`)
  — we can exercise **all three render paths on a single OS**.
- **Monitor logic**: `utility/utility_functions.py:get_monitor_info()` is mockable; tooltip/floating-frame
  positioning (`ctk_tooltip.py`, `ctk_floating_frame.py`) can be unit-tested by injecting fake monitor bounds.
  Note: `get_monitor_info()` raises `NotImplementedError` on **Linux**, so true multi-monitor *rendering*
  must run on Windows/macOS or self-hosted machines.
- **Platform branches**: all use `sys.platform` (easy to monkeypatch) — listed across `ctk_tk.py`,
  `dropdown_menu.py`, `ctk_scrollable.py`, `ctk_canvas.py`, `font_manager.py`, `theme_manager.py`.

**Reusable scene sources** (don't write demo UIs from scratch): `run_showroom()` / `_Showroom`
(`customtkinter/__init__.py`) is a single window exercising every widget; plus
`test/manual_integration_tests/test_all_widgets_with_colors.py`, `test_theme_colors.py`, and
`examples/complex_example.py`.

## Architecture

```
test/
  conftest.py            # fixtures + global-state reset (autouse)
  util/
    capture.py           # capture_widget()/capture_window() -> PIL.Image (per-OS backend)
    reset.py             # reset all singleton trackers between tests
    scenes.py            # named scene builders (showroom, single-widget grids, tooltip, floating)
    compare.py           # perceptual diff + baseline lookup by platform-key
  unit/                  # converted from test/unit_tests/ (pytest, headless-friendly logic)
  behavioral/            # scaling math, appearance switch, theme load, monitor-info (mocked)
  visual/
    test_widgets_visual.py
    baselines/<platform-key>/...png   # committed, Phase B
  manual_integration_tests/           # kept as-is for local human use
```

### Critical new pieces

1. **Global-state reset fixture** (`test/util/reset.py`, autouse in `conftest.py`) — *the linchpin*.
   The trackers are module-level singletons (`AppearanceModeTracker`, `ScalingTracker`, `ThemeManager`,
   `BaseShape.preferred_drawing_method`). Without reset, tests leak state. Fixture must: restore default
   drawing method for the OS, reset appearance to "light", reset scaling to 1.0, reload default theme,
   and clear tracker callback/window lists. Pair with a `ctk_root` fixture that creates `CTk()` and
   guarantees `destroy()` teardown.

2. **Parametrizable rendering fixtures** in `conftest.py`: `appearance` (light/dark),
   `drawing_method` (polygons/font/circles), `scaling` (e.g. 1.0, 1.5, 2.0). Visual tests get the
   cartesian product via `pytest.mark.parametrize`/fixture params.

3. **Screenshot helper** (`test/util/capture.py`): `capture_widget(widget) -> PIL.Image`. Calls
   `update_idletasks`/`update`, reads absolute geometry (`winfo_rootx/rooty/width/height`), grabs that
   rect. Backend: use **`mss`** (works on X11/Xvfb, Windows, macOS) with `PIL.ImageGrab` fallback.
   Force a bundled font (assets in `customtkinter/assets/fonts/`) so text metrics are stable, and
   disable animations (call `.set()` instead of `.start()` on progressbars) before capture.

4. **Visual scenes** (`test/util/scenes.py`): build deterministic windows — full showroom, and
   per-widget grids — reusing `_Showroom` / `test_all_widgets_with_colors.py`. Each scene is captured
   once per matrix cell.

5. **Comparison** (`test/util/compare.py`, Phase B): perceptual diff (Pillow `ImageChops` +
   tolerance, or `pixelmatch`) against `baselines/<platform-key>/`, where platform-key =
   `{os}-{tk_major}-{drawing_method}`. On mismatch, write the actual + diff image to an artifacts dir
   and fail. A `--update-baselines` CLI flag (added in `conftest.py`) regenerates baselines.

### Test layers (by ease of automation)

| Layer | Runs where | Asserts |
|-------|-----------|---------|
| Smoke (instantiate every widget, configure/cget round-trip, geometry) | All OS, Xvfb on Linux | bare logic, no pixels |
| Behavioral (scaling math, appearance switch, theme load, monitor-info via mock) | Any host (mock `sys.platform`/`get_monitor_info`) | deterministic values |
| Visual still (PNG per matrix cell) | All OS | Phase A: artifact only; Phase B: pixel-diff vs baseline |
| Animation/interaction (indeterminate progressbar, slider drag, tooltip hover, multi-monitor) | self-hosted + macOS/Win runners | recordings (ffmpeg) for human review |

## CI design (`.github/workflows/`)

- **`tests.yml`** — push/PR. Matrix `os: [ubuntu, windows, macos] × python: [3.9, 3.12, 3.13]`.
  Linux wraps pytest in `xvfb-run` (or `pytest-xvfb`); Windows/macOS use the runner's real display.
  Runs smoke + behavioral + visual-still (Phase A: capture & **upload artifacts**, no gating).
  Generate an HTML **contact sheet** of all PNGs as a single reviewable artifact.

- **`visual.yml`** — Phase B gating. Most-deterministic cell first: **Ubuntu + Xvfb, all three drawing
  methods**, diff against committed baselines, upload actual+diff on failure. Expand to Windows/macOS
  baselines as they stabilize.

- **`self-hosted.yml`** — `runs-on: [self-hosted, <label>]`, triggered by label/schedule (not every PR):
  - multi-monitor rendering (tooltip/floating-frame) on real dual-display Win/macOS,
  - real high-DPI capture,
  - **Tk 9 on macOS** incl. a dedicated regression scene for the transparency bug.

- **Tk 8 vs Tk 9**: GH `setup-python` ships Tk 8.6; add a job using a **Tk 9** build via conda/Homebrew
  (or Python 3.13+ where bundled) to cover both. Full macOS-Tk9 coverage lives on self-hosted.

## Files to create / modify

- `pyproject.toml` — add `[project.optional-dependencies] test = ["pytest", "pytest-xvfb", "mss", "pillow", "pixelmatch"]`
  and a `[tool.pytest.ini_options]` section (markers: `visual`, `selfhosted`, `slow`; testpaths).
- New: `test/conftest.py`, `test/util/{reset,capture,scenes,compare}.py`.
- New test dirs: `test/unit/`, `test/behavioral/`, `test/visual/` (+ `baselines/`).
- Convert `test/unit_tests/*.py` (the `assert`-based `after()` checks) into pytest functions using
  `ctk_root`; keep their assertions, drop `mainloop()`.
- New: `.github/workflows/tests.yml`, `visual.yml`, `self-hosted.yml`.
- Update `CLAUDE.md` test section once pytest is the norm.
- Reuse (no change): `customtkinter.run_showroom`/`_Showroom`, `test_all_widgets_with_colors.py`,
  `test_theme_colors.py`, `examples/complex_example.py`.

## Milestones (phased)

- **M1 — Foundation**: pytest config, `conftest.py`, reset fixture, convert existing unit tests, smoke
  tests for every widget. `tests.yml` green on Linux(Xvfb)/Win/macOS. *Exit: CI gates logic regressions.*
- **M2 — Artifacts (human review)**: `capture.py` + scenes + Phase-A PNG/contact-sheet upload; ffmpeg
  recordings for animated widgets. *Exit: every PR produces a visual contact sheet.*
- **M3 — Visual regression**: `compare.py`, commit Linux baselines for all 3 drawing methods,
  `visual.yml` gates pixel drift; `--update-baselines` workflow documented. *Exit: visual gating on Linux.*
- **M4 — Matrix expansion**: add appearance×scaling×Tk8/Tk9 cells; Windows/macOS baselines.
- **M5 — Self-hosted**: register runners; multi-monitor + real-DPI + macOS-Tk9 transparency regression
  scene. *Exit: the environment-specific bugs that motivated this are covered.*

## Verification

- Local fast loop: `pip install -e ".[test]"` then `xvfb-run -a pytest test/unit test/behavioral`
  (Linux) or `pytest test/unit test/behavioral` (Win/macOS).
- Visual capture locally: `xvfb-run -a pytest test/visual -m visual` → inspect PNGs / contact sheet in
  the artifacts dir.
- Regenerate baselines: `xvfb-run -a pytest test/visual -m visual --update-baselines` (commit per-platform).
- Multi-monitor logic without hardware: behavioral tests monkeypatch `get_monitor_info()` and assert
  tooltip/floating-frame placement; real rendering validated on self-hosted dual-display runners.
- Confirm matrix runs: trigger `tests.yml` (PR), `visual.yml` (PR), `self-hosted.yml` (label/manual);
  verify artifacts upload and that an intentional pixel change fails `visual.yml` with a diff image.
- Sanity-check the macOS Tk 9 transparency regression: the dedicated scene reproduces the white/black
  corner artifact on self-hosted macOS-Tk9 and passes once fixed.
