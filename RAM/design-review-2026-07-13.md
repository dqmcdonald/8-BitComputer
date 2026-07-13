# RAM Board — Design Review (re-run after fixes)

**Date:** 2026-07-13
**Board:** RAM.kicad_pro rev 1.0 — "RAM Board for 8-Bit computer modules"
**KiCad:** 10.0
**Assembly:** hand-soldered (pick-and-place / sourcing findings not applicable)
**Analysis run:** `analysis/2026-07-13_1422/` (schematic) + `analysis/2026-07-13_1422-2/` (PCB, cross, EMC, thermal, SPICE)
**Supersedes:** `design-review-2026-07-12.md`

## Verdict

**Both HIGH blockers from the 2026-07-12 review are resolved.** The logic-level margin
violation is fixed and guaranteed by datasheet numbers, and the address lines can no
longer float. The layout is fully routed, cross-checks cleanly against the schematic,
and has no redundant routing.

**Ready to fab, pending a DRC run in KiCad** — that's the only gate left that I can't close
headlessly.

The RAMI/~RAMO bus-contention risk is being handled at microcode generation (see below), and
the address-jumper block is confirmed as intentional (banked memory / stack page). Neither
requires a board change.

## What Changed

| # | Prior finding | Change made | Status |
|---|---|---|---|
| 1 | SRAM VOH (2.4 V) below 74HC245 VIH (3.15 V) | U2 → **74HCT245**; R1–R8 330 Ω → **1 kΩ** | **Resolved** |
| 2 | A8–A14 float unless every shunt is fitted | **R9–R15 = 7 × 10 kΩ pull-downs** added; J2 GND header removed | **Resolved** |
| — | 4 duplicate track segments | (fixed 2026-07-12) | Still clean |

Board grew from 27 to 33 footprints and 604 to 629 track segments. Still fully routed.

---

## Issue 1 — Logic levels: now within spec, with margin

The fix works, and both halves of it were necessary.

**Threshold.** SN74HCT245, §6.3 Recommended Operating Conditions, p.4:

> VIH ≥ **2.0 V**, VIL ≤ 0.8 V, at VCC = 4.5–5.5 V

The CY62256N guarantees VOH ≥ **2.4 V** at IOH = 1.0 mA (Electrical Characteristics,
p.4). So the worst-case high level clears the worst-case threshold by **0.4 V**. That
margin is now guaranteed by the datasheets rather than by how the parts happen to behave.

**Load.** The LED sits on the same node, so the SRAM has to hold ≥ 2.4 V *while*
driving it. At the 2.4 V floor, with a red LED (Vf ≈ 1.9 V) and 1 kΩ:

```
I = (2.4 − 1.9) / 1000 ≈ 0.5 mA   ≤ 1.0 mA guaranteed source current  ✓
```

This is why the resistor change was needed too — at the old 330 Ω the same node draws
~1.5 mA, which is *above* the 1 mA the VOH spec is defined at, so 2.4 V wouldn't have
been guaranteed even with the HCT part. The two changes only work together.

Brightness is unaffected in practice: at a realistic logic high (~4.5 V) the LEDs pull
~2.6 mA, which is plenty on modern parts.

## Issue 2 — Address lines: now defined in every population

R9–R15 (10 kΩ) tie A8–A14 to GND. Verified on both the schematic and the PCB — each
resistor is `A<n> ↔ GND` on its pads. There is no longer any way to leave a CMOS input
floating, whatever you do or don't fit.

**Design intent (confirmed 2026-07-13):** J1 is not a jumper-to-ground block. A8–A14
default to `0` via the pull-downs, and the intent is to wire them to real signals from the
backplane to implement **banked memory / a stack page**. J1 is therefore a 1×7 header with
each pin on an address line, driven by short jumpers from the backplane breakout rows
(B2/B3) on the same board.

This is a good fit for the pull-downs: an undriven or tri-stated source leaves the bit at a
defined `0` rather than floating, so a partly-wired harness degrades gracefully.

J1 has no ground pin, which would normally be a concern for flying address wires. **Accepted
as-is** — the runs are short and stay on this board, so the return path is through the GND
pour directly underneath and the loop area is small. (This would be worth revisiting if the
bank signals ever came from an off-board harness.)

See "Constraint on banked-address signals" below for the one timing rule these signals must
obey.

