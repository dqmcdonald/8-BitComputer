# Registers Module Design Review

**Project:** Ben Eater 8-Bit Computer — Registers Module (KiCad 8, single sheet, 2-layer PCB)
**Date:** 2026-06-05 (updated from 2026-06-04)
**Analyzers run:** `analyze_schematic.py`, `analyze_pcb.py --full`, `cross_analysis.py`, `analyze_thermal.py`
**Analysis run:** `analysis/2026-06-05_1135/` and `analysis/2026-06-05_1135-2/`

---

## Overview

An 8-bit register module for a Ben Eater-style breadboard computer, implemented on a custom PCB. Two CD74HC173E quad D-type flip-flop ICs (U1, U2) provide 4 bits each for an 8-bit register, a SN74HC245N octal bus transceiver (U3) drives the 8-bit data bus under control of an active-low /ROUT signal, and an ATtiny84A (U4) monitors register contents to drive an external serial display via J1. Eight red LEDs with 330 Ω current-limiting resistors directly indicate the register state. 10 kΩ pull-down resistors (R10–R17) hold REG0–REG7 to a defined low on the backplane when the register board is unpowered or in reset; 10 kΩ pull-up resistors (R18, R19) keep the active-low control signals ~{RIN} and ~{ROUT} de-asserted when the backplane controller is not driving them. The board is powered from 5 V supplied via two 40-pin backplane connectors (B1, B2) and one additional 40-pin connector (B3).

---

## Previous Review Delta

Previous analysis run: `analysis/2026-06-04_1248/` and `analysis/2026-06-04_1248-2/` (2026-06-04)

| Status | Count |
|--------|-------|
| Fixed since last review | 3 (both pull-up WARNINGs resolved; 330 Ω LED resistor SUGGESTION applied) |
| Still open | 0 warnings, 6 suggestions (see below) |
| New findings | None |

Changes since last run (analyzer diff, 2026-06-04 → 2026-06-05):

- **Added: R10–R17** — eight 10 kΩ 0805 pull-down resistors on REG0–REG7 (pin 1 to each REG net, pin 2 to GND). Ensures defined low level on those backplane lines when U1/U2 are not driving.
- **Added: R18** — 10 kΩ 0805 pull-up on ~{RIN} (pin 1 to ~{RIN}, pin 2 to 5V\_2). Resolves WARNING: ~{RIN} floating.
- **Added: R19** — 10 kΩ 0805 pull-up on ~{ROUT} (pin 1 to ~{ROUT}, pin 2 to 5V\_2). Resolves WARNING: ~{ROUT} floating.
- **Modified: R1–R8** — value changed 220 Ω → 330 R. Reduces per-LED current from ~11 mA to ~7.3 mA, increasing margin to 74HC173 VCC/GND absolute maximum. Resolves SUGGESTION.
- All 10 new footprints are placed on F.Cu and fully routed (routing remains 100% complete).

---

## Critical Findings

No CRITICAL or WARNING-level issues. Both prior pull-up warnings have been resolved by adding R18 and R19.

| Severity | Issue | Status |
|----------|-------|--------|
| ~~WARNING~~ | ~~{ROUT} (U3 /CE) had no pull-up~~ | **RESOLVED** — R19 10 kΩ to 5V\_2 added |
| ~~WARNING~~ | ~~{RIN} (U1/U2 Ē1/Ē2) had no pull-up~~ | **RESOLVED** — R18 10 kΩ to 5V\_2 added |

---

## Component Summary

| Type | Count |
|------|-------|
| Resistors | 19 (R1–R19) |
| Capacitors | 4 (C1–C4) |
| LEDs | 8 (D1–D8) |
| ICs | 4 (U1–U4) |
| Connectors | 2 (J1 4-pin, J2 10-pin) |
| Backplane headers | 3 (B1–B3, 40-pin each) |
| **Total** | **40** |

