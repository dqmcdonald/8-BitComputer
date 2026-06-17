"""
SevenSegDisplay — draws a 4-digit 7-segment display on a tk.Canvas.

Segments are labelled in the classic order:
    aaa
  f     b
  f     b
    ggg
  e     c
  e     c
    ddd
"""

import tkinter as tk

# On/off colours — classic amber (as in vintage LED displays)
_SEG_ON  = "#ff8800"
_SEG_OFF = "#251200"
_BG      = "#0d0800"

# a  b  c  d  e  f  g
_PATTERNS = [
    (1, 1, 1, 1, 1, 1, 0),  # 0
    (0, 1, 1, 0, 0, 0, 0),  # 1
    (1, 1, 0, 1, 1, 0, 1),  # 2
    (1, 1, 1, 1, 0, 0, 1),  # 3
    (0, 1, 1, 0, 0, 1, 1),  # 4
    (1, 0, 1, 1, 0, 1, 1),  # 5
    (1, 0, 1, 1, 1, 1, 1),  # 6
    (1, 1, 1, 0, 0, 0, 0),  # 7
    (1, 1, 1, 1, 1, 1, 1),  # 8
    (1, 1, 1, 1, 0, 1, 1),  # 9
]
_BLANK = (0, 0, 0, 0, 0, 0, 0)


def _make_digit(
    canvas: tk.Canvas,
    x0: int, y0: int,
    dw: int, dh: int,
    sw: int = 2,
    cap: int = 2,
) -> list[int]:
    """Draw one digit's 7 segments (all off) and return their canvas IDs."""
    x1 = x0 + dw
    y1 = y0 + dh
    ym = y0 + dh // 2
    kw = dict(fill=_SEG_OFF, width=sw, capstyle="round")
    return [
        canvas.create_line(x0 + cap, y0, x1 - cap, y0, **kw),       # a top
        canvas.create_line(x1, y0 + cap, x1, ym - cap, **kw),        # b upper-right
        canvas.create_line(x1, ym + cap, x1, y1 - cap, **kw),        # c lower-right
        canvas.create_line(x0 + cap, y1, x1 - cap, y1, **kw),        # d bottom
        canvas.create_line(x0, ym + cap, x0, y1 - cap, **kw),        # e lower-left
        canvas.create_line(x0, y0 + cap, x0, ym - cap, **kw),        # f upper-left
        canvas.create_line(x0 + cap, ym, x1 - cap, ym, **kw),        # g middle
    ]


class SevenSegDisplay:
    """4-digit 7-segment display centred at (cx, y_top)."""

    def __init__(
        self,
        canvas: tk.Canvas,
        cx: int,
        y_top: int,
        n_digits: int = 4,
        digit_w: int = 20,
        digit_h: int = 32,
        gap: int = 5,
        seg_width: int = 2,
    ):
        self._canvas = canvas
        self._n = n_digits

        total_w = n_digits * digit_w + (n_digits - 1) * gap
        x0 = cx - total_w // 2

        # Dark background
        canvas.create_rectangle(
            x0 - 3, y_top - 3,
            x0 + total_w + 3, y_top + digit_h + 3,
            fill=_BG, outline="#332200", width=1,
        )

        self._digit_ids: list[list[int]] = []
        for i in range(n_digits):
            dx = x0 + i * (digit_w + gap)
            ids = _make_digit(canvas, dx, y_top, digit_w, digit_h, seg_width)
            self._digit_ids.append(ids)

    def set_value(self, value: int) -> None:
        """Update the display to show `value` right-justified, space-padded."""
        text = f"{value:4d}" if 0 <= value <= 9999 else "----"
        for i, ch in enumerate(text):
            if ch.isdigit():
                pattern = _PATTERNS[int(ch)]
            else:
                pattern = _BLANK
            for seg_id, on in zip(self._digit_ids[i], pattern):
                self._canvas.itemconfig(seg_id, fill=_SEG_ON if on else _SEG_OFF)
