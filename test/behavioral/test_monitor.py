"""Multi-monitor placement logic, exercised without real multiple monitors.

We inject fake monitor bounds and assert the *invariant* that tooltip placement
always lands inside the target monitor. This validates the cross-monitor
clamping logic on any host; true multi-display rendering is covered separately on
self-hosted runners (see ``.github/workflows/self-hosted.yml``).
"""

import sys

import pytest

import customtkinter
from customtkinter.windows.widgets.utility import utility_functions


def test_get_monitor_info_not_implemented_on_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(NotImplementedError):
        utility_functions.get_monitor_info(0, 0)


@pytest.mark.parametrize(
    "monitor",
    [
        (0, 0, 1920, 1080),       # primary monitor at origin
        (1920, 0, 3840, 1080),    # second monitor to the right
        (-1920, 0, 0, 1080),      # second monitor to the left
        (0, 0, 200, 200),         # tiny monitor (forces clamping)
    ],
)
def test_tooltip_placement_stays_within_monitor(ctk_root, monitor):
    ctk_root.deiconify()
    host = customtkinter.CTkButton(ctk_root, text="host")
    host.pack(padx=20, pady=20)
    ctk_root.update_idletasks()

    tooltip = customtkinter.CTkToolTip(host, text="hello")
    tooltip.update_idletasks()

    # inject the fake monitor regardless of the real screen
    tooltip._get_monitor_info = lambda mon=monitor: mon

    mon_left, mon_top, mon_right, mon_bottom = monitor
    x_root, y_root, anchor = tooltip._master_mode()

    assert mon_left <= x_root <= mon_right
    assert isinstance(anchor, str)
