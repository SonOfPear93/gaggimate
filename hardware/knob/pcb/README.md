
## Board A — knob-base

Status: rev 1 layout, generated 2026-11-07 while Ryan was away. ERC/DRC clean, not yet ordered.
Decisions marked **[Claude's call]** are open to change.

Files (`knob-base/`): `knob-base.kicad_sch`, `knob-base.kicad_pcb`, `knob-base.kicad_pro`,
`lib/knob-base.pretty` (SmartKnob hole footprints), `scripts/` (generators), `fab/` (outputs).
The design is fully script-generated; edit the scripts, not the board, or regeneration will undo it:

```sh
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
cd hardware/knob/pcb/knob-base
python3 scripts/gen_sch.py      # schematic
$PY scripts/gen_pcb.py          # placement, hand routes on the flexure, grid router, GND pours (~20 s)
$PY scripts/gen_fab.py          # Gerbers/drill zip, JLC BOM + CPL, renders, schematic PDF, ERC/DRC reports
```

### Credit and what changed from SmartKnob

Derived from **SmartKnob View `electronics/view_base` by Scott Bezek (Apache-2.0)**,
https://github.com/scottbez1/smartknob. Kept, at the same coordinates: the press-sensor flexure
(all inner Edge.Cuts: arc slots r = 15–16 mm, 1.0 mm radial slots either side of four 5 mm arms out to
r = 23.8 mm, the motor-wire cut-out and the Ø3 display-wire hole), MT6701 (U1) at the exact centre on
the front, its 100 n (C20), the four 2512 strain-gauge resistors (R18–R21) on the back of the ±X arms,
the HX711 circuit (U4 + PNP AVDD regulator Q1/R3/R4, excitation filter, 100 Ω/100 n input filter,
decoupling, GNDA–GND net tie NT1), motor holes H1–H3, M2 holes H4–H7 and alignment holes H8/H9.
Hole footprints are copied from SmartKnob's `lib/Holes.pretty`; reference designators match view_base.

Removed: ESP32 module, USB-C, CH340, both regulators, TMC6300, SK6812 LEDs, VEML7700, LCD pads,
test points and the J4/J5 glued-gauge pads. Changed:
- Outline: 81.2 mm rounded square → **Ø75.0 mm circle**, 1.2 mm FR4, 2 layers.
- HX711 group moved onto the rigid quadrant at 135° (back side); power is 3V3 from Board B.
- **[Claude's call]** L1 3.3 µH (C307744, extended, 5k stock) → FB1 ferrite bead GZ2012D101TF (C1015, basic).
  Same 0805 footprint, so C307744 can be fitted instead if the HX711 reading is noisier than SmartKnob's.
- **[Claude's call]** MMBT4403 → SS8550 (C8542, basic; same SOT-23 B-E-C pinout; the HX711 datasheet's own PNP).
- Bridge routing keeps SmartKnob's topology (+X-arm nets cross the inner disc and leave up the 90° arm,
  −X-arm nets leave along the −X arm) but is redrawn for 0.25 mm tracks / 0.15 mm clearance / 0.3 mm edge
  clearance. R18's E+ leaves from the outer root and goes round on the ring. The encoder bus (3V3, CS,
  CLK, DO on F.Cu; GND on B.Cu) now runs down the 270° arm instead of the −X arm.
- Added J1 (JST-SH 8p) and the 3.0 × 7.0 mm wire slot.

### Placement and coordinates

Front view (looking at the knob side), origin at the board centre, +x right, +y up, mm, angles CCW from +x
(alignment holes on the x axis). KiCad file coordinates: board centre at (100, 100), KiCad X = 100 + x,
KiCad Y = 100 − y.

| Item | Position (x, y) | Notes |
|---|---|---|
| Board outline | circle Ø75.0 | 1.2 mm thick |
| U1 MT6701CT (front) | (0, 0) | under the motor magnet, as SmartKnob |
| H1 / H2 / H3 motor (M1.6) | (5.125, −8.877), (−10.25, 0), (5.125, 8.877) | r = 10.25 at −60°/180°/60°, Ø1.7 plated, pad Ø2.4 |
| H4 / H5 / H6 / H7 mount (M2) | (0, −29.8), (−29.8, 0), (0, 29.8), (29.8, 0) | r = 29.8 at 270°/180°/90°/0°, Ø2.2 plated, pad Ø3.5 |
| H8 / H9 alignment | (35, 0), (−35, 0) | r = 35 at 0°/180°, Ø2.2 plated, pad Ø3.5 |
| **Wire slot** | centre (−23.688, −23.688) | r = 33.5 at 225°, 3.0 × 7.0 obround, long axis tangential (along the 135°/315° direction); inner edge r = 32.0, outer r = 35.0; ≥ 8 mm outside the flexure slots, ~4.9 mm from J1's courtyard |
| Display-wire hole (kept) | (−7.071, −7.071) | Ø3.0, r = 10 at 225° |
| Motor-wire cut-out (kept) | centre (8.75, 0) | 3.5 × 7.0, r = 0.75 corners |
| Strain gauges R18/R19/R20/R21 (back) | (23.5, 0), (15.6, 0), (−15.6, 0), (−23.5, 0) | 2512 across the arm roots |
| U4 HX711 (back) | (−15.91, 15.91) | r = 22.5 at 135°, rotated 45°; passives at r ≈ 17–32 |
| **J1 JST-SH (back)** | footprint origin (−10.0, −29.5) | pins 1…8 at y = −31.5, x = −13.5 … −6.5 (front view); cable opening faces the board centre (+y) |

