"""Theme-loading behaviour (no display required).

Loading a theme is plain file IO plus per-platform value filtering, so these run
on any host. The autouse ``reset_global_state`` fixture restores the default
theme afterwards.
"""

import json

import pytest

import customtkinter
from customtkinter import ThemeManager


@pytest.mark.parametrize("theme_name", ThemeManager._built_in_themes)
def test_builtin_theme_loads(theme_name):
    customtkinter.set_default_color_theme(theme_name)
    assert ThemeManager._last_loaded_theme == theme_name
    # every built-in theme defines the core widget keys
    assert "CTkButton" in ThemeManager._theme
    assert "CTkFrame" in ThemeManager._theme


def test_custom_theme_path(tmp_path):
    customtkinter.set_default_color_theme("blue")
    theme_copy = dict(ThemeManager._theme)
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(theme_copy))

    customtkinter.set_default_color_theme(str(path))
    assert ThemeManager._last_loaded_theme == str(path)
    assert "CTkButton" in ThemeManager._theme


def test_save_builtin_theme_without_path_raises():
    customtkinter.set_default_color_theme("blue")
    with pytest.raises(ValueError):
        ThemeManager.save_theme()


def test_get_info_merges_kwargs():
    customtkinter.set_default_color_theme("blue")
    info = ThemeManager.get_info("CTkButton", None, corner_radius=999)
    assert info["corner_radius"] == 999
