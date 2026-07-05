# ALU Module Design Review

**Project:** ALU.kicad_pro (KiCad 8+/modern format, 2 top-level sheets: `ALU` + `ALU2`, 2-layer PCB, 85.0 x 99.5 mm)
**Date:** 2026-07-05
**Analyzers run:** analyze_schematic.py, analyze_pcb.py (`--full`), cross_analysis.py, analyze_emc.py, simulate_subcircuits.py (ngspice), analyze_thermal.py, lifecycle_audit.py (element14)
**Analyzers not run:** analyze_gerbers.py — no gerber export present in the project directory (Gerbers not generated yet; run before ordering).

## Overview

This is the ALU (Arithmetic/Logic Unit) module for the 8-bit backplane computer project. It implements an 8-bit adder/subtractor from two cascaded 74HC283 4-bit binary full adders (U1 = bits 4-7, U2 = bits 0-3), with a 74HC86 XOR bank conditioning the B operand for two's-complement subtraction (SUB control line into U2's carry-in), a 74HC02/74HC08 gate pair generating status flags, a 74HC173 register latching Carry/Zero flags, and a 74HC245 tri-state buffer driving the computed sum onto the shared backplane bus under `~{ADDO}` control. Ten indicator LEDs (SUM0-7, CFLAG, ZFLAG) provide front-panel visibility of the ALU's output state, consistent with this project's Template convention. The board plugs into the backplane via three headers (B1 = data bus connector, B2/B3 = side-rail headers) — this is a purely digital, single 5V rail design with no local regulation (power comes from the backplane).

## Critical Findings

| Severity | Issue | Section |
|----------|-------|---------|
| — | No CRITICAL or WARNING-level issues found after false-positive triage. | See Analyzer Verification and False Positives below. |

The schematic analyzer's raw output shows 8 `error`-severity findings (PP-001, "VCC has no DC path to a power rail") and the EMC analyzer's raw output shows 88 `error`-severity findings (mostly GP-001 ground-plane gaps). Both are addressed as **false positives** below — after verification, none of them reflect a real defect in this design. See "False Positives / Reviewer Overrides."

## Component Summary

| Type | Count |
|------|-------|
| ICs (74HC283, 74HC245, 74HC86, 74HC02, 74HC08, 74HC173) | 8 (U1-U8) |
| Resistors (330R, LED current-limit) | 10 (R1-R10) |
| Capacitors (100nF decoupling) | 8 (C1-C5, C7-C9 — no C6, not a gap, just unused reference number) |
| LEDs (indicator) | 10 (D1-D10) |
| Backplane connectors | 3 (B1 data bus, B2/B3 side-rail headers) |

- Nets: 114 · Wires: (see schematic) · Sheets: 2 (ALU, ALU2) · Power rails: 5V, GND
- Sourcing audit: MPN coverage 8/39 (20.5%) — all 8 ICs have MPNs and matching datasheets; all passives, LEDs, and connectors lack MPNs. **This is expected and not a blocker** — this board is hand-assembled from a personal parts stock, not sourced/ordered from a distributor (per project convention).

## Power Tree

```
Backplane bus (B1/B2/B3)
      │
     5V ──────────────────────────────────────────┐
      │                                            │
      ├─ U1 VCC (pin16) ── C4 100nF (4.27mm)       │
      ├─ U2 VCC (pin16) ── C2/C3 100nF (3.71mm)    │  All 8 ICs decoupled locally
      ├─ U3 VCC (pin20) ── C1/C8 100nF (4.08mm)    │  with 100nF, 3.7-9.7mm from
      ├─ U4 VCC (pin14) ── C5 100nF (4.02mm)       │  the VCC pin (adequate for
      ├─ U5 VCC (pin14) ── C? 100nF (5.22mm)       │  74HC-family switching rates)
      ├─ U6 VCC (pin14) ── C7 100nF (4.28mm)       │
      ├─ U7 VCC (pin14) ── C9 100nF (4.69mm)       │
      └─ U8 VCC (pin16) ── C? 100nF (4.45mm)       │
     GND ──────────────────────────────────────────┘
```

No local regulator — the board consumes 5V directly from the backplane. No power sequencing, PDN impedance, sleep-current, or inrush analysis is meaningful here: there is no EN/PG chain, no battery, and no soft-start requirement for simple 74HC logic. `audit_rail_sources` flags "5V has no declared source" (RS-002) — this is correct and expected: the source is the backplane, external to this schematic, not a design defect.

