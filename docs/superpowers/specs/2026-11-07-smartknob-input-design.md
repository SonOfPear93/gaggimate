# GaggiMate Knob — design (rev 1)

Status: rev 1 design, written 2026-11-07. Owner: Ryan (SonOfPear93). Decisions marked
**[Claude's call]** were made while Ryan was away and are open to change.

## 1. Intent

Replace GaggiMate's round touchscreen unit with a SmartKnob-style motorised knob: a
detented, force-feedback knob with a press-to-confirm, wrapped around a stationary round
screen. Adjusting brew temperature, target weight/time, steam temperature and moving
through menus should feel like turning a good physical dial instead of tapping small
`+`/`−` targets. Prior art: [SmartKnob View](https://github.com/scottbez1/smartknob)
(Scott Bezek, Apache-2.0 software/electronics, CC-BY-4.0 mechanical).

### Goals
- A drop-in replacement for the GaggiMate display unit on a **Gaggia Classic**: same spot
  on the machine, powered from the same controller cable, talks to the unmodified
  GaggiMate controller over BLE exactly as the stock display does.
- Looks as close as possible to the stock unit: **round, ~78 mm across**.
- Knob turns change values with software-defined detents; pressing the knob confirms.
- PCBs are fabricated and assembled by **JLCPCB** using cheap, well-stocked parts.
- Firmware is a fork of GaggiMate's display firmware (the existing screens, web UI,
  BLE scales, profiles, etc. all keep working) with the knob as the input device.

### Non-goals (rev 1)
- No changes to the GaggiMate controller board or its firmware.
- No new settings UI on the device: deep configuration stays in the web UI.
- No watch glass over the screen (the touch panel's own cover glass is the front face).
- No LED ring (SmartKnob's SK6812s) and no ambient light sensor.

### Anti-goals (would be a failure even if it "works")
- The unit rocks or flexes on the machine when pressed or when detents kick.
- Press detection that is mushy or triggers while turning.
- A design that depends on parts JLCPCB is likely to run out of.
- Breaking the stock GaggiMate builds (`display`, `controller`, `display-sim`, tests).

## 2. Architecture overview

```
           ┌──────────── front ────────────┐
 knob ring (rotates, ~66 mm OD) around a stationary 1.75" AMOLED (466×466, CO5300, touch)
           │  screen adapter PCB "C" on the stationary ScreenPlatform
           │  13 thin wires down the motor's 5.9 mm hollow shaft
 SparkFun ROB-20441 gimbal motor (32 mm, hollow shaft, diametric magnet)
           │  MountBase (SmartKnob part)
 knob-base PCB "A" (Ø75 mm, 1.2 mm, strain flexure, MT6701 under motor, HX711)
           │  8-pin JST-SH cable
 main PCB "B" (Ø≤75 mm, ESP32-S3-WROOM-1-N16R8, DRV8311H motor driver, USB-C, power)
           │  4-pin JST-XH from GaggiMate controller (5 V + GND only)
 back case (grips the machine housing edge firmly: groove + clamp screw)
           └──────────── back ─────────────┘
```

Why two main boards **[Claude's call]**: the press sensor *is* the PCB (a flexure cut into
the board with SMD resistors as strain gauges, ~58 mm across). On a Ø75 mm round board the
rigid ring outside the flexure is only ~7 mm wide, too narrow for the ESP32-S3 module.
So the flexure board keeps only the sensors, and everything else lives on a second
board behind it. Motor phase wires and screen wires go straight to board B.

Why the 1.75" CO5300 AMOLED **[Claude's call]**: GaggiMate already drives 466×466
CO5300 QSPI panels (`src/display/drivers/AmoledDisplay`), and its UI is laid out for
~480×480. A 240×240 GC9A01 (SmartKnob's screen) would mean redoing every screen layout.
1.75" (~44 mm active) is also the largest panel that leaves a usable knob ring inside a
~78 mm unit. Fallback: a 1.43" 466×466 panel (also supported by GaggiMate) if the
1.75" panel's pinout cannot be pinned down.

Why DRV8311H instead of SmartKnob's TMC6300 **[Claude's call]**: TMC6300 showed 38 units
in JLC stock; DRV8311HRRWR (3–20 V, 5 A, WQFN-24) showed ~3.5k at $1.50 and runs from
5 V like the TMC6300.

## 3. Interaction design

Two knob modes, LVGL "encoder" style, with the haptics changing per mode:

| Action | Navigate mode | Edit mode |
|---|---|---|
| Turn | move focus between items on the screen, one detent per item, end stops at first/last | change the value, one detent per step, end stops at min/max |
| Short press | activate the focused item (button → click; value → enter Edit mode) | leave Edit mode |
| Long press (~0.6 s) | back to the menu screen (or cancel a dialog) | leave Edit mode |

Value edits call the existing controller functions once per detent
(`raiseTemp()/lowerTemp()`, `raiseBrewTarget()/lowerBrewTarget()`,
`raiseSteamTemp()/lowerSteamTemp()`, `raiseGrindTarget()/lowerGrindTarget()`,
next/previous profile), so all existing logic (limits, dirty-profile marking, BLE sync)
is reused unchanged.

Per-screen focus lists (rev 1):

| Screen | Focus items (turn order) | Edit step |
|---|---|---|
| Standby | any turn or press wakes (`action_on_wakeup`) | — |
| Menu | Brew, Steam, Water, Grind, Info, Standby (Settings is web-only) | — |
| Brew | Profile, Temperature, Target (weight or time), Start | profile ±1, 1 °C, 1 g / 1 s |
| Brew – running | press = stop; turn = nothing | — |
| Brew – settings/dirty | Temperature, Target, Save, Save as new, Accept | as above |
| Steam | Steam temperature, Start/Stop | 1 °C |
| Water | Start/Stop | — |
| Grind | Target, Start/Stop | 1 s / 0.5 g |
| Warning dialog | Back, Ignore | — |
| Info | long press = back | — |

The focused item gets a visible highlight (outline/glow in the theme accent colour).

Haptic profiles (initial values, tuned on hardware later):
- Navigate: ~25° per item, strong detents, hard end stops.
- Temperature: 1 °C per ~6°, medium detents; end stops at the controller's limits.
- Weight/time: 1 unit per ~5°, light detents.
- Profile: ~20° per profile, strong detents, end stops at first/last profile.
- A wake/press "click" is a short torque pulse.

## 4. Firmware

- New PlatformIO env `display-knob` (board JSON for ESP32-S3-WROOM-1-N16R8:
  16 MB QIO flash, 8 MB OPI PSRAM). Existing envs must still build.
- Display: reuse `AmoledDisplayDriver` / `Amoled_DisplayPanel` / `CO5300` with a new
  `AmoledHwConfig` for this board (append to `VARIANTS`, never reorder — indices are
  persisted in NVS). Touch is optional (works if wired, not required).
- New `KnobPlugin` (or `core/knob/`) containing:
  - `MotorTask`: FOC loop on its own FreeRTOS task pinned to core 1, ported from
    SmartKnob `firmware/src/motor_task.cpp` (Apache-2.0, keep attribution), SimpleFOC
    (`askuric/Simple FOC`), `BLDCDriver3PWM` on the DRV8311H, MT6701 over SSI (port
    SmartKnob's `mt6701_sensor.cpp`). Motor calibration (direction, pole pairs, zero
    electrical angle) runs automatically on first boot and is stored in Preferences.
  - Press detection: HX711 read continuously; running-baseline tare while idle;
    press/long-press thresholds stored in Preferences with defaults.
  - Haptic config struct (positions, min/max, detent width/strength, end-stop strength)
    analogous to SmartKnob's `PB::SmartKnobConfig`, without nanopb.
  - `KnobNavigator`: owns the per-screen focus lists in §3, receives detent and press
    events from the motor task (thread-safe queue), drives the UI on the LVGL thread,
    and pushes a new haptic config whenever the screen, focus or mode changes.
- Pure logic (navigator state machine, detent maths, press classifier) is
  hardware-free and covered by Unity tests in the `native` env.
- `display-sim`: keyboard/mouse-wheel emulation of the knob (wheel/arrow = turn,
  Enter = press, hold Enter = long press) so the navigation can be checked visually.

## 5. Electronics

GPIO map for the ESP32-S3-WROOM-1-N16R8 (GPIO 35–37 are used by OPI PSRAM; 0, 3, 45, 46
are strapping pins; 19/20 are USB):

| GPIO | Signal | Notes |
|---|---|---|
| 1 | DRV_SOA | current-sense out A (ADC1), optional/unused in rev 1 firmware |
| 2 | DRV_SOB | current-sense out B (ADC1), optional |
| 3 | DRV_nFAULT | input, 10 k pull-up to 3V3 |
| 4 | DRV_INHA | PWM phase A |
| 5 | DRV_INHB | PWM phase B |
| 6 | TP_SCL | touch I2C, 4.7 k pull-up |
| 7 | TP_SDA | touch I2C, 4.7 k pull-up |
| 8 | TP_RST | touch reset |
| 9 | TP_INT | touch interrupt |
| 10 | LCD_CS | QSPI |
| 11 | LCD_D0 | QSPI |
| 12 | LCD_CLK | QSPI |
| 13 | LCD_D1 | QSPI |
| 14 | LCD_D2 | QSPI |
| 15 | LCD_D3 | QSPI |
| 16 | LCD_RST | panel reset |
| 17 | LCD_EN | high = panel power on (load switch on board B) |
| 18 | DRV_INHC | PWM phase C |
| 19 / 20 | USB D− / D+ | native USB (flashing, logs) |
| 21 | DRV_nSLEEP | high = driver awake, 100 k pull-down |
| 38 | ENC_CS | MT6701 SSI chip select |
| 39 | ENC_CLK | MT6701 SSI clock |
| 40 | ENC_DO | MT6701 SSI data |
| 41 | HX_SCK | HX711 clock |
| 42 | HX_DOUT | HX711 data |
| 43 / 44 | U0TXD / U0RXD | test pads |
| 47 | DRV_EN | drives all three INLx (enable/Hi-Z) in 3x PWM mode |
| 48 | STATUS_LED | optional single LED |
| 0 | BOOT | button to GND |

The hardware builder may change this map if the DRV8311H's pin modes require it, but
must update this table and the firmware `AmoledHwConfig`/knob pin header together.

### Board A — knob base ("knob-base")
- Ø75 mm round, **1.2 mm FR4** (the flexure depends on it), white mask not required.
- Centre region copied from SmartKnob `electronics/view_base` (geometry and footprints):
  flexure slot cut-outs, 3× M1.6 motor/MountBase holes (r ≈ 10.3 mm), MT6701CT (SOIC-8)
  exactly at the centre under the motor magnet, SMD strain-gauge resistor bridge on the
  flexure arms, HX711 and its passives on the rigid outer ring.
- Mounting: 4× M2 holes at r = 29.8 mm on 0°/90°/180°/270° and 2× Ø2.2 alignment holes
  at r = 35 mm on 0°/180°, exactly as SmartKnob's view_base (H4–H9), so the board
  clamps to the front case at the same points SmartKnob's back plate does.
- A hole/slot so the 13 screen wires and 3 motor wires can pass through to board B.
- Connector to board B: JST-SH 8-pin (3V3, GND, ENC_CS, ENC_CLK, ENC_DO, HX_SCK,
  HX_DOUT, GND).

### Board B — main ("knob-main")
- Ø74 mm round, 1.6 mm, 4× M2 mounting holes at r = 33 mm on 45°/135°/225°/315°.
  Max component height 6 mm on top (facing board A), 3 mm on the bottom except
  connectors; board A–B spacing is set by the mechanical design (target 8 mm).
- ESP32-S3-WROOM-1-N16R8 with the antenna overhanging/at the board edge with the
  standard copper keep-out; BOOT and RESET buttons; USB-C (USB 2.0, ESD protected,
  5.1 k CC pull-downs) for flashing and bench power.
- Power: 5 V from the GaggiMate controller cable (JST-XH 4-pin, same pinout as the stock
  display connector on the GaggiMate PCB; only 5 V/GND used) OR USB-C, diode-ORed.
  3.3 V ≥ 800 mA LDO for ESP32 + panel. Panel 3V3 behind a load switch on LCD_EN.
- DRV8311H from 5 V, bulk + ceramic decoupling, 3× motor phase pads/connector,
  3x PWM mode (INHx = PWM, INLx tied to DRV_EN).
- Connector to board A (JST-SH 8-pin) and 13 solder pads for the screen wires
  (3V3_LCD, GND, LCD_CS, LCD_CLK, LCD_D0–D3, LCD_RST, TP_SDA, TP_SCL, TP_INT, TP_RST).

### Board C — screen adapter ("knob-screen")
- Small round board on the stationary ScreenPlatform behind the panel, ≤ the panel's
  outline. FPC connector matching the chosen panel's tail, any extra rails the panel
  needs (e.g. 1.8 V IO, AMOLED supply), decoupling, and 13 solder pads matching board B.
- **Panel [Claude's call]:** the 1.75" CO5300 + CST9217 466×466 panel used on Waveshare's
  ESP32-S3-Touch-AMOLED-1.75. Its pinout is published in Waveshare's schematic
  (connector J3, Hirose FH26-31S-0.3SHW, 31 pins, 0.3 mm pitch, bottom contact).
  Guaranteed source: buy that Waveshare board (~US$45–68) and unplug the panel. Bare
  panels with the same 31-pin tail are sold on AliExpress, but check the pinout first.
  Panel mechanics (Waveshare drawing): cover glass Ø48.96 mm, view area Ø44.16 mm,
  active area Ø43.76 mm, glass + panel stack 2.05 mm thick, FPC tail exits one edge and
  folds behind. Waveshare's own carrier PCB behind the panel is Ø46 mm.
- Panel FPC pinout (J3 on the Waveshare schematic):

  | Pin | Net | Pin | Net |
  |---|---|---|---|
  | 0 (shell), 1, 4, 7, 10, 20, 25, 31 | GND | 21, 22, 23, 24, 26 | 3V3 (panel makes its own AMOLED rails) |
  | 2, 3, 5, 6, 8, 9, 19 | NC | 11 | LCD_TE (not routed in rev 1, pad only) |
  | 12 | QSPI D2 | 13 | QSPI D3 |
  | 14 | QSPI CLK | 15 | QSPI D1 |
  | 16 | QSPI D0 | 17 | LCD_CS |
  | 18 | LCD_RESET | 27 | TP_SCL |
  | 28 | TP_SDA | 29 | TP_RESET |
  | 30 | TP_INT | | |

- Connector on board C: FH26W-31S-0.3SHW(60), LCSC C2973806 (~10k in stock).
- Board C is Ø46 mm (same as Waveshare's carrier) with 13 wire pads near the centre so
  the bundle drops straight down the motor shaft.

### Parts policy
- Prefer JLC **Basic** parts; Extended parts only where needed (ESP32, DRV8311H, MT6701,
  HX711, connectors). Every part must show healthy stock in the JLC parts database
  (kicad-jlcpcb-tools DB, refreshed if stale) — target ≥ 10× the build quantity.
- Fab outputs per board: Gerbers + drill, BOM and CPL in JLC format (generated with
  kicad-jlcpcb-tools or kicad-cli), plus a JLC price estimate (website quote only; **no
  orders, no contacting anyone**).

## 6. Mechanics

All parts 3D-printable (PLA/PETG), designed parametrically (build123d/CadQuery), exported
as STEP + STL with PNG renders.
- Reuse SmartKnob's `MountBase` and `RotorSpacer` where the motor interface is identical.
- New knob ring: ~66 mm OD, attaches to the rotor like SmartKnob's knob, inner bore
  clears the stationary panel by ~0.5 mm; panel face flush with the knob face.
- New ScreenPlatform: holds board C + panel (panel taped to the platform by its bezel),
  fixed to the motor's stationary hollow shaft, wire channel down the shaft.
- Front case: Ø77.8 mm, same outer look as the GaggiMate `case_front`.
- Back case for the Gaggia Classic (and Classic Pro variant): GaggiMate's housing-edge
  groove plus a clamp (screw pressing a pad against the inside of the sheet metal) so
  pressing and haptic torque do not rock the unit; holds board B, cable exit for the
  controller cable.

## 7. Rev 1 acceptance

- Fork builds: `display`, `display-knob`, `controller`, `display-sim`; `pio test -e native`
  passes including new knob tests.
- Simulator shows knob navigation across all screens in §3.
- Three KiCad 10 projects pass ERC/DRC with no errors; fab outputs + BOM/CPL exist; every
  BOM line has an LCSC part with stock noted; a JLC price estimate is recorded.
- STEP/STL for all printed parts with renders; parts fit-checked against each other in an
  assembly render.
- A README in `hardware/knob/` covering build order, wiring, flashing, calibration and
  known risks.

## 8. Licensing

GaggiMate is CC BY-NC-SA 4.0. SmartKnob software/electronics are Apache-2.0 and
mechanical CC-BY-4.0; ported files keep their copyright headers and the hardware README
credits Scott Bezek. This fork is for personal use.

## 9. Known risks
- Panel pinout/sourcing for a bare 1.75" CO5300 panel (mitigation: fallback 1.43").
- FOC loop and LVGL/BLE/WiFi sharing the ESP32-S3 (mitigation: FOC task on core 1 at
  high priority; GaggiMate's Arduino loop runs on core 0).
- Haptic strength with a wider knob ring (≈ 66 mm vs SmartKnob's 51 mm).
- Strain flexure behaviour on a round outline is untested (geometry copied from
  SmartKnob, only the outer outline changes).
