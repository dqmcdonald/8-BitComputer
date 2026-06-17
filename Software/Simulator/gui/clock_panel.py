"""
ClockPanel — clock-mode, speed, run/stop/step/reset controls.
"""

import math
import tkinter as tk

from clock import ClockMode
from simulator import Simulator

_SPEED_MIN = 0.5    # Hz
_SPEED_MAX = 100.0  # Hz


def _slider_to_hz(val: float) -> float:
    return _SPEED_MIN * (_SPEED_MAX / _SPEED_MIN) ** (val / 100.0)


def _hz_to_slider(hz: float) -> float:
    return 100.0 * math.log(hz / _SPEED_MIN) / math.log(_SPEED_MAX / _SPEED_MIN)


class ClockPanel(tk.LabelFrame):
    def __init__(self, parent, sim: Simulator, root: tk.Tk, on_tick):
        super().__init__(parent, text="CLOCK", padx=6, pady=6)
        self._sim = sim
        self._root = root
        self._on_tick = on_tick
        self._running = False
        self._after_id = None
        self._build()

    def _build(self):
        # Pulse LED + tick counter
        self._pulse_led = tk.Label(self, text="●", font=("Courier", 14), fg="#0d2e0d")
        self._pulse_led.grid(row=0, column=0, sticky="w", padx=(0, 4))
        self._tick_label = tk.Label(self, text="Tick: 0", anchor="w")
        self._tick_label.grid(row=0, column=1, sticky="w")

        # Mode
        self._mode_var = tk.IntVar(value=ClockMode.CONTINUOUS)
        tk.Label(self, text="Mode:").grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        tk.Radiobutton(
            self, text="Continuous", variable=self._mode_var,
            value=ClockMode.CONTINUOUS, command=self._on_mode_change,
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            self, text="Single-step", variable=self._mode_var,
            value=ClockMode.SINGLE_STEP, command=self._on_mode_change,
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        # Speed slider
        self._speed_label = tk.Label(self, text="1.0 Hz", anchor="w")
        self._speed_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._speed_var = tk.DoubleVar(value=_hz_to_slider(1.0))
        tk.Scale(
            self, from_=0, to=100, orient="horizontal",
            variable=self._speed_var, showvalue=False,
            command=self._on_speed_change,
        ).grid(row=5, column=0, columnspan=2, sticky="ew")

        # Buttons
        btn = tk.Frame(self)
        btn.grid(row=6, column=0, columnspan=2, pady=(10, 0))

        self._run_btn = tk.Button(btn, text="Run", width=7, command=self._on_run)
        self._run_btn.grid(row=0, column=0, padx=2, pady=2)

        self._stop_btn = tk.Button(btn, text="Stop", width=7, command=self._on_stop,
                                   state="disabled")
        self._stop_btn.grid(row=0, column=1, padx=2, pady=2)

        self._step_btn = tk.Button(btn, text="Step", width=7, command=self._on_step,
                                   state="disabled")
        self._step_btn.grid(row=1, column=0, padx=2, pady=2)

        tk.Button(btn, text="Reset", width=7, command=self._on_reset).grid(
            row=1, column=1, padx=2, pady=2
        )

        self._root.bind("<space>", lambda _e: self._on_step())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _speed_hz(self) -> float:
        return _slider_to_hz(self._speed_var.get())

    def _stop_running(self):
        self._running = False
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_speed_change(self, _=None):
        self._speed_label.configure(text=f"{self._speed_hz():.1f} Hz")

    def _on_mode_change(self):
        self._stop_running()
        mode = self._mode_var.get()
        if mode == ClockMode.CONTINUOUS:
            self._sim.setClockProps(self._speed_hz(), ClockMode.CONTINUOUS)
            self._run_btn.configure(state="normal")
            self._step_btn.configure(state="disabled")
        else:
            self._sim.setClockProps(self._speed_hz(), ClockMode.SINGLE_STEP)
            self._run_btn.configure(state="disabled")
            self._step_btn.configure(state="normal")

    def _on_run(self):
        self._running = True
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._run_step()

    def _on_stop(self):
        self._stop_running()

    def _on_step(self):
        if self._mode_var.get() != ClockMode.SINGLE_STEP:
            return
        self._sim.getClock().tick()
        self._on_tick()

    def _on_reset(self):
        self._stop_running()
        self._sim.reset()
        self._on_tick()

    def _run_step(self):
        self._sim.getClock().tick()
        self._on_tick()
        if self._running and not self._sim.getClock().isHalted():
            delay_ms = max(1, int(1000 / self._speed_hz()))
            self._after_id = self._root.after(delay_ms, self._run_step)
        else:
            self._stop_running()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        state = self._sim.getClock().getState()
        tick = state["tick_count"]
        self._tick_label.configure(text=f"Tick: {tick}")
        self._pulse_led.configure(fg="#22ee22" if tick % 2 else "#0d2e0d")
