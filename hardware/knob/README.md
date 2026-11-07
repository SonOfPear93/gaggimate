# GaggiMate Knob — hardware (rev 1)

A SmartKnob-style motorised haptic knob that replaces GaggiMate's round touchscreen
unit on a Gaggia Classic / Classic Pro. Design: [`docs/superpowers/specs/2026-11-07-smartknob-input-design.md`](../../docs/superpowers/specs/2026-11-07-smartknob-input-design.md).
Firmware: [`docs/knob-firmware.md`](../../docs/knob-firmware.md) (`pio run -e display-knob`).

**Status: rev 1 is designed but not built.** Every file passes its automated checks
(KiCad ERC/DRC, CAD interference check, firmware builds and unit tests), but nothing has
been fabricated, printed, assembled or powered. Expect a rev 2.

| Folder | What |
|---|---|
| [`pcb/knob-base`](pcb/knob-base) | Board A: Ø75 mm, 1.2 mm flexure board (press sensing), MT6701 encoder, HX711 |
| [`pcb/knob-main`](pcb/knob-main) | Board B: Ø74 mm, 4-layer main board, ESP32-S3, DRV8311H motor driver, power, USB-C |
| [`pcb/knob-screen`](pcb/knob-screen) | Board C: Ø46 mm adapter behind the 1.75" AMOLED (31-pin FPC) |
| [`pcb/README.md`](pcb/README.md) | Per-board details: parts + stock, pinouts, coordinates, risks |
| [`mechanical`](mechanical) | Printed parts (build123d → STEP/STL), renders, interference check, hardware list |

## What to buy

| Item | Notes |
|---|---|
| 3 PCB orders at JLCPCB (below) | Gerbers, BOM and CPL are in each board's `fab/` folder |
| 1.75" round AMOLED, 466×466, CO5300 + CST9217 touch, 31-pin 0.3 mm FPC | Guaranteed match: buy Waveshare's ESP32-S3-Touch-AMOLED-1.75 board (~US$45–68) and unclip its panel. A bare AliExpress panel only if its FPC pinout matches the table in the design doc |
| SparkFun ROB-20441 motor | You already have these |
| Screws, heat-set inserts, tape, wire | See [`mechanical/README.md`](mechanical/README.md#hardware): mostly M2, one M3 thumbscrew, 13 × 30 AWG wire |
| JST-SH 8-pin cable (~50 mm, same-end/pin-1-to-pin-1) | Board A ↔ board B |
| Filament | PETG or ASA (the top of the machine gets warm) |

## JLCPCB ordering notes and price estimate (5 of each board)

Bare-board prices are from JLCPCB's online quote today (7 Nov 2026), entered by size and
spec only (no files uploaded, nothing ordered). Assembly is calculated from JLCPCB's
published fees (Economic PCBA: $8.18 setup, $1.53 stencil, $3.07 per extended part)
plus the parts cost from each BOM. Treat it as ±25 %: the real number appears once the
Gerber/BOM/CPL are uploaded.

| Board | PCB spec | Bare (5) | Assembly + parts (5) | Est. total |
|---|---|---|---|---|
| A knob-base | 2-layer, 75×75, **1.2 mm**, HASL | $4 | ~$25 (bottom side only, see below) | **~$29** |
| B knob-main | 4-layer, 74×74, 1.6 mm, standard 3–4 day build | $8 | ~$86 (8 extended parts; J2 is through-hole: add JLC hand-soldering or fit it yourself) | **~$94** |
| C knob-screen | 2-layer, 46×46, 1.0 mm, **tented vias** | $4 | ~$14 | **~$18** |
| | | | Shipping (UPS, one combined order) | ~$27 |
| | | | **Total for 5 units** | **≈ $170 (≈ $34/unit)** |

Plus the panel (~$45–68 each), which costs more than all the electronics put together.

Watch for:
- **Board A has parts on both sides.** Only the MT6701 (U1, SOIC-8) and its capacitor
  (C20) are on the front. Cheapest: order Economic assembly of the **bottom side only**
  and hand-solder U1 + C20 (easy SOIC-8 / 0603). Full double-sided Standard assembly
  works too but costs about $75 more ($51 setup + $16 stencil).
- **Board C quote defaulted to a paid via-covering option** at 1.0 mm. Pick "Tented".
- **Board B quote defaulted to an expedited build time** for 4 layers. Pick the
  standard 3–4 day option ($0).
- In JLCPCB's placement preview, check rotations on: board B U1 (ESP32), U4
  (DRV8311H), J5/J8 (JST connectors), U3; board A J1, Q1, U4; board C J1 (FPC). The
  CPLs include a best guess for each.
- Stock was checked live today for the key parts: ESP32-S3-WROOM-1-N16R8 28k,
  DRV8311HRRWR 8.5k, FH26W-31S 9.6k, AP7361C-33ER-13 1.5k (backup: LDL1117S33R). The
  lowest-stock part on board A is the MT6701 (~5k in Sept); recheck before ordering.

## Build order (suggested)

1. Print the parts (see mechanical README for orientation and settings) and fit-check
   them against each other and on the machine's housing edge before soldering anything.
2. Board B alone on USB-C: check 3V3, flash `display-knob`, confirm USB serial logs.
3. Board C + panel on short wires to board B on the bench: confirm the display
   (orientation/offset may need a tweak in `GAGGIMATE_KNOB_AMOLED_175_HW_CONFIG`).
4. Board A + motor + MountBase, cabled to B: first boot runs motor calibration
   (the knob turns by itself briefly). Then hold BOOT 2–6 s for press calibration.
5. Thread the 13 screen wires down the MountBase tube, out through the 225° channel and
   board A's slot, onto board B's pads. Close up, mount on the machine, tighten the
   clamp.

## Top risks for rev 1

1. **Panel pinout/orientation:** follows Waveshare's schematic and 3D model; board C's
   connector position is good to ±1 mm.
2. **Press sensing:** the flexure is SmartKnob's, but the outline is round and it is
   clamped only at 4 screws. Sensitivity/noise need checking on hardware.
3. **Haptic feel:** the Ø66 knob ring has ~1.9× the inertia of SmartKnob's knob, and
   detent strengths are starting values.
4. **Thin parts of the case:** 1.55 mm wall around board A; the groove overhang needs a
   clean print.
5. **Depth:** ~61 mm vs ~37 mm for the stock unit, giving more lever on the groove when the
   knob is pressed. The thumbscrew clamp is meant to handle that, but it is untested.
6. **USB-C faces down** (toward the machine, in front of the housing edge) because
   the stack is rotated to keep the ESP32 antenna off the steel. Firmware also updates
   over Wi-Fi like stock GaggiMate.

## Credits and licences

Flexure, strain-gauge and encoder circuit, motor interface, RotorSpacer and parts of
the firmware come from [SmartKnob](https://github.com/scottbez1/smartknob) by Scott Bezek
(Apache-2.0 software/electronics, CC-BY-4.0 mechanical). GaggiMate is CC BY-NC-SA 4.0;
the housing groove profile comes from GaggiMate's case files. Panel pinout from
Waveshare's published ESP32-S3-Touch-AMOLED-1.75 schematic.