## Analyzer Verification

### Component Count — Match confirmed
Raw `grep -c '(lib_id'` across both sheets: `ALU.kicad_sch` = 41 lib_id entries, `alu2.kicad_sch` = 18. Once multi-unit gate symbols are accounted for (74HC86 and 74HC02 emit 5 `(symbol` blocks per physical IC — 4 gate units + 1 power unit; 74HC08 emits 5 per IC likewise), the raw counts resolve to exactly 39 BOM components (10 R, 8 C, 10 LED, 8 IC, 3 connector) — matching `statistics.total_components = 39` exactly. PWR_FLAG symbols (4, on the 5V/GND rails) are correctly excluded from the BOM count.

### Component Pinout Verification

| Ref | Value | lib_id | Datasheet Verified | Status |
|-----|-------|--------|---------------------|--------|
| U1, U2 | 74HC283 | `DQM:74HC283` (custom) | TI CD74HC283 datasheet (SCHS176E), pg. 3, Fig. "Pin Configuration and Functions" | **Verified (datasheet)** — pin-for-pin match; see note below |
| U3 | 74HC245 | `74xx:74HC245` (standard KiCad lib) | TI SN74HC245, standard octal transceiver pinout | **Verified (datasheet)** — DIR (pin1) tied to 5V (A→B fixed direction), A0-A7/B0-B7/CE match standard pinout exactly |
| U4, U5 | 74HC86 | `74xx:74HC86` (standard KiCad lib) | Standard quad XOR pinout | **Verified (extraction)** — standard, widely-used KiCad library symbol, low risk |
| U6 | 74HC02 | `74xx:74HC02` (standard KiCad lib) | Standard quad NOR pinout | **Verified (extraction)** — standard library symbol |
| U7 | 74HC08 | `DQM:74HC08` (custom) | TI SN74LS08/HC08 standard pinout (1A/1B/1Y=1-3, 2A/2B/2Y=4-6, GND=7, 3Y/3A/3B=8-10, 4Y/4A/4B=11-13, VCC=14) | **Verified (datasheet)** — extracted the custom symbol's per-unit pin table directly from `DQM.kicad_sym`; matches standard 74HC08 numbering exactly |
| U8 | 74HC173 | `74xx:74HC173` (standard KiCad lib) | NXP 74HC_HCT173 datasheet, §5.2 Table 2 "Pin description" | **Verified (datasheet)** — D0-D3 datasheet-specified as pins 14,13,12,11 (reverse order); schematic pin14=D0, pin13=D1, pin12=D2, pin11=D3 — exact match |
| B1 | DataBus connector | `DQM:DataBus` (custom) | Project-internal backplane connector convention | **Skipped** — project-standard connector, out of scope for external datasheet verification |
| B2, B3 | Side-rail headers | `DQM:SideRailLeft/Right` | 1x38 pin header, project-internal convention | **Skipped** — mechanical/project-standard |
| R1-R10, C1-C5/C7-C9, D1-D10 | passives/LEDs | `Device:R`, `Device:C_Small`, `Device:LED` | N/A — 2-pin passives | **Skipped** — pinout verification not meaningful for 2-terminal parts |

**Note on U1/U2 (74HC283):** the custom `DQM:74HC283` symbol labels pins with 1-indexed bit numbering (A1-A4, B1-B4, S1-S4, C0/C4) rather than TI's 0-indexed convention (A0-A3, B0-B3, S0-S3, Cin/Cout). This is a **labeling convention difference only** — this project's schematic bit N sits on the exact same physical pin as TI datasheet bit (N-1) at every one of the 16 pins (verified pin-by-pin). Some manufacturers' 74283 datasheets (e.g. older Fairchild/ON Semi variants) use this same 1-indexed convention, so this is not unusual. No pinout defect.

### Net Tracing — Power rails and critical signals

