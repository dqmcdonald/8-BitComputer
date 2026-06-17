# Simulator GUI — Design Plan

A graphical front end for the 8-bit computer simulator that visually displays
the state of all modules, the connections between them, and the values they
hold, with full interactive control of the clock.

## Goals

1. Show every module (registers, bus, controller, clock — and later ALU, RAM,
   PC, output) as a panel with its current value displayed as 8 LEDs plus
   hex/decimal, in the spirit of Ben Eater's breadboard layout.
2. Draw the connections between modules and the bus, and highlight them when
   data is actually flowing (module driving the bus, module latching from it).
3. Show all control signals and which are asserted on the current tick.
4. Clock controls: speed slider, mode selector (Continuous / Single-step),
   a **Step** button for single-step mode, plus Run/Stop and Reset.
5. New modules added to the simulator should appear in the GUI with little or
   no GUI-specific wiring.

## Toolkit choice: Tkinter

**Recommendation: Tkinter** (with `tkinter.Canvas` for the module diagram).

- Ships with Python — no new dependencies, works everywhere the simulator
  already runs.
- `Canvas` is well suited to this job: boxes, wires, LED circles, and text are
  all first-class items that can be tagged and updated in place.
- `root.after()` gives us a timer-driven clock that integrates cleanly with
  the event loop — no threads needed at breadboard-realistic clock speeds.

Alternatives considered: **PySide6/Qt** (nicer widgets, but a heavy dependency
for this scale) and a **browser-based UI** (Flask + JS — adds a client/server
split and two languages for no benefit here). If the GUI later needs >1 kHz
visualised clock rates or fancier rendering, Qt's `QGraphicsScene` is the
natural upgrade path; the model/view split below keeps that door open.

## Architecture

Strict model/view separation. The existing simulator classes are the model;
the GUI never reaches into private attributes and the model never imports
anything from the GUI.

```
Simulator/
    simulator.py          # model (existing, lightly refactored)
    clock.py, bus.py, register.py, controller.py, module.py
    gui/
        __init__.py
        app.py            # SimulatorGUI: main window, owns the Simulator
        clock_panel.py    # speed / mode / step / run / reset controls
        diagram.py        # Canvas: module boxes, bus, connection wires
        module_view.py    # per-module widgets (LED row, hex/dec labels)
        signal_panel.py   # control-signal state display
        led.py            # small reusable LED indicator widget
```

Run with `python -m gui.app` (or a `--gui` flag on `simulator.py`); the
existing console mode keeps working unchanged.

### Update strategy: poll after each tick

The whole machine state is tiny (a handful of bytes plus signal booleans), so
rather than an observer/event system, the GUI simply refreshes every view
after each `clock.tick()`. One code path, no stale-listener bugs, and at
human-visible clock speeds the cost is negligible. Canvas items are created
once and updated via `itemconfig`, so refreshes don't flicker.

### Required model refactors (prerequisite, no behaviour change)

1. **Non-blocking clock.** `Clock.run()`'s `while True: tick(); sleep()` loop
   and `Simulator.run()`'s `input()` prompt both block, so neither can live
   inside a GUI event loop. Split control from stepping:
   - `Clock.tick()` stays the single-step primitive (it already is).
   - The *caller* owns the loop. Console mode keeps a loop like today's; the
     GUI schedules `tick()` with `root.after(int(1000 / speed), ...)`.
   - Add `Clock.isHalted()` (the existing `TODO` for the HLT condition) so
     both front ends know when to stop.

2. **State inspection API.** Give `Module` a uniform read-only snapshot:

   ```python
   def getState(self) -> dict:
       """e.g. {"name": "RegisterA", "value": 0x2A,
                "signals": {"RAIN": False, "RAOU": True}}"""
   ```

   `Register`, `Bus` (value + current driver name), and `Clock` (tick count,
   mode, speed) each override it. The GUI consumes only these dicts.

3. **Expose the wiring.** The data needed to draw connections already exists:
   - `Controller._registered_modules` maps module → signals. Add a public
     `getConnections()` accessor returning it (read-only copy), plus
     `getSignalStates()` returning the full signal-state dict.
   - `Simulator` gets `getModules()`, `getBus()`, `getClock()`,
     `getController()` accessors so the GUI can enumerate everything without
     touching underscore attributes.
   - `Bus.getDriver()` already identifies who is driving — used to highlight
     the active output connection.

4. **Reset.** `Simulator.reset()` — clear bus, controller signals, register
   values, and the tick counter — backing the GUI's Reset button.

With these in place the GUI is purely additive; `test_simulator.py` continues
to pass untouched (new accessors get their own tests).

## Window layout

