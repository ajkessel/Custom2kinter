from __future__ import annotations

import tkinter
from abc import ABC
from threading import Lock
from typing import Callable
from typing_extensions import Literal


class CTkToggleable(ABC):

    def __init__(self) -> None:
        self._check_state: bool = False
        self._onvalue: int | float | str | bool = True
        self._offvalue: int | float | str | bool = False

        self._state: Literal["normal", "disabled"] = tkinter.NORMAL
        self._command: Callable[[int | float | str | bool], Literal["break"] | None] | None = None
        self._variable: tkinter.Variable | None = None
        self._variable_callback_name: str | None = None
        self._block_value_propagation: Lock = Lock()

    def _update_variable(self, variable: tkinter.Variable | None) -> None:
        if self._variable is not None:
            self._variable.trace_remove("write", self._variable_callback_name)
        self._variable = variable
        if self._variable is not None:
            self._variable_callback_name = self._variable.trace_add("write", self._variable_callback)
            self._variable_callback()

    def _variable_callback(self, *_: str) -> None:
        if not self._block_value_propagation.locked():
            with self._block_value_propagation:
                if self._variable.get() == self._onvalue:
                    self.set(True)
                elif self._variable.get() == self._offvalue:
                    self.set(False)

    def destroy(self) -> None:
        if self._variable is not None:
            self._variable.trace_remove("write", self._variable_callback_name)

    def set(self, state: bool) -> None:
        self._check_state = state

        if self._variable is not None and not self._block_value_propagation.locked():
            with self._block_value_propagation:
                self._variable.set(self._onvalue if self._check_state else self._offvalue)

    def invoke(self, _: tkinter.Event | None = None) -> None:
        """ Toggles the selection status if the widget is not disabled.\n
        Can be called to simulate the user who clicks on the widget. """
        if self._state == tkinter.NORMAL:
            retval = "" if self._command is None else self._command(self._offvalue if self._check_state else self._onvalue)

            #if _command() returns exactly "break", operation is stopped
            if retval != "break":
                self.set(not self._check_state)

    def select(self) -> None:
        self.set(True)

    def deselect(self) -> None:
        self.set(False)

    def get(self) -> int | float | str | bool:
        return self._onvalue if self._check_state else self._offvalue
