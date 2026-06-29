"""Scaling-tracker behaviour.

The setter-clamping tests are pure (no display). The applied-scaling test uses a
real window so the scaling callbacks fire.
"""

import customtkinter
from customtkinter import ScalingTracker


def test_set_widget_scaling_clamps_minimum():
    ScalingTracker.set_widget_scaling(0.1)
    assert ScalingTracker._widget_scaling == 0.4


def test_set_window_scaling_clamps_minimum():
    ScalingTracker.set_window_scaling(0.0)
    assert ScalingTracker._window_scaling == 0.4


def test_set_scaling_values_stored():
    ScalingTracker.set_widget_scaling(1.75)
    ScalingTracker.set_window_scaling(2.0)
    assert ScalingTracker._widget_scaling == 1.75
    assert ScalingTracker._window_scaling == 2.0


def test_widget_scaling_applies_to_widget(ctk_root):
    customtkinter.deactivate_automatic_dpi_awareness()
    button = customtkinter.CTkButton(ctk_root, text="B")
    button.pack()
    ctk_root.update_idletasks()

    ScalingTracker.set_widget_scaling(2.0)
    ctk_root.update_idletasks()
    # widget scaling factor is dpi (1.0, awareness disabled) * widget_scaling
    assert button.get_scaling() == 2.0


def test_geometry_scaling_is_reversible(ctk_root):
    customtkinter.deactivate_automatic_dpi_awareness()
    ScalingTracker.set_window_scaling(1.5)
    ctk_root.update_idletasks()

    scaled = ctk_root._apply_geometry_scaling("200x100")
    assert ctk_root._reverse_geometry_scaling(scaled) == "200x100"
