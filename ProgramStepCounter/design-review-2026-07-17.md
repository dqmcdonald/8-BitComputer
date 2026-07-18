# ProgramStepCounter Board — Design Review

**Date:** 2026-07-17
**Board:** ProgramStepCounter.kicad_pro — dual-role Program Counter / Step Counter
**KiCad:** 10.0
**Assembly:** hand-soldered (pick-and-place / sourcing findings not applicable)
**Analysis run:** `analysis/2026-07-17_1927/` (schematic, PCB, cross, EMC, thermal, SPICE)
**Prior review:** none — this is the first review of this board

## Verdict

**Not ready to fab. Three defects, two of which stop the board's bus interface from working at all.**

The counter core is right — the cascade, the bit ordering, the jumper scheme, the decoupling
and the pinouts all check out against the datasheets. The problems are all in how the board
talks to the backplane:

1. **U3 (74HC245) has its direction pin tied to GND**, so the bus buffer points the wrong way.
2. **`COUO` is split into two unconnected nets**, so the buffer's output enable never reaches it.
3. **J1 pin 4 is wired to count bit 2 instead of bit 3.**

Findings 1 and 2 both come from the same corner of the schematic and are independent of each
other — fixing one without the other still leaves a non-working board. Finding 2 is **inherited
from `Template/Template.kicad_sch`**, so it will land on every future board unless the template
is fixed too.

All three are schematic-level; the PCB faithfully implements the schematic in each case.

---

## Blockers

| # | Finding | Severity |
|---|---|---|
| 1 | U3 `DIR` (pin 1) tied to GND — bus buffer drives backwards into the counter outputs | **Critical** |
| 2 | `COUO` / `~{COUO}` net split — U3 output-enable disconnected from backplane B1.67 | **High** |
| 3 | J1 pin 4 → U1.Q2 (duplicate); count bit 3 reaches no header pin | **High** |

---

## Issue 1 — U3 direction pin is backwards (CRITICAL)

U3 pin 1 is tied to **GND** in both the schematic and the PCB:

```
U3 pad  1 -> GND      (A->B_1)      <-- DIR
U3 pad 19 -> ~{COUO}  (CE_19)       <-- OE
U3 pads 2-9   -> counter Q outputs (A0..A7)
U3 pads 11-18 -> BUS0..BUS7        (B0..B7)
```

SN74HC245 (SCLS131F), Table 8-1 Function Table:

| OE | DIR | Operation |
|----|-----|-----------|
| L | L | **B data to A bus** |
| L | H | A data to B bus |
| H | X | Isolation |

With `DIR = L`, asserting `~COUO` makes the '245 drive **B → A**: it pushes whatever is on the
backplane data bus back onto the counters' Q outputs. Two consequences, both fatal:

- The counter value **never reaches the bus**, so the program counter can never drive an address
  during a fetch or jump.
- The '245's A-side drivers fight the 74HC161's totem-pole Q outputs directly. These are not
  open-drain and not tri-state — they are always driving. That is a hard short between two active
  outputs whenever `~COUO` is asserted and the bus disagrees with the count.

**`DIR` must be tied to 5V** (A → B). The counters load from the bus through their D inputs
(U1.3-6 → BUS0-3, U2.3-6 → BUS4-7) under `~PE`, not through the '245 — so this buffer is
output-only and has no reason to ever run in reverse.

This is corroborated by the sibling boards, which use the identical output-only pattern:

| Board | Part | pin 1 (DIR) | pin 19 (OE) |
|-------|------|-------------|-------------|
| Registers | 74HC245 | **5V** | `~{ROUT}` |
| ALU | 74HC245 | **5V** | `~{ADDO}` |
| RAM | 74HCT245 | `~{RAMI}` | `~{RAMEN}` (genuinely bidirectional — correct there) |
| **ProgramStepCounter** | 74HC245 | **GND** | `~{COUO}` |

ProgramStepCounter is the only output-only board that doesn't tie DIR high.

---

## Issue 2 — `COUO` is two nets, not one (HIGH)

