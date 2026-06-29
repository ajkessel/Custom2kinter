# Custom2kinter test suite

Automated tests for the library. Built on **pytest**. Because this is a GUI
library, the tests open real Tk windows and therefore need a display — on
headless Linux they run under **Xvfb**.

## Install

```bash
pip install -e ".[test]"
```

This pulls in the test extras: `pytest`, `pytest-xvfb`, `mss`, `pillow`,
`pixelmatch`.

On **headless Linux** you also need the Xvfb binary (the CI installs it; locally):

```bash
sudo apt-get install -y xvfb      # Debian/Ubuntu
```

## Run

```bash
# Linux (headless): wrap in a virtual display
xvfb-run -a pytest test/unit test/behavioral

# Windows / macOS (real display): no wrapper needed
pytest test/unit test/behavioral
```

`pytest-xvfb` auto-starts a virtual display on Linux when `DISPLAY` is unset, so
plain `pytest` often works there too; `xvfb-run -a` is the explicit, reliable form.

### Useful subsets

```bash
# the display-free behavioral tests run on any host, no display at all
pytest test/behavioral/test_geometry_parsing.py test/behavioral/test_theme_loading.py

# a single test by keyword
pytest -k tooltip

# one file / one test
pytest test/unit/test_ctk.py
pytest test/unit/test_ctk.py::test_geometry_sets_desired_size
```

## Layout

| Path | What it covers |
|------|----------------|
| `test/conftest.py` | shared fixtures (see below) |
| `test/util/` | test helpers (`reset.py` = singleton reset) |
| `test/unit/` | per-widget logic + smoke (instantiate/configure/cget, render under every drawing method) |
| `test/behavioral/` | scaling math, theme loading, multi-monitor placement logic; much of it display-free / mockable |
| `test/visual/` | screenshot + visual-regression tests, marked `visual` (added in a later milestone) |
| `test/unit_tests/`, `test/manual_integration_tests/` | legacy scripts kept for local/manual use; **not** run by pytest |

## Fixtures (in `conftest.py`)

- **`reset_global_state`** (autouse) — resets the library's process-global
  singletons (`AppearanceModeTracker`, `ScalingTracker`, `ThemeManager`,
  `BaseShape.preferred_drawing_method`) before and after every test, so render
  configuration never leaks between tests.
- **`ctk_root`** — a withdrawn `CTk` window, destroyed on teardown. Call
  `root.deiconify()` if a test needs it mapped.
- **`appearance`**, **`drawing_method`**, **`scaling`** — indirectly
  parametrizable fixtures that force a deterministic render configuration, e.g.:

  ```python
  @pytest.mark.parametrize("drawing_method", ["polygons", "font", "circles"], indirect=True)
  def test_something(ctk_root, drawing_method):
      ...
  ```

## Markers

- `visual` — visual/screenshot tests (slow, need a display)
- `selfhosted` — needs real hardware (multi-monitor, real DPI, macOS Tk 9)
- `slow` — long-running

Skip a group with e.g. `pytest -m "not visual"`.

## CI

`.github/workflows/tests.yml` runs `test/unit` + `test/behavioral` across
Linux (Xvfb) / Windows / macOS × Python 3.9 / 3.12 / 3.13.

The full multi-milestone testing strategy is in
[`docs/testing-plan.md`](../docs/testing-plan.md).