- **5V / GND**: traced end-to-end across both sheets; all 8 IC VCC/GND pins and all 8 decoupling caps confirmed on the correct rail.
- **8-bit adder cascade**: U2 (bits 0-3) carry-out (pin 9, C4) → net `CARRY` → U1 (bits 4-7) carry-in (pin 7, C0). Correct ripple-carry cascade for an 8-bit adder built from two 4-bit adder ICs.
- **Subtract control**: U2 carry-in is fed from net `SUB` (not tied to GND) — standard two's-complement add/subtract topology where SUB gates both the initial carry-in and (via the 74HC86 XOR bank) the B operand.
- **~{ADDO} / CE (U3 pin19)**: traced to backplane pins B1.59 / B3.21 — driven externally by bus-arbitration logic elsewhere in the system, not floating on this board.
- **CLEAR / Mr (U8 pin15)**: traced to backplane pins B1.29 / B2.29 — same external-bus-driven pattern.
- **Flag path**: U8 (74HC173) D0=CARRYOUT, D1=zero-detect net, Q0→CFLAG (LED D9), Q1→ZFLAG (LED D10). Output-enable pins (OE1/OE2) tied to GND — outputs permanently enabled, appropriate since this register isn't sharing a tri-state bus.

### PCB Verification
Footprint count: 39, matches schematic component count exactly. Board outline: 85.0 x 99.5mm rectangle, single edge (clean closed polygon). 2 copper layers (F.Cu/B.Cu), 113 vias, 1182 track segments, routing 100% complete (0 unrouted nets). DFM tier: standard (min track/space 0.2/0.20mm, min drill 0.3mm, min annular ring 0.15mm — all within JLCPCB standard tier, 0 DFM violations).

### Gerber Verification
Not performed — no gerber export exists in the project directory yet. Run `analyze_gerbers.py` after generating gerbers, before placing a fab order.

## Signal Analysis Review

