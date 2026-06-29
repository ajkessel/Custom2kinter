"""Unit tests for ``CTkEntry`` configure/cget round-trips and textvariable.

Converted from the legacy ``test/unit_tests/test_ctk_entry.py``.
"""

import customtkinter


def test_configure_cget_round_trip(ctk_root):
    entry = customtkinter.CTkEntry(ctk_root, width=100, height=25)
    entry.pack(padx=20, pady=20)

    txt_var = customtkinter.StringVar(value="test")
    entry.configure(
        width=300,
        height=35,
        corner_radius=1000,
        border_width=4,
        bg_color="green",
        fg_color=("red", "yellow"),
        border_color="blue",
        text_color=("brown", "green"),
        placeholder_text_color="blue",
        textvariable=txt_var,
        placeholder_text="new_placeholder",
        font=("Times New Roman", -8, "bold"),
        state="normal",
        insertborderwidth=5,
        insertwidth=10,
        justify="right",
        show="+",
    )

    assert entry.cget("width") == 300
    assert entry.cget("height") == 35
    assert entry.cget("corner_radius") == 1000
    assert entry.cget("border_width") == 4
    assert entry.cget("bg_color") == "green"
    assert entry.cget("fg_color") == ("red", "yellow")
    assert entry.cget("border_color") == "blue"
    assert entry.cget("text_color") == ("brown", "green")
    assert entry.cget("placeholder_text_color") == "blue"
    assert entry.cget("textvariable") == txt_var
    assert entry.cget("placeholder_text") == "new_placeholder"
    assert entry.cget("font") == ("Times New Roman", -8, "bold")
    assert entry.cget("state") == "normal"
    assert entry.cget("insertborderwidth") == 5
    assert entry.cget("insertwidth") == 10
    assert entry.cget("justify") == "right"


def test_textvariable_updates_entry(ctk_root):
    txt_var = customtkinter.StringVar(value="test")
    entry = customtkinter.CTkEntry(ctk_root, textvariable=txt_var)
    entry.pack(padx=20, pady=20)
    ctk_root.update_idletasks()

    txt_var.set("test_2")
    assert entry.get() == "test_2"
