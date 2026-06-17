"""
ModuleView — canvas items for one module: box, name, 8 LEDs, hex/dec, signal badges.
"""

import tkinter as tk

from .led import LED

_BOX_FILL    = "#0d1a0d"
_BOX_OUTLINE = "#336633"
_NAME_COLOR  = "#88aa88"
_HEX_COLOR   = "#00ff88"
_DEC_COLOR   = "#008844"
_SIG_OFF     = "#334433"
_SIG_ON      = "#22ee22"


class ModuleView:
    def __init__(
        self,
        canvas: tk.Canvas,
        x1: int, y1: int,
        x2: int, y2: int,
        name: str,
        signal_names: tuple[str, ...] = (),
    ):
        self._canvas = canvas
        self._y_mid = (y1 + y2) // 2
        self._x1, self._x2 = x1, x2
        cx = (x1 + x2) // 2
        box_w = x2 - x1

        # Box
        canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=_BOX_OUTLINE, fill=_BOX_FILL, width=1,
        )

        # Module name
        canvas.create_text(
            cx, y1 + 12,
            text=name, fill=_NAME_COLOR,
            font=("Courier", 9, "bold"), anchor="center",
        )

        # 8 LEDs — spacing scales with box width
        pad_x = max(10, box_w // 10)
        led_area = box_w - 2 * pad_x
        led_spacing = led_area // 7
        led_r = max(4, min(8, led_spacing // 3))
        led_x0 = x1 + pad_x
        led_y = y1 + 34
        self._leds = [
            LED(canvas, led_x0 + i * led_spacing, led_y, led_r)
            for i in range(8)
        ]

        # Hex + decimal
        self._hex_id = canvas.create_text(
            cx - 22, y1 + 55,
            text="0x00", fill=_HEX_COLOR,
            font=("Courier", 10, "bold"), anchor="center",
        )
        self._dec_id = canvas.create_text(
            cx + 24, y1 + 55,
            text="0", fill=_DEC_COLOR,
            font=("Courier", 10), anchor="center",
        )

        # Signal badges — one coloured name per registered signal, bottom of box
        self._sig_ids: dict[str, int] = {}
        if signal_names:
            badge_spacing = min(46, (box_w - 12) // len(signal_names))
            badge_y = y2 - 10
            for i, sig_name in enumerate(signal_names):
                item_id = canvas.create_text(
                    x1 + 6 + i * badge_spacing, badge_y,
                    text=sig_name, fill=_SIG_OFF,
                    font=("Courier", 7), anchor="w",
                )
                self._sig_ids[sig_name] = item_id

    @property
    def wire_y(self) -> int:
        return self._y_mid

    @property
    def left_x(self) -> int:
        return self._x1

    @property
    def right_x(self) -> int:
        return self._x2

    def update(self, value: int) -> None:
        value &= 0xFF
        for i, led in enumerate(self._leds):
            led.set(bool((value >> (7 - i)) & 1))
        self._canvas.itemconfig(self._hex_id, text=f"0x{value:02X}")
        self._canvas.itemconfig(self._dec_id, text=str(value))

    def update_signals(self, states: dict[str, bool]) -> None:
        for sig_name, item_id in self._sig_ids.items():
            on = states.get(sig_name, False)
            self._canvas.itemconfig(item_id, fill=_SIG_ON if on else _SIG_OFF)
