// Detent / end-stop maths of the haptic knob, extracted from SmartKnob's motor
// task so it is hardware-free and unit-testable.
//
// Ported from smartknob firmware/src/motor_task.cpp
//   smartknob - Copyright 2022 Scott Bezek
//   Licensed under the Apache License, Version 2.0 (the "License"); you may not use
//   this file except in compliance with the License. You may obtain a copy of the
//   License at http://www.apache.org/licenses/LICENSE-2.0
//   Unless required by applicable law or agreed to in writing, software distributed
//   under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//   CONDITIONS OF ANY KIND, either express or implied. See the License for the
//   specific language governing permissions and limitations under the License.
// Modifications for GaggiMate: plain HapticConfig instead of nanopb, no
// detent_positions / snap_point_bias, rotation inversion handled by the caller
// (angles passed in are already in "knob" direction), idle correction uses the
// same (inverted) angle frame as the detent centre.
#pragma once

#include "HapticConfig.h"
#include <cstdint>

namespace knob {

class DetentModel {
  public:
    struct Output {
        float pidInput = 0.0f;     // angle error fed to the torque PID (radians)
        bool outOfBounds = false;  // pushing against an end stop
        bool torqueEnabled = true; // false when spinning too fast (runaway protection)
    };

    DetentModel();

    // Adopt a new config. `shaftAngle` is the current knob angle (radians, knob
    // direction). Returns false (and keeps the old config) if `config` is invalid.
    bool applyConfig(const HapticConfig &config, float shaftAngle);

    // One control-loop iteration (~1 kHz). Updates the detent position and
    // returns what the torque controller should do.
    Output update(float shaftAngle, float shaftVelocity, uint32_t nowMs);

    int32_t position() const { return currentPosition; }
    float subPositionUnit() const { return latestSubPositionUnit; }
    const HapticConfig &config() const { return cfg; }

    // Torque PID gains for the current state (SmartKnob: P = strength * 4).
    float proportionalGain(bool outOfBounds) const;
    float derivativeGain() const { return dGain; }

    // Discrete helper used by the simulator: step `position` by `delta` detents
    // honouring the config's end stops.
    static int32_t stepClamped(const HapticConfig &config, int32_t position, int32_t delta);

    static constexpr float MAX_VELOCITY_RAD_PER_SEC = 60.0f;

  private:
    HapticConfig cfg;
    int32_t currentPosition = 0;
    float currentDetentCenter = 0.0f;
    float latestSubPositionUnit = 0.0f;
    float idleVelocityEwma = 0.0f;
    uint32_t lastIdleStart = 0;
    float dGain = 0.0f;
};

} // namespace knob
