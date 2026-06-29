"""Smoke tests: every CTk widget instantiates, packs, configures and renders.

These are logic-level checks (no pixels). They catch crashes in construction,
the configure/cget plumbing, and the three drawing-method render paths
(``polygons`` / ``font`` / ``circles``) on whatever platform runs them.

Each entry in ``WIDGET_BUILDERS`` is ``(name, builder)`` where ``builder(parent)``
returns a freshly constructed widget. Widgets that need values, a tab, or a host
widget are built by dedicated helpers below.
"""

from __future__ import annotations

import pytest

import customtkinter
from customtkinter import BaseShape


def _build_simple(cls, **kwargs):
    def builder(parent):
        return cls(parent, **kwargs)
    return builder


def _build_tabview(parent):
    tabview = customtkinter.CTkTabview(parent)
    tabview.add("Tab 1")
    tabview.add("Tab 2")
    return tabview


def _build_tooltip(parent):
    host = customtkinter.CTkButton(parent, text="host")
    host.pack()
    return customtkinter.CTkToolTip(host, text="tooltip text")


# (name, builder) — keep alphabetical-ish, one per public widget
WIDGET_BUILDERS = [
    ("CTkButton", _build_simple(customtkinter.CTkButton, text="Button")),
    ("CTkCheckBox", _build_simple(customtkinter.CTkCheckBox, text="Check")),
    ("CTkComboBox", _build_simple(customtkinter.CTkComboBox, values=["a", "b", "c"])),
    ("CTkEntry", _build_simple(customtkinter.CTkEntry, placeholder_text="Entry")),
    ("CTkFloatingFrame", _build_simple(customtkinter.CTkFloatingFrame)),
    ("CTkFrame", _build_simple(customtkinter.CTkFrame)),
    ("CTkLabel", _build_simple(customtkinter.CTkLabel, text="Label")),
    ("CTkOptionMenu", _build_simple(customtkinter.CTkOptionMenu, values=["a", "b", "c"])),
    ("CTkProgressBar", _build_simple(customtkinter.CTkProgressBar)),
    ("CTkRadioButton", _build_simple(customtkinter.CTkRadioButton, text="Radio")),
    ("CTkScrollableFrame", _build_simple(customtkinter.CTkScrollableFrame)),
    ("CTkScrollbar", _build_simple(customtkinter.CTkScrollbar)),
    ("CTkSegmentedButton", _build_simple(customtkinter.CTkSegmentedButton, values=["a", "b", "c"])),
    ("CTkSlider", _build_simple(customtkinter.CTkSlider)),
    ("CTkSpinBox", _build_simple(customtkinter.CTkSpinBox)),
    ("CTkSwitch", _build_simple(customtkinter.CTkSwitch, text="Switch")),
    ("CTkSymbolBox", _build_simple(customtkinter.CTkSymbolBox, values=["", "check", "x"])),
    ("CTkTabview", _build_tabview),
    ("CTkTextbox", _build_simple(customtkinter.CTkTextbox)),
    ("CTkToggleButton", _build_simple(customtkinter.CTkToggleButton)),
    ("CTkToolTip", _build_tooltip),
]

WIDGET_IDS = [name for name, _ in WIDGET_BUILDERS]


def _pack(widget) -> None:
    """Pack a widget if it is a geometry-manageable widget (tooltips are not)."""
    if isinstance(widget, customtkinter.CTkToolTip):
        return
    try:
        widget.pack(padx=5, pady=5)
    except Exception:
        pass  # detached widgets (e.g. floating frame) are not packed into parent


@pytest.mark.parametrize("builder", [b for _, b in WIDGET_BUILDERS], ids=WIDGET_IDS)
def test_widget_instantiates_and_packs(ctk_root, builder):
    widget = builder(ctk_root)
    _pack(widget)
    ctk_root.update_idletasks()
    assert widget is not None


@pytest.mark.parametrize("builder", [b for _, b in WIDGET_BUILDERS], ids=WIDGET_IDS)
@pytest.mark.parametrize("drawing_method", ["polygons", "font", "circles"], indirect=True)
def test_widget_renders_with_each_drawing_method(ctk_root, drawing_method, builder):
    """Each widget must build and draw under every drawing method without error."""
    assert BaseShape.preferred_drawing_method == drawing_method
    widget = builder(ctk_root)
    _pack(widget)
    ctk_root.update_idletasks()
    assert widget is not None


@pytest.mark.parametrize(
    "cls,kwargs",
    [
        (customtkinter.CTkButton, {"text": "B"}),
        (customtkinter.CTkLabel, {"text": "L"}),
        (customtkinter.CTkFrame, {}),
        (customtkinter.CTkSlider, {}),
        (customtkinter.CTkProgressBar, {}),
    ],
)
def test_width_height_configure_cget_round_trip(ctk_root, cls, kwargs):
    widget = cls(ctk_root, width=120, height=40, **kwargs)
    widget.pack(padx=5, pady=5)
    ctk_root.update_idletasks()

    assert widget.cget("width") == 120
    assert widget.cget("height") == 40

    widget.configure(width=200, height=60)
    assert widget.cget("width") == 200
    assert widget.cget("height") == 60
