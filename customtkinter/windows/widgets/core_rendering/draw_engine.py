from __future__ import annotations

import tkinter
import sys
import math
from dataclasses import dataclass, field
from typing import Callable, ClassVar, TYPE_CHECKING
from typing_extensions import Literal

if TYPE_CHECKING:
    from ..core_rendering import CTkCanvas


DRAWING_METHODS: list[str] = ["polygons", "font", "circles"]


def rototraslation(points: tuple[tuple[float | int, float | int], ...],
                   angle: float | int = 0,
                   x_pos: float | int = 0,
                   y_pos: float | int = 0) -> tuple[tuple[float | int, float | int], ...]:
    """ Performs a Rotation+Translation of all provided points.\n
    The Rotation is performed always around the origin (0, 0) using an angles expressed in 360 degrees.\n
    Provided coordinates are then added to perform the Translation. """

    cos = math.cos(angle*math.pi/180)
    sin = math.sin(angle*math.pi/180)
    return tuple((x*cos - y*sin + x_pos, x*sin + y*cos + y_pos) for x, y in points)


@dataclass(frozen=True)
class BaseShape:
    """ Provides common attributes and methods to all Shapes. """

    preferred_drawing_method: ClassVar[Literal["polygons", "font", "circles"]] = "polygons"

    canvas: CTkCanvas
    round_width_to_even_numbers: bool = True
    round_height_to_even_numbers: bool = True
    drawing_method: Literal["polygons", "font", "circles"] = None

    _name: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if self.drawing_method is None:
            super().__setattr__("drawing_method", self.preferred_drawing_method)
        super().__setattr__("_name", f"shape{self.canvas.shapes_counter}")
        self.canvas.shapes_counter += 1

    def raise_(self) -> None:
        self.canvas.tag_raise(self._name)

    def delete(self) -> None:
        self.canvas.delete(self._name)

    def bind(self,
             sequence: str | None = None,
             func: Callable[[tkinter.Event], None] | None = None,
             add: str | bool = True) -> str:
        return self.canvas.tag_bind(self._name, sequence, func, add)

    def unbind(self, sequence: str, funcid: None = None) -> None:
        self.canvas.tag_unbind(self._name, sequence, funcid)

    def _correct_width_height(self,
                              width: float | int,
                              height: float | int) -> tuple[float | int, float | int]:
        if self.round_width_to_even_numbers:
            width = math.floor(width / 2) * 2
        if self.round_height_to_even_numbers:
            height = math.floor(height / 2) * 2
        return width, height

    def _correct_corner_radius(self,
                               corner_radius: float | int,
                               width: float | int,
                               height: float | int) -> float | int:
        """optimize corner_radius for different drawing methods (different rounding)"""

        # restrict corner_radius if it's too large
        corner_radius = min(corner_radius, width / 2, height / 2)

        if self.drawing_method == "polygons":
            if sys.platform == "darwin":
                return corner_radius
            else:
                return round(corner_radius)

        elif self.drawing_method == "font":
            return round(corner_radius)

        else:
            return 0.5 * round(corner_radius / 0.5)  # round to 0.5 steps


@dataclass(frozen=True)
class BackgroundCorners(BaseShape):
    drawing_method: None = field(default=None, init=False, repr=False, compare=False)  #not used

    def update(self,
               width: float | int,
               height: float | int) -> bool:
        """Returns True if recoloring is necessary."""

        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        TOP_LEFT = f"{self._name}_top_left"
        TOP_RIGHT = f"{self._name}_top_right"
        BOTTOM_RIGHT = f"{self._name}_bottom_right"
        BOTTOM_LEFT = f"{self._name}_bottom_left"

        if not self.canvas.find_withtag(self._name):
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(TOP_LEFT, self._name))
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(TOP_RIGHT, self._name))
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BOTTOM_RIGHT, self._name))
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BOTTOM_LEFT, self._name))
            requires_recoloring = True

        width, height = self._correct_width_height(width, height)
        mid_width, mid_height = round(width / 2), round(height / 2)

        self.canvas.coords(TOP_LEFT    , 0        , 0         , mid_width, mid_height)
        self.canvas.coords(TOP_RIGHT   , mid_width, 0         , width    , mid_height)
        self.canvas.coords(BOTTOM_RIGHT, mid_width, mid_height, width    , height    )
        self.canvas.coords(BOTTOM_LEFT , 0        , mid_height, mid_width, height    )

        return requires_recoloring

    def set_colors(self,
                   top_left: str | None = None,
                   top_right: str | None = None,
                   bottom_right: str | None = None,
                   bottom_left: str | None = None) -> None:
        if top_left is not None:
            self.canvas.itemconfig(f"{self._name}_top_left", fill=top_left)
        if top_right is not None:
            self.canvas.itemconfig(f"{self._name}_top_right", fill=top_right)
        if bottom_right is not None:
            self.canvas.itemconfig(f"{self._name}_bottom_right", fill=bottom_right)
        if bottom_left is not None:
            self.canvas.itemconfig(f"{self._name}_bottom_left", fill=bottom_left)


