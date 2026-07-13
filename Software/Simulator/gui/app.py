"""
SimulatorGUI — main application window.

Run with:
    python -m gui.app PROG_ROM [--ram FILE] [--rom1 FILE] [--rom2 FILE]
"""

import logging
import tkinter as tk

# Imported for its side effect: gui/__init__.py puts the Simulator directory on
# sys.path so the plain "from simulator import ..." below resolves. Not dead.
import gui  # pylint: disable=unused-import
from simulator import Simulator
from gui.clock_panel import ClockPanel
from gui.diagram import DiagramCanvas
from gui.disassembler import DisassemblerWindow
from gui.signal_panel import SignalPanel


# ---------------------------------------------------------------------------
# Logging handler that appends records to a tk.Text widget
# ---------------------------------------------------------------------------

class _TextHandler(logging.Handler):
    def __init__(self, widget: tk.Text):
        super().__init__()
        self._widget = widget

    def emit(self, record):
        msg = self.format(record) + "\n"
        self._widget.configure(state="normal")
        self._widget.insert(tk.END, msg)
        self._widget.see(tk.END)
        self._widget.configure(state="disabled")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class SimulatorGUI:
    def __init__(self, root: tk.Tk, sim: Simulator):
        self.root = root
        self.sim = sim
        self.root.title("8-Bit Computer Simulator")
        self._listing_win: DisassemblerWindow | None = None
        self._build_ui()
        self._attach_logging()
        self.refresh_all()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        # ---- top area: left (diagram) + right (panels) ----
        top = tk.Frame(self.root)
        top.grid(row=0, column=0, sticky="nsew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=0)
        top.rowconfigure(0, weight=1)

        # Left — diagram canvas (Phase 3)
        self._diagram = DiagramCanvas(top, self.sim)
        self._diagram.grid(row=0, column=0, sticky="nsew", padx=(4, 2), pady=4)

        # Right — clock panel + signal panel placeholder
        right = tk.Frame(top, width=220)
        right.grid(row=0, column=1, sticky="ns", padx=(2, 4), pady=4)
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)

        self._clock_panel = ClockPanel(right, self.sim, self.root, self.refresh_all)
        self._clock_panel.pack(fill="x", padx=2, pady=2)

        tk.Button(right, text="Listing…", command=self._toggle_listing).pack(
            fill="x", padx=4, pady=(0, 4)
        )

        self._signal_panel = SignalPanel(right, self.sim)
        self._signal_panel.pack(fill="both", expand=True, padx=2, pady=(2, 2))

        # ---- bottom — log pane ----
        log_frame = tk.LabelFrame(self.root, text="Log", padx=4, pady=2)
        log_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        log_frame.columnconfigure(0, weight=1)

        self._log_text = tk.Text(
            log_frame, height=5, state="disabled",
            font=("Courier", 10), bg="#0d0d0d", fg="#bbbbbb",
        )
        _lsb = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=_lsb.set)
        self._log_text.grid(row=0, column=0, sticky="ew")
        _lsb.grid(row=0, column=1, sticky="ns")

    def _attach_logging(self):
        handler = _TextHandler(self._log_text)
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        handler.setLevel(logging.INFO)
        root = logging.getLogger()
        # Pin any pre-existing handlers (e.g. the StreamHandler from basicConfig)
        # to WARNING so that raising the root level to INFO below does not cause
        # INFO messages to spill onto the terminal.
        for h in root.handlers:
            if h.level < logging.WARNING:
                h.setLevel(logging.WARNING)
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _toggle_listing(self):
        if self._listing_win is not None:
            self._listing_win._close()
        else:
            self._listing_win = DisassemblerWindow(
                self.root, self.sim,
                on_close=self._on_listing_closed,
            )

    def _on_listing_closed(self):
        self._listing_win = None

    def refresh_all(self):
        """Called after every tick to update all displayed state."""
        self._diagram.refresh()
        self._clock_panel.refresh()
        self._signal_panel.refresh()
        if self._listing_win is not None:
            self._listing_win.refresh()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="8-Bit Computer Simulator GUI")
    parser.add_argument("prog_rom", metavar="PROG_ROM",
                        help="Binary file to load into program ROM")
    parser.add_argument("--ram",  default="", metavar="FILE")
    parser.add_argument("--rom1", default="rom1.bin", metavar="FILE")
    parser.add_argument("--rom2", default="rom2.bin", metavar="FILE")
    args = parser.parse_args()

    root = tk.Tk()
    root.geometry("900x680")

    sim = Simulator(
        ram_file=args.ram,
        prog_rom_file=args.prog_rom,
        rom1_file=args.rom1,
        rom2_file=args.rom2,
    )
    SimulatorGUI(root, sim)
    root.mainloop()


if __name__ == "__main__":
    main()