Max part height on the back (towards Board B): J1 2.9 mm (plus the mated plug in front of the opening),
U4 1.75 mm, everything else ≤ 1.3 mm. Front side: only U1 (1.75 mm) and C20, within r ≈ 5 of the centre.

**[Claude's call]** The brief said "HX711 on the rigid ring r ≈ 29–37". The ring between the M2 holes and the
edge is ~7 mm wide and already holds H4–H9, so U4 and its 12 passives sit on the quadrant between the 90° and
180° arms at r ≈ 17–32. That area is rigid: the radial flexure slots stop at r = 23.8, so each quadrant is joined to
the outer ring along its full width (SmartKnob put LEDs and caps there).

### Connector J1 to Board B

JST SM08B-SRSS-TB (side entry, 1.0 mm), back side. Board B uses the same header (C160407), so the cable is a
JST-SH 8-way **pin-1-to-pin-1** (same-side) lead, e.g. two SHR-08V-S housings with SSH crimps or a pre-made
"Qwiic-style" 8-way cable.

| Pin | Net | Board A use |
|---|---|---|
| 1 | 3V3 | MT6701 VDD/MODE, HX711 VSUP/DVDD/RATE, PNP emitter |
| 2 | GND | |
| 3 | ENC_CS | MT6701 pin 8 (CSN) |
| 4 | ENC_CLK | MT6701 pin 7 (CLK) |
| 5 | ENC_DO | MT6701 pin 6 (DO) |
| 6 | HX_SCK | HX711 PD_SCK |
| 7 | HX_DOUT | HX711 DOUT |
| 8 | GND | |

MT6701 MODE is tied to VDD (SSI, as SmartKnob). HX711 RATE is tied high (80 SPS), XI to AGND (internal
oscillator). Board A has no pull-ups or series resistors on the interface; SmartKnob had 2.2 k pull-ups on the
encoder DO/CLK on its main board, so put those on Board B if the SSI read needs them.

### Parts (JLC, qty 5 boards)

Stock and price from the local kicad-jlcpcb-tools parts DB (snapshot dated 2026-09-21; not refreshed today,
that needs a download). Unit price is the JLC tier for the quantity bought.

| Ref | Value | MPN | LCSC | Type | Stock | Unit | Qty (5 bds) | Cost |
|---|---|---|---|---|---|---|---|---|
| U1 | MT6701CT-STD-R | Novosense MT6701CT-STD-R | C3003196 | Extended | 5,421 | $1.724 | 5 | $8.62 |
| U4 | HX711 | Avia HX711 | C6705483 | Extended | 177,864 | $0.505 | 5 | $2.52 |
| J1 | JST-SH 8p | JST SM08B-SRSS-TB(LF)(SN) | C160407 | Extended | 125,076 | $0.332 | 5 | $1.66 |
| R18–R21 | 330 Ω 2512 (strain) | Uniroyal 25121WJ0331T4E | C19866 | Extended | 113,348 | $0.028 | 20 | $0.56 |
| Q1 | SS8550 | CJ SS8550 Y2 | C8542 | Basic | 888,952 | $0.015 | 5 | $0.07 |
| FB1 | 100 Ω@100 MHz 0805 | Sunlord GZ2012D101TF | C1015 | Basic | 2,395,344 | $0.027 | 5 | $0.14 |
| C16, C18 | 10 µF 0805 | Samsung CL21A106KAYNNNE | C15850 | Basic | 5,982,699 | $0.084 | 10 | $0.84 |
| C12, C19, C20, C22, C23 | 100 nF 0603 | Yageo CC0603KRX7R9BB104 | C14663 | Basic | 53,676,678 | $0.012 | 25 | $0.30 |
| R3 | 10 k 0603 | Uniroyal 0603WAF1002T5E | C25804 | Basic | 24,484,378 | $0.003 | 5 | $0.01 |
| R4 | 8.2 k 0603 | Uniroyal 0603WAF8201T5E | C25981 | Basic | 1,133,039 | $0.004 | 5 | $0.02 |
| R5, R6 | 100 Ω 0603 | Uniroyal 0603WAF1000T5E | C22775 | Basic | 12,954,942 | $0.003 | 10 | $0.03 |
| NT1 | net tie | copper only | — | not placed | | | | |

BOM cost for 5 boards: **components ≈ $14.78**, plus 4 extended-part fees (≈ $3 each) ≈ **$26.80**. Not included:
bare PCBs (Ø75, 1.2 mm, 2 layers), PCBA setup for **both sides** (U1/C20 front, the rest back), stencil, shipping.
No JLC quote was requested. Every line is ≥ 10× the build quantity; the tightest is the MT6701 (5.4k).

### Fab outputs (`knob-base/fab/`)

- `knob-base-gerbers.zip`: Gerbers (F/B Cu, Mask, Paste, Silkscreen, Edge.Cuts) + Excellon drills (PTH; the NPTH file is empty).
- `knob-base-BOM-JLC.csv`, `knob-base-CPL-JLC.csv`: JLC format. CPL rotation uses kicad-jlcpcb-tools' rule (back side
  `180 − rot`) plus its corrections (SOIC +270, SOT-23 −90) and +180 for the JST SH header (by analogy with the
  plugin's JST_GH_SM/JST_PH_S entries; Board B uses the same value).
- `knob-base-top.png`, `knob-base-bottom.png` (`kicad-cli pcb render`), `knob-base-schematic.pdf`, `erc-report.txt`, `drc-report.txt`.
- Order settings: 1.2 mm thickness (the flexure depends on it), 2 layers, any mask colour.

### Verification

```sh
kicad-cli sch erc knob-base.kicad_sch                                     # 0 errors, 0 warnings
kicad-cli pcb drc --schematic-parity --severity-all knob-base.kicad_pcb   # 0 violations, 0 unconnected, 0 parity issues
```

Rules in `knob-base.kicad_pro`: clearance 0.15 mm (pours 0.25), all tracks 0.25 mm, vias 0.6/0.3 mm, copper to edge
0.3 mm, min drill 0.3 mm. Routing: the flexure/arm traces are hand-placed in `gen_pcb.py`; everything outside the
flexure is routed by `scripts/router.py` (a small 2-layer grid maze router, kept away from the arms, the inner disc and
the M2 screw/nut and alignment-pin areas), giving 163 track segments and 28 vias. GND is poured on both layers.

### Risks / open points (Board A)

1. **Board B's 225° mounting hole (r = 33) sits directly under this wire slot (r = 33.5, 225°).** The 16 wires
   will drop onto B's screw/standoff. Move one of them (for example B's hole to 210°/240°, or the slot) before ordering.
   Board B's 135° hole (r = 33) also lands near A's back-side HX711 passives (R5/R6 reach r ≈ 32.5): a standoff there needs
   to be ≤ Ø2 mm wide at A, or the hole moved.