@dataclass(frozen=True)
class RoundedRect(BaseShape):
    """ Draws a rounded rectangle with an optional border.\n
    It can be divided into left/right sections that can be managed separately. """

    vertical_split: bool = False

    def update(self,
               width: float | int,
               height: float | int,
               corner_radius: float | int,
               border_width: float | int,
               left_section_width: float | int | None = None) -> bool:
        """Returns True if recoloring is necessary."""

        width, height = self._correct_width_height(width, height)
        corner_radius = self._correct_corner_radius(corner_radius, width, height)
        border_width = round(border_width)
        inner_corner_radius = max(0, corner_radius - border_width)

        if not self.vertical_split or left_section_width is None:
            left_section_width = round(width / 2)
        else:
            left_section_width = round(left_section_width)
            if left_section_width > width - corner_radius * 2:
                left_section_width = width - corner_radius * 2
            elif left_section_width < corner_radius * 2:
                left_section_width = corner_radius * 2

        if self.drawing_method == "font":
            requires_recoloring = self._font_method(width, height, corner_radius, border_width, inner_corner_radius, left_section_width)
        elif self.vertical_split:
            requires_recoloring = self._vertical_method(width, height, corner_radius, border_width, inner_corner_radius, left_section_width)
        elif self.drawing_method == "polygons":
            requires_recoloring = self._polygons_method(width, height, corner_radius, border_width, inner_corner_radius)
        else:
            requires_recoloring = self._circles_method(width, height, corner_radius, border_width, inner_corner_radius)

        if requires_recoloring and border_width > 0:
            self.canvas.tag_raise(f"{self._name}_main", f"{self._name}_border")
        return requires_recoloring

    def set_border_color(self,
                         color: str,
                         section: Literal["left", "right"] | None = None) -> None:
        tag = f"{self._name}_border"
        if section is not None:
            tag += f"_{section}"
        self.canvas.itemconfig(tag, outline=color, fill=color)

    def set_main_color(self,
                       color: str,
                       section: Literal["left", "right"] | None = None) -> None:
        tag = f"{self._name}_main"
        if section is not None:
            tag += f"_{section}"
        self.canvas.itemconfig(tag, outline=color, fill=color)

    def raise_(self) -> None:
        self.canvas.tag_raise(f"{self._name}_border")
        self.canvas.tag_raise(f"{self._name}_main")

    def delete(self) -> None:
        self.canvas.delete(f"{self._name}_border")
        self.canvas.delete(f"{self._name}_main")

    def bind(self,
             sequence: str | None = None,
             func: Callable[[tkinter.Event], None] | None = None,
             add: str | bool = True,
             section: Literal["left", "right"] | None = None) -> None:
        for part in ("main", "border"):
            tag = f"{self._name}_{part}"
            if section is not None:
                tag += f"_{section}"
            self.canvas.tag_bind(tag, sequence, func, add)

    def unbind(self, sequence: str, funcid: None = None, section: Literal["left", "right"] | None = None) -> None:
        for part in ("main", "border"):
            tag = f"{self._name}_{part}"
            if section is not None:
                tag += f"_{section}"
            self.canvas.tag_unbind(tag, sequence, funcid)

    def _polygons_method(self,
                         width: float | int,
                         height: float | int,
                         corner_radius: float | int,
                         border_width: float | int,
                         inner_corner_radius: float | int) -> bool:
        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        BORDER = f"{self._name}_border"
        MAIN = f"{self._name}_main"

        # create border button parts (only if border exists)
        if border_width > 0:
            if not self.canvas.find_withtag(BORDER):
                self.canvas.create_polygon((0, 0, 0, 0), tags=BORDER)
                requires_recoloring = True

            self.canvas.coords(BORDER, corner_radius        , corner_radius         ,
                                       width - corner_radius, corner_radius         ,
                                       width - corner_radius, height - corner_radius,
                                       corner_radius        , height - corner_radius)
            self.canvas.itemconfig(BORDER, joinstyle=tkinter.ROUND, width=corner_radius * 2)

        else:
            self.canvas.delete(BORDER)

        # create inner button parts
        if not self.canvas.find_withtag(MAIN):
            self.canvas.create_polygon((0, 0, 0, 0), tags=MAIN, joinstyle=tkinter.ROUND)
            requires_recoloring = True

        if corner_radius <= border_width:
            bottom_right_shift = -1  # weird canvas rendering inaccuracy that has to be corrected in some cases
        else:
            bottom_right_shift = 0

        self.canvas.coords(MAIN, border_width + inner_corner_radius,
                                 border_width + inner_corner_radius,
                                 width - (border_width + inner_corner_radius) + bottom_right_shift,
                                 border_width + inner_corner_radius,
                                 width - (border_width + inner_corner_radius) + bottom_right_shift,
                                 height - (border_width + inner_corner_radius) + bottom_right_shift,
                                 border_width + inner_corner_radius,
                                 height - (border_width + inner_corner_radius) + bottom_right_shift)
        self.canvas.itemconfig(MAIN, width=inner_corner_radius * 2)

        return requires_recoloring

    def _font_method(self,
                     width: float | int,
                     height: float | int,
                     corner_radius: float | int,
                     border_width: float | int,
                     inner_corner_radius: float | int,
                     left_section_width: float | int) -> bool:
        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        BORDER = f"{self._name}_border"
        BORDER_LEFT = f"{self._name}_border_left"
        BORDER_RIGHT = f"{self._name}_border_right"
        BORDER_OVAL_1_A = f"{self._name}_border_oval_1_a"
        BORDER_OVAL_1_B = f"{self._name}_border_oval_1_b"
        BORDER_OVAL_2_A = f"{self._name}_border_oval_2_a"
        BORDER_OVAL_2_B = f"{self._name}_border_oval_2_b"
        BORDER_OVAL_3_A = f"{self._name}_border_oval_3_a"
        BORDER_OVAL_3_B = f"{self._name}_border_oval_3_b"
        BORDER_OVAL_4_A = f"{self._name}_border_oval_4_a"
        BORDER_OVAL_4_B = f"{self._name}_border_oval_4_b"
        BORDER_RECT_L_1 = f"{self._name}_border_rect_l_1"
        BORDER_RECT_L_2 = f"{self._name}_border_rect_l_2"
        BORDER_RECT_R_1 = f"{self._name}_border_rect_r_1"
        BORDER_RECT_R_2 = f"{self._name}_border_rect_r_2"
        MAIN = f"{self._name}_main"
        MAIN_LEFT = f"{self._name}_main_left"
        MAIN_RIGHT = f"{self._name}_main_right"
        MAIN_OVAL_1_A = f"{self._name}_main_oval_1_a"
        MAIN_OVAL_1_B = f"{self._name}_main_oval_1_b"
        MAIN_OVAL_2_A = f"{self._name}_main_oval_2_a"
        MAIN_OVAL_2_B = f"{self._name}_main_oval_2_b"
        MAIN_OVAL_3_A = f"{self._name}_main_oval_3_a"
        MAIN_OVAL_3_B = f"{self._name}_main_oval_3_b"
        MAIN_OVAL_4_A = f"{self._name}_main_oval_4_a"
        MAIN_OVAL_4_B = f"{self._name}_main_oval_4_b"
        MAIN_RECT_L_1 = f"{self._name}_main_rect_l_1"
        MAIN_RECT_L_2 = f"{self._name}_main_rect_l_2"
        MAIN_RECT_R_1 = f"{self._name}_main_rect_r_1"
        MAIN_RECT_R_2 = f"{self._name}_main_rect_r_2"

        # create border button parts
        if border_width > 0:
            if corner_radius > 0:
                # create border corner parts if not already created, but only if needed, and delete if not needed
                if not self.canvas.find_withtag(BORDER_OVAL_1_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_1_A, BORDER_LEFT, BORDER), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_1_B, BORDER_LEFT, BORDER), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True

                if width > 2 * corner_radius:
                    if not self.canvas.find_withtag(BORDER_OVAL_2_A):
                        self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_2_A, BORDER_RIGHT, BORDER), anchor=tkinter.CENTER)
                        self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_2_B, BORDER_RIGHT, BORDER), anchor=tkinter.CENTER, angle=180)
                        requires_recoloring = True
                elif self.canvas.find_withtag(BORDER_OVAL_2_A):
                    self.canvas.delete(BORDER_OVAL_2_A, BORDER_OVAL_2_B)

                if height > 2 * corner_radius and width > 2 * corner_radius:
                    if not self.canvas.find_withtag(BORDER_OVAL_3_A):
                        self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_3_A, BORDER_RIGHT, BORDER), anchor=tkinter.CENTER)
                        self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_3_B, BORDER_RIGHT, BORDER), anchor=tkinter.CENTER, angle=180)
                        requires_recoloring = True
                elif self.canvas.find_withtag(BORDER_OVAL_3_A):
                    self.canvas.delete(BORDER_OVAL_3_A, BORDER_OVAL_3_B)

                if height > 2 * corner_radius:
                    if not self.canvas.find_withtag(BORDER_OVAL_4_A):
                        self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_4_A, BORDER_LEFT, BORDER), anchor=tkinter.CENTER)
                        self.canvas.create_aa_circle(0, 0, 0, tags=(BORDER_OVAL_4_B, BORDER_LEFT, BORDER), anchor=tkinter.CENTER, angle=180)
                        requires_recoloring = True
                elif self.canvas.find_withtag(BORDER_OVAL_4_A):
                    self.canvas.delete(BORDER_OVAL_4_A, BORDER_OVAL_4_B)

                # change position of border corner parts
                self.canvas.coords(BORDER_OVAL_1_A, corner_radius        , corner_radius         , corner_radius)
                self.canvas.coords(BORDER_OVAL_1_B, corner_radius        , corner_radius         , corner_radius)
                self.canvas.coords(BORDER_OVAL_2_A, width - corner_radius, corner_radius         , corner_radius)
                self.canvas.coords(BORDER_OVAL_2_B, width - corner_radius, corner_radius         , corner_radius)
                self.canvas.coords(BORDER_OVAL_3_A, width - corner_radius, height - corner_radius, corner_radius)
                self.canvas.coords(BORDER_OVAL_3_B, width - corner_radius, height - corner_radius, corner_radius)
                self.canvas.coords(BORDER_OVAL_4_A, corner_radius        , height - corner_radius, corner_radius)
                self.canvas.coords(BORDER_OVAL_4_B, corner_radius        , height - corner_radius, corner_radius)

            else:
                self.canvas.delete(BORDER_OVAL_1_A, BORDER_OVAL_1_B, BORDER_OVAL_2_A, BORDER_OVAL_2_B,
                                   BORDER_OVAL_3_A, BORDER_OVAL_3_B, BORDER_OVAL_4_A, BORDER_OVAL_4_B)

            # create border rectangle parts if not already created
            if not self.canvas.find_withtag(BORDER_RECT_L_1):
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BORDER_RECT_L_1, BORDER_LEFT, BORDER))
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BORDER_RECT_L_2, BORDER_LEFT, BORDER))
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BORDER_RECT_R_1, BORDER_RIGHT, BORDER))
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BORDER_RECT_R_2, BORDER_RIGHT, BORDER))
                requires_recoloring = True

            # change position of border rectangle parts
            self.canvas.coords(BORDER_RECT_L_1, 0                 , corner_radius, left_section_width   , height - corner_radius)
            self.canvas.coords(BORDER_RECT_L_2, corner_radius     , 0            , left_section_width   , height                )
            self.canvas.coords(BORDER_RECT_R_1, left_section_width, corner_radius, width                , height - corner_radius)
            self.canvas.coords(BORDER_RECT_R_2, left_section_width, 0            , width - corner_radius, height                )

        else:
            self.canvas.delete(BORDER)

        # create inner button parts
        if inner_corner_radius > 0:
            # create inner corner parts if not already created, but only if they're needed and delete if not needed
            if not self.canvas.find_withtag(MAIN_OVAL_1_A):
                self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_1_A, MAIN_LEFT, MAIN), anchor=tkinter.CENTER)
                self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_1_B, MAIN_LEFT, MAIN), anchor=tkinter.CENTER, angle=180)
                requires_recoloring = True

            if width - (2 * border_width) > 2 * inner_corner_radius:
                if not self.canvas.find_withtag(MAIN_OVAL_2_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_2_A, MAIN_RIGHT, MAIN), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_2_B, MAIN_RIGHT, MAIN), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(MAIN_OVAL_2_A):
                self.canvas.delete(MAIN_OVAL_2_A, MAIN_OVAL_2_B)

            if height - (2 * border_width) > 2 * inner_corner_radius and width - (2 * border_width) > 2 * inner_corner_radius:
                if not self.canvas.find_withtag(MAIN_OVAL_3_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_3_A, MAIN_RIGHT, MAIN), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_3_B, MAIN_RIGHT, MAIN), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(MAIN_OVAL_3_A):
                self.canvas.delete(MAIN_OVAL_3_A, MAIN_OVAL_3_B)

            if height - (2 * border_width) > 2 * inner_corner_radius:
                if not self.canvas.find_withtag(MAIN_OVAL_4_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_4_A, MAIN_LEFT, MAIN), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(MAIN_OVAL_4_B, MAIN_LEFT, MAIN), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(MAIN_OVAL_4_A):
                self.canvas.delete(MAIN_OVAL_4_A, MAIN_OVAL_4_B)

            # change position of inner corner parts
            self.canvas.coords(MAIN_OVAL_1_A, border_width + inner_corner_radius        , border_width + inner_corner_radius         , inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_1_B, border_width + inner_corner_radius        , border_width + inner_corner_radius         , inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_2_A, width - border_width - inner_corner_radius, border_width + inner_corner_radius         , inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_2_B, width - border_width - inner_corner_radius, border_width + inner_corner_radius         , inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_3_A, width - border_width - inner_corner_radius, height - border_width - inner_corner_radius, inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_3_B, width - border_width - inner_corner_radius, height - border_width - inner_corner_radius, inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_4_A, border_width + inner_corner_radius        , height - border_width - inner_corner_radius, inner_corner_radius)
            self.canvas.coords(MAIN_OVAL_4_B, border_width + inner_corner_radius        , height - border_width - inner_corner_radius, inner_corner_radius)
        else:
            self.canvas.delete(MAIN_OVAL_1_A, MAIN_OVAL_1_B, MAIN_OVAL_2_A, MAIN_OVAL_2_B,
                               MAIN_OVAL_3_A, MAIN_OVAL_3_B, MAIN_OVAL_4_A, MAIN_OVAL_4_B)

        # create inner rectangle parts if not already created
        if not self.canvas.find_withtag(MAIN_RECT_L_1):
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(MAIN_RECT_L_1, MAIN_LEFT, MAIN))
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(MAIN_RECT_R_1, MAIN_RIGHT, MAIN))
            requires_recoloring = True

        if inner_corner_radius * 2 < height - (border_width * 2):
            if not self.canvas.find_withtag(MAIN_RECT_L_2):
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(MAIN_RECT_L_2, MAIN_LEFT, MAIN))
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(MAIN_RECT_R_2, MAIN_RIGHT, MAIN))
                requires_recoloring = True
        elif self.canvas.find_withtag(MAIN_RECT_L_2):
            self.canvas.delete(MAIN_RECT_L_2, MAIN_RECT_R_2)

        # change position of inner rectangle parts
        self.canvas.coords(MAIN_RECT_L_1, border_width + inner_corner_radius, border_width         ,
                                          left_section_width                , height - border_width)
        self.canvas.coords(MAIN_RECT_L_2, border_width      , border_width + inner_corner_radius         ,
                                          left_section_width, height - inner_corner_radius - border_width)
        self.canvas.coords(MAIN_RECT_R_1, left_section_width                        , border_width         ,
                                          width - border_width - inner_corner_radius, height - border_width)
        self.canvas.coords(MAIN_RECT_R_2, left_section_width  , border_width + inner_corner_radius         ,
                                          width - border_width, height - inner_corner_radius - border_width)

        return requires_recoloring

    def _circles_method(self,
                        width: float | int,
                        height: float | int,
                        corner_radius: float | int,
                        border_width: float | int,
                        inner_corner_radius: float | int) -> bool:
        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        BORDER = f"{self._name}_border"
        BORDER_OVAL_1 = f"{self._name}_border_oval_1"
        BORDER_OVAL_2 = f"{self._name}_border_oval_2"
        BORDER_OVAL_3 = f"{self._name}_border_oval_3"
        BORDER_OVAL_4 = f"{self._name}_border_oval_4"
        BORDER_RECT_1 = f"{self._name}_border_rect_1"
        BORDER_RECT_2 = f"{self._name}_border_rect_2"
        MAIN = f"{self._name}_main"
        MAIN_OVAL_1 = f"{self._name}_main_oval_1"
        MAIN_OVAL_2 = f"{self._name}_main_oval_2"
        MAIN_OVAL_3 = f"{self._name}_main_oval_3"
        MAIN_OVAL_4 = f"{self._name}_main_oval_4"
        MAIN_RECT_1 = f"{self._name}_main_rect_1"
        MAIN_RECT_2 = f"{self._name}_main_rect_2"

        # border button parts
        if border_width > 0:
            if corner_radius > 0:
                if not self.canvas.find_withtag(BORDER_OVAL_1):
                    self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(BORDER_OVAL_1, BORDER))
                    self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(BORDER_OVAL_2, BORDER))
                    self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(BORDER_OVAL_3, BORDER))
                    self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(BORDER_OVAL_4, BORDER))
                    requires_recoloring = True

                self.canvas.coords(BORDER_OVAL_1, 0, 0, corner_radius * 2 - 1, corner_radius * 2 - 1)
                self.canvas.coords(BORDER_OVAL_2, width - corner_radius * 2, 0, width - 1, corner_radius * 2 - 1)
                self.canvas.coords(BORDER_OVAL_3, 0, height - corner_radius * 2, corner_radius * 2 - 1, height - 1)
                self.canvas.coords(BORDER_OVAL_4, width - corner_radius * 2, height - corner_radius * 2, width - 1, height - 1)

            else:
                self.canvas.delete(BORDER_OVAL_1, BORDER_OVAL_2, BORDER_OVAL_3, BORDER_OVAL_4)

            if not self.canvas.find_withtag(BORDER_RECT_1):
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BORDER_RECT_1, BORDER))
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(BORDER_RECT_2, BORDER))
                requires_recoloring = True

            self.canvas.coords(BORDER_RECT_1, 0, corner_radius, width, height - corner_radius)
            self.canvas.coords(BORDER_RECT_2, corner_radius, 0, width - corner_radius, height)

        else:
            self.canvas.delete(BORDER)

        # inner button parts
        if inner_corner_radius > 0:
            if not self.canvas.find_withtag(MAIN_OVAL_1):
                self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(MAIN_OVAL_1, MAIN))
                self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(MAIN_OVAL_2, MAIN))
                self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(MAIN_OVAL_3, MAIN))
                self.canvas.create_oval(0, 0, 0, 0, width=0, tags=(MAIN_OVAL_4, MAIN))
                requires_recoloring = True

            self.canvas.coords(MAIN_OVAL_1, border_width,
                                            border_width,
                                            border_width + inner_corner_radius * 2 - 1,
                                            border_width + inner_corner_radius * 2 - 1)
            self.canvas.coords(MAIN_OVAL_2, width - border_width - inner_corner_radius * 2,
                                            border_width,
                                            width - border_width - 1,
                                            border_width + inner_corner_radius * 2 - 1)
            self.canvas.coords(MAIN_OVAL_3, border_width,
                                            height - border_width - inner_corner_radius * 2,
                                            border_width + inner_corner_radius * 2 - 1,
                                            height - border_width - 1)
            self.canvas.coords(MAIN_OVAL_4, width - border_width - inner_corner_radius * 2,
                                            height - border_width - inner_corner_radius * 2,
                                            width - border_width - 1,
                                            height - border_width - 1)
        else:
            self.canvas.delete(MAIN_OVAL_1, MAIN_OVAL_2, MAIN_OVAL_3, MAIN_OVAL_4)

        if not self.canvas.find_withtag(MAIN_RECT_1):
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(MAIN_RECT_1, MAIN))
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(MAIN_RECT_2, MAIN))
            requires_recoloring = True

        self.canvas.coords(MAIN_RECT_1, border_width + inner_corner_radius,
                                        border_width,
                                        width - border_width - inner_corner_radius,
                                        height - border_width)
        self.canvas.coords(MAIN_RECT_2, border_width,
                                        border_width + inner_corner_radius,
                                        width - border_width,
                                        height - inner_corner_radius - border_width)

        return requires_recoloring

    def _vertical_method(self,
                         width: float | int,
                         height: float | int,
                         corner_radius: float | int,
                         border_width: float | int,
                         inner_corner_radius: float | int,
                         left_section_width: float | int) -> bool:
        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        BORDER = f"{self._name}_border"
        BORDER_LEFT = f"{self._name}_border_left"
        BORDER_RIGHT = f"{self._name}_border_right"
        BORDER_LINE_L = f"{self._name}_border_line_l"
        BORDER_LINE_R = f"{self._name}_border_line_r"
        BORDER_RECT_L = f"{self._name}_border_rect_l"
        BORDER_RECT_R = f"{self._name}_border_rect_r"
        MAIN = f"{self._name}_main"
        MAIN_LEFT = f"{self._name}_main_left"
        MAIN_RIGHT = f"{self._name}_main_right"
        MAIN_LINE_L = f"{self._name}_main_line_l"
        MAIN_LINE_R = f"{self._name}_main_line_r"
        MAIN_RECT_L = f"{self._name}_main_rect_l"
        MAIN_RECT_R = f"{self._name}_main_rect_r"

        # create border button parts (only if border exists)
        if border_width > 0:
            if not self.canvas.find_withtag(BORDER):
                self.canvas.create_polygon((0, 0, 0, 0), tags=(BORDER_LINE_L, BORDER_LEFT, BORDER))
                self.canvas.create_polygon((0, 0, 0, 0), tags=(BORDER_LINE_R, BORDER_RIGHT, BORDER))
                self.canvas.create_rectangle((0, 0, 0, 0), width=0, tags=(BORDER_RECT_L, BORDER_LEFT, BORDER))
                self.canvas.create_rectangle((0, 0, 0, 0), width=0, tags=(BORDER_RECT_R, BORDER_RIGHT, BORDER))
                requires_recoloring = True

            self.canvas.coords(BORDER_LINE_L, corner_radius                     , corner_radius         ,
                                              left_section_width - corner_radius, corner_radius         ,
                                              left_section_width - corner_radius, height - corner_radius,
                                              corner_radius                     , height - corner_radius)
            self.canvas.coords(BORDER_LINE_R, left_section_width + corner_radius, corner_radius         ,
                                              width - corner_radius             , corner_radius         ,
                                              width - corner_radius             , height - corner_radius,
                                              left_section_width + corner_radius, height - corner_radius)
            self.canvas.coords(BORDER_RECT_L, left_section_width - corner_radius, 0     ,
                                              left_section_width                , height)
            self.canvas.coords(BORDER_RECT_R, left_section_width                , 0     ,
                                              left_section_width + corner_radius, height)
            self.canvas.itemconfig(BORDER_LINE_L, joinstyle=tkinter.ROUND, width=corner_radius * 2)
            self.canvas.itemconfig(BORDER_LINE_R, joinstyle=tkinter.ROUND, width=corner_radius * 2)

        else:
            self.canvas.delete(BORDER)

        # create inner button parts
        if not self.canvas.find_withtag(MAIN):
            self.canvas.create_polygon((0, 0, 0, 0), tags=(MAIN_LINE_L, MAIN_LEFT, MAIN), joinstyle=tkinter.ROUND)
            self.canvas.create_polygon((0, 0, 0, 0), tags=(MAIN_LINE_R, MAIN_RIGHT, MAIN), joinstyle=tkinter.ROUND)
            self.canvas.create_rectangle((0, 0, 0, 0), width=0, tags=(MAIN_RECT_L, MAIN_LEFT, MAIN))
            self.canvas.create_rectangle((0, 0, 0, 0), width=0, tags=(MAIN_RECT_R, MAIN_RIGHT, MAIN))
            requires_recoloring = True

        self.canvas.coords(MAIN_LINE_L, corner_radius                           , corner_radius         ,
                                        left_section_width - inner_corner_radius, corner_radius         ,
                                        left_section_width - inner_corner_radius, height - corner_radius,
                                        corner_radius                           , height - corner_radius)
        self.canvas.coords(MAIN_LINE_R, left_section_width + inner_corner_radius, corner_radius         ,
                                        width - corner_radius                   , corner_radius         ,
                                        width - corner_radius                   , height - corner_radius,
                                        left_section_width + inner_corner_radius, height - corner_radius)
        self.canvas.coords(MAIN_RECT_L, left_section_width - inner_corner_radius, border_width         ,
                                        left_section_width                      , height - border_width)
        self.canvas.coords(MAIN_RECT_R, left_section_width                      , border_width         ,
                                        left_section_width + inner_corner_radius, height - border_width)
        self.canvas.itemconfig(MAIN_LINE_L, width=inner_corner_radius * 2)
        self.canvas.itemconfig(MAIN_LINE_R, width=inner_corner_radius * 2)

        return requires_recoloring