---

## Constraint on banked-address signals (A8–A14)

Once A8–A14 are driven by real signals rather than held at 0, they become part of the SRAM's
address during writes, and the write-cycle timing applies to them. From the CY62256N write
cycle table (p.8, -70 part):

| Parameter | Value |
|---|---|
| tSA — address setup to write start | **0 ns** |
| tAW — address setup to write end | **60 ns** |
| tHA — address hold from write end | **0 ns** |

Together these mean the address may become valid at the moment `/WE` falls, but **must then
stay valid until `/WE` rises**. A bank bit that changes while `/WE` is low is an address
transition mid-write — the write can land in the wrong page, or in both.

Since `/WE = NAND(RAMI, CLOCK)` is low for the whole CLOCK-high phase, the rule is:

> **Whatever drives A8–A14 must be settled before CLOCK goes high and hold until it goes low.**

This is satisfied for free if the bank/stack-select bits are **microcode ROM control-word
outputs**, which are stable for the entire step. The antipattern to avoid is driving a bank
bit from a **register clocked on the same rising edge that pulls `/WE` low** — the address
would be changing at the instant the write starts, and `tSA = 0` leaves no cushion for the
race. If a CPU-loadable bank register is ever added, clock it on the falling edge or from a
different phase.

Levels and loading are a non-issue: the SRAM's address inputs are TTL-level (VIH = 2.2 V,
VIL = 0.8 V, p.4) and the 10 kΩ pull-down is a 0.5 mA load, so any 74HC/HCT/LS output drives
them with large margin.

## Still open

### No interlock against simultaneous RAMI + ~RAMO (MEDIUM) — being handled in microcode

`~RAMEN = ~RAMI AND ~RAMO`, so the state `RAMI=1, ~RAMO=0` puts the '245 in B→A *while* the
SRAM has /OE low — both drive the internal bus and fight. Whether that state can occur is
decided entirely by the Control Logic microcode, not by this board.

**Resolution (decided 2026-07-13): enforced at microcode generation.** The microcode
generator script will verify that `RAMI` and `~RAMO` are never asserted in the same cycle,
rather than adding a hardware interlock. This is the right call — all four of U3's NAND
gates are already used, so gating U1's /OE with `~RAMI` would have cost another package to
guard against a state the microcode can simply never emit.

Worth folding the banked-address rule above into the same generator check, since it's the
same class of invariant.

### Low / informational

- **5 V rail is still thin.** 167 mm of 0.2 mm track. Current capacity isn't the issue
  (~0.9 A capability vs ~130 mA load; IR drop ~20 mV) — it's just thinner than a power
  rail needs to be. Widen to 0.4–0.6 mm where there's room. Low priority.
- **DRC minimums are still 0.0.** `min_track_width` and `min_clearance` are both 0 in
  `RAM.kicad_pro`. The Default netclass (0.2/0.2 mm) is what actually governs and is
  comfortable for any fab, but with the floor at zero DRC won't catch an accidentally
  thin trace. Consider setting both to 0.2 mm.
- **Internal data bus still floats when idle**, and HCT is slightly more exposed to this
  than HC (VIL = 0.8 V, VIH = 2.0 V, so the indeterminate band is narrower and sits lower).
  With both U1 and U2 in Hi-Z, leakage charges each node up to roughly the LED's sub-knee
  voltage (~1.4 V) — inside the indeterminate band, so U2's A-side input buffers can idle
  in their linear region and draw extra ICC. TI calls this out explicitly (datasheet note 1,
  p.4 → SCBA004). **It is benign** — no functional error, just a little idle current.
  You *could* add 8 × 10 kΩ pull-downs on the internal bus; the numbers still work
  (0.5 mA LED + 0.24 mA pull-down = 0.74 mA, still under the 1 mA budget), but it eats
  most of your new margin for a non-problem. My recommendation: leave it.
- **/CS tied permanently to GND** — SRAM always active (ICC 25–50 mA vs ~0.3 mA standby).
  Fine for a bench machine.
- **Cosmetic: U2's symbol is still `74xx:74HC245`** while its Value is `74HCT245`. The
  pinout is identical so this is electrically harmless, and Value is what drives the BOM —
  but a future symbol-based check could report the wrong part. Worth tidying.
