"""
LED — a single LED indicator drawn as a canvas oval.
"""

import tkinter as tk


class LED:
    _ON = "#22ee22"
    _OFF = "#0d2e0d"
    _OUTLINE = "#446644"

    def __init__(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        radius: int = 7,
        on_color: str | None = None,
        off_color: str | None = None,
    ):
        r = radius
        self._canvas = canvas
        self._on_color = on_color or self._ON
        self._off_color = off_color or self._OFF
        self._id = canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=self._off_color, outline=self._OUTLINE, width=1,
        )

    def set(self, on: bool) -> None:
        self._canvas.itemconfig(self._id, fill=self._on_color if on else self._off_color)