@dataclass(frozen=True)
class ProgressBar(BaseShape):
    """ Draws a rounded progress bar on the canvas.\n
    It extends from start_value to end_value (range 0-1, left to right, bottom to top).\n
    It is meant to be placed on top of a RoundedRect that provides a background and a border. """

    def update(self,
               container_width: float | int,
               container_height: float | int,
               container_corner_radius: float | int,
               container_border_width: float | int,
               orientation: Literal["horizontal", "vertical"],
               start_value: float,
               end_value: float) -> bool:
        """Returns True if recoloring is necessary."""

        container_width, container_height = self._correct_width_height(container_width, container_height)
        container_corner_radius = self._correct_corner_radius(container_corner_radius, container_width, container_height)
        container_border_width = round(container_border_width)
        inner_corner_radius = max(0, container_corner_radius - container_border_width)

        if self.drawing_method == "font":
            requires_recoloring = self._font_method(container_width, container_height, container_border_width, inner_corner_radius, orientation, start_value, end_value)
        else:
            requires_recoloring = self._polygons_circles_method(container_width, container_height, container_border_width, inner_corner_radius, orientation, start_value, end_value)
        return requires_recoloring

    def set_color(self, color: str) -> None:
        self.canvas.itemconfig(self._name, outline=color, fill=color)


    def _polygons_circles_method(self,
                                 width: float | int,
                                 height: float | int,
                                 border_width: float | int,
                                 inner_corner_radius: float | int,
                                 orientation: Literal["horizontal", "vertical"],
                                 start_value: float,
                                 end_value: float) -> bool:
        requires_recoloring = False

        # create progress parts
        if not self.canvas.find_withtag(self._name):
            self.canvas.create_polygon((0, 0, 0, 0),
                                       tags=self._name,
                                       joinstyle=tkinter.ROUND)
            requires_recoloring = True

        min_spacing = border_width + inner_corner_radius

        if orientation == "horizontal":
            max_delta = width - 2 * min_spacing
            self.canvas.coords(self._name, min_spacing + max_delta * start_value, min_spacing         ,
                                           min_spacing + max_delta * end_value  , min_spacing         ,
                                           min_spacing + max_delta * end_value  , height - min_spacing,
                                           min_spacing + max_delta * start_value, height - min_spacing)

        elif orientation == "vertical":
            max_delta = height - 2 * min_spacing
            self.canvas.coords(self._name, min_spacing        , min_spacing + max_delta * (1 - end_value)  ,
                                           width - min_spacing, min_spacing + max_delta * (1 - end_value)  ,
                                           width - min_spacing, min_spacing + max_delta * (1 - start_value),
                                           min_spacing        , min_spacing + max_delta * (1 - start_value))

        self.canvas.itemconfig(self._name, width=inner_corner_radius * 2)

        return requires_recoloring

    def _font_method(self,
                     width: float | int,
                     height: float | int,
                     border_width: float | int,
                     inner_corner_radius: float | int,
                     orientation: Literal["horizontal", "vertical"],
                     start_value: float,
                     end_value: float) -> bool:
        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        OVAL_1_A = f"{self._name}_oval_1_a"
        OVAL_1_B = f"{self._name}_oval_1_b"
        OVAL_2_A = f"{self._name}_oval_2_a"
        OVAL_2_B = f"{self._name}_oval_2_b"
        OVAL_3_A = f"{self._name}_oval_3_a"
        OVAL_3_B = f"{self._name}_oval_3_b"
        OVAL_4_A = f"{self._name}_oval_4_a"
        OVAL_4_B = f"{self._name}_oval_4_b"
        RECT_1 = f"{self._name}_rect_1"
        RECT_2 = f"{self._name}_rect_2"

        if inner_corner_radius > 0:
            # create canvas border corner parts if not already created
            if not self.canvas.find_withtag(OVAL_1_A):
                self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_1_A, self._name), anchor=tkinter.CENTER)
                self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_1_B, self._name), anchor=tkinter.CENTER, angle=180)
                self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_2_A, self._name), anchor=tkinter.CENTER)
                self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_2_B, self._name), anchor=tkinter.CENTER, angle=180)
                requires_recoloring = True

            if round(inner_corner_radius) * 2 < height - 2 * border_width:
                if not self.canvas.find_withtag(OVAL_3_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_3_A, self._name), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_3_B, self._name), anchor=tkinter.CENTER, angle=180)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_4_A, self._name), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_4_B, self._name), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(OVAL_3_A):
                self.canvas.delete(OVAL_3_A, OVAL_3_B, OVAL_4_A, OVAL_4_B)

        if not self.canvas.find_withtag(RECT_1):
            self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(RECT_1, self._name))
            requires_recoloring = True

        if inner_corner_radius * 2 < height - (border_width * 2):
            if not self.canvas.find_withtag(RECT_2):
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(RECT_2, self._name))
                requires_recoloring = True
        elif self.canvas.find_withtag(RECT_2):
            self.canvas.delete(RECT_2)

        min_spacing = border_width + inner_corner_radius

        # horizontal orientation from the bottom
        if orientation == "horizontal":
            max_delta = width - 2 * min_spacing
            start_x_pos = min_spacing + max_delta * start_value
            end_x_pos = min_spacing + max_delta * end_value

            # set positions of progress corner parts
            self.canvas.coords(OVAL_1_A, start_x_pos, min_spacing         , inner_corner_radius)
            self.canvas.coords(OVAL_1_B, start_x_pos, min_spacing         , inner_corner_radius)
            self.canvas.coords(OVAL_2_A, end_x_pos  , min_spacing         , inner_corner_radius)
            self.canvas.coords(OVAL_2_B, end_x_pos  , min_spacing         , inner_corner_radius)
            self.canvas.coords(OVAL_3_A, end_x_pos  , height - min_spacing, inner_corner_radius)
            self.canvas.coords(OVAL_3_B, end_x_pos  , height - min_spacing, inner_corner_radius)
            self.canvas.coords(OVAL_4_A, start_x_pos, height - min_spacing, inner_corner_radius)
            self.canvas.coords(OVAL_4_B, start_x_pos, height - min_spacing, inner_corner_radius)

            # set positions of progress rect parts
            self.canvas.coords(RECT_1,
                               start_x_pos, border_width,
                               end_x_pos  , height - border_width)
            self.canvas.coords(RECT_2,
                               border_width + max_delta * start_value                        , min_spacing         ,
                               border_width + 2 * inner_corner_radius + max_delta * end_value, height - min_spacing)

        # vertical orientation from the bottom
        elif orientation == "vertical":
            max_delta = height - 2 * min_spacing
            start_x_pos = min_spacing + max_delta * (1 - start_value)
            end_x_pos = min_spacing + max_delta * (1 - end_value)

            # set positions of progress corner parts
            self.canvas.coords(OVAL_1_A, min_spacing        , end_x_pos  , inner_corner_radius)
            self.canvas.coords(OVAL_1_B, min_spacing        , end_x_pos  , inner_corner_radius)
            self.canvas.coords(OVAL_2_A, width - min_spacing, end_x_pos  , inner_corner_radius)
            self.canvas.coords(OVAL_2_B, width - min_spacing, end_x_pos  , inner_corner_radius)
            self.canvas.coords(OVAL_3_A, width - min_spacing, start_x_pos, inner_corner_radius)
            self.canvas.coords(OVAL_3_B, width - min_spacing, start_x_pos, inner_corner_radius)
            self.canvas.coords(OVAL_4_A, min_spacing        , start_x_pos, inner_corner_radius)
            self.canvas.coords(OVAL_4_B, min_spacing        , start_x_pos, inner_corner_radius)

            # set positions of progress rect parts
            self.canvas.coords(RECT_1,
                               min_spacing        , border_width + max_delta * (1 - end_value)                            ,
                               width - min_spacing, border_width + 2 * inner_corner_radius + max_delta * (1 - start_value))
            self.canvas.coords(RECT_2,
                               border_width        , end_x_pos  ,
                               width - border_width, start_x_pos)

        return requires_recoloring


