# GaggiMate Knob — firmware

Firmware half of the GaggiMate Knob (motorised haptic knob around a 1.75" 466×466 CO5300
AMOLED). Design and rationale: [`superpowers/specs/2026-11-07-smartknob-input-design.md`](superpowers/specs/2026-11-07-smartknob-input-design.md).
The knob firmware is the normal display firmware (screens, web UI, BLE scales, profiles…)
built with `-DGAGGIMATE_KNOB`; nothing knob-specific is compiled into the stock builds.

## Build and flash

```shell
pio run -e display-knob                    # build
pio run -e display-knob -t upload          # flash over the board's USB-C (native USB CDC)
pio run -e display-knob -t uploadfs        # web UI / LittleFS image, same as the stock display
pio device monitor -e display-knob         # logs (115200)
```

If the board doesn't enumerate, hold **BOOT**, tap **RESET**, release BOOT, then upload.
The env uses `boards/gaggimate-knob.json` (ESP32-S3-WROOM-1-N16R8: 16 MB QIO flash, 8 MB OPI
PSRAM) and adds SimpleFOC 2.3.3 (2.3.4+ needs arduino-esp32 3.x / IDF 5; this project is on
2.0.x). The HX711 is read by a small bit-banged reader, no library.

Desktop simulator with knob emulation (no hardware needed): see [Simulator](#simulator).

## First boot

1. **Motor calibration (automatic, ~15 s).** With nothing stored in NVS the motor task runs
   SmartKnob's calibration: it turns the knob by itself (direction, pole pairs, electrical
   zero). **Don't touch the knob while it moves.** Results are saved to NVS (`knob`
   namespace) and reused on every later boot. If it fails (log: `Calibration failed…`) the
   motor stays off and the knob still navigates, just without detents.
2. **Press + direction calibration (recommended once, guided, ~20 s).** Hold **BOOT** for
   2–6 s and release. A light click confirms the start, then:
   - hands off for 1 s (it measures the strain noise),
   - press the knob firmly **3 times** — a click confirms each press, a double click
     means the press threshold was saved,
   - turn the knob **clockwise about a quarter turn** — a double click confirms the
     direction (so clockwise = next item / higher value).
3. **Re-calibrate the motor** any time: hold **BOOT ≥ 6 s** and release.

Without step 2 the defaults apply (`pressDelta` 20000 counts, clockwise as on SmartKnob View);
the default press threshold is a guess, so do step 2 on every new unit.

## How the knob maps to the screens

Two modes (design §3). **Navigate**: turning moves the focus ring (accent-colour outline)
between items, one detent per item with end stops at first/last. **Edit**: turning changes
the value, one detent per step; the ring gets thicker and glows.

| Screen | Turn (navigate) | Short press | Long press (0.6 s) |
|---|---|---|---|
| Standby | any detent wakes (`action_on_wakeup`) | wake | wake |
| Menu | Brew → Steam → Water → Grind* → Info → Standby | open the item | — |
| Brew | Profile → Temperature → Target → **Start** (default) | Profile: open the profile chooser; Temperature/Target: edit (opens the adjustments view); Start: brew | back to menu |
| Brew – adjustments | Temperature → Target → Save* → Save as new* → Accept | Temperature/Target: edit; others: click | accept + close (like **✓**) |
| Brew – warning dialog | **Back** (default) → Ignore | click | Back |
| Status (brewing) | nothing (knob locked) | stop / done (`action_on_brew_cancel`) | back to menu (stops the brew) |
| Steam | Steam temperature | edit | back to menu |
| Water | Start/Stop | start/stop | back to menu |
| Grind | Target → **Start/Stop** (default) | Target: edit; Start/Stop | back to menu |
| Info | nothing | — | back to menu |
| Profile chooser | always editing: ±1 profile, end stops at first/last favourite | load profile | back to Brew without changing |

`*` only when shown/enabled (Grind needs a grinder configured, Save needs a dirty profile).
In Edit mode a short or long press leaves Edit mode. Edits call the existing handlers once
per detent (`action_on_brew_temp_raise/lower`, `action_on_brew_time_raise/lower`,
`action_on_steam_temp_raise/lower`, `action_on_grind_time_raise/lower`,
`action_on_next/previous_profile`), so limits, dirty-profile marking and BLE sync are
unchanged. Touch keeps working alongside the knob if the panel's touch layer is wired.

Haptics per state (initial values, `src/display/knob/HapticConfig.h`):

| State | Detent width | Detent strength | End stops |
|---|---|---|---|
| Navigate | 25° | 2.0 (strong) | 1.5, at first/last item |
| Temperature | 6° per °C | 1.0 (medium) | at the controller limits (0–160 °C) |
| Weight / time | 5° per unit | 0.4 (light) | none (the controller clamps) |
| Profile | 20° | 2.0 | first/last profile |
| Standby | 10° | 0.5 | none (any detent wakes) |
| Status / Info | locked single position | 1.0 | 1.0 |

