"""
DiagramCanvas — bus rail, module boxes, connection wires with live highlighting.
"""

import tkinter as tk

from instructions import InstructionSet
from signals import Signal
from simulator import Simulator
from .led import LED
from .module_view import ModuleView

# Signals that represent a bus connection (drive or read the bus).
_BUS_SIGNALS = frozenset({
    Signal.ARGI, Signal.ARGO,
    Signal.BRGI, Signal.BRGO,
    Signal.ALUO,
    Signal.IRGI, Signal.IRGO,
    Signal.MRAI, Signal.MROI,
    Signal.OUTI,
    Signal.RAMI, Signal.RAMO,
    Signal.ROMO,
    Signal.COUO, Signal.JUMP,
})

# Subset of _BUS_SIGNALS that mean "latch FROM bus" (wire arrow toward module).
_BUS_IN_SIGNALS = frozenset({
    Signal.ARGI, Signal.BRGI, Signal.IRGI,
    Signal.MRAI, Signal.MROI, Signal.OUTI,
    Signal.RAMI, Signal.JUMP,
})

# LED colors per module kind: (on_color, off_color)
_KIND_LED_COLORS: dict[str, tuple[str, str]] = {
    "register": ("#22ee22", "#0d2e0d"),   # green
    "output":   ("#66ff66", "#0d2e0d"),   # bright green
    "counter":  ("#2277ee", "#0d0d2e"),   # blue
    "memory":   ("#ddcc22", "#2a250d"),   # amber/yellow
    "alu":      ("#ee8822", "#2e1a0d"),   # orange
    "flags":    ("#cc44ee", "#1e0d2e"),   # purple
}

# Bus bit-LEDs
_BUS_LED_ON  = "#dd2222"
_BUS_LED_OFF = "#200808"
_BUS_LED_R   = 5
_BUS_LED_GAP = 13          # centre-to-centre spacing

# Layout
_BOX_H          = 100
_BUS_GAP        = 28
_ROW_H          = _BOX_H + 20
_MARGIN_TOP     = 86       # room for bus LEDs above the rail
_MARGIN_BOTTOM  = 16
_MARGIN_SIDE    = 10

# Colours
_BG              = "#111111"
_BUS_RAIL_COLOR  = "#3355cc"
_BUS_LABEL_COLOR = "#7788ff"
_BUS_VAL_COLOR   = "#aabbff"
_WIRE_IDLE       = "#2a4a2a"
_WIRE_DRIVE      = "#cc2222"
_WIRE_LATCH      = "#22aa22"