@dataclass(frozen=True)
class Slider(BaseShape):
    """ Draws a rounded sliding bar on the canvas.\n
    It extends from start_value to end_value (range 0-1, left to right, bottom to top) OR
    it is centered in a position, and it has a fixed length.\n
    It is meant to be placed on top of a RoundedRect that provides a background. """

    def update(self,
               width: float | int,
               height: float | int,
               container_corner_radius: float | int,
               container_border_width: float | int,
               slider_corner_radius: float | int,
               orientation: Literal["horizontal", "vertical"],
               slider_value: float | None =  None,
               button_length: float | int | None = None,
               start_value: float | None = None,
               end_value: float | None = None) -> bool:

        width, height = self._correct_width_height(width, height)
        container_corner_radius = self._correct_corner_radius(container_corner_radius, width, height)
        slider_corner_radius = self._correct_corner_radius(slider_corner_radius, width, height)
        slider_corner_radius = max(0, slider_corner_radius - round(container_border_width))

        if start_value is None and end_value is None:
            if orientation == "vertical":
                #0.0 is placed at the bottom
                slider_value = 1.0 - slider_value

            max_delta = (width if orientation == "horizontal" else height) - 2 * container_corner_radius
            if max_delta > 0:
                start_value = slider_value * (max_delta - button_length) / max_delta
                end_value = start_value + button_length / max_delta
            else:
                start_value = 0.0
                end_value = 0.0

        if self.drawing_method == "font":
            return self._font_method(width, height, container_corner_radius, slider_corner_radius, orientation, start_value, end_value)
        else:
            return self._polygons_circles_method(width, height, container_corner_radius, slider_corner_radius, orientation, start_value, end_value)

    def set_color(self, color: str) -> None:
        self.canvas.itemconfig(self._name, outline=color, fill=color)


    def _polygons_circles_method(self,
                                 width: float | int,
                                 height: float | int,
                                 corner_radius: float | int,
                                 slider_corner_radius: float | int,
                                 orientation: Literal["horizontal", "vertical"],
                                 start_value: float,
                                 end_value: float) -> bool:
        requires_recoloring = False

        if not self.canvas.find_withtag(self._name):
            self.canvas.create_polygon((0, 0, 0, 0), tags=self._name, joinstyle=tkinter.ROUND)
            requires_recoloring = True

        if orientation == "vertical":
            max_delta = height - 2 * corner_radius
            self.canvas.coords(self._name, corner_radius        , corner_radius + max_delta * start_value,
                                           width - corner_radius, corner_radius + max_delta * start_value,
                                           width - corner_radius, corner_radius + max_delta * end_value  ,
                                           corner_radius        , corner_radius + max_delta * end_value  )
        elif orientation == "horizontal":
            max_delta = width - 2 * corner_radius
            self.canvas.coords(self._name, corner_radius + max_delta * start_value, corner_radius         ,
                                           corner_radius + max_delta * end_value  , corner_radius         ,
                                           corner_radius + max_delta * end_value  , height - corner_radius,
                                           corner_radius + max_delta * start_value, height - corner_radius)

        self.canvas.itemconfig(self._name, width=slider_corner_radius * 2)

        return requires_recoloring

    def _font_method(self,
                     width: float | int,
                     height: float | int,
                     corner_radius: float | int,
                     slider_corner_radius: float | int,
                     orientation: Literal["horizontal", "vertical"],
                     start_value: float,
                     end_value: float) -> bool:
        requires_recoloring = False

        #sub-shape tags
        # pylint: disable=invalid-name
        OVAL_1_A = f"{self._name}_oval_1_a"
        OVAL_1_B = f"{self._name}_oval_1_b"
        OVAL_2_A = f"{self._name}_oval_2_a"
        OVAL_2_B = f"{self._name}_oval_2_b"
        OVAL_3_A = f"{self._name}_oval_3_a"
        OVAL_3_B = f"{self._name}_oval_3_b"
        OVAL_4_A = f"{self._name}_oval_4_a"
        OVAL_4_B = f"{self._name}_oval_4_b"
        RECT_1 = f"{self._name}_rect_1"
        RECT_2 = f"{self._name}_rect_2"

        if slider_corner_radius > 0:
            if not self.canvas.find_withtag(OVAL_1_A):
                self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_1_A, self._name), anchor=tkinter.CENTER)
                self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_1_B, self._name), anchor=tkinter.CENTER, angle=180)
                requires_recoloring = True

            if width > 2 * corner_radius:
                if not self.canvas.find_withtag(OVAL_2_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_2_A, self._name), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_2_B, self._name), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(OVAL_2_A):
                self.canvas.delete(OVAL_2_A, OVAL_2_B)

            if height > 2 * corner_radius and width > 2 * corner_radius:
                if not self.canvas.find_withtag(OVAL_3_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_3_A, self._name), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_3_B, self._name), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(OVAL_3_A):
                self.canvas.delete(OVAL_3_A, OVAL_3_B)

            if height > 2 * corner_radius:
                if not self.canvas.find_withtag(OVAL_4_A):
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_4_A, self._name), anchor=tkinter.CENTER)
                    self.canvas.create_aa_circle(0, 0, 0, tags=(OVAL_4_B, self._name), anchor=tkinter.CENTER, angle=180)
                    requires_recoloring = True
            elif self.canvas.find_withtag(OVAL_4_A):
                self.canvas.delete(OVAL_4_A, OVAL_4_B)
        else:
            self.canvas.delete(OVAL_1_A, OVAL_1_B, OVAL_2_A, OVAL_2_B,
                               OVAL_3_A, OVAL_3_B, OVAL_4_A, OVAL_4_B)

        if height > 2 * corner_radius:
            if not self.canvas.find_withtag(RECT_1):
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(RECT_1, self._name))
                requires_recoloring = True
        elif self.canvas.find_withtag(RECT_1):
            self.canvas.delete(RECT_1)

        if width > 2 * corner_radius:
            if not self.canvas.find_withtag(RECT_2):
                self.canvas.create_rectangle(0, 0, 0, 0, width=0, tags=(RECT_2, self._name))
                requires_recoloring = True
        elif self.canvas.find_withtag(RECT_2):
            self.canvas.delete(RECT_2)

        if orientation == "vertical":
            max_delta = height - 2 * corner_radius
            start_x_pos = corner_radius + max_delta * start_value
            end_x_pos = corner_radius + max_delta * end_value

            self.canvas.coords(OVAL_1_A, corner_radius        , start_x_pos, slider_corner_radius)
            self.canvas.coords(OVAL_1_B, corner_radius        , start_x_pos, slider_corner_radius)
            self.canvas.coords(OVAL_2_A, width - corner_radius, start_x_pos, slider_corner_radius)
            self.canvas.coords(OVAL_2_B, width - corner_radius, start_x_pos, slider_corner_radius)
            self.canvas.coords(OVAL_3_A, width - corner_radius, end_x_pos  , slider_corner_radius)
            self.canvas.coords(OVAL_3_B, width - corner_radius, end_x_pos  , slider_corner_radius)
            self.canvas.coords(OVAL_4_A, corner_radius        , end_x_pos  , slider_corner_radius)
            self.canvas.coords(OVAL_4_B, corner_radius        , end_x_pos  , slider_corner_radius)

            self.canvas.coords(RECT_1,
                               corner_radius - slider_corner_radius          , start_x_pos,
                               width - (corner_radius - slider_corner_radius), end_x_pos  )
            self.canvas.coords(RECT_2,
                               corner_radius          , corner_radius - slider_corner_radius + max_delta * start_value,
                               width - (corner_radius), corner_radius + slider_corner_radius + max_delta * end_value  )

        elif orientation == "horizontal":
            max_delta = width - 2 * corner_radius
            start_y_pos = corner_radius + max_delta * start_value
            end_y_pos = corner_radius + max_delta * end_value

            self.canvas.coords(OVAL_1_A, start_y_pos, corner_radius         , slider_corner_radius)
            self.canvas.coords(OVAL_1_B, start_y_pos, corner_radius         , slider_corner_radius)
            self.canvas.coords(OVAL_2_A, end_y_pos  , corner_radius         , slider_corner_radius)
            self.canvas.coords(OVAL_2_B, end_y_pos  , corner_radius         , slider_corner_radius)
            self.canvas.coords(OVAL_3_A, end_y_pos  , height - corner_radius, slider_corner_radius)
            self.canvas.coords(OVAL_3_B, end_y_pos  , height - corner_radius, slider_corner_radius)
            self.canvas.coords(OVAL_4_A, start_y_pos, height - corner_radius, slider_corner_radius)
            self.canvas.coords(OVAL_4_B, start_y_pos, height - corner_radius, slider_corner_radius)

            self.canvas.coords(RECT_1,
                               corner_radius - slider_corner_radius + max_delta * start_value, corner_radius         ,
                               corner_radius + slider_corner_radius + max_delta * end_value  , height - corner_radius)
            self.canvas.coords(RECT_2,
                               start_y_pos, corner_radius - slider_corner_radius           ,
                               end_y_pos  , height - (corner_radius - slider_corner_radius))

        return requires_recoloring


