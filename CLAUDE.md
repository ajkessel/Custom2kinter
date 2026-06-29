# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Custom2kinter is a community-maintained fork/continuation of [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), a modern-looking widget library built on top of Tkinter. The fork numbering continues the original (first release `v5.3.0`) and is meant to be a drop-in replacement: the package is named `custom2kinter` on PyPI but **is still imported as `customtkinter`**, and the source directory is still `customtkinter/`. Do not rename imports or the package directory.

Requires Python >= 3.9. Runtime deps: `darkdetect`, `typing_extensions`, `packaging`, `pillow`.

## Commands

```bash
pip install -e .                      # install for development
pip install -r requirements.txt       # runtime deps only

python -m customtkinter               # nothing; instead run the showroom:
python -c "import customtkinter as ctk; ctk.run_showroom()"   # interactive widget gallery

python examples/complex_example.py    # run an example
```

Tests use **pytest** (`pip install -e ".[test]"`). They open real Tk windows, so they need a display: on headless Linux run them under Xvfb. Layout: `test/unit/` (per-widget logic + smoke), `test/behavioral/` (scaling/theme/monitor logic, much of it display-free and mockable), `test/visual/` (screenshot/regression, marked `visual`). Shared fixtures live in `test/conftest.py` — notably the autouse `reset_global_state` (resets the singleton trackers between tests), `ctk_root`, and the indirectly-parametrizable `appearance`/`drawing_method`/`scaling` fixtures.

```bash
xvfb-run -a pytest test/unit test/behavioral     # Linux (headless)
pytest test/unit test/behavioral                 # Windows/macOS (real display)
pytest test/behavioral/test_geometry_parsing.py  # display-free subset runs anywhere
pytest -k tooltip                                 # run a single test by name
```

CI is in `.github/workflows/tests.yml` (Linux+Xvfb / Windows / macOS × Python 3.9/3.12/3.13). The legacy `test/unit_tests/*.py` (class-based `main()` scripts) referenced removed public attrs (`current_width`); they're superseded by `test/unit/`. `test/manual_integration_tests/` stays for local human-watched checks. Pre-commit hooks (yaml/whitespace/eof + setup-cfg-fmt): `pre-commit run --all-files`.

## Release process (see `dev-proces.md`)

Development happens on the `develop` branch; one feature per PR; no commented-out code; no "changed/fixed/was" comments. Bump version with `tbump <version>` (updates `pyproject.toml` and `customtkinter/__init__.py` together — keep `__version__` in sync). Update `CHANGELOG.md`. PRs merge `develop` → `master` after owner approval. Publish with `python -m build && twine upload dist/*`.

## Architecture

The public API surface is assembled in `customtkinter/__init__.py` — every widget, window, manager, and module-level function (`set_appearance_mode`, `set_default_color_theme`, `set_widget_scaling`, `run_showroom`, etc.) is re-exported there. Add new public widgets to this file.

Everything lives under `customtkinter/windows/`:

- **`windows/`** — top-level containers: `CTk` (root window), `CTkToplevel`, `CTkInputDialog`. These handle OS-level concerns (DPI awareness, dark title bars, geometry/scaling).
- **`windows/widgets/`** — all the `CTk*` widgets (button, entry, slider, tabview, etc.), each in its own `ctk_*.py`.
- **`windows/widgets/core_widget_classes/`** — base classes every widget inherits from: `CTkWidget` (base; itself a `tkinter.Frame`), `CTkContainer`, `CTkScrollable`, plus `dropdown_menu`. `CTkWidget` owns dimensions, `bg_color`/transparency, scaling, and appearance-mode wiring.
- **`windows/widgets/core_rendering/`** — the custom rendering layer. `CTkCanvas` plus `draw_engine.py`, which draws rounded rectangles, arrows, checkmarks, stars, etc. as `BaseShape` dataclasses. Three interchangeable `DRAWING_METHODS` exist — `"polygons"`, `"font"`, `"circles"` — selected per-platform (`polygons` on macOS, `font` elsewhere; `BaseShape.preferred_drawing_method`). This is how widgets get smooth corners without native theming.

Four cross-cutting **manager** subsystems, each a singleton-style tracker that widgets subscribe to via a base class:

- **`appearance_mode/`** — `AppearanceModeTracker` + `CTkAppearanceModeBaseClass`. Tracks light/dark/system and notifies widgets to redraw. `system` mode polls the OS via `darkdetect`.
- **`scaling/`** — `ScalingTracker` + `CTkScalingBaseClass`. HighDPI/user scaling for both widget dimensions and window geometry. `CTkWidget` keeps `_desired_*` (unscaled) vs `_current_*` (scaled) sizes; use `_apply_scaling`/`_reverse_scaling`.
- **`theme/`** — `ThemeManager` loads JSON theme files from `assets/themes/` (`blue`, `dark-blue`, `green`, `gold`) or a custom path; defines `AnchorType`/`ColorType`/`TransparentColorType`.
- **`font/`** — `FontManager` (loads bundled/custom font files) + `CTkFont`.
- **`image/`** — `CTkImage`, the scaling/appearance-aware replacement for `PIL.ImageTk.PhotoImage`.

A typical widget multiply-inherits `CTkWidget` (→ Tk Frame + appearance + scaling base classes), draws itself onto an embedded `CTkCanvas` using `draw_engine` shapes, reads its colors from `ThemeManager`, and re-renders on appearance/scaling change events.

Bundled non-code assets live in `customtkinter/assets/` (`fonts/`, `icons/`, `themes/`) and must be listed in `pyproject.toml` packaging if a new asset subpackage is added.

### Conventions

- `"transparent"` is the sentinel for "use parent's color" (not `None`). Colors are typically 2-tuples `(light, dark)`.
- All widgets implement `configure()`/`cget()` over a known set of attributes; when adding an attribute, wire it into both, plus `__init__` and the draw routine.
- New code uses `from __future__ import annotations` and `typing_extensions` (`Literal`, `TypedDict`, `Unpack`) for typing; match the surrounding style.
