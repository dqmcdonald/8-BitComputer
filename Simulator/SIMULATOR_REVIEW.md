# Simulator Review & Improvement Plan

A review of the 8-bit computer simulator against the goal of faithfully modelling
the [Ben Eater 8-bit computer](https://eater.net/8bit), with the ultimate aims of
(1) testing microcode and programs before/while building the hardware, (2)
driving a ROM module from the **same** microcode definition that gets uploaded to
the EEPROMs, and (3) eventually adding a GUI.

---

## Overall assessment

The foundation is solid. In particular:

- A clean `Module` base class with a two-phase clock model — `clock_pulse` drives
  the bus, `clock_inv_pulse` latches from it.
- Bus-contention detection (a second driver in the same phase raises).
- Signal registration through the `Controller`, so the wiring is introspectable.
- A thorough, disciplined `pytest` suite covering bus, clock, controller,
  register and memory.
- A well-considered `GUI_DESIGN.md` (model/view separation, `getState()`
  snapshots, non-blocking clock) that is the right shape for the GUI phase.

The architecture is good enough to grow into the full machine without a rewrite.

**The core gap relative to the stated goal:** nothing yet drives the control
signals, and the microcode definition you want to share with hardware does not
exist anywhere. `Software/microcode_upload.py` currently streams placeholder data
(`data = 254 - i`), and the simulator's `Controller` is a passive signal-state
holder — there is no sequencer that reads the instruction register + step counter
+ flags and asserts a control word. Closing that gap is the highest-value work and
unlocks both "test the microcode" and "share one definition with the EEPROM."

---

## The keystone: one canonical microcode definition

Define the instruction set and its microcode **once**, as plain Python data, with
two consumers:

1. **The simulator's control unit** — looks up `(opcode, step, flags)` each tick
   and asserts the corresponding signals.
2. **An EEPROM image generator** — produces the byte image that
   `microcode_upload.py` streams to the Arduino.

Sketch:

```python
# Control signals as bit positions in a 16-bit control word
# (matches the two-EEPROM layout on the hardware).
HLT, MI, RI, RO, IO, II, AI, AO, EO, SU, BI, OI, CE, CO, J, FI = (1 << i for i in range(16))

FETCH = [CO | MI, RO | II | CE]   # T0, T1 — common to every instruction

MICROCODE = {
    0x0: ("NOP", []),
    0x1: ("LDA", [IO | MI, RO | AI]),
    0x2: ("ADD", [IO | MI, RO | BI, EO | AI | FI]),
    0x3: ("SUB", [IO | MI, RO | BI, EO | AI | SU | FI]),
    # ... STA, LDI, JMP, JC, JZ, OUT, HLT
}
```

Details that keep the two consumers in sync with the real machine:

- **Active-low in hardware.** The simulator's signals are active-high booleans
  (clearer for simulation). The EEPROM generator should own the inversion — the
  table stores "logically asserted", and the generator flips the bits that are
  active-low on the board. The register design review confirms `~RIN`/`~ROUT` are
  active-low. The simulator never has to reason about polarity.
- **ROM address layout must match Eater's:**
  `address = (flags << 7) | (opcode << 3) | step` — 2 flag bits, 4 opcode bits,
  3 step bits = 1024 entries. That is why `microcode_upload.py` sends a two-byte
  address (`add1`, `add2`). The 16-bit control word splits across two EEPROMs, so
  the generator emits two images and the uploader runs once per chip.
- **Flags-dependent steps** (JC/JZ) fall out naturally because the flags are part
  of the address — the simulator's control unit and the ROM use the same lookup.

Payoff: a `Memory` subclass `ControlROM` can be initialised straight from
`MICROCODE` for the GUI/simulator, while the same table feeds the uploader. One
source of truth, exactly as intended.

---

## Missing modules for fidelity to Eater's machine

The simulator currently has A, B, IR and RAM. To run real programs it still needs,
in rough priority order:

| Module | Role | Notes |
|---|---|---|
| **Control unit / sequencer** | Drives all signals from microcode | The keystone above. Owns the 3-bit microstep counter (T0–T5); T0/T1 are always the fetch. |
| **Program counter (PC)** | Holds/increments the address | Signals CO (out), CE (enable/increment), J (jump-load from bus). |
| **MAR** | Latches the RAM address | RAM reads/writes go through this, not a direct address argument (see bugs below). |
| **ALU + flags register** | Add/subtract, carry + zero flags | EO (sum out), SU (subtract); FI latches carry/zero, which feed the microcode address. |
| **Output register** | The decimal display | OI latches; in the simulator, just print/store the value. |

---

## Concrete gaps and bugs in the current code

- **`Memory` cannot actually touch the bus.** Unlike `Register`, it never
  overrides `clock_pulse`/`clock_inv_pulse`, and it takes an explicit `address`
  argument with no link to a MAR. As written, RAM cannot be driven by RAMO or
  loaded by RAMI during a tick. It needs a MAR reference and clock methods that
  read `address = mar.getValue()`.
- **The controller is passive.** It stores signal state but offers no clean way to
  assert a control word — the tests poke `_signal_state` directly. Add an API
  (e.g. `setControlWord(bits)` / assert / deassert) that the sequencer calls, and
  derive the `signals` set from the microcode signal definitions rather than the
  hand-maintained module-level global.
- **Dead singletons.** `clock.py` ends with a module-level `clock = Clock()` that
  nothing uses (the `Simulator` builds its own), and `bus.py`'s docstring mentions
  an importable `master` bus that does not exist. Both are confusing leftovers —
  remove them. `GUI_DESIGN.md` already flags singletons as something to avoid.
- **`Clock` HLT is a TODO.** `run()`'s continuous loop has no stopping condition.
  Implement `isHalted()` (anticipated by the GUI doc) tied to the HLT signal so
  both the console and GUI loops terminate.
- **Blocking `input()` in single-step.** `Simulator.run()` blocks on `input()`,
  which cannot live in a GUI event loop. The GUI doc's "caller owns the loop"
  refactor fixes this — worth doing early as it is a GUI prerequisite anyway.
- **RAM size vs. Eater.** Eater's RAM is 16 bytes (4-bit address from the MAR);
  the current default is 1024 bits = 128 bytes. For fidelity, model 16 bytes and
  make the address width explicit so it matches the MAR. The `numpy` array is also
  overkill here — a plain `bytearray` drops a dependency.

---

## Lower-priority polish

- **An assembler** mirrors the microcode story for the program side: mnemonics →
  the 16-byte image, shared between the simulator and `program_upload.py`. The
  `lextest.py`/`bytetest.py` PLY experiments suggest this direction already; a
  tiny two-pass assembler (it is an ~11-instruction ISA) is plenty and avoids the
  PLY dependency.
- **Two-phase timing note.** The drive-then-latch split nicely sidesteps
  bus-ordering hazards. Keep the real-hardware ordering in mind for the sequencer:
  the control word is combinational from `(step, IR, flags)` and the microstep
  counter advances on the falling edge — so compute the control word at the top of
  the tick, drive/latch, then advance the step counter.
- **Keep the test discipline.** The existing suite is a real asset; give each new
  module (PC, MAR, ALU, control unit) the same treatment, and add a golden test
  that asserts the generated EEPROM image matches a known-good byte dump.

---

## Suggested order of work

1. Refactor the blocking clock loop + add `isHalted()`/HLT (also unblocks the GUI).
2. Write the canonical `microcode.py` table + EEPROM image generator; point
   `microcode_upload.py` at it.
3. Add the control unit/sequencer so the simulator actually executes the microcode.
4. Fill in PC, MAR (+ fix `Memory`'s bus/MAR wiring), ALU + flags, output register.
5. Run a real program (e.g. the classic LDA / ADD / OUT / HLT) end to end in the
   console.
6. Build the GUI per the existing design doc.

The natural first implementation commit is step 2 — the canonical microcode
definition plus the EEPROM image generator wired into `microcode_upload.py` — since
that single piece is what ties the simulator and the hardware together.