@dataclass(frozen=True)
class Arrow(BaseShape):
    """ Draws an arrow at (x_position, y_position) with given size and rotation.\n
    - angle ==  0 degrees => arrow points up.\n
    - angle == 90 degrees => arrow points right. """

    round_width_to_even_numbers: bool = field(default=False, init=False, repr=False, compare=False)  #not used
    round_height_to_even_numbers: bool = field(default=False, init=False, repr=False, compare=False)  #not used

    def update(self,
               x_position: float | int,
               y_position: float | int,
               size: float | int,
               angle: float | int) -> bool:
        """Returns True if recoloring is necessary."""

        x_position, y_position, size = round(x_position), round(y_position), round(size)
        requires_recoloring = False

        if self.drawing_method == "font":
            if not self.canvas.find_withtag(self._name):
                self.canvas.create_text(0, 0, text="Y",
                                        font=("CustomTkinter_shapes_font", -size),
                                        angle=180-angle,
                                        tags=self._name,
                                        anchor=tkinter.CENTER)
                requires_recoloring = True

            self.canvas.coords(self._name, x_position, y_position)
            self.canvas.itemconfigure(self._name, font=("CustomTkinter_shapes_font", -size))

        else:
            if not self.canvas.find_withtag(self._name):
                self.canvas.create_line(0, 0, 0, 0,
                                        tags=self._name,
                                        width=round(size / 4),
                                        joinstyle=tkinter.ROUND,
                                        capstyle=tkinter.ROUND)
                requires_recoloring = True

            #points for arrow centered in (0, 0) pointing up
            points = ((- size / 2, + size / 5),
                      (    0     , - size / 5),
                      (+ size / 2, + size / 5))
            points = rototraslation(points, angle, x_position, y_position)

            #older Python versions require the coordinates to be passed individually...
            self.canvas.coords(self._name, *points[0], *points[1], *points[2])
            self.canvas.itemconfigure(self._name, width=round(size / 4))

        return requires_recoloring

    def set_color(self, color: str) -> None:
        self.canvas.itemconfig(self._name, fill=color)


