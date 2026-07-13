# Library Bank — Design Note

*Reserving an address line on the ProgramROM board for a future "standard
library" of subroutines. Status: idea / provision only — depends on stack +
CALL/RET opcodes landing first. (2026-07-14)*

## The idea

Programs are limited to a 256-byte slot (A0–A7 from LBA via the PC; A8–A12
bank-selected by the DIP switch). A microcode-controlled 1-bit "library
register" driving one of the bank lines would let a program jump into a fixed
page of shared routines (multiply, BCD conversion, …) without spending its own
256 bytes on them.

**Decision: provision for it now.** The insurance is a 3-pin header and one
backplane net; retrofitting later means cutting a trace on a fabbed board.
Build nothing beyond the jumper until the stack and subroutine opcodes exist.

## Wiring

Take **EE_A12 only** (the MSB, U1.2) off the DIP and route it through a 3-pin
jumper:

| Pin | Connects to | Notes |
|-----|-------------|-------|
| Center | EE_A12 (U1.2) | |
| Pos 1 "DIP" | SW1 + R13 pull-up | Exactly today's behavior. Default position. |
| Pos 2 "LIB" | New backplane global label **LBA8** | 10k pulldown on this side so an undriven rail reads 0 (user space). |

Name the net **LBA8**, not LIB — it is really a 9th program-address bit; the
1-bit microcode-set flip-flop that drives it is an implementation detail. Who
drives it and from which board is decided later.

### Why the MSB, and why only one line

With A12 as the bank bit and A8–A11 still on the DIP, every user slot (16 of
them) gets a paired upper page at `{1, DIP[11:8]}`. That allows two usage
modes with no extra hardware:

1. **Shared library** — uploader flashes the same 256-byte library into all 16
   upper pages (4 KB of mirrors; the AT28C64 has room to burn). Every program
   sees the library at the same in-page addresses regardless of DIP setting.
2. **Per-program overlay** — treat the paired page as a private second page,
   doubling a program to 512 bytes. "Library" becomes a convention, not
   hardware.

A second jumpered line only buys extra *fixed* library pages, which doesn't
matter until the first 256 bytes are full. Padding A11 with the same 3-pin
footprint is cheap and optional; only wire one register bit and one microcode
signal.

## Gotchas

- **Flashing the library page**: the Arduino drives only A0–A7, so with the
  jumper in LIB position the upper pages can't be programmed. Flip the jumper
  to DIP and set the A12 switch when flashing the library. Rare, but deserves
  a silkscreen note.
- **Timing**: the bit is in the ROM fetch path — same rule as the RAM board's
  bank bits: it must change only on the clock edge that loads the PC and stay
  stable through CLOCK-high. A 74HC74 set/cleared by microcode outputs,
  clocked by the system clock, satisfies this.
- **The bank bit is not on the stack.** Return addresses are 8 bits (LBA0–7),
  so RET cannot restore the bank. Discipline required:
  - Dedicated `LCALL` (push PC, set bit, load PC) and `LRET` (clear bit,
    pop PC) opcodes.
  - Library routines may call each other (stay in-bank) but never call back
    into user code; no plain `CALL` from inside the library.
  - Enforce in the assembler.
- **Calling convention**: reserve a few fixed RAM locations as library
  scratch/argument space, and have the assembler emit a `library.inc` of EQUs
  so programs `LCALL MUL8` by name. Pin the ABI before the first reflash.

## Library contents (ranked by bytes saved per call)

1. **8×8→16 multiply** and **8÷8 divide with remainder** (shift-add /
   shift-subtract) — ~30–50 bytes each, the biggest win
2. **Binary → BCD** (double dabble) for the display; BCD → binary — ~40–60 bytes
3. **16-bit helpers**: add / sub / compare / increment on RAM byte pairs
4. **Multi-bit shift/rotate** loops (ALU shifts by one only)
5. **Calibrated delay** (delay-N-ms busy loop)
6. **LFSR pseudo-random**
7. **min / max / abs / compare**; memory fill/copy if RAM addressing permits

A 256-byte page holds roughly 6–8 of these. Multiply, divide, and double
dabble alone justify the jumper.