2. Flexure geometry is SmartKnob's, but the clamp ring is now round, and the quadrants carry the HX711 group.
   Press sensitivity and stiffness are untested.
3. Two-sided assembly (U1 and C20 front, everything else back), as SmartKnob's strain gauges were already on the back.
   JLC charges a second side; the economic PCBA service may not cover it.
4. CPL rotations for J1 (+180, guessed), Q1 and the SOICs must be checked in JLC's placement preview.
5. J1 is a side-entry header with its opening facing the centre. The mated plug lies over bare tracks towards
   r ≈ 23 and needs ~5 mm of space in front of the opening plus ~3 mm height. Board B parts below it must clear
   that (A–B gap target 8 mm).
6. Strain signals: S+ and E+ have longer runs than SmartKnob (the HX711 moved further from the +X arm), and some
   of the outer routing uses vias. The 100 Ω/100 nF input filter, separate GNDA (net tie at the HX711) and GND pours
   on both sides should hold the noise down, but this is unproven. FB1 vs the original 3.3 µH is a second variable.
7. The flexure slots are 1.0 mm wide, at JLC's minimum milled-slot width (unchanged from SmartKnob).
8. Parts DB snapshot is ~7 weeks old. Re-check MT6701 (C3003196) stock before ordering.

## Board B — knob-main

