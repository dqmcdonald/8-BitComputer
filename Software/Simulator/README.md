# 8-Bit Computer Simulator

A cycle-accurate software simulator for the homebrew 8-bit computer described by
[Ben Eater](https://eater.net/8bit). The goal is a platform for writing and testing
programs and microcode before — or while — building the physical hardware, using
the **same microcode definition** that gets burned to the control EEPROMs.

---

## Contents

- [Quick start](#quick-start)
- [Running the simulator](#running-the-simulator)
- [Graphical interface](#graphical-interface)
- [Assembler](#assembler)
- [Instruction set](#instruction-set)
- [Assembly language syntax](#assembly-language-syntax)
- [Microcode and ROM generation](#microcode-and-rom-generation)
- [Signal strategy](#signal-strategy)
- [Test suite](#test-suite)
- [Module architecture](#module-architecture)

---

## Quick start

```bash
# Prerequisites: Python 3.11+, numpy, tkinter (included with most Python installs)
pip install numpy

# Assemble a program and run it
python ../Assembler/assembler.py tests/test_08_countdown.asm -o prog.bin
python simulator.py prog.bin --speed 10

# Launch the GUI
python simulator.py prog.bin --gui
```

---

## Running the simulator

```
python simulator.py PROG_ROM [options]
```

`PROG_ROM` is required — a flat binary produced by the assembler.

| Flag | Default | Description |
|------|---------|-------------|
| `--ram FILE` / `-r` | *(none)* | Binary image to preload into RAM |
| `--rom1 FILE` | `rom1.bin` | Microcode ROM 1 |
| `--rom2 FILE` | `rom2.bin` | Microcode ROM 2 |
| `--mode single\|continuous` / `-m` | `continuous` | Clock mode |
| `--speed HZ` / `-s` | `1.0` | Clock speed in Hz |
| `--gui` / `-g` | *(off)* | Launch the graphical interface |
| `--debug` / `-d` | *(off)* | Enable DEBUG logging for all modules |
| `--debug-module NAME` / `-D` | *(none)* | Enable DEBUG for a specific module (repeatable) |

In **single-step** mode the simulator pauses after each tick and waits for Enter
(or `q` to quit). In **continuous** mode it runs at the requested speed until
`HLT` is encountered.

### Example: inspect the fetch cycle

```bash
python simulator.py prog.bin --mode single --debug-module controller
```

---

## Graphical interface

```bash
python -m gui.app PROG_ROM [--ram FILE] [--rom1 FILE] [--rom2 FILE]
# or equivalently:
python simulator.py prog.bin --gui
```

The GUI window has three areas:

**Left — diagram canvas**  
A vertical bus rail in the centre with module boxes alternating left and right,
Ben Eater breadboard style. Each box shows:
- Module name
- 8 LED indicators (MSB first) reflecting the current value
- Hex and decimal value
- Signal badges — the module's registered signals, lit green when asserted

Wires between module boxes and the bus rail change colour each tick:
- **Red, thick, arrowhead toward bus** — this module is driving the bus
- **Green, thick, arrowhead toward module** — this module is latching from the bus
- **Grey, thin** — idle

**Right — control panels**  
- *Clock panel*: mode (Continuous / Single-step), logarithmic speed slider
  (0.5–100 Hz), Run / Stop / Step / Reset buttons. Space bar steps in
  single-step mode. The `●` pulse LED next to the tick counter alternates
  each tick.
- *Signal panel*: all 21 control signals with LED indicators. Click any
  signal LED to toggle it manually — useful for experimenting in single-step
  mode before a control ROM exists.

**Bottom — log pane**  
Python `logging` output at INFO level, scrolling.

---

## Assembler

The assembler lives at `../Assembler/assembler.py` and produces a flat binary
suitable for passing as `PROG_ROM` to the simulator.

```bash
python ../Assembler/assembler.py SOURCE.asm [-o OUTPUT.bin] [-l]
```

| Flag | Description |
|------|-------------|
| `-o FILE` | Output binary (default: source with `.bin` extension) |
| `-l` | Print an address/byte listing alongside source lines |

### Example

```bash
python ../Assembler/assembler.py tests/test_09_data_init.asm -l
```

```
; --- auto-generated initialization preamble ---
0000: 05 0A    LDAI 10
0002: 06 08    STA 8
0004: 05 01    LDAI 1
0006: 06 09    STA 9
0008: 02 08    JMP 8
          ...
```

---

## Instruction set

The machine has a 5-bit opcode field (32 possible opcodes; 18 defined).
All instructions that take an operand encode it as the next byte in the
program ROM.

| Mnemonic | Opcode | Operand | Operation |
|----------|--------|---------|-----------|
| `NOP` | `0x00` | — | No operation |
| `LDA addr` | `0x01` | RAM address | A ← RAM[addr] |
| `LDB addr` | `0x02` | RAM address | B ← RAM[addr] |
| `ADD` | `0x03` | — | A ← A + B; flags |
| `SUB` | `0x04` | — | A ← A − B; flags |
| `LDAI imm` | `0x05` | byte | A ← imm |
| `STA addr` | `0x06` | RAM address | RAM[addr] ← A |
| `STB addr` | `0x07` | RAM address | RAM[addr] ← B |
| `JMP addr` | `0x08` | ROM address | PC ← addr |
| `JMC addr` | `0x09` | ROM address | if carry: PC ← addr |
| `JMZ addr` | `0x0A` | ROM address | if zero: PC ← addr |
| `OUT` | `0x0B` | — | Output register ← A |
| `HLT` | `0x0C` | — | Stop clock |
| `LDBI imm` | `0x0D` | byte | B ← imm |
| `ADDI imm` | `0x0E` | byte | A ← A + imm (clobbers B) |
| `SUBI imm` | `0x0F` | byte | A ← A − imm (clobbers B) |
| `CMP` | `0x10` | — | flags ← A − B; A unchanged |
| `CMPI imm` | `0x11` | byte | flags ← A − imm; A unchanged (clobbers B) |

### Flags

The ALU produces two flags after any arithmetic operation:

| Flag | Set when |
|------|----------|
| **carry** | Result overflowed 8 bits (addition) or A ≥ B (subtraction) |
| **zero** | Result is 0x00 |

Flags are latched into the flags register only when `FLGI` is asserted in the
microcode. `JMC` and `JMZ` branch on the **previously latched** flags.
`CMP` / `CMPI` set the flags without altering A.

---

## Assembly language syntax

```
[LABEL:]  [MNEMONIC [OPERAND]]  [; comment]
```

- Labels end with `:` and can appear on their own line or before an instruction.
- Comments begin with `;` and run to end of line.
- Labels in jump/load operands resolve to ROM addresses at assembly time.

### Numeric literals

| Format | Example |
|--------|---------|
| Decimal | `42` |
| Hexadecimal | `0xFF` or `$FF` |
| Binary | `0b00101010` |

### Sections

A source file may contain a `.code` section and a `.data` section.

**`.code`** (default) contains instructions and may include raw byte literals.

**`.data`** declares named variables with initial values. The assembler
automatically prepends an initialization preamble to the program ROM that
stores each value into RAM before jumping to the first `.code` instruction —
no separate RAM image is required.

```asm
.code
        LDB  ONE        ; B = 1  (loaded from RAM by preamble)
        LDA  COUNT      ; A = 10
LOOP:   OUT
        SUB
        JMZ  DONE
        STA  COUNT
        JMP  LOOP
DONE:   HLT

.data
COUNT:  10
ONE:    1
```

Data variables are placed at the end of ROM and their RAM addresses are
assigned contiguously after the program code.

---

## Microcode and ROM generation

The microcode is defined in `microcode.py` as a human-readable
`32 × 8` table of control words (32 instructions × 8 T-states), with a
separate copy for each of the 4 possible flag states (carry × zero).

```python
T0 = SF.COUO | SF.MROI              # Fetch: PC → ProgROM address register
T1 = SF.ROMO | SF.IRGI | SF.COUE   # Fetch: ROM[PC] → IR, PC++
```

T0 and T1 are the common fetch cycle shared by every instruction. From T2
onward each instruction executes its own microcode steps, ending with `TRES`
to reset the step counter.

The 10-bit ROM address is:

```
address = (flags << 8) | (opcode << 3) | t_state
```

giving `4 × 32 × 8 = 1024` entries per ROM, matching the two-EEPROM layout
on the hardware.

### Generating ROM files

```bash
python microcode.py                       # writes rom1.bin and rom2.bin
python microcode.py --rom1 a.bin --rom2 b.bin
```

The simulator loads `rom1.bin` / `rom2.bin` by default. The same files can
be uploaded to the physical EEPROMs — this is the single shared definition.

### Conditional jumps

`JMC` and `JMZ` work by having **two different microcode rows for the same
opcode**, selected by the flag bits in the ROM address. The default row
(no condition) advances PC past the unused operand byte. When the condition
is met, the flag-specific row instead loads PC from the operand byte.

---

## Signal strategy

### Two-phase clock

Every module implements two methods called on each tick:

| Phase | Method | Purpose |
|-------|--------|---------|
| Rising edge | `clock_pulse()` | **Drive** — modules place values on the bus |
| Falling edge | `clock_inv_pulse()` | **Latch** — modules read values from the bus |

The bus is cleared between ticks so a module can only drive it during the
phase it was designed for. Attempting to drive an already-driven bus raises
immediately (contention detection).

The controller's `clock_pulse()` decodes the ROM and asserts the control word
first, before any module acts. Modules then read the asserted signals to decide
whether to drive or latch.

### Control signal encoding

The 21 control signals are packed into a 24-bit control word split across two
ROM bytes. The physical hardware uses two 74HC138 decoders (one signal per
group, encoded to 3 bits) plus direct bits for signals that must be asserted
simultaneously:

**ROM1 byte** `[HALT | FLGI | COUO | COUE | RAMI | enc2 enc1 enc0]`

**ROM2 byte** `[SUBT | enc2 enc1 enc0]`

| Bit | Signal | Group | Description |
|-----|--------|-------|-------------|
| 0 | `CLEA` | Decoder 1 | Clear: reset all registers (hardware reset only) |
| 1 | `JUMP` | Decoder 1 | Load PC from bus |
| 2 | `MROI` | Decoder 1 | Program ROM address register in |
| 3 | `MRAI` | Decoder 1 | RAM address register in |
| 4 | `ARGI` | Decoder 1 | Register A in |
| 5 | `BRGI` | Decoder 1 | Register B in |
| 6 | `IRGI` | Decoder 1 | Instruction register in |
| 7 | `OUTI` | Decoder 1 | Output register in |
| 8 | `RAMI` | Direct 1 | RAM write |
| 9 | `COUE` | Direct 1 | PC enable (increment) |
| 10 | `COUO` | Direct 1 | PC out |
| 11 | `FLGI` | Direct 1 | Latch ALU flags |
| 12 | `HALT` | Direct 1 | Stop clock |
| 14 | `ARGO` | Decoder 2 | Register A out |
| 15 | `BRGO` | Decoder 2 | Register B out |
| 16 | `ROMO` | Decoder 2 | Program ROM out |
| 17 | `RAMO` | Decoder 2 | RAM out |
| 18 | `TRES` | Decoder 2 | Reset T-state counter |
| 19 | `ALUO` | Decoder 2 | ALU out |
| 20 | `IRGO` | Decoder 2 | Instruction register out |
| 21 | `SUBT` | Direct 2 | ALU subtract mode |

Because each HC138 decoder can assert only one output at a time, signals in
the same decoder group are **mutually exclusive**. Signals that must fire
together (e.g. `ROMO + IRGI + COUE` during a fetch) span different groups or
use the direct bits.

The simulator stores all signals as active-high booleans. The EEPROM generator
owns any active-low inversion needed by the real hardware.

---

## Test suite

### Unit tests

```bash
python -m pytest test_simulator.py -v
```

167 tests covering Bus, Clock, Controller, Register, ALU, FlagsRegister,
RAM/ROM, ProgramCounter, and the Phase 1 public API (`getState`, `getConnections`,
`getSignalStates`, `reset`, `isHalted`, etc.).

### Integration tests

```bash
python run_tests.py
```

Each `.asm` file in `tests/` contains a `; EXPECT: v1 v2 …` comment listing
the expected `OUT` values in order. `run_tests.py` assembles the file, runs
the simulator at high speed, captures output, and compares.

| Test file | What it exercises |
|-----------|------------------|
| `test_01_nop.asm` | NOP pass-through |
| `test_02_immediate.asm` | LDAI, LDBI |
| `test_03_add_sub.asm` | ADD, ADDI, SUB, SUBI |
| `test_04_memory.asm` | LDA, LDB, STA, STB |
| `test_05_jmp.asm` | Unconditional jump |
| `test_06_jmz.asm` | Jump on zero |
| `test_07_jmc.asm` | Jump on carry |
| `test_08_countdown.asm` | Full loop: countdown 10→1 |
| `test_09_data_init.asm` | `.data` section, RAM initialisation |
| `test_10_cmp.asm` | CMP, CMPI |
| `test_11_fibonacci.asm` | Fibonacci sequence via carry-checked addition |

---

## Module architecture

```
Simulator/
├── simulator.py        Main Simulator class; entry point
├── module.py           Module base class (two-phase clock, getState, reset)
├── bus.py              8-bit Bus with driver tracking and contention detection
├── clock.py            Clock — tick(), run(), isHalted(), getState()
├── controller.py       Decodes ROM → control word → signal assertions
├── register.py         Register and OutputRegister
├── alu.py              ALU (add/subtract, carry/zero flags, combinatorial)
├── flags.py            FlagsRegister — latches ALU carry/zero on FLGI
├── progcounter.py      Program counter (JUMP / COUE / COUO)
├── memory.py           Memory base class; RAM and ROM subclasses
├── instructions.py     InstructionSet enum (5-bit opcodes)
├── signals.py          Signal enum, SignalFlags bit positions, encoding helpers
├── microcode.py        Microcode table + write_roms() EEPROM generator
├── gui/
│   ├── app.py          SimulatorGUI main window
│   ├── clock_panel.py  Clock controls (mode/speed/run/stop/step/reset)
│   ├── diagram.py      Scrollable canvas: bus rail, module boxes, wires
│   ├── module_view.py  Per-module box: LEDs, hex/dec, signal badges
│   ├── signal_panel.py Control signal display (click to toggle)
│   └── led.py          LED canvas primitive
└── tests/
    └── *.asm           Integration test programs
```

### Key design decisions

**Model/view separation.** The simulator classes know nothing about the GUI.
The GUI reads state via `getState()` snapshots and calls `tick()` — it never
touches private attributes.

**Non-blocking clock.** `Clock.tick()` is the single-step primitive. The
console loop and the GUI's `root.after()` callback both call it; neither owns
a `sleep` loop inside the clock itself.

**One microcode definition.** `microcode.py` is the single source of truth for
both the simulator's controller ROM and the physical EEPROM images. Running
`python microcode.py` regenerates `rom1.bin` / `rom2.bin`; those same files
are uploaded to the hardware EEPROMs.

**Signal registration.** Every module calls `controller.registerForSignal()`
during `setupSignals()`. This builds the wiring map used by
`getConnections()` for GUI introspection and bus-wire highlighting.