class DiagramCanvas(tk.Frame):
    """Scrollable canvas diagram of the full simulator state."""

    def __init__(self, parent, sim: Simulator):
        super().__init__(parent, bg=_BG)
        self._sim = sim

        self._module_views: list[ModuleView] = []
        self._wire_data: list[tuple[int, str, frozenset] | None] = []
        self._bus_val_id: int | None = None
        self._bus_driver_id: int | None = None
        self._bus_leds: list[LED] = []
        self._built = False
        self._last_w = 0
        self._ir_view_idx: int | None = None
        self._alu_view_idx: int | None = None

        self._canvas = tk.Canvas(self, bg=_BG, highlightthickness=0)
        _sb = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=_sb.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        _sb.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self._canvas.bind("<Button-4>",   self._on_wheel)
        self._canvas.bind("<Button-5>",   self._on_wheel)
        self._canvas.bind("<Configure>",  self._on_configure)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _on_configure(self, event):
        if event.width > 1 and event.width != self._last_w:
            self._last_w = event.width
            self._rebuild(event.width)

    def _on_wheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def _rebuild(self, w: int):
        c = self._canvas
        c.delete("all")
        self._module_views.clear()
        self._wire_data.clear()
        self._bus_leds.clear()
        self._ir_view_idx = None
        self._alu_view_idx = None
        self._built = True

        modules = self._sim.getModules()
        connections = self._sim.getController().getConnections()

        n_rows  = (len(modules) + 1) // 2
        total_h = _MARGIN_TOP + n_rows * _ROW_H + _MARGIN_BOTTOM
        c.configure(scrollregion=(0, 0, w, total_h))

        bus_x = w // 2

        # Bus rail
        c.create_line(bus_x, _MARGIN_TOP - 16, bus_x, total_h - _MARGIN_BOTTOM,
                      fill=_BUS_RAIL_COLOR, width=4)

        # Bus header: title, 8 red bit-LEDs, hex value, driver
        c.create_text(bus_x, 10, text="MASTER BUS",
                      fill=_BUS_LABEL_COLOR, font=("Courier", 10, "bold"), anchor="center")

        led_total_w = 7 * _BUS_LED_GAP
        led_x0 = bus_x - led_total_w // 2
        led_y  = 30
        for i in range(8):
            self._bus_leds.append(
                LED(c, led_x0 + i * _BUS_LED_GAP, led_y, _BUS_LED_R,
                    on_color=_BUS_LED_ON, off_color=_BUS_LED_OFF)
            )

        self._bus_val_id = c.create_text(
            bus_x, 50, text="0x00",
            fill=_BUS_VAL_COLOR, font=("Courier", 12, "bold"), anchor="center",
        )
        self._bus_driver_id = c.create_text(
            bus_x, 66, text="",
            fill="#5566aa", font=("Courier", 9), anchor="center",
        )

        # Module boxes and wires
        for i, m in enumerate(modules):
            row  = i // 2
            y1   = _MARGIN_TOP + row * _ROW_H
            y2   = y1 + _BOX_H
            side = "left" if i % 2 == 0 else "right"

            if side == "left":
                x1, x2 = _MARGIN_SIDE, bus_x - _BUS_GAP
            else:
                x1, x2 = bus_x + _BUS_GAP, w - _MARGIN_SIDE

            mod_sigs = set(connections.get(m.getName(), []))
            sig_names = tuple(s.name for s in mod_sigs)

            kind = m.getState().get("kind", "module")
            led_on, led_off = _KIND_LED_COLORS.get(kind, ("#22ee22", "#0d2e0d"))
            is_output = (m.getName() == "Output Register")

            mv = ModuleView(
                c, x1, y1, x2, y2, m.getName(),
                signal_names=sig_names,
                led_on_color=led_on,
                led_off_color=led_off,
                use_seven_seg=is_output,
            )
            self._module_views.append(mv)

            if m.getName() == "InstructionReg":
                self._ir_view_idx = i
            if m.getName() == "ALU":
                self._alu_view_idx = i

            if mod_sigs & _BUS_SIGNALS:
                wy  = mv.wire_y
                in_sigs = mod_sigs & _BUS_IN_SIGNALS
                if side == "left":
                    wid = c.create_line(x2, wy, bus_x, wy,
                                        fill=_WIRE_IDLE, width=2,
                                        arrowshape=(10, 12, 4))
                else:
                    wid = c.create_line(bus_x, wy, x1, wy,
                                        fill=_WIRE_IDLE, width=2,
                                        arrowshape=(10, 12, 4))
                self._wire_data.append((wid, side, in_sigs))
            else:
                self._wire_data.append(None)

        self.refresh()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._built:
            return

        bus_state      = self._sim.getBus().getState()
        bus_val        = bus_state["value"]
        bus_driver     = bus_state["driver"]
        sig_states     = self._sim.getController().getSignalStates()
        sig_str_states = {s.name: v for s, v in sig_states.items()}

        # Bus LEDs
        for i, led in enumerate(self._bus_leds):
            led.set(bool((bus_val >> (7 - i)) & 1))

        for idx, (mv, m, wire) in enumerate(
            zip(self._module_views, self._sim.getModules(), self._wire_data)
        ):
            value = m.getState().get("value", 0)
            mv.update(value)
            mv.update_signals(sig_str_states)

            if idx == self._ir_view_idx:
                opcode = value & 0x1F
                try:
                    mnemonic = InstructionSet(opcode).name
                except ValueError:
                    mnemonic = "???"
                mv.set_annotation(mnemonic)

            if idx == self._alu_view_idx:
                mv.set_annotation("SUB" if sig_states.get(Signal.SUBT, False) else "")

            if wire is None:
                continue
            wire_id, side, in_sigs = wire
            name = m.getName()

            if name == bus_driver:
                fill  = _WIRE_DRIVE
                width = 4
                arrow = "last" if side == "left" else "first"
            elif any(sig_states.get(s, False) for s in in_sigs):
                fill  = _WIRE_LATCH
                width = 4
                arrow = "first" if side == "left" else "last"
            else:
                fill  = _WIRE_IDLE
                width = 2
                arrow = "none"

            self._canvas.itemconfig(wire_id, fill=fill, width=width, arrow=arrow)

        # Bus text labels
        self._canvas.itemconfig(self._bus_val_id, text=f"0x{bus_val:02X}")
        driver_text = f"← {bus_driver}" if bus_driver else ""
        self._canvas.itemconfig(self._bus_driver_id, text=driver_text)
