"""Reset Custom2kinter's module-level singletons to a known baseline.

The library keeps process-global state in a handful of class-level singletons
(``AppearanceModeTracker``, ``ScalingTracker``, ``ThemeManager`` and
``BaseShape.preferred_drawing_method``). Tests that change appearance, scaling,
theme or drawing method would otherwise leak that state into later tests. The
``reset_global_state`` fixture in ``conftest.py`` calls :func:`reset_all` around
every test so each one starts from the same baseline.
"""

from __future__ import annotations

import sys

import customtkinter
from customtkinter import (
    AppearanceModeTracker,
    ScalingTracker,
    ThemeManager,
    BaseShape,
)

#: Drawing method the library selects for the current platform (see
#: ``customtkinter/windows/widgets/core_rendering/__init__.py``).
DEFAULT_DRAWING_METHOD = "polygons" if sys.platform == "darwin" else "font"

#: Theme the library ships with as its default.
DEFAULT_THEME = "blue"


def reset_appearance_mode() -> None:
    AppearanceModeTracker._callback_list = []
    AppearanceModeTracker._app_list = []
    AppearanceModeTracker._update_loop_running = False
    AppearanceModeTracker._appearance_mode_set_by = "user"
    AppearanceModeTracker._appearance_mode = 0  # light


def reset_scaling() -> None:
    ScalingTracker._window_widgets_dict = {}
    ScalingTracker._window_dpi_scaling_dict = {}
    ScalingTracker._widget_scaling = 1.0
    ScalingTracker._window_scaling = 1.0
    ScalingTracker._update_loop_running = False
    ScalingTracker.deactivate_automatic_dpi_awareness = False


def reset_drawing_method() -> None:
    BaseShape.preferred_drawing_method = DEFAULT_DRAWING_METHOD


def reset_theme() -> None:
    customtkinter.set_default_color_theme(DEFAULT_THEME)


def reset_all() -> None:
    """Restore every global singleton to its default baseline."""
    reset_appearance_mode()
    reset_scaling()
    reset_drawing_method()
    reset_theme()