Every backplane control signal on this board appears twice: once on the `B1` DataBus connector
and once on the `B3` side rail, joined by a shared global label. `COUE` shows the intended
pattern; `COUO` breaks it.

```
COUE      [3 pins]  B3.30(COUE), B1.68(COUE), JP3.1(A)        <-- one net, correct
~{COUO}   [2 pins]  B3.29(COUO), U3.19(CE)
COUO      [1 pin ]  B1.67(COUO)                               <-- isolated
```

The labels sit in the two connector columns at matching coordinates but don't match in name:

| Column | Coordinate | Label |
|--------|-----------|-------|
| B1 (DataBus) | (52.07, 52.07) | `COUO` |
| B3 (side rail) | (106.68, 52.07) | `~{COUO}` |

So backplane pin B1.67 is a dead-end single-pin net, and U3's output enable is reachable only
from side-rail pin B3.29. Nothing else on the board drives it and there's no pull-up, so
**U3.19 floats** — the buffer's enable state is undefined at power-up.

DRC didn't catch this: a single-pin net has nothing to route, so the board still reports
`routing_complete: true, unrouted_net_count: 0`. The schematic analyzer did flag it as
`NT-001`.

**The correct name is `COUO`** — all six other boards (ALU, Registers, ProgramROM, ControlLogic,
RAM, Clock) use the un-inverted form, and this board's own `B1` column agrees. Rename the two
`~{COUO}` labels (at `(106.68, 52.07)` and at U3.19, `(208.28, 63.5)`) to `COUO`.

### This came from the Template

`Template/Template.kicad_sch` has the same mismatch **at identical coordinates**:

```
Template     : ~{COUO} at (106.68, 52.07)   |   COUO at (52.07, 52.07)
ProgramStep. : ~{COUO} at (106.68, 52.07)   |   COUO at (52.07, 52.07)
Registers    :   COUO  at (111.76, 62.23)   |   COUO at (52.07, 62.23)   <-- correct
```

Since new boards in this project start from `Template/`, every future board inherits a
disconnected `COUO`. Worth fixing in the template in the same sitting — note `Template.kicad_sch`
already has uncommitted changes in the working tree.

---

## Issue 3 — J1 pin 4 taps the wrong count bit (HIGH)

J1 ("Count Jumper", 1x08) is meant to tap Q0-Q7. Pins 3 and 4 both land on U1.Q2, and U1.Q3
reaches no header pin at all:

```
J1 pad 1 -> Net-(D8-A)   = U1.Q0  ✓
J1 pad 2 -> Net-(D7-A)   = U1.Q1  ✓
J1 pad 3 -> Net-(D6-A)   = U1.Q2  ✓
J1 pad 4 -> Net-(D6-A)   = U1.Q2  ✗  should be Net-(D5-A) = U1.Q3
J1 pad 5 -> Net-(D4-A)   = U2.Q0  ✓
J1 pad 6 -> Net-(D3-A)   = U2.Q1  ✓
J1 pad 7 -> Net-(D2-A)   = U2.Q2  ✓
J1 pad 8 -> Net-(D1-A)   = U2.Q3  ✓
```

The taps form a regular staircase — each J1 pin drops 2.54 mm and steps 2.54 mm right to meet the
next U3 A-input node. Pin 4's vertical is one row short:

```
wire (189.23, 43.18) -> (189.23, 30.48)      terminates on the Q2 node (y=43.18)
                                              should terminate on the Q3 node (y=45.72)
junction at (189.23, 43.18)                   the anomaly
junctions at 191.77@48.26, 194.31@50.8, ...   the correct pattern for pins 5-8
```