Status: rev 1 layout, generated 2026-11-07 while Ryan was away. Not yet ordered. Decisions marked
**[Claude's call]** are open to change. Verification results are in the "Verification" subsection below.

Files (`knob-main/`): `knob-main.kicad_sch/.kicad_pcb/.kicad_pro`, `knob-main.kicad_sym` (local symbol: AP7361C-33ER), `knob-main.pretty/` (local footprints:
ESP32-S3-WROOM-1 copy with 0.3 mm EP vias, 13-pad wire field, motor pads), `gen/` (generators), `fab/` (outputs).
Everything is script-generated; edit the scripts, not the board:

```sh
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
cd hardware/knob/pcb/knob-main
python3 gen/make_footprints.py && python3 gen/build_sch.py           # local footprints, schematic + .kicad_pro
$K sch upgrade knob-main.kicad_sch && $K sch export netlist -o /tmp/b.net knob-main.kicad_sch
$PY gen/build_pcb.py /tmp/b.net knob-main.kicad_pcb && python3 gen/build_sch.py --pro-only
$PY gen/prefan.py knob-main.kicad_pcb    # hand routes at the DRV8311 + GND/3V3 fan-out vias to the inner planes
$PY gen/dsn.py knob-main.kicad_pcb /tmp/b.dsn                         # then Freerouting 1.9.0 (Java 21):
java -jar freerouting-1.9.0.jar -de /tmp/b.dsn -do /tmp/b.ses -mp 30 -inc Plane
$PY gen/ses.py knob-main.kicad_pcb /tmp/b.ses                         # 0 unrouted in this revision
$PY gen/finish_pcb.py knob-main.kicad_pcb   # cleanup, pours, stitching vias
$PY gen/fab.py knob-main.kicad_pcb fab      # gerbers/drill zip, JLC BOM/CPL, renders
```

(`gen/inner_route.py` and `dsn.py --in2-signal` exist for finishing leftovers on In2 but were not needed here.
`build_pcb.py` calls `pcbnew.SaveBoard`, which rewrites the .kicad_pro with defaults, hence the
`--pro-only` re-run that restores the net classes. Freerouting 2.x needs Java 25 and routed this board badly;
1.9.0 is used.)

### What is on it

| Block | Parts | Notes |
|---|---|---|
| MCU | U1 ESP32-S3-WROOM-1-N16R8 | GPIO map exactly as the design doc §5 table (no changes). EN: 10k/1µF RC + RESET button SW1. GPIO0: 10k pull-up + BOOT button SW2. Status LED D3 (red) + 1k on GPIO48. 10µF + 100nF at the 3V3 pin. |
| USB | J1 USB-C 16P (HRO TYPE-C-31-M-12), U2 USBLC6-2SC6, R1/R2 5.1k CC pull-downs | D+/D− direct to GPIO20/19, VBUS also clamped by U2. SBU unused. |
| 5 V in | J2 JST-XH B4B-XH-A (THT, **bottom side**), D1/D2 SS34 Schottky OR, C1 22µF | J2 pinout = GaggiMate controller J4 (the display connector): 1 +5V, 2 controller UART_TX0, 3 controller UART_RX0, 4 GND. Only 1/4 are used; 2/3 go to test pads TP6/TP7. +5V after the diodes ≈ 4.5–4.6 V. |
| 3.3 V | U3 AP7361C-33ER-13 (Diodes, SOT-223R, 1 A, 340 mV dropout @ 1 A), C2 10µF/25V in, C3 22µF + C4 100nF out | Datasheet asks CIN ≥ 1 µF, COUT ≥ 2.2 µF ceramic. Tab (= OUT on the "R" pinout) on a top-copper +3V3 island with vias into the In2 +3V3 plane. See the U3 note below. |
| Panel power | Q1 AO3401A high-side P-FET, Q2 2N7002, R14 100k, C8 100nF, R15 10k, R16 100k, C9 10µF | LCD_EN (GPIO17) high = panel on. Gate RC gives ≈1 ms soft start so the panel's input caps don't sag the 3V3 rail. Default off (R16 pull-down). |
| Display/touch | R6–R11 33Ω series on QSPI CS/CLK/D0–D3 (at the ESP32), R12/R13 4.7k touch I2C pull-ups **to 3V3_LCD** | Pull-ups go to the switched rail so nothing back-powers the touch IC when the panel is off. **[Claude's call]** the 33Ω resistors damp ringing on the ~10–15 cm loose wire bundle. |
| Motor | U4 DRV8311HRRWR, J5 Molex PicoBlade 53261-0371, J6 3 bare pads | See "DRV8311H configuration". |
| Board A link | J8 JST-SH SM08B-SRSS-TB, R21–R23 2.2k pull-ups on ENC_CS/ENC_CLK/ENC_DO | Board A has no pull-ups; SmartKnob used 2.2k. |
| Wire pads | J7 13 bare THT pads (2 staggered rows, 2.0 mm pitch, Ø0.9 drill) | Screen bundle, same numbering as board C J2. |
| Test pads | TP1 +5V, TP2 +3V3, TP3 GND, TP4 U0TXD, TP5 U0RXD, TP6/TP7 XH pins 2/3 | Ø1.5 mm SMD pads. |

### DRV8311H configuration (hardware variant)

- **MODE tied to AVDD → 3x PWM mode** (datasheet Table 8-2; this setting also selects the 5 A OCP level).
  INHA/INHB/INHC = GPIO4/GPIO5/GPIO18 PWM. All three INLx are tied together to **DRV_EN (GPIO47, 100k pull-down)**:
  INLx = 0 puts every half-bridge in Hi-Z (Table 8-4), so the motor is free while the ESP32 boots.
- nSLEEP = GPIO21 with 100k pull-down. nFAULT → GPIO3 with 10k pull-up to 3V3.
- **GAIN left open (Hi-Z) → 1 V/A** current-sense gain, ±1.65 A full scale around CSAREF/2. SOA/SOB → GPIO1/GPIO2 (ADC1); SOC unused.
  **[Claude's call]**: the gimbal motor draws well under 1 A at 5 V, so 1 V/A uses the ADC range without clipping.
- **SLEW: 47k to GND → 75 V/µs** (and the matching dead time). **[Claude's call]**: slow enough for low EMI near the
  QSPI bundle, fast enough for 20–30 kHz FOC PWM.
- CSAREF tied to AVDD with 100nF; AVDD 1µF; CP–VM 100nF/50V; VM 100nF/50V + 2× 22µF/25V; VIN_AVDD (from +5V) 100nF + 10µF/25V.
- The exposed pad has 4 × 0.3 mm vias to the In1 GND plane. PGND/AGND pins are tied straight into the pad.

### Placement and coordinates

Front view (looking at the knob; board B's top side faces board A and the front), origin at the board centre,
+x right, +y up, angles CCW from +x. KiCad file: board centre at (100, 100), KiCad X = 100 + x, KiCad Y = 100 − y.

| Item | Position | Notes |
|---|---|---|
| Outline | Ø74.0 circle | 1.6 mm, **4 layers** (F.Cu signals / In1 GND plane / In2 +3V3 plane / B.Cu signals) |
| H1–H4 M2 (Ø2.2 NPTH) | r = 33 at 22.5°, 112.5°, 202.5°, 292.5°: (30.488, 12.629), (−12.629, 30.488), (−30.488, −12.629), (12.629, −30.488) | per the updated doc, clear of board A's wire slot |
| U1 ESP32 | centre (0, 22.75); **antenna end at the 90° edge** (top, +y), antenna region y = 29.5…35.5 | Espressif keep-out: the footprint rule area forbids copper (tracks/vias/pours, all 4 layers) in a 48 × 21 mm band over and beside the antenna; nothing else is placed there. H2 (112.5°) sits in that band (no copper; a metal M2 screw ~3.6 mm from the antenna edge — prefer a nylon screw there). |
| J1 USB-C | axis on the 180° direction (−x), footprint origin (−33.2, 0) | Mating face at x = −36.85: flush with the Ø74 edge (centre 0.15 mm inside, shell corners 0.12 mm outside). |
| J2 JST-XH (bottom) | pin 1 at (16.0, −10.0), pins along +x to (23.5, −10.0) | vertical header on the bottom side: the controller cable plugs in from the back |
| J8 JST-SH to board A | footprint origin (−10.0, −29.5), rot 180 | directly under board A's J1 (front view (−10, −29.5)), pins at y = −31.5, opening towards the centre, like A |
| J7 screen pads | row A (pads 1–7) on r = 29, row B (8–13) on r = 27, centred on 225°, tangential | under board A's wire slot (r = 33.5, 225°) |
| J6 motor pads | r = 32 at 225°, tangential, 2.54 mm pitch (1 = A, 2 = B, 3 = C) | |
| J5 PicoBlade | origin (4.0, −27.0) | alternative motor connector (same nets as J6) |
| U4 DRV8311H | (6.0, −16.0) | |

Height: top side ≤ 3.4 mm (PicoBlade 3.4, USB-C 3.26, ESP32 3.1, JST-SH 2.9, everything else ≤ 2.3) — inside the
4 mm limit under board A. Bottom side: only J2 (JST-XH, 7 mm, connector exception) and the THT pad tails.

### Connectors

| J8 (to board A J1, JST-SH 8p, pin-1-to-pin-1 cable) | | J2 (GaggiMate cable, JST-XH 4p) | |
|---|---|---|---|
| 1 +3V3 | 5 ENC_DO | 1 +5V (used) | 3 controller RX0 → TP7 (unused) |
| 2 GND | 6 HX_SCK | 2 controller TX0 → TP6 (unused) | 4 GND (used) |
| 3 ENC_CS | 7 HX_DOUT | | |
| 4 ENC_CLK | 8 GND | | |

J7 screen wires (same numbers on board C J2): 1 3V3_LCD, 2 GND, 3 LCD_CS, 4 LCD_CLK, 5 LCD_D0, 6 LCD_D1, 7 LCD_D2,
8 LCD_D3, 9 LCD_RST, 10 TP_SDA, 11 TP_SCL, 12 TP_INT, 13 TP_RST. Pad 1 is the square one.
J5/J6 motor: 1 = OUTA, 2 = OUTB, 3 = OUTC (phase order only matters for direction; calibration handles it).

The GaggiMate cable pinout was read from GaggiMate's own KiCad PCB (J4, B4B-XH-A: +5V, UART_TX0, UART_RX0, GND).
This assumes a straight 1:1 XH cable, as on the stock display.

### Parts (JLC, qty 5 boards)

Stock and unit price are **live JLCPCB values fetched 2026-11-07** (jlcpcb.com parts search API, no account);
the unit price is the JLC tier for the quantity bought. MPNs from the kicad-jlcpcb-tools DB.

| Ref | Value | MPN | LCSC | Type | JLC stock (live) | Unit @qty | Qty (5 bds) | Cost |
|---|---|---|---|---|---|---|---|---|
| C1, C14, C15 | 22uF/25V | CL31A226KAHNNNE | C12891 | Basic | 2,037,486 | $0.108 | 15 | $1.62 |
| C12, C13 | 100nF/50V | CC0603KRX7R9BB104 | C14663 | Basic | 34,254,991 | $0.015 | 10 | $0.15 |
| C2, C17 | 10uF/25V | CL21A106KAYNNNE | C15850 | Basic | 13,967,885 | $0.035 | 10 | $0.35 |
| C3 | 22uF | CL21A226MAQNNNE | C45783 | Basic | 3,393,006 | $0.183 | 5 | $0.92 |
| C4…C16 (5) | 100nF | CL05B104KO5NNNC | C1525 | Basic | 34,360,402 | $0.003 | 25 | $0.08 |
| C5, C9 | 10uF | CL10A106KP8NNNC | C19702 | Basic | 10,320,170 | $0.020 | 10 | $0.20 |
| C7, C11 | 1uF | CL05A105KA5NQNC | C52923 | Basic | 11,567,547 | $0.006 | 10 | $0.06 |
| D1, D2 | SS34 | SS34 | C8678 | Basic | 3,053,593 | $0.035 | 10 | $0.35 |
| D3 | RED | KT-0603R | C2286 | Basic | 6,604,588 | $0.008 | 5 | $0.04 |
| J1 | USB-C | TYPE-C-31-M-12 | C165948 | Extended | 320,036 | $0.187 | 5 | $0.93 |
| J2 | B4B-XH-A | B4B-XH-A(LF)(SN) | C144395 | Extended | 636,111 | $0.057 | 5 | $0.28 |
| J5 | 53261-0371 | 532610371 | C293630 | Extended | 54,454 | $0.147 | 5 | $0.74 |
| J8 | SM08B-SRSS-TB | SM08B-SRSS-TB(LF)(SN) | C160407 | Extended | 180,740 | $0.324 | 5 | $1.62 |
| Q1 | AO3401A | AO3401A | C15127 | Basic | 1,685,597 | $0.083 | 5 | $0.41 |
| Q2 | 2N7002 | 2N7002 | C8545 | Basic | 5,965,732 | $0.017 | 5 | $0.08 |
| R1, R2 | 5.1k | 0402WGF5101TCE | C25905 | Basic | 4,544,591 | $0.002 | 10 | $0.02 |
| R12, R13 | 4.7k | 0402WGF4701TCE | C25900 | Basic | 15,768,690 | $0.002 | 10 | $0.02 |
| R14, R16, R18, R19 | 100k | 0402WGF1003TCE | C25741 | Basic | 8,797,320 | $0.001 | 20 | $0.02 |
| R20 | 47k | 0402WGF4702TCE | C25792 | Basic | 6,132,232 | $0.002 | 5 | $0.01 |
| R21, R22, R23 | 2.2k | 0402WGF2201TCE | C25879 | Basic | 3,376,709 | $0.001 | 15 | $0.02 |
| R3, R4, R15, R17 | 10k | 0402WGF1002TCE | C25744 | Basic | 22,767,737 | $0.003 | 20 | $0.06 |
| R5 | 1k | 0402WGF1001TCE | C11702 | Basic | 33,787,595 | $0.001 | 5 | $0.01 |
| R6…R11 (6) | 33R | 0402WGF330JTCE | C25105 | Basic | 3,866,713 | $0.002 | 30 | $0.04 |
| SW1 | RESET | TS-1187A-B-A-B | C318884 | Basic | 873,050 | $0.021 | 5 | $0.10 |
| SW2 | BOOT | TS-1187A-B-A-B | C318884 | Basic | 873,050 | $0.021 | 5 | $0.10 |
| U1 | ESP32-S3-WROOM-1-N16R8 | ESP32-S3-WROOM-1-N16R8 | C2913202 | Extended | 28,356 | $5.346 | 5 | $26.73 |
| U2 | USBLC6-2SC6 | USBLC6-2SC6 | C2687116 | Extended | 93,239 | $0.048 | 5 | $0.24 |
| U3 | AP7361C-33ER-13 | AP7361C-33ER-13 | C3743528 | Extended | 1,551 | $0.604 | 5 | $3.02 |
| U4 | DRV8311HRRWR | DRV8311HRRWR | C5218862 | Extended | 8,546 | $1.577 | 5 | $7.88 |

Components for 5 boards ≈ **$46.11** (≈ $9.22/board, of which the ESP32 module is $5.35 and the DRV8311H $1.58),
plus 8 extended-part loading fees (≈ $3 each = $24) → **≈ $70 for 5 boards' parts**. Not included: the bare PCBs
(Ø74 mm 4-layer, 1.6 mm; JLC's 4-layer price for a 74 × 74 mm board was roughly $8–15 for 5 last time I knew it — not
quoted today), PCBA setup/stencil (standard PCBA because of the bottom-side THT J2), THT soldering of J2, shipping.
No JLC quote was requested (that needs the website/account). Every line is ≥ 10× a 10-board build; the tightest are the
AP7361C-33ER-13 (1.5k), DRV8311HRRWR (8.5k) and the ESP32-S3-WROOM-1-N16R8 (28k).

**U3 note (changed after the first layout, at the coordinator's request):** AMS1117-3.3 → AP7361C to fix the 3V3
headroom (≈ 4.5 V in after the Schottkys). The requested **AP7361C-33E-13 (C500795) showed 0 stock at JLC and LCSC on
2026-11-07** (the 4.3k figure is the Sep parts-DB snapshot), and its "E" SOT-223 pinout is 1 IN / 2 GND (tab) / 3 OUT
(Diodes DS37274 Rev.5-2, p.2) — not the 1117's. I used the same regulator in the **"ER" (SOT-223R) package,
AP7361C-33ER-13, C3743528, 1,551 in stock**, whose pinout is 1 GND / 2 OUT (tab) / 3 IN, identical to the 1117, so the
footprint, routing and the +3V3 tab copper are unchanged. Symbol: project-local `knob-main.kicad_sym` (KiCad only ships the
"E" symbol). If the ER stock runs out: ST **LDL1117S33R (C435835, ~59k stock, ~$0.50)** has the same 1 GND / 2 OUT / 3 IN
SOT-223 pinout (check its dropout/cap requirements before swapping); the "E" part would need the board re-laid. Bare pads (J6, J7, TP1–TP7) and holes are not in the BOM/CPL.

### Fab outputs (`knob-main/fab/`)

- `knob-main-gerbers.zip`: 4-layer Gerbers (F.Cu, In1.Cu, In2.Cu, B.Cu, masks, pastes, silks, Edge.Cuts) + Excellon drill (PTH+NPTH in one file) + drill map.
- `knob-main-BOM.csv` (Comment, Designator, Footprint, LCSC) and `knob-main-CPL.csv` (Designator, Mid X, Mid Y, Layer, Rotation), JLC format.
  CPL coordinates are relative to the board centre (aux origin), same origin as the Gerbers/drill.
  Rotation corrections (from kicad-jlcpcb-tools' corrections DB): SOT-223 +180, SOT-23/SOT-23-6 −90, HRO USB-C +180;
  **+180 for JST-SH and Molex PicoBlade by analogy with the plugin's JST_GH_SM/JST_PH_S rules (guess, check)**; bottom side uses 180 − rot.
- `knob-main-render-top.png`, `knob-main-render-bottom.png`.
- Order settings: 4 layers, 1.6 mm, JLC04161H-7628 (default) stackup, min track/space 0.15/0.15 (0.2/0.15 default net class), min drill 0.3 mm.
  Assembly: top side SMT + J2 THT (bottom side — JLC "standard" PCBA; or leave J2 off and hand-solder 4 pins).

### Verification

```sh
cd hardware/knob/pcb/knob-main
kicad-cli sch erc --severity-all knob-main.kicad_sch                         # 0 violations (0 errors, 0 warnings)
kicad-cli pcb drc --schematic-parity --severity-all knob-main.kicad_pcb      # 0 errors; 2 warnings; 0 unconnected; 0 parity issues
```

The 2 DRC warnings are `silk_edge_clearance`: the stock USB-C footprint's silkscreen outline runs past the round edge
(the receptacle is flush with it); that silk is simply clipped. Reports: `fab/erc-report.txt`, `fab/drc-report.txt`.
Rules (`knob-main.kicad_pro`): Default class 0.2 mm track / 0.15 mm clearance, USB 0.3, Power (+5V) 0.5 / 0.2,
PowerIn (VBUS, VIN_XH, 3V3_LCD) 0.4 / 0.2, Motor 0.5 / 0.2; vias 0.6/0.3 mm (power 0.8/0.4); copper-to-edge 0.3 mm;
min drill 0.3 mm (the ESP32 footprint's EP vias were enlarged from 0.2 to 0.3 mm for this). Routing: hand-placed escape
routing at the DRV8311H (power island, charge pump, motor outputs fanned out to J5, INLx/EN, CSA outputs) and GND/+3V3
fan-out vias to the planes (`prefan.py`), everything else by Freerouting 1.9.0 on F.Cu/B.Cu (≈550 track segments),
then GND pours on both outer layers + ~110 stitching vias (`finish_pcb.py`). In1 = solid GND plane, In2 = solid +3V3 plane
(no signals on inner layers).

### Risks / open points (Board B)

1. **JLC part orientation (CPL) needs a look in JLC's placement preview** for: U4 DRV8311H (no correction applied —
   the plugin DB's QFN rule doesn't match the TI WQFN name), U1 ESP32 (none), J8/J5 (+180 guessed by analogy),
   U2/Q1/Q2 (−90 from the DB), U3 (+180 from the DB), J1 (+180 from the DB).
2. ~~3.3 V headroom~~ **Resolved:** U3 is now an AP7361C-33ER (340 mV dropout @ 1 A), so 3V3 stays in regulation down to
   ≈ 3.7 V in; +5V after the SS34s is ≈ 4.5 V. Thermal: ≈ 0.4–0.5 W typical in the LDO, tab heatsinked into the +3V3 plane.
   Remaining note: the AP7361C's absolute-max input is 6.5 V (fine for 5 V USB/GaggiMate supplies, not for anything higher).
3. **Exposed-pad vias** (DRV8311H 4 × 0.3 mm, ESP32 EP 12 × 0.3 mm) are untented via-in-pad. Normal practice for prototypes;
   some solder wicking possible. JLC offers via plugging if wanted.
4. **H2 (112.5°) is inside the ESP32 antenna keep-out band** (no copper there; the hole positions are fixed by the case
   posts). Use a nylon M2 screw/standoff at H2 if possible.
5. Autorouted: electrically complete and DRC-clean but not hand-optimised. The QSPI bus to J7 is ~35 mm on the board plus the
   wire bundle; the 33Ω series resistors are there for that. USB D+/D− (12 Mbit/s full speed) are not length-matched — not
   needed at that speed.
6. Firmware: keep LCD/TP pins low or Hi-Z while LCD_EN is low (otherwise the panel is back-powered through its I/O
   protection diodes). Keep DRV_EN low until the FOC loop is running (outputs are Hi-Z with it low).
7. J2 (XH) is THT on the **bottom**: needs JLC's standard PCBA with THT assembly; alternatively leave it off the
   order and hand-solder 4 pins.
8. The KiCad install has no 3D models for the HRO USB-C and the TS-1187A buttons, so they are missing from the renders
   (footprints are correct).
9. ESP32 antenna points to the 90° edge (front view +y). The enclosure turns the whole stack −90°, so the antenna ends up
   pointing sideways; keep metal (the machine's sheet metal) away from that edge as far as the case allows.

## Board C — knob-screen

Status: rev 1 layout, generated 2026-11-07. Not yet ordered.

Files (`knob-screen/`): `knob-screen.kicad_sch/.kicad_pcb/.kicad_pro`, `knob-screen.pretty/` (13-pad wire ring),
`gen/` (generators, reusing `../knob-main/gen/kgen_*.py`), `fab/`. Regenerate:

```sh
cd hardware/knob/pcb/knob-screen
python3 gen/make_footprints.py && python3 gen/build_sch.py
$K sch upgrade knob-screen.kicad_sch && $K sch export netlist -o /tmp/c.net knob-screen.kicad_sch
$PY gen/build_pcb.py /tmp/c.net knob-screen.kicad_pcb x && python3 gen/build_sch.py --pro-only
$PY ../knob-main/gen/route.py knob-screen.kicad_pcb /tmp freerouting-2.1.0.jar 30 6   # Freerouting 2.1, retries until 0 unrouted
$PY gen/finish_pcb.py knob-screen.kicad_pcb && $PY ../knob-main/gen/fab.py knob-screen.kicad_pcb fab
```

### What is on it

Ø46 mm, **1.0 mm** FR4, 2 layers. No active parts:

- J1 Hirose FH26W-31S-0.3SHW(60) (C2973806), 31 pins, 0.3 mm, bottom contact, back-flip lock — the panel tail.
  Pinout exactly as the design doc table (Waveshare J3): GND 1/4/7/10/20/25/31 + shell, 3V3 21–24/26, TE 11,
  D2 12, D3 13, CLK 14, D1 15, D0 16, CS 17, RESET 18, TP_SCL 27, TP_SDA 28, TP_RESET 29, TP_INT 30; 2/3/5/6/8/9/19 NC.
- C1 10µF 0603, C2 1µF, C3/C4 100nF on 3V3_LCD next to the 3V3 pins. **[Claude's call]**: Waveshare's schematic shows
  no local caps at J3 (their 3V3 comes from the AXP2101 a few cm away). Here 3V3_LCD arrives over a ~10–15 cm wire,
  so a small local reservoir is added.
- TP1: LCD_TE pad only (not wired in rev 1).
- J2: 13 bare SMD pads (1.0 × 1.8 mm) on the **bottom** in a ring r = 5.5 mm around the centre, for the bundle coming up
  the motor's hollow shaft. Same numbering as board B J7 (legend on the bottom silkscreen).
- **Touch I2C pull-ups are on board B** (4.7k to 3V3_LCD), not here.

### Placement and coordinates

Board C's top side (with J1) faces the back of the panel; front view = KiCad top view with y flipped.
Front view, origin at the board/panel centre, +x right, +y up:

| Item | Position | Notes |
|---|---|---|
| Outline | Ø46.0 circle | same as Waveshare's carrier |
| J1 FH26W | footprint origin (−0.70, +4.38), rot 0 | FPC enters from **−x** (the panel's FPC exits the glass on the −x side and folds back). Pin 1 at (−2.10, +8.88), pin 31 at (−2.10, −0.12). |
| FPC corridor | x < −2.6, y = −0.4 … +9.2 | kept free of parts (the folded tail lies on the board there; tracks/vias under it are tented) |
| J2 wire ring (bottom) | centre (0, 0), r = 5.5 | pads ≈ 7.5 mm across; centre Ø5.9 circle on silk marks the shaft |
| H1 / H2 / H3 M2 (Ø2.2 NPTH) | (0, +19.5), (−16.887, −9.75), (16.887, −9.75) | r = 19.5 at 90°, 210°, 330° (front view), clear of the FPC corridor. Recorded for the ScreenPlatform. |

How J1's position was derived: Waveshare's STEP of the ESP32-S3-Touch-AMOLED-1.75 was loaded with OpenCascade and
every solid's bounding box listed. The FH26 (a 10.9 × 4.2 × 0.8 mm box) sits on the panel-facing side of their Ø46 board
with its centre at (−0.49, −4.38) in the model's (x, z) and the FPC solid running from x = −18.9 to −1.7 at the same z,
board-to-panel gap 2.3 mm. (Model z maps to −y front view, so the connector is at y = +4.38 here.) J1's pad-pattern centre
is placed there, shifted 0.2 mm towards the panel edge so the tail has slack rather than being short; uncertainty ≈ ±1 mm
from Waveshare's simplified connector model. Orientation: the FH26 lock flips back away from the FPC entry, which is on
the −x side, matching Waveshare. Parts on the panel side are ≤ 1.0 mm tall (J1 1.0, caps ≤ 0.9; gap 2.3 mm).

### Parts (JLC, qty 5 boards)

Live JLCPCB stock/price, 2026-11-07:

| Ref | Value | MPN | LCSC | Type | JLC stock (live) | Unit @qty | Qty (5 bds) | Cost |
|---|---|---|---|---|---|---|---|---|
| C1 | 10uF | CL10A106KP8NNNC | C19702 | Basic | 10,320,170 | $0.020 | 5 | $0.10 |
| C2 | 1uF | CL05A105KA5NQNC | C52923 | Basic | 11,567,547 | $0.006 | 5 | $0.03 |
| C3, C4 | 100nF | CL05B104KO5NNNC | C1525 | Basic | 34,360,402 | $0.003 | 10 | $0.03 |
| J1 | FH26W-31S-0.3SHW(60) | FH26W-31S-0.3SHW(60) | C2973806 | Extended | 9,625 | $0.242 | 5 | $1.21 |

Components for 5 boards ≈ **$1.37** + 1 extended fee (≈ $3) → **≈ $4.40**. Bare PCB (Ø46, 2-layer, 1.0 mm) not quoted
(typically the $2–5 JLC minimum for 5). The FH26W is the only extended part (9.6k stock).

### Fab outputs (`knob-screen/fab/`)

Same set as board B: `knob-screen-gerbers.zip`, `knob-screen-BOM.csv`, `knob-screen-CPL.csv`, top/bottom renders.
Order settings: 2 layers, **1.0 mm**, min track/space 0.15/0.15, min drill 0.3. Single-sided SMT (top); the bottom has
only bare pads. FH26 rotation: no correction applied (no rule in the plugin DB) — check in JLC's preview: the lock
(actuator) must be on the −x side, toward the board edge marked "PANEL FPC".

### Verification

```sh
cd hardware/knob/pcb/knob-screen
kicad-cli sch erc --severity-all knob-screen.kicad_sch                       # 0 violations
kicad-cli pcb drc --schematic-parity --severity-all knob-screen.kicad_pcb    # 0 violations, 0 unconnected, 0 parity issues
```

Rules: 0.15 mm track/clearance (3V3_LCD/GND 0.4 mm), vias 0.5–0.6/0.3 mm, copper-to-edge 0.3 mm. Routed by Freerouting 2.1
(with retries), GND poured on both layers with ~60 stitching vias.

### Risks / open points (Board C)

1. **Panel FPC pin order cannot be verified without the panel.** The pinout is Waveshare's; the connector is placed and
   oriented like theirs, so the order follows. Before powering a bare (AliExpress) panel: on its FPC, contacts 4 and 10
   (both GND) must be shorted to each other; if instead 22 and 28 are (= mirrored numbering), the panel/tail is different.
2. J1 position derived from a simplified 3D model (±1 mm). If the tail is short, the connector can't be moved later;
   a slack of ~0.5 mm was built in. Check with the real panel before ordering more than a few.
3. 13 thin wires carry 40–80 MHz QSPI with a single GND return. The 33Ω series resistors on board B help; if the
   display shows noise, lower the QSPI clock in firmware (e.g. 40 MHz) or add a second GND wire.
4. Bottom wire pads are SMD only (no holes, so nothing pokes up under J1); strain-relieve the bundle on the ScreenPlatform.