- Nets: 97 | Wires: 97 | No-connects: 1 (U4 PB0 / XTAL1)
- Power rails: 5 V, 5V\_2 (both externally supplied from backplane)
- MPN coverage: 28/40 (70%) — new R10–R19 are generic 0805 10 kΩ and R1–R8 are now 330 R 0805; none carry MPNs yet

---

## Power Tree

```
Backplane B1 pin 1  ──┬── 5V  ──── U3 VCC (pin 20)
Backplane B2 pin 1  ──┘         ── U3 DIR (pin 1, fixed HIGH → A→B)
                                 ── C3 100 nF  [⚠ 25mm from U3]

Backplane B1 pin 39 ──┬── 5V_2 ─── U1 VCC (pin 16)
Backplane B3 pin 1  ──┘         ─── U2 VCC (pin 16)
                                 ─── U4 VCC (pin 1)
                                 ─── C1, C2, C4 100 nF (total 300 nF)
                                 ─── R9 4.7 kΩ → U4 /RESET (pin 4)
                                 ─── R18 10 kΩ → ~{RIN}
                                 ─── R19 10 kΩ → ~{ROUT}
                                 ─── J1 pin 1 (display power)

Backplane B1 pins 2/40, B2 pin 2, B3 pin 2 ─── GND (common)
  └── R10–R17 10 kΩ each → REG0–REG7
```

No on-board regulators. Both rails are externally supplied 5 V. The split between 5V (U3 only) and 5V\_2 (U1/U2/U4) is a routing artifact — they are the same nominal potential from different backplane pins. No PWR_FLAG symbols exist on either rail; this generates KiCad ERC RS-001 warnings and the PP-001 analyzer error on U3 VCC — both are false positives from missing flags on externally-supplied rails.

---

## Analyzer Verification

### Component Count
Schematic: 40 real components (power symbols excluded). PCB: 40 footprints. **Match ✓**

### Component Pinout Verification

| Ref | Value | Package | Datasheet Verified | Status |
|-----|-------|---------|-------------------|--------|
| U1 | CD74HC173E | 16-PDIP | TI SCHS158F, p. 3 pin diagram | Verified (datasheet) ✓ |
| U2 | CD74HC173E | 16-PDIP | TI SCHS158F, p. 3 pin diagram | Verified (datasheet) ✓ |
| U3 | SN74HC245N | 20-PDIP | TI SCLS131F, p. 3 pin table | Verified (datasheet) ✓ |
| U4 | ATtiny84A-PU | 14-PDIP | Microchip DS40002269A, p. 8 Fig 1-1 | Verified (datasheet) ✓ |
| D1–D8 | LED 150080RS75000 | SMD | — | Skipped (2-pin, polarity via net) |
| R1–R19 | Resistors | 0805 | — | Skipped (non-polar) |
| C1–C4 | 100 nF | 0805 | — | Skipped (non-polar) |
| J1, J2, B1–B3 | Connectors | — | — | Verified by net trace |

**U1/U2 CD74HC173E pin mapping (datasheet vs schematic, verified):**

| DS Pin | DS Name | Analyzer Net |
|--------|---------|-------------|
| 1 | /OE1 | GND (always enabled) ✓ |
| 2 | /OE2 | GND (always enabled) ✓ |
| 3–6 | Q0–Q3 | REG0–REG3 / REG4–REG7 ✓ |
| 7 | CP | CLOCK (from backplane) ✓ |
| 8 | GND | GND ✓ |
| 9 | Ē1 | ~{RIN} (active-low, backplane) ✓ |
| 10 | Ē2 | ~{RIN} (active-low, backplane) ✓ |
| 11–14 | D3–D0 | BUS3–BUS0 / BUS7–BUS4 ✓ |
| 15 | MR | CLEAR (from backplane) ✓ |
| 16 | VCC | 5V\_2 ✓ |

Note: CD74HC173E Ē1/Ē2 are **active-LOW** (per TI SCHS158F description and functional block diagram). The schematic net name ~{RIN} (tilde = active-low) matches. Data is latched when ~{RIN} is asserted LOW and CP rises. ✓