- **Cosmetic: R9–R15 use `Device:R_Small`** while R1–R8 use `Device:R`. Harmless.

---

## PCB Layout Analysis

| | |
|---|---|
| Size | 2 layers, 1.6 mm |
| Components | 33 (26 SMD, 7 THT) |
| Routing | 629 segments, 28 vias, **complete — 0 unrouted** |
| Copper | GND pour on B.Cu, fill ratio 0.861, **refilled after the edit** |
| Connectivity | 101 nets, **0 with multiple islands, 0 disconnected pad pairs** |

**Duplicate/redundant routing check** (`scripts/find_duplicate_tracks.py`, per project
convention): **0 exact duplicates, 0 overlapping collinear segments, 0 duplicate vias.**
The board is clean — the 4 duplicates found on 2026-07-12 have not come back, and the
re-route to add R9–R15 didn't introduce new ones.

The zone was refilled after the new parts went in (`is_filled: true`, ratio 0.861 vs 0.858
before), so the copper-presence data is current rather than stale.

## Verification basis

- **U2 pinout verified against the SN74HCT245 datasheet** (Pin Functions, p.3) — all 20
  pins match, including DIR (pin 1) and OE (pin 19). Control polarity re-checked: DIR =
  `~RAMI`, and the datasheet defines High = A→B. Read (RAMI=0) → DIR high → SRAM→BUS ✓.
  Write (RAMI=1) → DIR low → BUS→SRAM ✓.
- **Logic-level numbers taken from the manufacturer PDF**, not the KiCad symbol.
  `datasheets/SN74HCT245.pdf` downloaded this session — the folder previously held only
  the **HC** variant, which would have given the wrong VIH (3.15 V vs 2.0 V) and made the
  fix look like it hadn't worked.
- **PCB pad→net cross-checked against schematic pin→net: 233 named-net pads, 0 mismatches.**
  The 16 internal-bus net groupings are identical in both domains. No bit reversal, no
  footprint pin-numbering error.
- **LED polarity re-confirmed** — anode (pin 2) on the bus node, cathode (pin 1) through
  the 1 kΩ to GND. Correct orientation; the resistor swap didn't flip anything.
- **All 7 pull-downs confirmed on the PCB**, not just the schematic: R9→A8 … R15→A14,
  each with its other pad on GND.
- Thermal: 0 findings, score 100/100. SPICE (ngspice): 0 simulatable subcircuits — purely
  digital board, nothing to verify.

## Analyzer findings triaged as false positives

| Finding | Count | Why it's not real |
|---|---|---|
| PP-001 — U1.28/U2.20/U3.14 VCC "has no DC path to a power rail" | 3 (error) | False, and a known analyzer bug on this project. All three VCC pins sit directly on the 5V net. The detector excludes power-symbol pins and the backplane pins are typed `bidirectional`, not `power_out`. |
| RS-001 — "5V has no declared source" | 1 | Same root cause. False — 4 PWR_FLAGs are correctly wired. |
| SS-001 — MPN coverage < 50% | 1 (error) | N/A — hand-assembled, by design. |
| GP-001 — reference plane gaps | 80 (error) | Over-fires on 2-layer boards, where the B.Cu pour is necessarily carved up by B.Cu routing. Fill ratio is still 0.861. Not actionable at this clock rate. |
| RP-002 — CLOCK/~CLOCK 67–79% reference plane coverage | 2 | Same 2-layer artifact. Irrelevant at this board's clock speed. |
| VS-002 — sparse via stitching | 1 | Every decoupling cap has a GND via within ~2 mm; board-wide stitching doesn't matter here. |
| CG-AUD — "Connector J1 has no ground pins" | 1 | **Expected now** — this is J2's removal. Ground reference is provided by R9–R15 instead of a header row. |
| EMC risk score 64/100 | — | Dominated by the GP-001 2-layer artifacts above. No FCC/CE relevance for a bench machine. |

## Not performed / limits

- **DRC** — not run (needs KiCad GUI). Run it before fab; it's the one gate I can't close for you.
- **Gerbers** — not exported yet, so GR-00x checks did not run.
- **Lifecycle audit** — skipped (hand assembly, no MPNs on the BOM by design).
- **Control ROM microcode** — out of scope for this board's files. The RAMI/~RAMO
  interlock question can only be answered by the Control Logic project.
