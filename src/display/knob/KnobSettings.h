// Persistent knob settings (motor calibration, rotation direction, press
// thresholds). Stored in NVS namespace "knob" by KnobPlugin (Preferences).
#pragma once

#include "PressClassifier.h"
#include <cstdint>

namespace knob {

struct KnobSettings {
    // Motor calibration (SimpleFOC): found automatically on first boot.
    bool motorCalibrated = false;
    float zeroElectricAngle = 0.0f;
    int8_t sensorDirection = 1; // 1 = CW, -1 = CCW (SimpleFOC Direction)
    uint8_t polePairs = 7;      // SparkFun ROB-20441 / Wanzhida OT-EM3215D2450Y1R: 7 pole pairs

    // Knob angle sign (SmartKnob's SK_INVERT_ROTATION, true on the MT6701 "view"
    // stack this board copies). Chosen so turning clockwise increases the position;
    // the guided press calibration measures it.
    bool invertRotation = true;

    PressSettings press;
};

#ifdef GAGGIMATE_KNOB
// NVS persistence (knob board only).
KnobSettings loadKnobSettings();
void saveKnobSettings(const KnobSettings &settings);
#endif

} // namespace knob
