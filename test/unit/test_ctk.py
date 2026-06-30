"""Unit tests for the ``CTk`` root window.

Converted from the legacy ``test/unit_tests/test_ctk.py`` (a class with
``after()``-scheduled checks). Assertions target the current internal API
(``_desired_width``/``_min_width``/...); the legacy file referenced public
``current_width``/``window_scaling`` attributes that no longer exist.
"""

import customtkinter


def test_geometry_sets_desired_size(ctk_root):
    ctk_root.geometry("100x200+200+300")
    assert ctk_root._desired_width == 100
    assert ctk_root._desired_height == 200


def test_minsize_bounds_desired_size(ctk_root):
    ctk_root.geometry("100x200")
    ctk_root.minsize(300, 400)
    assert ctk_root._min_width == 300
    assert ctk_root._min_height == 400
    # desired width is raised up to the minimum
    assert ctk_root._desired_width == 300


def test_maxsize_bounds_desired_size(ctk_root):
    ctk_root.maxsize(400, 500)
    ctk_root.geometry("600x600")
    assert ctk_root._max_width == 400
    assert ctk_root._max_height == 500
    # desired width is clamped down to the maximum
    assert ctk_root._desired_width == 400


def test_configure_fg_color(ctk_root):
    ctk_root.configure(fg_color="white")
    assert ctk_root.cget("fg_color") == "white"
    assert ctk_root.cget("bg") == "white"

    ctk_root.configure(fg_color="red")
    assert ctk_root.cget("fg_color") == "red"
    assert ctk_root.cget("bg") == "red"


def test_configure_fg_color_tuple(ctk_root):
    ctk_root.configure(fg_color=("green", "#FFFFFF"))
    assert ctk_root.cget("fg_color") == ("green", "#FFFFFF")


def test_appearance_mode_selects_color_from_tuple(ctk_root):
    ctk_root.configure(fg_color=("green", "#FFFFFF"))

    customtkinter.set_appearance_mode("light")
    assert ctk_root.cget("bg") == "green"

    customtkinter.set_appearance_mode("dark")
    assert ctk_root.cget("bg") == "#FFFFFF"