```
+--------------------------------------------------------------------------+
|  8-Bit Computer Simulator                                                 |
+------------------------------------------------------+-------------------+
|                                                      | CLOCK             |
|   +-------------+        ||        +-------------+   |  Tick: 42         |
|   |  Clock      |========||        | Register A  |   |  Mode: (•) Cont   |
|   |  ● tick 42  |        ||========| ●●○○●○●○    |   |        ( ) Step   |
|   +-------------+        ||        | 0xA5  165   |   |  Speed: 2 Hz      |
|                          ||        +-------------+   |  [----|------]    |
|                          ||                          |                   |
|                       MASTER       +-------------+   |  [ Run ] [ Stop ] |
|                        BUS ========| Register B  |   |  [ Step ]         |
|                          ||        | ○○●●○○●●    |   |  [ Reset ]        |
|                          ||        | 0x33   51   |   +-------------------+
|                          ||        +-------------+   | CONTROL SIGNALS   |
|   +------------------------------------------+       |  HALT ○  CLEA ○   |
|   | BUS  ●○●○○●○●   0xA5   driver: RegisterA |       |  RAIN ○  RAOU ●   |
|   +------------------------------------------+       |  RBIN ○  RBOU ○   |
|                                                      +-------------------+
+------------------------------------------------------+-------------------+
|  Log: RegisterA: output 0xA5 to bus | Master Bus: set to 0xA5 by ...      |
+--------------------------------------------------------------------------+
```

- **Left: diagram canvas.** A vertical master-bus rail in the centre (Ben
  Eater style), module boxes placed alternately left/right of it, each with a
  wire to the rail. Layout is computed from `Simulator.getModules()`, so new
  modules slot in automatically.
- **Right top: clock panel** (details below).
- **Right bottom: signal panel.** One LED + label per signal from
  `Controller.getSignalStates()`; asserted signals light up. Stretch goal:
  clicking a signal LED toggles it manually — invaluable for experimenting
  before a real control ROM exists.
- **Bottom: log pane.** A `logging.Handler` that appends to a scrolling text
  widget, replacing the console as the debug trace while the GUI runs.

### Module view (one per module)

| Element       | Source                          |
|---------------|---------------------------------|
| Title         | `getState()["name"]`            |
| 8 LEDs        | bits of `value`, MSB first      |
| Hex + decimal | `value`                         |
| Signal badges | module's entries in `getConnections()`, lit per signal state |

The bus box additionally shows the current driver name, and the clock box
shows the tick count with a pulsing LED.

### Connection rendering

- One wire per module from its box to the bus rail, derived from
  `getConnections()` (any module registered for an `*IN`/`*OU` bus signal).
- During refresh: if `Bus.getDriver()` is module *M*, draw *M*'s wire thick
  red with an arrowhead toward the bus; if a module's `IN` signal is asserted,
  draw its wire thick green with the arrowhead toward the module; otherwise a
  thin grey line. This makes each transfer visually obvious in single-step.

### Clock panel

| Control     | Widget                          | Behaviour |
|-------------|---------------------------------|-----------|
| Mode        | Radio: Continuous / Single-step | Switching to Single-step cancels any pending `after()` callback; switching to Continuous enables Run. |
| Speed       | Slider, logarithmic 0.5–100 Hz, current value shown | Read each cycle, so it takes effect live while running. |
| Run / Stop  | Buttons (enabled in Continuous) | Run schedules the tick loop via `after()`; Stop cancels it. |
| **Step**    | Button (enabled in Single-step), keyboard shortcut **Space** | One `clock.tick()` + full GUI refresh. |
| Reset       | Button                          | Stops the clock, calls `Simulator.reset()`, refreshes. |
| Tick count  | Label                           | From `Clock.getState()`. |

Continuous-mode loop:

```python
def _run_step(self):
    self.sim.getClock().tick()
    self.refresh_all()
    if self._running and not self.sim.getClock().isHalted():
        delay_ms = int(1000 / self.speed_var.get())
        self._after_id = self.root.after(delay_ms, self._run_step)
```

## Implementation phases

Each phase ends working and committed.

1. **Model refactor.** Non-blocking clock control, `getState()` on all
   modules, `Controller.getConnections()` / `getSignalStates()`, `Simulator`
   accessors and `reset()`, `Clock.isHalted()`. Update/extend tests; console
   mode behaviour unchanged.
2. **GUI skeleton + clock controls.** Window, clock panel fully functional
   (mode, speed, run/stop/step/reset, tick counter), log pane. State shown
   only as plain text — proves the event-loop integration end to end.
3. **Diagram canvas.** Module boxes with LEDs and hex/dec values, bus rail,
   static connection wires, per-tick refresh.
4. **Live signals & data flow.** Signal panel, driver/latch wire
   highlighting, bus driver label, clock pulse LED. Optional: click-to-toggle
   signals.
5. **(Later, as the simulator grows.)** Views for ALU/RAM/PC/IR/output,
   memory contents table, program load dialog — each new module only needs a
   `getState()` and, if it isn't a plain register, a small view subclass.

## Out of scope (for now)

- Editing memory/microcode from the GUI.
- Clock speeds above ~100 Hz with per-tick rendering (would need decoupled
  render rate).
- Saving/restoring machine state.
