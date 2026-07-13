# RAM Board — Design Review

**Date:** 2026-07-12
**Board:** RAM.kicad_pro rev 1.0 — "RAM Board for 8-Bit computer modules"
**KiCad:** 10.0
**Assembly:** hand-soldered (pick-and-place / sourcing findings not applicable)
**Analysis run:** `analysis/2026-07-12_1839/`

## Verdict

**Not ready to fab as drawn.** Two issues should be resolved first: a logic-level
margin violation between the SRAM and the '245 (Issue 1), and undefined address
lines A8–A14 (Issue 2). Both have cheap fixes. Everything else is minor.

The layout itself is in good shape: fully routed, no unrouted nets, correct
pad-to-net mapping throughout, and clean decoupling.

## Board Summary

| | |
|---|---|
| Size | 85.0 × 99.5 mm, 2 layers, 1.6 mm |
| Components | 27 (19 SMD, 8 THT) |
| Routing | 608 segments, 27 vias, complete (0 unrouted) |
| Copper | GND pour on B.Cu (fill ratio 0.858); 0.2 mm tracks throughout |

**Circuit:** CY62256 32K×8 SRAM (U1) behind a 74HC245 bus transceiver (U2), with a
74HC00 (U3) generating the enable/direction/write-strobe logic. Eight LEDs display
the internal data bus. J1/J2 jumper the SRAM's upper address lines. B1/B2/B3 are the
backplane connector and its two breakout rows.

---

## Issue 1 — SRAM output levels don't meet the 74HC245's input threshold (HIGH)

**The SRAM cannot be guaranteed to drive a valid logic HIGH into U2.**

The CY62256N's *only* output-high specification is:

> VOH ≥ **2.4 V** at IOH = **1.0 mA**, VCC = min — *CY62256N, Electrical Characteristics, p.4*

There is no CMOS-level VOH row in the table — the part guarantees TTL levels only.

The 74HC245 requires:

> VIH ≥ **3.15 V** at VCC = 4.5 V — *SN74HC245, Recommended Operating Conditions*