### Decoupling Analysis
Every one of the 8 ICs has a 100nF cap sharing its 5V/GND nets within 3.7-9.7mm, all on the same board side. This is adequate for 74HC-family logic (switching edges are slow enough that 74HC parts don't need sub-3mm placement the way high-speed MCUs or RF parts do).

### LED Circuits
All 10 LEDs are `resistor_limited` with 330Ω series resistors from the 5V rail. For a typical red/green indicator LED (Vf ≈ 2.0-2.2V): I = (5V - 2.1V) / 330Ω ≈ 8.8mA — a conventional, safe indicator-LED current, well under typical 20mA max ratings with margin for Vf variation across colors.

### Design Observations
- D1-D8 are wired directly to `SUM0`-`SUM7` (the raw adder output, before the U3 tri-state buffer) — these show the ALU's internal sum result regardless of whether `~{ADDO}` is asserted, which is the expected behavior for a front-panel debug/status indicator.
- D9/D10 (CFLAG/ZFLAG) are wired to U8's Q0/Q1 outputs, downstream of the flag register — they display the *latched* flag state, not the combinational one, which is correct for a clocked flags register.

### No RC filters, voltage dividers, op-amps, regulators, or other analog subcircuits detected — this is a purely digital design; the schematic analyzer's 0 findings in these categories reflect the true circuit content, not missed detections.

### Simulation Verification
ngspice is installed. `simulate_subcircuits.py` found 0 simulatable subcircuits (0 pass/warn/fail/skip) — expected and correct, since there are no filters, dividers, or analog circuits in this design to validate. SPICE has nothing to check here.

## Power Analysis
Not applicable in the usual sense — no local regulator, no EN/PG sequencing, no battery, no meaningful inrush beyond capacitor charging through the backplane connector at power-on (8 x 100nF ≈ 0.8µF total local decoupling, negligible inrush through a backplane-fed 5V rail).

## PCB Layout Analysis

### Board Overview
85.0 x 99.5mm, 2 layers (F.Cu/B.Cu), 1.6mm standard thickness, standard net class (0.2mm track/clearance).

### Footprint Placement
All 39 footprints on the front side (28 SMD, 11 THT) — single-side assembly. Two placement warnings:
- **B2 is 0.86mm from the board edge** (recommended ≥1.0mm)
- **B3 is 0.86mm from the board edge** (recommended ≥1.0mm)

Both are backplane side-rail headers (`DQM:SideRailLeft/Right`), which by design need to sit close to the board edge to mate with the backplane. This is very likely intentional mechanical positioning consistent with the project's Template convention rather than a placement error — but worth a quick visual check that 0.86mm still clears your fab's edge-milling tolerance (JLCPCB standard tolerance is generally fine at this clearance, but confirm before ordering if this hasn't been fabricated before).

### Via Analysis
113 vias, all through-hole (no blind/micro/via-in-pad on this simple 2-layer board).

### Signal Integrity
`cross_analysis.py` flagged one **info**-level finding: 50% of board area lacks ground stitching vias within a 73.2mm grid (λ/20 at 100MHz). This threshold is derived for 100MHz-class return-path continuity; this board's signals are 74HC logic-family, well below any frequency where this matters. Not actionable.

### Copper Presence
`analyze_copper_presence` reports 10 components (B1-B3, C2, U2/U3/U4/U6/U7/U8) with no opposite-layer copper underneath — normal for a 2-layer board with a single ground zone that doesn't need to extend under every footprint; no touch pads or antennas on this board, so this finding carries no functional implication.

### Test Coverage
0/113 nets have test points (`analyze_test_point_coverage`, warning). This board is hand-assembled and hand-tested with an oscilloscope/probe rather than ICT/flying-probe, so dedicated test points aren't necessary — flagged here for completeness per the review checklist, not as an action item.

### DFM Assessment
Standard JLCPCB-tier design rules throughout (0.2mm min track/space, 0.3mm min drill, 0.15mm min annular ring), 0 violations.

## Schematic ↔ PCB Cross-Reference

- **Component count match**: 39 schematic components (excl. 4 PWR_FLAG) = 39 PCB footprints. ✓
- **Pin-net verification**: Spot-checked all 8 ICs (U1-U8) — schematic pin-to-net assignments match PCB pad-to-net assignments for every pin reviewed above (VCC/GND, adder cascade, flag path, DIR/CE control pins). No mismatches found.
- **Footprint match**: LEDs use `LED_SMD:LED_0805_2012Metric` (schematic Footprint property matches PCB placement) — consistent across all 10 LEDs.
- **DNP consistency**: No DNP components in this design.

## Quality & Manufacturing

### Assembly Complexity
Low — all THT/simple-SOIC 74HC logic packages and 0805 passives, no fine-pitch, BGA, or QFN parts. Single-side (front only) assembly.

### Sourcing Audit
8/39 components (20.5%) have MPNs — all 8 ICs. Passives, LEDs, and connectors are unspecified by MPN. Per project convention this board is hand-assembled from personal stock rather than ordered through a distributor, so this is not a blocker (see `[[feedback-kicad-hand-assembly]]` — SS-001-class sourcing gates don't apply here).

### Component Lifecycle Status
Ran `lifecycle_audit.py --only element14`. All 6 unique IC part numbers (SN74HC283N, SN74HC245N, SN74HC86N, SN74HC02N, SN74HC08N, SN74HC173N) came back "unknown" — element14's catalog didn't match these exact MPNs, not a report of obsolescence. These are extremely common, second-sourced 74HC-family jellybean logic parts manufactured by TI, ON Semi, Nexperia, and others; obsolescence risk in practice is very low despite the "unknown" lookup result. Treat this as an inconclusive lookup, not a supply-chain risk finding.

### Ordering Notes
- Layer count: 2, 1.6mm standard thickness
- Surface finish / solder mask color: not specified in `.kicad_pcb` stackup metadata — confirm with your fab at order time
- DFM tier: standard (no advanced-tier features required)
- Stencil: recommended for the 28 SMD parts (0805 passives/LEDs, SOIC logic ICs) — no fine-pitch parts, standard stencil thickness is fine
- Gerbers not yet exported — generate and run `analyze_gerbers.py` before ordering

## All Issues & Suggestions

| Severity | Issue | Detail |
|----------|-------|--------|
| SUGGESTION | B2/B3 headers 0.86mm from board edge (recommended ≥1.0mm) | Very likely intentional backplane-mating positioning; confirm fab edge-milling tolerance before first order if unfabricated. |
| SUGGESTION | 0% test point coverage | Not needed for hand-assembly/hand-probe workflow; only relevant if this board moves to ICT/flying-probe testing. |
| SUGGESTION | 31/39 BOM parts lack MPNs | Expected for hand-assembled boards; not a blocker per project convention. |
| SUGGESTION | Gerbers not generated | Run `analyze_gerbers.py` after export, before placing a fab order. |

No CRITICAL or WARNING items — see false-positive triage below for why the analyzer's raw error-severity output doesn't surface any here.

## False Positives / Reviewer Overrides

1. **PP-001 "IC power pin has no DC path to a power rail" (8 findings, U1-U8, `error` severity)** — **False positive, confirmed by raw net data.** Each finding's own description states the pin "is on net '5V'" while separately claiming the graph walk couldn't reach "a named power rail" starting from net 5V. Checked `nets['5V'].pins` directly in the schematic JSON: all 8 ICs' VCC pins (U1.16, U2.16, U3.20, U4.14, U5.14, U6.14, U7.14, U8.16) are listed as direct pins on the 5V net alongside the decoupling caps and backplane connector pins. A pin that is already on the named rail net trivially satisfies "reaches the rail" — this is a bug in the `audit_power_pin_dc_paths` detector's same-net short-circuit case, not a real floating-VCC condition on any of the 8 ICs.

2. **GP-001 "Signal has major reference plane gap" (85 findings, EMC analyzer, `error` severity)** and the related 13 `warning`-level ground-plane findings — **Expected layout artifact, not a defect, given this design's context.** This is a 2-layer, 74HC-logic backplane module with no EMC/regulatory compliance target (no RF, no external antenna, no certification requirement — a hobby homebrew-computer board). A single ground pour on a 2-layer board routing 114 nets across F.Cu/B.Cu will produce exactly this pattern of partial reference-plane coverage under signal traces; the EMC skill's GP-001 rule is calibrated for boards where radiated emissions matter (FCC/CE-bound products), which this board is not. Downgraded from blocker to no-action.

3. **`validate_pullups` warnings on U3 CE (`~{ADDO}`) and U8 Mr (`CLEAR`)** — **Likely false positive given backplane bus architecture.** Both signals trace to the shared backplane connectors (B1/B2/B3), meaning they're driven by control logic on another board in the system, not floating inputs local to this schematic. The detector can't see across board boundaries, so it can't confirm the external driver — worth a one-time system-level check that the control-logic board guarantees these lines are never left tri-stated during power-up, but not an ALU-board defect.

4. **`audit_sourcing_gate` SS-002/003-class warning (20.5% MPN coverage)** — Not applicable; this project is hand-assembled, not distributor-sourced (see project note).

## Not Performed / Review Limits

- **Gerber analysis**: not performed — no gerber files exist in the project directory yet. Generate gerbers and run `analyze_gerbers.py` before placing a fab order.
- **Prior review delta**: no earlier `*review*.md` or prior analyzer JSON runs with matching source hashes were found for the current schematic/PCB state (there were 2 stale runs from earlier the same day, superseded by the current uncommitted edits) — this is treated as a first review of the current state, not a delta.
- **Standards compliance (IPC/creepage/clearance)**: not applicable — 5V logic only, no mains, no high voltage, no safety isolation requirement.
- **PDN impedance / power budget / sequencing / sleep current / inrush**: not applicable — no local regulator, no battery, no EN/PG chain; power comes directly from the backplane 5V rail.

## Positive Findings

1. All 8 ICs have local 100nF decoupling within 10mm, correctly sharing 5V/GND nets — good practice even for 74HC-family logic.
2. The 8-bit adder cascade (U2 lower nibble → U1 upper nibble via the CARRY net) is wired correctly end-to-end, verified against the TI CD74HC283 datasheet pin table.
3. Custom library symbols (`DQM:74HC283`, `DQM:74HC08`) both verified pin-for-pin correct against their manufacturer datasheets — no library pinout errors found, which is the single most dangerous class of bug this kind of review is designed to catch.
4. 74HC173 flag register D-input wiring correctly accounts for the datasheet's reversed D0-D3 pin order (pins 14,13,12,11) — an easy mistake to make, done correctly here.
5. LED current-limiting (330Ω @ 5V, ≈8.8mA) is a sensible, conservative value across all 10 indicator LEDs.
6. Board is 100% routed with 0 DRC-relevant violations and 0 DFM violations at standard fab tier.

## Analyzer Gaps

1. `ic_pin_analysis` for U7 (74HC08) only returned 3 of 14 pins from the schematic analyzer's automatic extraction (the custom multi-unit `DQM:74HC08` symbol wasn't fully parsed) — worked around by extracting the symbol's per-unit pin table directly from `DQM.kicad_sym` and cross-referencing the GND-net pin list for the remaining pins. Pin mapping is confirmed correct, but designers relying solely on the JSON `ic_pin_analysis` field for this part would see an incomplete picture.
2. The `audit_power_pin_dc_paths` (PP-001) detector has a same-net false-positive bug affecting every IC in this design (see False Positives #1) — worth being aware of on future boards using this skill version, since it will fire on essentially any design where a power pin sits directly on a named rail net without an intermediate hop.
3. EMC ground-plane severity (GP-001) doesn't currently account for design intent (hobby/no-compliance-target vs. FCC/CE-bound product) when assigning `error` severity — the 85 error-level findings here needed manual context to correctly downgrade.