Press: a 5 V torque "click" when the press registers, another when it becomes a long press.

## Tunables (NVS namespace `knob`)

| Key | Default | Meaning |
|---|---|---|
| `mcal`, `zea`, `sdir`, `pp` | — | motor calibration (calibrated flag, zero electrical angle, sensor direction, pole pairs) |
| `inv` | `true` | knob angle sign (clockwise = increase); set by the guided calibration |
| `pdelta` | 20000 | HX711 counts of a firm press (signed = bridge polarity); set by the guided calibration |
| `pon` / `poff` | 1.0 / 0.5 | press / release thresholds as a fraction of `pdelta` (hysteresis) |
| `plong` | 600 | long-press time, ms |
| `pdeb` | 2 | consecutive HX711 samples needed to change state |

Compile-time constants: motor PID/voltage in `MotorTask.h` (SmartKnob's ROB-20441 values,
5 V limit), press lock-out while turning (200 ms after a detent / 4 rad/s) and drift handling
(running tare while idle, re-tare after an 8 s "press") in `MotorTask.cpp` /
`PressClassifier.h`. There's no on-device settings UI for these (non-goal); change them in
code, or via the guided calibration above.

## Code map

| File | What |
|---|---|
| `src/display/knob/KnobPins.h` | every knob GPIO (design §5) |
| `src/display/drivers/AmoledDisplay/pin_config.h` | `GAGGIMATE_KNOB_AMOLED_175_HW_CONFIG` (variant index 3, appended; selected directly by the knob build, never probed by stock builds) |
| `KnobNavigator.*` | pure interaction model: focus lists, modes, actions, haptic configs |
| `DetentModel.*` | pure detent/end-stop maths ported from SmartKnob's motor task |
| `PressClassifier.*` | pure HX711 press classifier, press timer, guided press calibrator |
| `KnobUi.*` | LVGL glue on the UI task: screen detection, actions → `action_*`, focus ring |
| `MotorTask.*`, `MT6701Sensor.*`, `HX711Reader.h` | hardware: SimpleFOC loop on core 1 (prio 2, ~1 kHz), MT6701 SSI, HX711 |
| `KnobPlugin.*` | starts the motor task, NVS persistence, BOOT-button gestures |
| `test/test_knob` | Unity tests for the pure parts: `pio test -e native -f test_knob` |
| `sim/driver/SimKnob.*` | simulator knob emulation |

Threading: the motor task (core 1) sends absolute detent positions (tagged with the haptic
config's nonce) and press events through a FreeRTOS queue; `KnobUi::loop` drains it on the
LVGL task (also core 1, prio 1, called from `DefaultUI::loop`), so every UI mutation happens
where touch input would. New haptic configs go back through a 1-deep overwrite queue.
Position reports carrying an older nonce are dropped, so nothing is misapplied across a
screen change.

## Simulator

`pio run -e display-sim -t run`, then:
- mouse wheel up / **→** = one detent clockwise, wheel down / **←** = counter-clockwise,
- **Enter** = press, hold **Enter ≥ 0.6 s** = long press.

The knob emulation switches on with the first knob key (or `--knob`), so the stock sim
looks unchanged until you use it. Scripted, headless capture:

```shell
SDL_VIDEODRIVER=offscreen ./.pio/build/display-sim/program \
  --knob-script "s.r.sll.sp.rr.s" --knob-shots /tmp/knob
# r/l = turn, p = press, P = long press, . = wait, s = screenshot (/tmp/knob-<n>.bmp)
```

## Known gaps / untested

- **Nothing here has run on knob hardware yet** (no boards exist). Untested: SimpleFOC on the
  DRV8311H in 3x-PWM mode with one shared enable, MT6701 SSI timing, the HX711 wiring,
  calibration on the real motor, haptic feel, and the 1.75" panel on the new pin map.
- DRV8311H: assumes the hardware strap selects 3x-PWM mode (INHx PWM, INLx = DRV_EN) and
  that a ~30 µs nSLEEP low pulse clears latched faults; current-sense outputs are unused.
- The normal Brew view has no temperature/target widget of its own; while those are
  focused the ring sits on the temperature readout / target-mode switch, and pressing opens
  the adjustments view.
- Steam has no start/stop control in the stock UI (single-boiler steam follows the machine
  switch), so the Steam focus list is the temperature only.
- Weight/time edits have no end stops on the knob (the controller clamps the value).
- Panel orientation: `rotation_175 = 0` and the GRAM offsets / touch mirroring are copied
  from the Waveshare 1.75" board; if the panel is mounted rotated, change `rotation_175` in
  `GAGGIMATE_KNOB_AMOLED_175_HW_CONFIG`.
- No firmware OTA concerns specific to the knob; `display-knob` firmware is not part of
  the release scripts.
- Haptic profile values and press defaults are SmartKnob starting points, to be tuned.