Note that U1.Q3's own path to U3.A3 is intact — `(189.23, 68.58) -> (189.23, 45.72) -> (208.28,
45.72)` — so the count itself is fine and only the header tap is wrong. Rerouting pin 4's tap to
the Q3 node needs a little care, because the Q2 node's horizontal run to U3 currently starts at
x=189.23; the cleanest fix is to pull that horizontal back to start at x=186.69 and let pin 4's
vertical run down to y=45.72.

---

## Medium

### U1/U2 are labelled 74LS161 but the MPN is SN74HC161N — populate the HC part

```
U1, U2:  Value = 74LS161    lib_id = 74xx:74LS161    MPN = SN74HC161N
```

This isn't cosmetic — an actual LS161 would not work here:

- **LS161 `IOH` = -400 µA max**, so it cannot drive the LED on its Q output at all.
- **LS161 `VOH` min = 2.7 V**, which is below the **74HC245 `VIH` min of 3.15 V** (SCLS131F §6.3).
  An LS output driving an HC input is out of spec even with the LED removed. This is the same
  logic-level trap the RAM board hit in its 2026-07-12 review.

The MPN (SN74HC161N) is the right call — HC → HC is clean. Fix the `Value` field so nobody
builds it from the silkscreen/BOM. The rest of the project is HC-based, so this is consistent.

### LED load isn't guaranteed by the HC161 datasheet — consider 330 Ω → 1 kΩ

D1-D8 sit anode-on-Q, cathode through 330 Ω to GND, so the counter output sources the LED
current. SN74HC161 (SCLS297D) specifies `VOH ≥ 3.98 V` at `IOH = -4 mA`, `VCC = 4.5 V`.

```
At the 3.98 V floor, red LED Vf ~ 1.9 V, R = 330 R:
    I = (3.98 - 1.9) / 330 = 6.3 mA    > 4 mA  -> beyond the point where VOH is specified
```

So VOH is not guaranteed at this load, on the same node that feeds U3's A input (VIH 3.15 V).
In practice it will work — typical VOH at -4 mA is 4.3 V, giving ~7 mA and a comfortable margin,
and abs-max output current is ±25 mA so nothing is at risk of damage. But it isn't guaranteed by
the numbers.

```
With R = 1 kR:
    I = (3.98 - 1.9) / 1000 = 2.1 mA   <= 4 mA  -> VOH >= 3.98 V guaranteed
                                                    clears HC245 VIH by 0.83 V
```

This is exactly the change made on the RAM board (330 Ω → 1 kΩ) for the same reason, so it also
keeps LED brightness consistent across modules. Recommended, not a blocker.

### `~COUO` has no pull-up

Once Issue 2 is fixed, U3.19 is driven by the backplane. If the control logic ever tri-states or
is slow coming up at power-on, the '245 can enable itself onto the shared bus. A 10 kΩ pull-up to
5V makes "disabled" the default. Flagged by the analyzer as `PU-001`; same spirit as the RAM
board's microcode-enforced `RAMI`/`~RAMO` interlock.

### Redundant routing (per the project's standard duplicate-track check)

`scripts/find_duplicate_tracks.py` reports **5 issues** out of 704 segments — all on BUS1 and GND,
consistent with leftovers from a re-route:

```
Exact duplicate segment groups: 3
  net=BUS1 F.Cu (41.725,51.475)-(46.525,51.475)      segments [369, 370]
  net=BUS1 F.Cu (46.525,51.475)-(47.425,50.575)      segments [372, 380]
  net=BUS1 F.Cu (47.425,50.575)-(47.8964,49.721)     segments [374, 377]

Overlapping collinear pairs: 2
  net=GND  F.Cu  x=36.081446, y 44.143->44.069 vs 44.143->43.969   (near C1)
  net=BUS1 B.Cu  y=51.475,    x 37.525->41.725  vs 39.025->41.725  (near U1)