2.4 V < 3.15 V, so on a **read** (SRAM drives → U2's A-side receives) there is no
guaranteed high-level noise margin. This is the classic TTL-output-into-HC-input
mismatch.

The LED loads make it worse. D1–D8 sit directly on the internal bus (anode to the
SRAM Q pin / '245 A pin, cathode through 330 Ω to GND). At 3.15 V a red LED
(Vf ≈ 1.9 V) draws:

```
I = (3.15 − 1.9) / 330 ≈ 3.8 mA
```

That is roughly **4× the SRAM's guaranteed 1 mA source current**, at the exact node
voltage the '245 needs to see.

In practice a CMOS SRAM output stage will pull much closer to VCC than the datasheet
floor, so the board will very likely work on the bench. But it is outside the
guaranteed envelope, and it is exactly the kind of margin that varies with part,
date code, and temperature.

**Fix (do both):**

1. **Swap U2 → 74HCT245.** Pin-compatible DIP-20 drop-in. VIH = 2.0 V, designed for
   TTL-level drivers. This restores guaranteed margin and costs nothing.
2. **Raise R1–R8 from 330 Ω to 1 kΩ–2.2 kΩ.** Cuts the LED load to ~1–1.5 mA (still
   clearly visible on modern LEDs) and stops the display from dragging the bus node
   down.

Note this is **specific to the RAM board**. The Registers board uses the identical
LED row at 330 Ω, but there the LEDs are driven by a proper CMOS register output, so
the same value is fine. Don't "fix" that board to match.

## Issue 2 — A8–A14 have no defined level unless every shunt is fitted (HIGH)

Each of A8…A14 connects to exactly two things: a J1 pin and the SRAM address pin.
There is no pull-up or pull-down anywhere on these nets. J2 is a 7-pin GND header
sitting next to J1, so a shunt across J1↔J2 grounds that address bit.

Consequences as drawn:

- **All 7 shunts fitted** → A8–A14 = 0 → the SRAM is restricted to the bottom 256
  bytes. (Which is all the 8-bit LBA bus can reach anyway, so this is presumably the
  intent.)
- **Any shunt omitted** → that address input is a **floating CMOS input**.
  Indeterminate addressing, possible oscillation, and elevated ICC in the SRAM's
  input buffer.
- There is **no 5 V on the jumper block**, so a bit can only be set to `0` or left
  floating — paging to a nonzero bank is not possible as drawn.

**Fix — pick one:**

- **Minimal:** add 7 × 10 kΩ resistors from A8–A14 to GND. An open jumper then still
  means a defined `0`, and the board is safe however it's populated.
- **Better:** make each bit a 3-pin header (5 V / A*n* / GND) so upper address bits
  can actually be selected high or low, which is presumably why the jumpers are there
  at all.
- **If you keep it as-is:** silkscreen it — "all 7 shunts must be fitted."

Worth deciding what the jumper block is *for* before respinning. If the answer is
"always ground them," the resistors alone are enough.

---

## Medium

### 4 duplicate track segments — FIXED 2026-07-12

`scripts/find_duplicate_tracks.py` found 4 exact-duplicate segment groups (0
overlapping-collinear, 0 duplicate vias):

| Net | Layer | Coordinates | Length | Near |
|---|---|---|---|---|
| GND | F.Cu | (53.79, 81.83)–(54.59, 81.83) | 0.8 mm | C1 |
| GND | F.Cu | (38.86, 94.95)–(39.66, 94.95) | 0.8 mm | C3 |
| GND | F.Cu | (59.80, 30.88)–(60.60, 30.88) | 0.8 mm | R6 |
| GND | F.Cu | (75.35, 30.75)–(76.15, 30.75) | 0.8 mm | R3 |

All four were stacked identical segments left over from routing passes — each group
was exactly two copies, identical apart from their UUID.

**Resolved.** The redundant copy of each pair was deleted from `RAM.kicad_pcb`.
Because each removed segment had an identical twin remaining, the union of copper on
the board is unchanged, so connectivity could not be affected.

- Backup: `RAM-backups/RAM.kicad_pcb.bak-preduptrack-20260712-192752`
- Segments: 608 → 604; total track length 1727.15 → 1723.95 mm (−3.20 mm, exactly the
  4 × 0.8 mm of double-counted duplicate)
- After: footprints 27, vias 27, zones 1, nets 101, routing complete, 0 unrouted nets,
  0 disconnected pad pairs — all unchanged
- `find_duplicate_tracks.py` re-run: **no redundant routing found**

Open in KiCad and run DRC to confirm before fab.

### No interlock against simultaneous RAMI + ~RAMO

U3's four NAND gates decode as:

| Gate | Pins | Function |
|---|---|---|
| 1 | 1,2 → 3 | `~RAMI = NOT RAMI` |
| 2 | 4,5 → 6 | `RAMEN = NAND(~RAMI, ~RAMO)` |
| 3 | 9,10 → 8 | `~RAMEN = NOT RAMEN` |
| 4 | 12,13 → 11 | `~RAMWE = NAND(RAMI, CLOCK)` |

giving `~RAMEN = ~RAMI AND ~RAMO`. Verified against all four control states:

| State | RAMI | ~RAMO | U2 /OE | U2 DIR | U1 /OE | Result |
|---|---|---|---|---|---|---|
| Idle | 0 | 1 | 1 (Hi-Z) | — | 1 (Hi-Z) | bus floats |
| Read | 0 | 0 | 0 | A→B | 0 | SRAM → BUS ✓ |
| Write | 1 | 1 | 0 | B→A | 1 (Hi-Z) | BUS → SRAM ✓ |
| **Both** | **1** | **0** | **0** | **B→A** | **0** | **contention** |

In the last row the '245 drives the internal bus B→A *while* the SRAM also drives it
(/OE low) — the two fight each other. Whether this can ever happen depends entirely
on the Control Logic ROM microcode. **Check that the control ROM never asserts RAMI
and ~RAMO in the same cycle.** All four of U3's gates are already used, so gating
U1's /OE with ~RAMI would need another package — only worth it if the microcode can
actually produce that state.

### 5 V rail is thin

5 V is routed entirely in 0.2 mm track (167 mm total, including one 56 mm F.Cu run
and a 27 mm B.Cu run). Current capacity is not the problem — 0.2 mm on 1 oz copper
carries ~0.9 A vs. an estimated ~130 mA peak load, and IR drop is ~20 mV. It's just
thinner than it needs to be for a power rail. Widen to 0.4–0.6 mm where there's room.
Low priority.

---

## Low / informational

- **Internal data bus floats when idle.** With both the SRAM and the '245 in Hi-Z,
  D1–D8 + 330 Ω is not a real pull-down (the LED stops conducting below Vf), so the
  eight nodes float between 0 V and ~1.8 V. Can cause slightly elevated ICC in the
  SRAM's I/O input buffers. Common in this class of design; pull-downs would fix it
  if you care.
- **/CS tied permanently to GND** — the SRAM is always in active mode (ICC 25–50 mA
  rather than ~0.3 mA standby). Fine for a bench machine, just noting the power cost.
- **Write timing is comfortable.** `/WE = NAND(RAMI, CLOCK)` holds /WE low for the
  whole clock-high period. The CY62256-70 needs tPWE ≥ 50 ns and tAW ≥ 60 ns, and
  tSA = 0 ns means the address may change coincident with the /WE fall. At 50% duty
  this only constrains the clock to below ~8 MHz — never a limit here.
- **LED bit order** — D8 (bit 0) is leftmost, D1 (bit 7) rightmost, so the display
  reads LSB-first left-to-right. This matches the Registers board exactly (identical
  footprint positions), so it's the project convention. No action.
- **DRC minimums are 0.0.** `min_track_width` and `min_clearance` are both 0 in
  `RAM.kicad_pro`, so DRC has no floor; the Default netclass (0.2 mm / 0.2 mm) is what
  actually governs, and that's comfortable for any fab. Consider setting the minimums
  to 0.2 mm so DRC actually catches an accidentally thin trace.
- **B2/B3 sit 0.86 mm from the board edge** (PM-002). Intentional for backplane edge
  headers, and `min_copper_edge_clearance` (0.5 mm) is satisfied. Just confirm it
  clears your card guides.
- **Ground stitching is sparse** (5 GND vias board-wide, VS-002). Not a concern here:
  every decoupling cap has a GND via within 1.8–2.4 mm, so the return paths that
  matter are solid, and board-wide stitching is irrelevant at this clock rate.

---

## Verification basis

- **U1 pinout verified against the CY62256N datasheet** (Pin Definitions, p.3). All
  28 pins match the JEDEC 32K×8 standard: A14, A12, A7–A0, Q0–Q2, GND, Q3–Q7, /CS,
  A10, /OE, A11, A9, A8, A13, /WE, VCC. No pin swaps.
- **PCB pad→net cross-checked against schematic pin→net**: 60 named-net pads
  compared across U1/U2/U3/J1/J2, **0 mismatches**. The 8 auto-named data-bus nets
  group identically in both domains (U1.Q0↔U2.A0 … U1.Q7↔U2.A7), and U2.B0–B7 map to
  BUS0–BUS7 in order. **No bit reversal or library footprint pin-numbering error.**
- **Control logic decoded gate-by-gate** and checked against all four control states
  (table above).
- **Decoupling:** one 100 nF per IC (C1/U1 4.2 mm, C2/U2, C3/U3 4.1 mm), each with a
  GND via within ~2 mm into the B.Cu pour. Good.
- Logic-level and timing numbers cited above come from the manufacturer PDFs in
  `datasheets/`, not from KiCad library symbols.

## Analyzer findings triaged as false positives

| Finding | Count | Why it's not real |
|---|---|---|
| PP-001 — "U1.28/U2.20/U3.14 VCC has no DC path to a power rail" | 3 (high) | False. All three VCC pins sit directly on the 5V net alongside B1.1/B1.39/B2.1/B3.1 and the three decoupling caps. Confirmed 4 PWR_FLAG symbols are correctly wired (2 × 5V, 2 × GND, at both backplane connectors). The detector misses them because the analyzer excludes power-symbol pins from net pin lists and the backplane pins are typed `bidirectional`, not `power_out`. |
| RS-001 — "5V has no declared source" | 1 | Same root cause. False. |
| GP-001 — reference plane gaps | 80 (high) | Over-fires on 2-layer boards, where the B.Cu pour is necessarily carved up by B.Cu routing (fill ratio is still 0.858). Not actionable at this board's clock rate. |
| SS-001 — MPN coverage < 50% | 1 (high) | N/A — hand-assembled. |
| FD-001 / TE-001 / OR-001 | 3 | Fiducials, test points, passive orientation — all pick-and-place concerns. N/A for hand assembly. |

## Not performed / limits

- **Gerbers** — not exported yet, so GR-00x checks did not run. Re-check after export.
- **SPICE** — ran (ngspice); found 0 simulatable subcircuits. This is a purely digital
  board with no filters, dividers, or op-amps. Nothing to verify.
- **Thermal** — ran; 0 findings, score 100/100. No power-dissipating parts.
- **Lifecycle audit** — skipped (hand assembly, no MPNs on the BOM by design).
- **EMC** — ran (risk score 64/100), but the findings are dominated by the 2-layer
  GP-001 artifacts above. No FCC/CE relevance for a bench machine.
- **Prior-review delta** — the two prior runs (2026-07-11) were schematic-only, so
  there is no previous PCB analysis to diff against. No prior review document existed
  for this board.
