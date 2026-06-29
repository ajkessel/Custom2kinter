"""Unit tests for ``CTkToplevel``.

Converted from the legacy ``test/unit_tests/test_ctk_toplevel.py``.
"""

import pytest

import customtkinter


@pytest.fixture
def toplevel(ctk_root):
    top = customtkinter.CTkToplevel(ctk_root)
    top.withdraw()
    top.update_idletasks()
    try:
        yield top
    finally:
        top.destroy()


def test_geometry_sets_desired_size(toplevel):
    toplevel.geometry("200x300+200+300")
    assert toplevel._desired_width == 200
    assert toplevel._desired_height == 300


def test_minsize_and_maxsize_bounds(toplevel):
    toplevel.minsize(300, 400)
    assert toplevel._min_width == 300
    assert toplevel._min_height == 400

    toplevel.maxsize(400, 500)
    toplevel.geometry("600x600")
    assert toplevel._max_width == 400
    assert toplevel._max_height == 500
    assert toplevel._desired_width == 400


def test_configure_fg_color_tuple(toplevel):
    toplevel.configure(fg_color=("green", "#FFFFFF"))
    assert toplevel.cget("fg_color") == ("green", "#FFFFFF")


def test_appearance_mode_selects_color_from_tuple(toplevel):
    toplevel.configure(fg_color=("green", "#FFFFFF"))

    customtkinter.set_appearance_mode("light")
    assert toplevel.cget("bg") == "green"

    customtkinter.set_appearance_mode("dark")
    assert toplevel.cget("bg") == "#FFFFFF"