@dataclass(frozen=True)
class Bar(BaseShape):
    """ Draws a rounded bar at (x_position, y_position) with given size and rotation.\n
    - angle ==  0 degrees => |.\n
    - angle == 90 degrees => -. """

    round_width_to_even_numbers: bool = field(default=False, init=False, repr=False, compare=False)  #not used
    round_height_to_even_numbers: bool = field(default=False, init=False, repr=False, compare=False)  #not used

    def update(self,
               x_position: float | int,
               y_position: float | int,
               size: float | int,
               angle: float | int) -> bool:
        """Returns True if recoloring is necessary."""

        x_position, y_position, size = round(x_position), round(y_position), round(size)
        requires_recoloring = False

        if self.drawing_method == "font":
            if not self.canvas.find_withtag(self._name):
                self.canvas.create_text(0, 0, text="X",
                                        font=("CustomTkinter_shapes_font", -size),
                                        angle=90-angle,
                                        tags=self._name,
                                        anchor=tkinter.CENTER)
                requires_recoloring = True

            self.canvas.coords(self._name, x_position, y_position)
            self.canvas.itemconfigure(self._name, font=("CustomTkinter_shapes_font", -size))

        else:
            if not self.canvas.find_withtag(self._name):
                self.canvas.create_line(0, 0, 0, 0,
                                        tags=self._name,
                                        width=round(size / 6),
                                        joinstyle=tkinter.ROUND,
                                        capstyle=tkinter.ROUND)
                requires_recoloring = True

            #points for vertical line centered in (0, 0)
            points = ((0, + size / 2),
                      (0, - size / 2))
            points = rototraslation(points, angle, x_position, y_position)

            #older Python versions require the coordinates to be passed individually...
            self.canvas.coords(self._name, *points[0], *points[1])
            self.canvas.itemconfigure(self._name, width=round(size / 6))

        return requires_recoloring

    def set_color(self, color: str) -> None:
        self.canvas.itemconfig(self._name, fill=color)