**U3 SN74HC245N pin mapping (datasheet vs schematic, verified):**

| DS Pin | DS Name | Analyzer Net |
|--------|---------|-------------|
| 1 | DIR | 5V (fixed HIGH → A→B, register→bus) ✓ |
| 2–9 | A1–A8 | REG0–REG7 ✓ |
| 10 | GND | GND ✓ |
| 11–18 | B8–B1 | BUS7–BUS0 ✓ |
| 19 | /OE | ~{ROUT} (active-low output enable) ✓ |
| 20 | VCC | 5V ✓ |

**U4 ATtiny84A-PU pin mapping (datasheet vs schematic, verified):**

| DS Pin | DS Name | Schematic Net |
|--------|---------|--------------|
| 1 | VCC | 5V\_2 ✓ |
| 2 | PB0/XTAL1 | NO\_CONNECT ✓ (internal osc in use) |
| 3 | PB1/XTAL2 | REG7 (GPIO, input for display) ✓ |
| 4 | PB3/RESET | R9 pull-up → 5V\_2 ✓ |
| 5 | PB2 | REG6 ✓ |
| 6–7 | PA7–PA6 | REG5–REG4 ✓ |
| 8–9 | PA5–PA4 | REG3–REG2 ✓ |
| 10–11 | PA3–PA2 | DIO, CLK (to J1 display) ✓ |
| 12–13 | PA1–PA0 | REG1, REG0 ✓ |
| 14 | GND | GND ✓ |

PA0 doubles as AREF on ATtiny84A. For digital output monitoring (reading REG0), the ADC/AREF function must be disabled in firmware — otherwise AREF output drive capability is limited by an internal 100 kΩ/32 pF network. This is a firmware requirement, not a schematic error. ✓ (inference-only)

### Connector Pin Tables

**J1 — Output to Display (4-pin):**

| Pin | Net | Function |
|-----|-----|----------|
| 1 | 5V\_2 | Display power |
| 2 | GND | Display ground |
| 3 | DIO | Serial data (U4 PA3) |
| 4 | CLK | Serial clock (U4 PA2) |

**J2 — Reg Specific Connections (10-pin):**

| Pin | Net | Function |
|-----|-----|----------|
| 1–8 | REG0–REG7 | Register data lines |
| 9 | ~{RIN} | Active-low data-enable (to U1/U2 Ē1/Ē2) |
| 10 | ~{ROUT} | Active-low output-enable (to U3 /OE) |

### Net Tracing

**5V net:** B1 pin 1 → B2 pin 1 → U3 VCC (pin 20) → U3 DIR (pin 1) → C3 (100 nF bypass). Supply comes from backplane. ✓

**5V\_2 net:** B1 pin 39 → B3 pin 1 → U1 VCC → U2 VCC → U4 VCC → C1/C2/C4 (300 nF total) → R9 pull-up → R18/R19 pull-ups → J1 pin 1. Supply from backplane. ✓

**GND net:** B1 pins 2/40 → B2 pin 2 → B3 pin 2 → U1/U2/U3/U4 GND → R1–R8 → R10–R17 → all caps → J1 pin 2. Common ground via backplane. ✓

**REG0–REG7 signal path (example REG0):**
BUS0 (backplane) → U3 B0 (pin 18) and U1 D0 (pin 14); U1 Q0 (pin 3) → REG0 → U3 A0 (pin 2) [input only, A→B fixed], U4 PA0 (input), D8 anode, R10 (10 kΩ to GND), J2 pin 1. ✓

### PCB Verification

PCB footprint count: 40 (matches schematic). Board dimensions: 85.0 × 99.5 mm (raw file cross-checked). Routing: complete — 0 unrouted nets. ✓

---

## Signal Analysis Review

### Bus Control

Both control signals now have correct termination:

**~{ROUT} → U3 /OE (pin 19), active-low:**
When LOW, the SN74HC245N is enabled and REG0–REG7 are driven onto BUS0–BUS7 (A→B direction, fixed by DIR=5V). When HIGH, U3 is tri-stated. **R19 (10 kΩ) pulls ~{ROUT} to 5V\_2, keeping U3 disabled when J2 is disconnected or the backplane controller has not yet asserted the signal.** ✓ (resolved)

**~{RIN} → U1/U2 Ē1/Ē2 (pins 9/10), active-low:**
When LOW, data on BUS0–BUS7 can be latched into U1/U2 on the next rising CLOCK edge. When HIGH, data is blocked regardless of clock. **R18 (10 kΩ) pulls ~{RIN} to 5V\_2, preventing unintended register writes when J2 is not connected.** ✓ (resolved)

The ERC "no driver" warnings for ~{ROUT} and ~{RIN} are expected — both are driven by the external bus controller. Correct as-is. ✓

### REG0–REG7 Bus Termination

R10–R17 (10 kΩ each) pull REG0–REG7 to GND. Since U1/U2 output-enables (OE1/OE2) are permanently tied to GND, the 74HC173 outputs always drive these lines while the ICs are powered — the pull-downs have negligible effect during normal operation (10 kΩ vs the µΩ output impedance of a driven CMOS output). Their role is to ensure defined low levels on the backplane REG0–REG7 lines when the register board is unpowered or held in reset (CLEAR asserted). Without pull-downs, REG0–REG7 would float on the backplane, potentially causing false reads in other modules. ✓

### LED Circuits

All eight LEDs (D1–D8, Würth 150080RS75000) use 330 Ω series resistors to GND. Anodes connect to REG0–REG7 (active-high drive from 74HC173 outputs).

**Current calculation (updated for 330 Ω):**
- Supply: REG signal = 74HC173 VOH. At 5V VCC with 13 mA load, VOH ≈ 4.5 V typical (conservative)
- LED forward voltage: 2.1 V typical (150080RS75000 datasheet)
- I = (4.5 V − 2.1 V) / 330 Ω = **7.3 mA** — well within the 20 mA recommended max of 150080RS75000

Each 74HC173 IC drives 4 LEDs. Worst-case (all 4 bits HIGH): total output current = 4 × 7.3 mA = **29 mA** from the IC's VCC/GND pins. The CD74HC173E absolute maximum VCC/GND pin current is 50 mA (TI SCHS158F abs max ratings). This gives a 21 mA margin — comfortable. ✓ (resolved from prior 6 mA margin at 220 Ω)

### Register Logic

U1/U2 output-enables (OE1, OE2 at pins 1/2) are both tied to GND (permanently enabled). Outputs REG0–REG7 always reflect the latched register state. This is intentional — the ATtiny84 monitors these lines as inputs, and U3 drives the bus only when ~{ROUT} is asserted. No contention exists as long as U4 PA0–PA7 are configured as inputs in firmware. ✓ (inference-only)

U4 PB1/XTAL2 (pin 3) is used as GPIO input for REG7. PB0/XTAL1 is NO\_CONNECT (internal oscillator in use). This is a valid configuration per ATtiny84A datasheet section 1.1.3. ✓

### Decoupling Analysis

| Rail | Capacitors | Total Capacitance |
|------|-----------|-------------------|
| 5V (U3 only) | C3 100 nF | 100 nF |
| 5V\_2 (U1, U2, U4) | C1, C2, C4 100 nF each | 300 nF |

