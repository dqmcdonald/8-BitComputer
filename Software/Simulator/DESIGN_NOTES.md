# Simulator — Design Notes

Architecture, current state, and future direction for the 8-bit computer
simulator. The goal is to faithfully model the
[Ben Eater 8-bit computer](https://eater.net/8bit), with the aims of
(1) testing microcode and programs before/while building the hardware, (2)
driving a ROM module from the **same** microcode definition that gets uploaded to
the EEPROMs, and (3) providing a GUI for interactive debugging.

---

## Overall assessment

The simulator is complete and working. Every Ben Eater module has a
software counterpart, the microcode definition is shared with the physical
EEPROM images, an assembler turns mnemonics into program ROM images, and a
Tkinter GUI provides cycle-level visual debugging. A high-level language
compiler at `../Compiler` can compile, assemble, and simulate programs in one
step.

A 167-test `pytest` suite covers all modules at the unit level; 11 assembly
integration tests run programs end-to-end through the full simulator stack.

---

## Architecture

### Modules

| Class | File | Role |
|-------|------|------|
| `Module` | `module.py` | Base: two-phase clock hooks, signal registration, `getState()` |
| `Bus` | `bus.py` | 8-bit master bus, driver tracking, contention detection |
| `Clock` | `clock.py` | `tick()`, `run()`, `isHalted()`, mode (single/continuous), speed |
| `Controller` | `controller.py` | Decodes `(flags, opcode, t_state)` from ROM; asserts control word |
| `Register` | `register.py` | General-purpose 8-bit register (A, B, IR, MAR variants) |
| `OutputRegister` | `register.py` | Register A that prints on every latch of `OUTI` |
| `ALU` | `alu.py` | Combinational add/subtract; carry and zero flags |
| `FlagsRegister` | `flags.py` | Latches carry + zero from ALU on `FLGI` |
| `ProgramCounter` | `progcounter.py` | Increment on `COUE`, drive on `COUO`, load on `JUMP` |
| `RAM` | `memory.py` | 256-byte writable memory |
| `ROM` | `memory.py` | Read-only memory (program ROM and microcode control ROMs) |

### Two-phase clock

Every module implements:

| Method | Phase | Purpose |
|--------|-------|---------|
| `clock_pulse()` | Rising edge | **Drive** — place values on bus |
| `clock_inv_pulse()` | Falling edge | **Latch** — read values from bus |

The controller asserts the full control word at the start of `clock_pulse()`
before any module acts, so all modules see a consistent signal state during
both phases of the same tick.

### Microcode and control ROM

`microcode.py` is the single source of truth. It defines:

- A `32 × 8` table of 24-bit control words (32 opcodes × 8 T-states).
- Four copies of the table, one per flag-state combination
  (`carry × zero` = 4 states), allowing conditional jumps to use different
  microcode rows for the same opcode.
- A `write_roms()` function that serialises the table to `rom1.bin` /
  `rom2.bin` — the same files the simulator loads and that get burned to
  the physical EEPROMs.

ROM addressing:

```
address = (flags << 8) | (opcode << 3) | t_state
```

giving `4 × 32 × 8 = 1024` entries per ROM, split across two files that
match the two-EEPROM physical layout.

T0 and T1 are the common fetch cycle (`PC → prog-ROM addr`, `ROM → IR + PC++`).
Each instruction executes its own steps from T2 onward and ends with `TRES`
to reset the T-state counter.

### Instruction set

18 instructions are defined across the 5-bit opcode space:

| Mnemonic | Opcode | Operation |
|----------|--------|-----------|
| `NOP` | `0x00` | No operation |
| `LDA addr` | `0x01` | A ← RAM[addr] |
| `LDB addr` | `0x02` | B ← RAM[addr] |
| `ADD` | `0x03` | A ← A + B; flags |
| `SUB` | `0x04` | A ← A − B; flags |
| `LDAI imm` | `0x05` | A ← imm |
| `STA addr` | `0x06` | RAM[addr] ← A |
| `STB addr` | `0x07` | RAM[addr] ← B |
| `JMP addr` | `0x08` | PC ← addr |
| `JMC addr` | `0x09` | if carry: PC ← addr |
| `JMZ addr` | `0x0A` | if zero: PC ← addr |
| `OUT` | `0x0B` | Output ← A |
| `HLT` | `0x0C` | Stop clock |
| `LDBI imm` | `0x0D` | B ← imm |
| `ADDI imm` | `0x0E` | A ← A + imm (clobbers B) |
| `SUBI imm` | `0x0F` | A ← A − imm (clobbers B) |
| `CMP` | `0x10` | flags ← A − B; A unchanged |
| `CMPI imm` | `0x11` | flags ← A − imm; A unchanged (clobbers B) |

### Signal encoding

21 control signals are packed into a 24-bit word split across two ROM bytes,
matching the physical two-HC138-decoder layout. Signals in the same decoder
group are mutually exclusive (hardware constraint). The simulator stores all
signals as active-high booleans; any active-low inversion for the real hardware
is the EEPROM generator's responsibility.

### GUI

A Tkinter GUI is in `gui/`:

| File | Role |
|------|------|
| `app.py` | Main window; owns the `Simulator`; drives `refresh_all()` after each tick |
| `diagram.py` | Scrollable canvas: vertical bus rail, module boxes left/right, animated wires |
| `module_view.py` | Per-module box: LED row, hex/dec labels, signal badges, optional 7-segment display |
| `clock_panel.py` | Mode, speed slider, Run/Stop/Step/Reset, tick counter, T-state indicator |
| `signal_panel.py` | All 21 control signals with LED indicators; click to toggle |
| `disassembler.py` | Floating listing window; highlights the current PC; shows operands in hex and decimal |
| `seven_seg.py` | 4-digit amber 7-segment canvas widget (used by the Output Register view) |
| `led.py` | Reusable LED canvas primitive with configurable colours |

Module boxes use colour-coded LEDs by type (green = register, blue = counter,
amber = memory, orange = ALU, purple = flags). The bus rail carries 8 red LEDs
showing the current bus value. The Output Register shows its value on a
7-segment display rather than LED bits. The IR box shows the current instruction
mnemonic as an annotation; the ALU box annotates "SUB" when `SUBT` is asserted.

### Assembler

`../Assembler/assembler.py` is a two-pass assembler supporting:

- Labels, all numeric literal formats (decimal, `0x` hex, `$` hex, `0b` binary).
- `.code` and `.data` sections. A `.data` section generates an initialisation
  preamble that stores each named variable's initial value into RAM before
  jumping to the first `.code` instruction.
- A `-l` listing flag that prints addresses and bytes alongside source lines.

### High-level compiler

`../Compiler/compiler.py` compiles a simple HLL (`.hll` files) to assembly:

- Statements: `let`, assignment, `print`, `while`/`end`, `if`/`else`/`end`.
- Expressions: `atom`, `atom + atom`, `atom - atom`, `atom * atom`
  (multiplication via repeated addition).
- Conditions: `==`, `!=`, `<`, `>`, `<=`, `>=`.
- `--run` flag compiles, assembles, and simulates in one step.

Four compiler integration tests cover: multiplication, conditionals,
Fibonacci, and a prime-number finder (triple-nested loop, 121 bytes total).

---

## Differences from Ben Eater's original design

These are deliberate extensions, not bugs:

| Area | Ben Eater | This simulator |
|------|-----------|----------------|
| Opcode width | 4 bits (16 opcodes max) | 5 bits (32 opcodes max) |
| Operand encoding | Packed in low nibble of IR | Separate byte fetched from program ROM |
| RAM size | 16 bytes | 256 bytes (shared with program code) |
| Address space | 4-bit addresses | 8-bit addresses |
| Instruction count | 16 | 18 (plus `LDBI`, `ADDI`, `SUBI`, `CMP`, `CMPI`) |

The wider opcode and separate operand byte make programs much easier to write
and allow a proper assembler and compiler, at the cost of departing from
Ben Eater's exact instruction encoding.

---

## Remaining software/simulator opportunities

- **numpy dependency.** The `ROM`/`RAM` classes use `numpy` arrays. A plain
  `bytearray` would eliminate the only non-stdlib dependency and simplify the
  code.
- **EEPROM image golden test.** A test that generates `rom1.bin`/`rom2.bin`
  and compares them byte-for-byte against a committed reference image would
  catch any accidental microcode regression before burning new EEPROMs.
- **Program load from GUI.** There is currently no file picker; the program ROM
  must be specified on the command line. A "Load program…" button in the GUI
  would allow loading new programs without restarting.
- **Memory viewer.** The RAM and program ROM contents are not currently visible
  in the GUI beyond the single byte at the current address. A small hex-dump
  panel would be useful for debugging.
- **Clock speeds above ~100 Hz with live rendering.** At high speeds the
  per-tick GUI refresh becomes the bottleneck. Decoupling the render rate from
  the tick rate (render every N ticks, or on a fixed timer) would allow the
  simulator to run at MHz speeds while the GUI updates at ~30 fps.

---

## Most impactful hardware additions

Ordered by the breadth of software capability they unlock:

**1. Stack pointer + CALL/RET**
The single biggest limitation right now. Without a call stack there are no
subroutines, so every program is one flat sequence — the HLL compiler
explicitly lists "no functions" as a hard constraint. Adding a stack pointer
register (SP), PUSH/POP, and CALL/RET instructions unlocks recursion, modular
code, and proper function support in the compiler.

**2. Bitwise instructions (AND, OR, XOR)**
Useful in almost every non-trivial program: masking, testing individual bits,
building flags, packing data. The ALU already handles add/subtract; AND/OR/XOR
are the natural complement at low hardware cost.

**3. Shift instructions (LSL, LSR)**
Fast multiply/divide by powers of two, and essential for serial communication,
bit-banging, and packing/unpacking byte fields. Combined with AND/OR they give
full bit manipulation capability.

**4. Indirect/indexed addressing**
Every address in the current instruction set is a hardcoded literal. Indirect
addressing (e.g. use A's value as the RAM address) enables arrays, lookup
tables, and pointer-based data structures. Without it the compiler's "no
arrays" limitation cannot be removed regardless of what else is added.

**5. Negative (sign) flag**
CMP currently yields carry (unsigned ≥) and zero (=). A negative flag makes
signed comparisons straightforward without multi-instruction workarounds, which
matters as soon as programs deal with signed arithmetic or two's-complement
values.

Beyond these five, 16-bit registers, hardware multiply, and interrupts are all
real improvements but their payoff is limited by the 256-byte address space
ceiling — programs will hit that constraint before the absence of 16-bit
arithmetic becomes the bottleneck. The stack is the highest-leverage single
addition because it is a prerequisite for nearly everything else at the
software level.

### ALU replacement: 74181

The natural IC choice for adding bitwise operations is the **74181** — a 4-bit
ALU that Ben Eater discusses but set aside as too complex for his original
build. Two chained 74181s replace the current 74LS283 adder pair and support
32 operations via four function-select pins (S0–S3) and a mode pin (M):

- **M = 0** (arithmetic): add, subtract, add-with-carry, subtract-with-borrow,
  increment, decrement, and others.
- **M = 1** (logic): AND, OR, XOR, NOT, XNOR, and combinations.

The carry chain is identical to the existing design (carry-out of the low chip
feeds carry-in of the high chip), so flag logic stays intact. Zero detection
still requires an external 8-input NOR (or two 4-input NORs) since the 74181
does not provide a zero output. Modern drop-in equivalents are the **74HC181**
(CMOS, still in production) and **74HCT181** (TTL-compatible inputs).

The single `SUBT` control signal would be replaced by five lines (`M`, `S0`–`S3`),
which need to be driven from the microcode. Importantly, **no third microcode
ROM is required**: ROM2 currently uses only 4 of its 8 output bits (`SUBT` plus
the 3-bit decoder-group-2 encoding), leaving exactly 4 bits spare. Replacing
`SUBT` with `M` + `S0`–`S3` adds 4 net bits, which fits within ROM2's existing
unused capacity.

A third microcode ROM would only be needed if additional control signals beyond
the 74181 function-select lines were added at the same time (e.g. shift-register
direction/enable lines). Adding one is purely mechanical: another EEPROM on the
same 10-bit address bus, with its output bits wired as new control lines and a
matching extension to `encode()` in `signals.py`.
