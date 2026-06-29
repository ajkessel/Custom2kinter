"""Pure-logic tests for geometry-string parsing (no display required)."""

from customtkinter.windows.widgets.utility.utility_functions import parse_geometry_string


def test_full_geometry_string():
    assert parse_geometry_string("100x200+30+40") == (100, 200, 30, 40)


def test_size_only():
    assert parse_geometry_string("640x480") == (640, 480, None, None)


def test_position_only():
    assert parse_geometry_string("+10+20") == (None, None, 10, 20)


def test_negative_position():
    assert parse_geometry_string("100x200-5-15") == (100, 200, -5, -15)


def test_empty_string():
    assert parse_geometry_string("") == (None, None, None, None)
