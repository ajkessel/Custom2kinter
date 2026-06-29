"""Shared pytest fixtures for the Custom2kinter test suite.

Key pieces:

* ``reset_global_state`` (autouse) wraps every test with
  :func:`test.util.reset.reset_all`, so the library's process-global singletons
  never leak state between tests.
* ``ctk_root`` yields a ready, withdrawn ``CTk`` window and destroys it on
  teardown.
* ``appearance`` / ``drawing_method`` / ``scaling`` are indirectly
  parametrizable fixtures that force a deterministic render configuration. They
  default to a single value but visual tests parametrize them to sweep the
  matrix, e.g. ``@pytest.mark.parametrize("drawing_method", ["polygons",
  "font", "circles"], indirect=True)``.

Most fixtures need a live Tk display. On headless Linux run under
``xvfb-run -a pytest``; Windows/macOS runners have a real display.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the existing class-based ``test/unit_tests`` importable too, and allow
# ``from util import ...`` style imports from within the test tree.
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter
from customtkinter import BaseShape, ScalingTracker

from util.reset import reset_all


# --------------------------------------------------------------------------- #
# pytest configuration
# --------------------------------------------------------------------------- #
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "visual: visual/screenshot tests (slow, need a display)")
    config.addinivalue_line("markers", "selfhosted: needs real hardware (multi-monitor, real DPI, macOS Tk9)")
    config.addinivalue_line("markers", "slow: long-running tests")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="(re)write visual baseline images instead of comparing against them",
    )


@pytest.fixture(scope="session")
def update_baselines(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-baselines"))


# --------------------------------------------------------------------------- #
# global-state hygiene
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset library singletons before and after every test."""
    reset_all()
    yield
    reset_all()


# --------------------------------------------------------------------------- #
# windows
# --------------------------------------------------------------------------- #
@pytest.fixture
def ctk_root():
    """A withdrawn ``CTk`` root window, destroyed on teardown.

    Withdrawn so the window manager never actually maps it (faster, no stray
    windows), while still giving widgets a real Tk connection. Call
    ``root.deiconify()`` in a test that needs the window mapped (e.g. for
    screenshots).
    """
    root = customtkinter.CTk()
    root.withdraw()
    root.update_idletasks()
    try:
        yield root
    finally:
        try:
            root.update_idletasks()
        except Exception:
            pass
        root.destroy()


# --------------------------------------------------------------------------- #
# deterministic render configuration (indirectly parametrizable)
# --------------------------------------------------------------------------- #
@pytest.fixture
def appearance(request: pytest.FixtureRequest) -> str:
    """Force ``light`` (default) or ``dark`` appearance, bypassing darkdetect."""
    mode = getattr(request, "param", "light")
    customtkinter.set_appearance_mode(mode)
    return mode


@pytest.fixture
def drawing_method(request: pytest.FixtureRequest) -> str:
    """Force one of ``polygons`` / ``font`` / ``circles`` for shape rendering."""
    method = getattr(request, "param", BaseShape.preferred_drawing_method)
    BaseShape.preferred_drawing_method = method
    return method


@pytest.fixture
def scaling(request: pytest.FixtureRequest) -> float:
    """Force an exact widget+window scaling factor, independent of host DPI."""
    factor = getattr(request, "param", 1.0)
    customtkinter.deactivate_automatic_dpi_awareness()
    ScalingTracker.set_widget_scaling(factor)
    ScalingTracker.set_window_scaling(factor)
    return factor