C1 is 3.5 mm from U4 (adequate), C2/C4 are 4.4–9.1 mm from U1/U2 (acceptable for slow digital). C3 is **25 mm from U3** — this is outside the recommended <10 mm range for effective decoupling. (SUGGESTION: relocate C3 within 10 mm of U3's VCC pin.) The analyzer SPICE simulation confirmed the decoupling network is electrically valid for the low-frequency digital operation.

---

## Power Analysis

### Power Budget

Both rails are 5 V from the backplane. No on-board regulators. Total estimated current (updated):
- U1 + U2 (74HC173): ~20 mA each @ 5 V (active with all LEDs on, worst case)
- U3 (74HC245): ~80 µA ICC + drive current
- U4 (ATtiny84): ~5 mA at 5 V @ 8 MHz (typical active)
- 8 LEDs at ~7.3 mA each: ~58 mA total (reduced from ~88 mA at 220 Ω)
- **Total: ~105 mA worst case** — well within typical backplane capability.

### Inrush Analysis

No regulators with soft-start. At power-on, C1–C4 (400 nF total) charge through trace resistance (~100 mΩ) plus backplane connector contact resistance. Peak inrush ≈ 5 V / 0.1 Ω = 50 A but limited to µs timescales — negligible for a 5 V backplane supply. The 74HC173 VCC pin absolute maximum input current is 50 mA continuous; the capacitive charging transient (charge time = RC = ~4 ns per cap) is far below this limit. ✓

### Voltage Derating

All components rated for 5 V supply. 74HC173 and 74HC245: VCC range 2–6 V. ATtiny84A: VCC range 1.8–5.5 V. C1–C4: rated for 5 V operation at 100 nF, 0805. No derating concerns. ✓

---

## PCB Layout Analysis

### Board Overview

- Size: 85.0 × 99.5 mm
- Layers: 2 (F.Cu, B.Cu)
- Board thickness: 1.6 mm (standard)
- Components: 27 SMD (0805 passives), 13 THT (ICs, connectors, backplane headers)
- Via count: 31
- Surface finish: not specified in PCB file (SUGGESTION: set in board setup)

### Footprint Placement

- B2 and B3 are 0.86 mm from the board edge. This is tight (PCB-way minimum is typically 0.3 mm, JLCPCB is 0.5 mm from trace, not courtyard). Since these are right-angle headers or sockets intended to align with a backplane edge, this placement is likely intentional. ✓ (not a fabrication issue, just a note)
- All other components appear to have adequate edge clearance.

### Via Analysis

31 through-hole vias. No blind/buried vias. Via stitching is sparse — cross-analysis reports 75% of the board area lacks ground vias (VS-002 warning). For a low-frequency digital design this is not a functional concern, but additional stitching vias would improve EMC margin.

### Trace Routing

- Routing: 100% complete, 0 unrouted nets. ✓
- Track segments: 722 (+39 since last review for new resistor routes)
- Total track length: 2117 mm (+203 mm)
- Power trace widths: 5V\_2 = 0.2 mm min, GND = 0.2 mm min. At 105 mA worst-case total, IPC-2221A allows ~0.2 mm at 1 oz copper for 1 A (internal) — 0.2 mm is adequate for this load. ✓
- Longest data nets: 5V\_2 128.8 mm, REG2 103.8 mm, REG3 102.4 mm. These are low-frequency digital signals (no clock rates expected >10 MHz) — trace length is not a concern. ✓

### Signal Integrity

Cross-analysis notes partial ground plane coverage on CLOCK (~{CLOCK}: 67%), CLK (89%) nets. For the backplane clock distribution at typical hobby speeds (<10 MHz), this is not a functional concern. The CLK/DIO lines to J1 are also short (<10 mm from U4).

### Thermal Analysis

Thermal script returned 0 findings, score 100/100. All ICs are PDIP/THT packages with large exposed copper area and good thermal convection. No thermal concerns for this power level. ✓

### Copper Presence

All THT components lack opposite-layer copper (expected — no ground plane fill on B.Cu under the ICs). No capacitive touch pads or RF antennas present. One ground stitching via (VS-002). Zone fills appear not to have been run (no filled polygon data for GND pour). (SUGGESTION: run Edit → Fill All Zones in KiCad to populate ground plane, then re-confirm via stitching.)

### Decoupling Placement

- U4 ↔ C1: 3.5 mm ✓
- U2 ↔ C4: 4.4 mm ✓
- U1 ↔ C2: 4.5 mm ✓ (C4 also within 9 mm)
- **U3 ↔ C3: 25 mm** ⚠ — too far for effective high-frequency decoupling

### DFM Assessment

| Metric | Value | JLCPCB Standard Minimum |
|--------|-------|------------------------|
| Min trace width | 0.20 mm | 0.09 mm ✓ |
| Min spacing | 0.34 mm | 0.09 mm ✓ |
| Min drill | 0.30 mm | 0.20 mm ✓ |
| Min annular ring | 0.15 mm | 0.13 mm ✓ |
| Board size | 85 × 99.5 mm | ≤500×500 mm ✓ |

DFM tier: **standard**. Zero violations. Board is straightforward to fabricate.

### Silkscreen

- Board name and author present: "Ben Eater 8-Bit Computer / Registers Module / D. Q. McDonald June 2026" ✓
- Signal label texts for J2 pins and backplane connector signals are present and helpful ✓
- **All reference designators are hidden** — this complicates rework and in-circuit debugging. (SUGGESTION: make refs visible, or at minimum U1–U4 and J1/J2.)
- **No revision marking** (SUGGESTION: add "Rev A" or "V1.0")
- Connector J1 and J2 lack pin-1 markers or function labels on silkscreen (SUGGESTION)
- LED polarity markers: 8 LEDs flagged; verify anode markers are visible on silk

---

## Schematic ↔ PCB Cross-Reference

### Component Count Match

Schematic: 40 components. PCB: 40 footprints. **Match ✓**

### Pin-Net Verification

Spot-checked all 4 ICs against both schematic net data and PCB pad-to-net assignments:

**U1 (74HC173) — all 16 pins verified:**

| Pin | Net (schematic) | Function | Correct? |
|-----|-----------------|----------|----------|
| 1 | GND | /OE1 = enabled | ✓ |
| 2 | GND | /OE2 = enabled | ✓ |
| 3–6 | REG0–REG3 | Q0–Q3 outputs | ✓ |
| 7 | CLOCK | CP clock | ✓ |
| 8 | GND | — | ✓ |
| 9/10 | ~{RIN} | Ē1/Ē2 data-enable | ✓ |
| 11–14 | BUS3–BUS0 | D3–D0 data inputs | ✓ |
| 15 | CLEAR | MR master reset | ✓ |
| 16 | 5V\_2 | VCC | ✓ |

U2 is identical with REG4–REG7 / BUS4–BUS7. All match. ✓

U3 SN74HC245N: all 20 pins verified — direction fixed HIGH (A→B), /OE controlled by ~{ROUT} with R19 pull-up. ✓

U4 ATtiny84A-PU: all 14 pins verified — PA0–PA7 read register, PB1 reads REG7, PA2/PA3 drive display, PB3 is /RESET with R9 pull-up. ✓

### Footprint Match

All ICs use standard library footprints (DIP-16, DIP-20, DIP-14) which match their respective PDIP packages. ✓

---

## Quality & Manufacturing

### Assembly Complexity

Score: 32/100 (low). Dominant packages: 0805 passives (27), THT (8 ICs/connectors). No fine-pitch SMD. Hand assembly is feasible throughout.

### Sourcing Audit

MPN coverage: **28/40 (70%)**. Missing:
- **B1**: custom 40-pin backplane header — expected to be sourced separately as part of the computer build
- **R9**: generic 0805 4.7 kΩ — add MPN (e.g., RC0805FR-074K7L) for BOM completeness
- **R1–R8**: now 330 R 0805 — add MPN (e.g., RC0805FR-07330RL)
- **R10–R19**: generic 0805 10 kΩ — add MPN (e.g., RC0805FR-0710KL)

No distributor part numbers are stored in the schematic (BOM export will require manual enrichment).

### Component Lifecycle

Lifecycle audit not performed — no distributor API keys configured. All parts are standard active 74HC-series logic and a common AVR MCU; obsolescence risk is low.

### BOM Optimization

| Value | Qty | Role |
|-------|-----|------|
| 330 R 0805 | 8 | LED current limiting (R1–R8) |
| 10 kΩ 0805 | 11 | Pull-up/pull-down (R9–R19) |
| 100 nF 0805 | 4 | Bypass caps (C1–C4) |

All passives are consolidated into three distinct values — excellent for minimising pick-and-place changeovers. ✓

### Test Coverage

Zero test points on any net (TE-001: 0/96 nets covered). For a hobby build this is acceptable, but probing key nets (5V, 5V\_2, CLOCK, ~{ROUT}, ~{RIN}, REG0) during bring-up would require direct IC leg contact. (SUGGESTION: add test points on CLOCK, ~{ROUT}, ~{RIN}, and both 5V nets.)

### Simulation Verification

ngspice is installed. Previous SPICE run confirmed the 300 nF decoupling network on 5V\_2 (C1/C4/C2) is correct — **pass**. No RC filters or analog circuits to simulate beyond decoupling. No new subcircuits detected in the updated schematic.

### Ordering Notes

- Layer count: 2 layers
- Board thickness: 1.6 mm (standard)
- Surface finish: not specified in PCB file — set before ordering (HASL is standard/low-cost)
- Solder mask: not specified — default green
- Copper weight: not specified — 1 oz (35 µm) is appropriate at these current levels
- Stencil: recommended for the 27 SMD 0805 components (all coarse-pitch, standard stencil)
- DFM tier: standard — no advanced process required
- Assembly notes: ICs (U1–U4) and connectors (J1, J2, B1–B3) are THT; solder last after reflow of passives

---

## All Issues & Suggestions

| Severity | Issue | Detail |
|----------|-------|--------|
| ~~WARNING~~ | ~~{ROUT} had no pull-up (U3 /OE floated)~~ | **RESOLVED** — R19 10 kΩ to 5V\_2 added (2026-06-05) |
| ~~WARNING~~ | ~~{RIN} had no pull-up (U1/U2 Ē1/Ē2 floated)~~ | **RESOLVED** — R18 10 kΩ to 5V\_2 added (2026-06-05) |
| ~~SUGGESTION~~ | ~~Consider R1–R8 = 330 Ω~~ | **RESOLVED** — changed 220 Ω → 330 R (2026-06-05); per-LED current now ~7.3 mA, 29 mA worst-case per IC |
| SUGGESTION | Add PWR\_FLAG to 5V and 5V\_2 nets | Eliminates RS-001 ERC warnings and the PP-001 false error on U3 VCC. Both rails are externally supplied — add a PWR\_FLAG power symbol to each. |
| SUGGESTION | Move C3 closer to U3 | C3 is 25 mm from U3 VCC. Relocate within 10 mm for effective high-frequency decoupling. Route a short spur from U3 pin 20 to C3. |
| SUGGESTION | Add reference designators to silkscreen | All 40 refs are currently hidden. At minimum U1–U4 and J1/J2 should be visible for rework. |
| SUGGESTION | Add revision marking | No "Rev A" / "V1.0" on silkscreen. Useful for tracking board versions. |
| SUGGESTION | Add MPNs for R1–R8 (330 R), R10–R19 (10 kΩ), R9 (4.7 kΩ) | All are generic 0805 values; any RCXXXXFR-07xxxL equivalent works. |
| SUGGESTION | Add test points on CLOCK, ~{ROUT}, ~{RIN}, 5V, 5V\_2 | Zero test point coverage currently. Critical for bring-up debugging. |
| SUGGESTION | Set fab notes in PCB board setup | Surface finish, copper weight, solder mask, and material are unspecified. These are needed to match the gerber order configuration. |

---

## Positive Findings

1. **All four IC pinouts verified against manufacturer PDFs** — U1/U2 CD74HC173E, U3 SN74HC245N, U4 ATtiny84A-PU pin-to-net assignments all match the respective TI and Microchip datasheets exactly. No library symbol errors.
2. **Routing is 100% complete** — zero unrouted nets on a 85 × 99.5 mm 2-layer board, including 10 newly placed resistors.
3. **DFM standard tier, zero violations** — straightforward to order from any standard PCB fabricator.
4. **R9 ATtiny84 /RESET pull-up is correctly implemented** — 4.7 kΩ to 5V\_2 matches ATtiny84A datasheet recommended reset circuit. ✓
5. **~{ROUT} and ~{RIN} pull-ups correctly implemented** — R18 and R19 (10 kΩ each to 5V\_2) ensure both active-low control signals are de-asserted at power-on and when J2 is disconnected. Resolves prior WARNINGs. ✓
6. **REG0–REG7 bus termination added** — R10–R17 (10 kΩ to GND) provide defined low levels on backplane data lines when the register board is unpowered or in reset. ✓
7. **LED current margin improved** — 330 Ω resistors give ~7.3 mA per LED, 29 mA worst-case per 74HC173; 21 mA margin to 50 mA absolute maximum (vs 6 mA margin at 220 Ω). ✓
8. **Decoupling cap placement is good for U1/U2/U4** — C1 at 3.5 mm, C2/C4 under 10 mm. Only U3's C3 is an outlier.
9. **Active-low control signal naming is consistent** — ~{ROUT} and ~{RIN} names correctly indicate signal polarity, matching CD74HC173E Ē1/Ē2 active-low data enable behavior.
10. **U4 ATtiny84 XTAL pins correctly managed** — PB0 (XTAL1) is NO\_CONNECT and PB1 (XTAL2) is repurposed as GPIO for REG7 monitoring. This is valid for internal-oscillator operation per Microchip DS40002269A §1.1.3.
11. **Passive BOM fully consolidated** — three distinct values (330 R, 10 kΩ, 100 nF) cover all 23 passives. Minimal pick-and-place changeovers. ✓

---

## Analyzer Gaps

1. **SPICE simulation limited to decoupling check only** — digital-only design; no RC filters, opamp, or analog subcircuits to simulate further.
2. **EMC analyzer not available** in this plugin version — `analyze_emc.py` was not found; EMC pre-compliance analysis was skipped.
3. **LED Vf not resolved in LED audit** — analyzer reported LED current as `None` due to missing Vf in the symbol properties. Manual calculation above used Würth 150080RS75000 datasheet values (2.1 V typical).
4. **No gerber files present** — `analyze_gerbers.py` was not run; layer completeness and drill alignment cannot be confirmed from fabrication outputs.
5. **Lifecycle audit not performed** — no distributor API credentials configured.
6. **Ground plane fill not present** — PCB zones appear unfilled (no fill polygon data). Re-run zone fill in KiCad before generating gerbers.

---

## Not Performed / Review Limits

- **Gerber analysis**: no fabrication outputs in project directory.
- **EMC analysis**: `analyze_emc.py` not found in this plugin version.
- **Lifecycle audit**: no distributor API keys.
- **Pin-level datasheet verification for connectors J1/J2**: generic through-hole headers — no datasheet required; verified by net trace only.

---

## Final Verdict

**Ready to order.** The board is mechanically complete, fully routed, DFM-clean, and all IC pinouts have been verified against manufacturer datasheets. No CRITICAL or WARNING-level issues remain — both prior pull-up warnings have been resolved in this revision.

Before powering up for the first time, add a PWR\_FLAG to both 5V nets to clean up ERC, and optionally move C3 closer to U3. All remaining items are cosmetic or BOM-housekeeping suggestions.

The ATtiny84 firmware must configure PA0–PA7 and PB1 as **inputs** (not outputs) to avoid contention with the permanently-enabled 74HC173 Q outputs on REG0–REG7. PA0 (AREF) must have the ADC reference disabled before using it as a digital input.
