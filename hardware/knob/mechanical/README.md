# GaggiMate Knob: printed parts

Parametric build123d model of the mechanical parts for the SmartKnob-style display
(see `docs/superpowers/specs/2026-11-07-smartknob-input-design.md`, §2, §5 and §6).
Written on 2026-11-07 while Ryan was away. **Nothing here has been printed or
test-fitted yet.** Every dimension is in `knobcad/params.py`.

![section](out/renders/section_3d_classic.png)

## Quick look (renders)

| File | What it shows |
|---|---|
| `out/renders/assembly_classic.png` | Assembled unit on a stand-in front panel, as it sits on the machine |
| `out/renders/assembly_exploded_classic.png` | Exploded stack |
| `out/renders/section_3d_classic.png` | 3D half-section through the centre |
| `out/renders/section_2d_x_classic.png`, `..._classic_pro.png` | Labelled 2D cross-section through the groove (x = 0) |
| `out/renders/section_2d_y_classic.png` | 2D cross-section across (y = 0) |
| `out/renders/section_2d_detail_knob.png` | Close-up of knob, panel, screen platform, motor |
| `out/renders/part_*.png` | Each printed part, front and back views |

## Parts

| Part | File (STEP / STL / print-oriented STL) | New or reused | Print |
|---|---|---|---|
| Knob ring | `out/step/knob_ring.step`, `out/stl/…`, `out/print/…` | new | front face down, no supports |
| Screen platform | `screen_platform` | new (replaces SmartKnob ScreenPlatform) | floor down, no supports |
| MountBase | `mount_base` | SmartKnob MountBase, re-modelled and modified (see below) | bottom down, no supports |
| RotorSpacer | `reused/RotorSpacer.stl` | **SmartKnob, unchanged** (v185 release) | as SmartKnob |
| Front case | `front_case` | new, Ø78.6 (stock GaggiMate `case_front` is Ø77.8) | front face down, no supports |
| Back case, Gaggia Classic | `back_case_classic` | new; groove profile copied from GaggiMate `case_back_gaggia_classic` | back face down, no supports |
| Back case, Classic Pro | `back_case_classic_pro` | same, groove from `case_back_gaggia_classic_pro` | back face down, no supports |

`out/standins/` holds the non-printed stand-ins used for the checks and renders (boards
A/B/C, panel, motor, RotorSpacer placed in the assembly, a 1 mm sheet in the groove, and
the wire-bundle envelope).

### Key dimensions

| | |
|---|---|
| Case Ø | 78.6 mm (stock GaggiMate is 77.8; widened for a 1.55 mm wall at board A) |
| Overall depth, knob face to back face | 61.4 mm (Classic), 59.6 mm (Classic Pro). Stock unit is ~37 mm. |
| Knob ring Ø | 66.0 mm, protrudes 13.25 mm from the case front face, straight knurl (60 flutes) |
| Knob ↔ case opening | 0.6 mm radial |
| Knob bore ↔ cover glass | 0.5 mm radial (Ø49.96 bore, Ø48.96 glass), glass flush with the knob face |
| Rotating ↔ stationary parts | ≥ 0.6 mm everywhere except the SmartKnob tube-in-shaft (0.2 mm, SK design) |
| Board A top → panel face | 32.25 mm |
| Board A ↔ board B | 8.0 mm (A bottom face to B top face) |
| Board B bottom → back-case floor | 4.2 mm |
| Front/back case seam | 8 mm in front of board A's top face |

Frames: `z = 0` is the top face of board A, `+z` points at the user. The back case's
groove is on `+y`, so on the machine world-up is about `-y` and the screen faces forward
and ~23° up (the stock unit's angle; it follows from the groove). The internal stack is
built in the PCB frame and rotated by `STACK_ROT = -90°` so that board B's ESP32 antenna
points sideways instead of down at the machine's sheet metal. Consequence for firmware:
**on the machine, "up" on the screen is board +X** (the direction of board A's alignment
hole H8).

## How it goes together

```
 knob ring ──press fit on──> RotorSpacer (SK) ──3x M1.6──> motor rotor
 panel ──tape ring──> screen platform <──glue── MountBase tube (through the motor's hollow shaft)
 board C ──3x M2──> screen platform
 MountBase + motor ──3x M1.6 from behind──> board A centre island (flexure)
 board A outer ring ──4x M2 + 2 pins──> front case deck bosses (front case clamps A, nothing behind the flexure)
 board B ──4x M2──> back-case posts
 front case ──3x radial M2──> back case (spigot inside the back case wall)
 back case ──groove + M3 thumbscrew──> machine front panel edge
```

### Design decisions (all open to change)

1. **Stack-up.** Same as SmartKnob from board A up to the rotor: MountBase 0–6 mm,
   motor base at 6, rotor 9.75–18.75, RotorSpacer top 20.25. Above that the screen
   platform starts 0.6 mm higher (20.85), board C sits on a ledge with a 2.5 mm pocket
   behind it for the 13 solder joints, and board C's front face is **5.70 mm behind the
   panel face, exactly as on Waveshare's ESP32-S3-Touch-AMOLED-1.75 carrier** (measured
   from their STEP). That way the panel's FPC tail, which is sized for that carrier, should
   reach board C's FH26 connector if the connector sits where Waveshare's J3 does.
