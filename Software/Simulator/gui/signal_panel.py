"""
SignalPanel — one LED + label per control signal, updated each tick.
Click a signal LED to toggle it (useful in single-step mode).
"""

import tkinter as tk

from signals import Signal
from simulator import Simulator

_OFF_COLOR = "#888888"
_ON_COLOR  = "#22dd22"


class SignalPanel(tk.LabelFrame):
    def __init__(self, parent, sim: Simulator):
        super().__init__(parent, text="CONTROL SIGNALS", padx=3, pady=3)
        self._sim = sim
        self._led_labels: dict[Signal, tk.Label] = {}
        self._build()

    def _build(self):
        signals = list(Signal)
        # Two signals per row, four grid columns per row:
        #   col 0: ● LED    col 1: name    col 2: ● LED    col 3: name
        for i, sig in enumerate(signals):
            pair = i % 2        # 0 = left column pair, 1 = right column pair
            row  = i // 2
            base_col = pair * 2

            led = tk.Label(
                self, text="●", font=("Courier", 10), fg=_OFF_COLOR, cursor="hand2",
            )
            led.grid(row=row, column=base_col, padx=(2, 1), pady=1, sticky="e")
            led.bind("<Button-1>", lambda _e, s=sig: self._toggle(s))

            tk.Label(
                self, text=sig.name, font=("Courier", 8), anchor="w",
                fg="#666666", width=5,
            ).grid(row=row, column=base_col + 1, padx=(0, 6), pady=1, sticky="w")

            self._led_labels[sig] = led

    def _toggle(self, sig: Signal) -> None:
        """Flip a signal's state directly in the controller (single-step testing)."""
        ctrl = self._sim.getController()
        states = ctrl.getSignalStates()
        ctrl._signal_state[sig] = not states[sig]
        self.refresh()

    def refresh(self) -> None:
        states = self._sim.getController().getSignalStates()
        for sig, led in self._led_labels.items():
            led.configure(fg=_ON_COLOR if states[sig] else _OFF_COLOR)
