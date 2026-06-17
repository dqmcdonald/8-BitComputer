"""
LED — a single LED indicator drawn as a canvas oval.
"""

import tkinter as tk


class LED:
    _ON = "#22ee22"
    _OFF = "#0d2e0d"
    _OUTLINE = "#446644"

    def __init__(self, canvas: tk.Canvas, x: int, y: int, radius: int = 7):
        r = radius
        self._canvas = canvas
        self._id = canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=self._OFF, outline=self._OUTLINE, width=1,
        )

    def set(self, on: bool) -> None:
        self._canvas.itemconfig(self._id, fill=self._ON if on else self._OFF)