2. **Knob ring** is a separate part pressed onto SmartKnob's unchanged RotorSpacer: its
   hub (bore Ø42) has five notches (1.7 mm wide) that take the spacer's five lobes, so
   the lobe tips centre it (Ø45, press fit, as SmartKnob's knob) and the notches key it.
   A one-piece knob would need supports. The ring is hollow from below (2 mm walls) so it
   prints support-free front face down. Its inertia is still ~1.9× SmartKnob's knob
   (14 200 vs 7 300 g·mm², solid material), which is part of the "haptics with a wider
   knob" risk in the spec.
3. **Screen platform** is carried by the MountBase tube, like SmartKnob's (its Ø5.6 socket
   slides over the Ø5.5 tube; glue it). It never touches the rotating parts. Its outer flank
   is a 45° cone parallel to the knob's bore chamfer, so both print without supports. The
   rim (r 23.2–24.38) carries the cover glass by its bezel on a tape ring; the rim is
   notched (14 mm) where the panel FPCs fold round the module edge. Three M2 inserts take
   board C's three holes (r 19.5, from `knob-screen.kicad_pcb`).
4. **MountBase** is SmartKnob's geometry (Ø30 × 6, Ø12.5 magnet pocket, MT6701 pocket,
   3× Ø1.8 holes, motor-wire slot), re-modelled so it can be changed. Changes: the
   wire channel (SmartKnob's 45° channel, which is 225° in board A's frame) now runs out
   through the side wall so the bundle can go over board A to its r = 33.5 mm slot along
   the same 225° ray; the tube is extended to 22.95 mm and its bore opened to Ø3.4 for
   13 wires (SmartKnob: Ø3.0 for 8); the light-shield flange is removed (no LEDs here, and
   it was a 6.5 mm overhang). Board A keeps SmartKnob's island wire hole (Ø3, r 10 at 225°)
   and island motor slot, so routing the wires through the island to board B instead
   of over the top also works with this MountBase.
5. **Front case** clamps board A's outer ring from the front: four Ø6 bosses with M2
   inserts at r 29.8, two Ø2 printed pins in the r 35 alignment holes, and a ring that rests
   on A's edge (r 35.6–37.55). Board A's top side only has U1 and C20 in the centre, so
   nothing else is touched. The flexure (island + arms, r < 24) has 2 mm free space behind
   it down to board B's tallest parts. The deck underside has an 8 mm channel along the
   225° ray for the wires. A 45° cone under the deck lets it print front face down.
6. **Front ↔ back join.** Board A (Ø75) and board B (Ø74) fill a Ø78.6 case almost
   completely, so no axial screw can pass from the back to the front without new holes in
   the boards. The front case therefore has a spigot that drops into the back case and
   three radial M2 button-head screws (60°, 180°, 300°) go through the back-case wall into
   heat-set inserts in the spigot. Twist-lock was rejected because the walls are too thin
   for lugs.
7. **Back case** holds board B on four posts with M2 inserts (r 33 at 22.5/112.5/202.5/292.5° in the board frame, per the updated spec; nothing stands between A and B). Below the floor it is the
   stock GaggiMate back block: the YZ profile of `case_back_gaggia_classic(_pro).stl`
   (chamfers, back face and the 1.4 mm groove at 23°) is copied exactly and only moved
   3.2 mm forward, so the unit sits on the machine exactly like the stock one. The block
   was solid in the stock part; here board B lives in the cavity above it.