@dataclass(frozen=True)
class Checkmark(BaseShape):
    """ Draws a checkmark at (x_position, y_position) with given size. """

    round_width_to_even_numbers: bool = field(default=False, init=False, repr=False, compare=False)  #not used
    round_height_to_even_numbers: bool = field(default=False, init=False, repr=False, compare=False)  #not used

    def update(self,
               x_position: float | int,
               y_position: float | int,
               size: float | int) -> bool:
        """Returns True if recoloring is necessary."""

        x_position, y_position, size = round(x_position), round(y_position), round(size)
        requires_recoloring = False

        if self.drawing_method == "font":
            if not self.canvas.find_withtag(self._name):
                self.canvas.create_text(0, 0, text="Z",
                                        font=("CustomTkinter_shapes_font", -size),
                                        tags=self._name,
                                        anchor=tkinter.CENTER)
                requires_recoloring = True

            self.canvas.coords(self._name, x_position, y_position)
            self.canvas.itemconfigure(self._name, font=("CustomTkinter_shapes_font", -size))

        else:
            if not self.canvas.find_withtag(self._name):
                self.canvas.create_line(0, 0, 0, 0,
                                        tags=self._name,
                                        width=round(size / 5),
                                        joinstyle=tkinter.MITER,
                                        capstyle=tkinter.ROUND)
                requires_recoloring = True

            radius = size / 2.8
            self.canvas.coords(self._name, x_position + radius    , y_position - radius,
                                           x_position - radius / 4, y_position + radius * 0.8,
                                           x_position - radius    , y_position + radius / 6)
            self.canvas.itemconfigure(self._name, width=round(size / 5))

        return requires_recoloring

    def set_color(self, color: str) -> None:
        self.canvas.itemconfig(self._name, fill=color)