Duplicate vias: 0
```

Harmless electrically, but worth clearing before fab. Back up the `.kicad_pcb` first and confirm
no via/pad sits at a freed endpoint.

---

## Low / informational

- **Via-in-pad, untented, on C2 pad 2** (`VP-001`). On a hand-soldered 0805 this can wick solder
  away from the joint. Worth tenting or nudging the via off the pad.
- **JP1 uses a different footprint variant** (`SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm_NumberLabels`)
  than JP2/JP3 (`...RoundedPad1.0x1.5mm`). Cosmetic silkscreen inconsistency only.
- **All three jumpers are `_Open`**, so `~CL`, `~LOAD` and `ENABLE` float until bridged, with no
  pull resistors to define a default. That's inherent to the config-jumper approach and matches
  the board's purpose, but it does mean the board is inert (and its HC inputs are floating) until
  all three are set. Worth a line in the build notes.
- **J1 has no ground pin** (`CG-AUD`) — awkward for scope probing an 8-pin count tap.
- **SN74HC161N is not stocked by element14/Newark** (they carry only the SOIC `SN74HC161D`).
  The PDIP is Active at TI — order it from DigiKey or Mouser. SN74HC245N and SN74HC08N are both
  fine at element14.
- **Datasheet property URLs are wrong on three parts**: U1/U2 point at `sn74LS161` and U4 points
  at `sn74LS08` while its MPN is `SN74HC08N`. This actively caused a bad download — see
  Verification basis below.

---

## Circuit checks that passed

**Counter pinouts** — U1/U2 verified pin-by-pin against SN74HC161 (SCLS297D, pinout for the
D/J/N/NS/PW/W packages). All 16 pins map correctly (`~MR`=CLR, `CP`=CLK, `D0-D3`=A-D, `CEP`=ENP,
`~PE`=LOAD, `CET`=ENT, `Q0-Q3`=QA-QD, `TC`=RCO).

**U4 pinout** — the custom `DQM:74HC08` symbol verified against SN74HC08 (SCLS081J §Pin
Functions). All four gates and both supply pins correct.

**Bit ordering** — U1.Q0 (LSB) → U3.A0 → BUS0, U2.Q0 → U3.A4 → BUS4. Correct across all 8 bits,
schematic and PCB.

**Cascade** — U1.CEP and U1.CET both to `ENABLE`; U1.TC → U2.CET; U2.CEP → `ENABLE`. Standard
two-stage synchronous cascade. U2.TC is unused (single-pin net) — expected, since nothing cascades
past 8 bits.

**Jumper scheme** — the three jumpers do exactly what the board is meant to do:

| Jumper | Common | A (Program Counter) | B (Step Counter) |
|--------|--------|---------------------|------------------|
| JP1 Clear | `~CL` → U1/U2 `~MR` | `~CLEAR` | U4 gate: `~CLEAR` AND `~TRES` |
| JP2 Load | `~LOAD` → U1/U2 `~PE` | `~JUMP` | 5V (never load) |
| JP3 Enable | `ENABLE` → CEP/CET | `COUE` | 5V (always count) |

The U4 AND gate is the right logic: with both inputs active-low, `~CLEAR AND ~TRES` goes low if
either asserts, which is the OR-of-resets the step counter needs.

**Unused gates** — U4's three spare gates have inputs tied to GND and outputs left open. Correct
CMOS practice.

**Decoupling** — one 100 nF per IC, 3.7-4.7 mm away, all on the same side. Fine for 74HC at these
speeds.

**Power** — PWR_FLAG verified wired to both rails (5V via `(21.59,17.78) → (24.13,15.24) →
(26.67,15.24)`, GND via `(22.86,21.59) → (22.86,12.7) → (26.67,12.7)`). 5V routed at 0.35 mm per
its netclass; GND at 0.2 mm plus a ground pour (81% fill). Total load is roughly 100 mA including
LEDs — both are far more copper than needed.

**Thermal** — 0 findings, score 100/100. Four small DIP logic parts, nothing dissipating.

---

## PCB Layout Analysis

| | |
|---|---|
| Board | 85.0 × 99.5 mm, 2-layer, rectangular outline (closed) |
| Footprints | 31 — matches the schematic's 31 components exactly |
| Routing | **Complete** — 704 segments, 54 vias, 0 unrouted nets |
| Track widths | 0.2 mm (649 segments) / 0.35 mm (55, all 5V) |
| Zones | 1 × GND pour, 81.1% fill |
| Duplicate tracks | **5 issues** — see Medium above |
| Cross-reference | Schematic ↔ PCB agree on every pad-to-net checked, including all three defects above |

Cross-domain analysis raised return-path coverage on `CLOCK` (48%) and sparse ground stitching
(75% of board). Real enough on a 2-layer board, but at this clock rate they're theoretical; noting
rather than recommending.

---

## Verification basis

Everything called "verified" above rests on a manufacturer PDF, not on a KiCad symbol:

| Part | Document | Source | Used for |
|------|----------|--------|----------|
| SN74HC161N | SCLS297D | ti.com | Pinout, VOH/IOH, VIH, abs max, PDIP availability |
| SN74HC245N | SCLS131F | **element14** | Function table (DIR/OE), VIH, pinout, PDIP availability |
| SN74HC08N | SCLS081J | ti.com | Pin function table, PDIP availability |

**The element14 sync needs a caveat.** It resolved SN74HC245N correctly, but:

- **SN74HC161N** is not in the element14/Newark catalogue at all, so it fell back and failed. I
  fetched SCLS297D from ti.com directly.
- **SN74HC08N** "succeeded" but downloaded the **wrong part**. The sync follows the schematic's
  `Datasheet` property URL first, and U4's URL points at `sn74LS08` — so it retrieved the
  SN7408/SN54LS08/SN54S08 datasheet (a 1988 bipolar TTL document) and filed it as the HC08. It
  did mark it `verification: unverified`. I replaced it with the real SN74HC08 datasheet and kept
  the wrong one as `SN74LS08_wrong-part-from-schematic-url.pdf` as evidence.

This is precisely why the Datasheet-URL cleanup in the Low section matters: a wrong datasheet is
more dangerous than a missing one. `datasheets/manifest.json` has been corrected to reflect what's
actually on disk, with per-part provenance and verification notes.

---

## Analyzer findings triaged as false positives

| Rule | Count | Why it doesn't apply |
|------|-------|---------------------|
| `PP-001` power pin no DC path | 4 (error) | Known same-net analyzer bug — it strips power symbols, then can't find the rail source. U1.16/U2.16/U3.20/U4.14 are all on net `5V`, and PWR_FLAG is verified wired to it. |
| `RS-001` 5V has no declared source | 1 | Same root cause. 5V arrives from B1/B2/B3 with PWR_FLAG attached. |
| `SS-001` sourcing blocker (<50% MPN) | 1 (error) | Hand-assembled board; MPNs on passives aren't needed per project convention. |
| `GP-001` EMC ground plane gaps | 82 (error) | Over-fires on 2-layer hobby boards — there is no dedicated plane layer by design. |
| `DS-002` no datasheets directory | 1 | Stale — the schematic run predates the datasheet sync. |
| `FD-001` no fiducials | 1 | Hand assembly. |
| `PM-002` B2/B3 0.86 mm from edge | 2 | Side rails are meant to sit at the board edge. |
| `TE-001` no test points | 1 | J1 and the side rails serve this role. |

Genuine analyzer hits worth keeping: `NT-001` (caught Issue 2), `PU-001` (the `~COUO` pull-up),
`VP-001` (via-in-pad), `CG-AUD` (J1 ground).

---

## Not performed / limits

- **DRC and ERC were not run** — I can't drive the KiCad GUI headlessly. Run both before fab. Note
  that DRC will *not* catch any of the three blockers: Issue 1 is a legal net, Issue 2 is a
  single-pin net (nothing to route), and Issue 3 is a legal net with the wrong members. ERC should
  flag Issue 2 as an unconnected/single-pin net.
- **SPICE** ran and found 0 simulatable subcircuits — expected, the board is entirely digital with
  no filters, dividers, or analog feedback. Not a gap.
- **Gerber analysis** skipped — no fabrication outputs exist in the project yet.
- **Lifecycle audit** not run as a batch. Covered ad hoc instead: all three ICs confirmed Active
  in their package option addenda, with the SN74HC161N DIP-sourcing caveat noted above.
- **Passive MPNs** are absent, so R/C/LED parts are unverified at part level. Values are
  conventional and appropriate for the application; the 330 Ω question above is a design point,
  not a sourcing one.
- **Prior-review delta** not applicable — first review of this board, and the manifest has only
  this one run.