8. **Housing clamp:** an M3 heat-set insert in the bottom face (the face that is horizontal
   on the machine, in front of the panel) and a thumbscrew that runs up at ~25–40° to the
   panel and presses on the outside of the sheet inside the groove, against the groove's
   inner tooth (Classic: right opposite the tooth; Pro: 12 mm below the groove end, where
   there is more material). Tightening it also pulls the unit down onto the panel edge.
   This is a reading of "pad on the sheet metal": the tooth side of the groove is inside
   the machine and cannot be reached once the unit is on, so the screw has to come from the
   outside.
9. **Controller cable** exits through a 20 × 8.5 mm duct straight under board B's J2
   (vertical JST-XH on B's bottom side) and out of the back face, behind and above the
   panel edge, i.e. into the machine.
10. **USB-C:** a 13 × 7 mm opening in the back-case wall in front of J1 (top-mounted HRO
    TYPE-C-31-M-12), on the underside of the unit when mounted.

## Hardware

| Qty | Item | Where |
|---|---|---|
| 14 | M2 heat-set insert, M2×3 (Ø3.2 hole) | front case 4 + 3 radial, back case 4, screen platform 3 |
| 1 | M3 heat-set insert, M3×5.7 (Ø4.0 hole) | back case, clamp |
| 4 | M2×5 button head (ISO 7380) | board A → front case, from behind A |
| 4 | M2×5 pan/button head | board B → back case posts |
| 3 | M2×4 button head (low head, ≤1.3 mm) | board C → screen platform (under the panel, 2.3 mm free) |
| 3 | M2×6 button head | back case → front case, radial |
| 3 | M1.6 × 8 (check against SmartKnob BOM) | board A + MountBase → motor base, from behind A |
| 3 | M1.6 flat head as in SmartKnob BOM | RotorSpacer → rotor |
| 1 | M3×20 (Classic) / M3×25 (Pro) knurled thumbscrew (DIN 464 or 653) | housing clamp; a TPU/felt cap on the tip protects the paint |
| 1 | double-sided tape ring, ~0.2 mm, OD 48.8 / ID 46.4 (e.g. 3M 467MP or thin VHB) | glass bezel → platform rim |
| | CA glue | platform socket on the tube; optionally knob on the spacer lobes |
| 13 | 30 AWG (or 32 AWG) wire, ~120 mm | screen wires through the Ø3.4 tube (13 × 30 AWG Kynar ≈ Ø2.1 bundle) |

## Print settings

PETG or ASA (the top of a Gaggia gets warm; PLA is not recommended for the back case).
0.4 mm nozzle, 0.2 mm layers (0.12–0.16 for knob and platform looks better), 3 walls
(4 for the knob), 15–20 % gyroid. Use the STLs in `out/print/`, already in print
orientation; none needs supports. Watch the groove: like the stock part its roof is a 67°
overhang. Check the 1.4 mm groove with the real panel edge and clean it up if it sagged.
FDM clearances used: 0.25 mm radial for parts that slide in (board A/B in the case),
0.2 mm for the spigot, 0.6 mm between rotating and stationary parts.

## Assembly order

1. Heat-set all inserts (front case 7, back case 5, platform 3).
2. Cut 13 screen wires (~120 mm). Thread them up through the MountBase channel and the
   tube. Motor wires: through the MountBase slot and board A's island slot (recommended),
   or along the channel with the screen wires.
3. MountBase + motor on board A: 3× M1.6 from behind board A. Check the MT6701 sits in the
   pocket under the magnet.
4. RotorSpacer on the rotor (3× M1.6, as SmartKnob).
5. Front case on board A: pins into H8/H9, 4× M2×5 from behind A. Lay the wire bundle in
   the deck channel and drop it through board A's slot.
6. Press the knob ring onto the spacer (lobes into the notches).
7. Screen platform over the tube end (wires through the socket), glue. Solder the wires to
   board C's back pads, screw board C down (3× M2×4), plug the panel FPC into J1, then tape
   the panel's bezel onto the rim.
8. Back case: controller cable up through the duct, plug into J2, board B on its posts
   (4× M2×5).
9. Solder the screen (and motor) wires to board B, plug the A–B JST-SH cable, fold the
   slack into the 8 mm gap, lower the front assembly into the back case and fit the three
   radial M2×6.
10. On the machine: slide the groove over the panel edge, tighten the thumbscrew.

## Rebuilding

```
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -r requirements.txt
.venv/bin/python build.py     # STEP + STL into out/
.venv/bin/python check.py     # interference + clearance report -> out/check_report.txt
.venv/bin/python render.py    # PNGs into out/renders/
```

Interference check result (rev 1, both variants): **no overlaps** between any two parts or
stand-ins (all pairs < 0.001 mm³); rotating ↔ stationary gaps ≥ 0.59 mm (0.6 nominal),
except the knob ↔ glass 0.5 mm (by spec) and the SmartKnob tube in the motor shaft (0.2 mm,
SmartKnob's own fit). See `out/check_report.txt`.

## Needs checking / open questions

- **Nothing is printed or fitted yet.** Print the knob ring, platform and MountBase first
  and test them on a real motor.
- **Motor details are assumed** where SmartKnob doesn't give them: shaft OD 8 and top at
  19.6, stator Ø28, ring magnet Ø12 × 2.25 under the stator. The parts that touch the
  motor (MountBase, RotorSpacer) are SmartKnob's, so this mostly affects the stand-ins.
  SmartKnob's own STLs suggest the hollow shaft turns with the rotor (the magnet hangs in
  the MountBase pocket); the platform therefore rides on the MountBase tube, not on the
  shaft, which works either way.
- **Knob ↔ RotorSpacer fit**: 1.7 mm notches on 1.4–1.6 mm lobes, lobe tips at Ø45 on a
  Ø45 seat. Any backlash will be felt in the detents; glue if it is loose.
- **Panel stack** (glass 1.10, module 2.05, folded FPC to 3.4 mm) is from Waveshare's STEP.
  Board C thickness is assumed 1.6 mm; the gap behind the panel is Waveshare's 3.65 mm.
- **Board positions:** board A from `hardware/knob/pcb/README.md` (final). Board B's
  holes are the updated spec values (r 33 at 22.5/112.5/202.5/292.5°); its J1 (USB-C), J2 (XH) and
  ESP32 positions and board C's holes (r 19.5 at 90/210/330°) are read from the work-in-progress
  KiCad files (knob-main.kicad_pcb still showed the old 45° holes when I read it). Re-run with updated values in
  `params.py` (`B_USB`, `B_XH`, `C_HOLE_*`) when the boards settle. Found in board B:
  - USB-C J1's mouth is ~2.7 mm inside board B's edge, so a plug probably cannot reach
    it through the wall. It should be flush with the edge.
  - J6 (1×3 2.54 mm vertical header) would stand 8.5 mm tall with pins fitted, more than
    the 8 mm A–B gap. Fit as pads only or use a right-angle header.
  - Tall parts on B's top under board A's four M2 screw heads (r 29.8, 0/90/180/270°)
    must stay below 6 mm (heads reach 2.2 mm below A's top face).
- **Back-case wall at board A is 1.55 mm** (Ø75 board in a Ø78.6 case) over an 8 mm
  band; the front-case spigot sits 0.2 mm behind it. `CASE_OD = 77.8` matches the stock
  diameter exactly but leaves only a 1.15 mm wall.
- **Depth:** 61 mm vs ~37 mm for the stock unit; more lever on the groove when the knob is
  pressed. The clamp should take it, but this needs a test on the machine.
- **Groove and clamp** reproduce the stock profile exactly but are unverified on a real
  Gaggia. It is also not verified that the back face behind the panel edge has room for
  the controller cable (the duct exits there); if not, move `B_XH` or cut a side exit.
- **Flexure support differs from SmartKnob.** SmartKnob's BackPlate has pads under the
  flexure arms from r 16 outward. Here board A is clamped only at its four screws from the
  front, with free space behind the whole flexure, so the arms work as fixed-guided beams.
  Fine for a load cell (and the firmware tares), but sensitivity will differ from
  SmartKnob. A pad plate behind A could be added later; it would need pockets for the
  four 2512 gauges, which are on A's back side.
- **Screen orientation:** world-up is board +X (see Frames).

## Credits and licences

- SmartKnob View by Scott Bezek, mechanical design **CC-BY-4.0**
  (<https://github.com/scottbez1/smartknob>, release `mechanical/v185`): `reused/RotorSpacer.stl`
  is unchanged; the MountBase is a modified re-model; the knob-to-spacer and
  platform-on-tube interfaces follow SmartKnob.
- GaggiMate by jniebuhr, **CC BY-NC-SA 4.0**: the back-case groove/back-block profile is
  copied from `case_back_gaggia_classic.stl` / `case_back_gaggia_classic_pro.stl`, and the
  case diameter and look follow `case_front.stl`. These parts are therefore CC BY-NC-SA 4.0
  as well.
- Waveshare ESP32-S3-Touch-AMOLED-1.75 drawing/STEP were used for the panel dimensions only.
