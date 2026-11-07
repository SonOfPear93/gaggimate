// Ported from smartknob firmware/src/motor_task.cpp
//   smartknob - Copyright 2022 Scott Bezek
//   Licensed under the Apache License, Version 2.0 (the "License"); you may not use
//   this file except in compliance with the License. You may obtain a copy of the
//   License at http://www.apache.org/licenses/LICENSE-2.0
//   Unless required by applicable law or agreed to in writing, software distributed
//   under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//   CONDITIONS OF ANY KIND, either express or implied. See the License for the
//   specific language governing permissions and limitations under the License.
// See DetentModel.h for the GaggiMate modifications.
#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB_LOGIC

#include "DetentModel.h"

#include <algorithm>
#include <cmath>

namespace knob {

static constexpr float DEAD_ZONE_DETENT_PERCENT = 0.2f;
static constexpr float DEAD_ZONE_RAD = 1.0f * KNOB_PI / 180.0f;

static constexpr float IDLE_VELOCITY_EWMA_ALPHA = 0.001f;
static constexpr float IDLE_VELOCITY_RAD_PER_SEC = 0.05f;
static constexpr uint32_t IDLE_CORRECTION_DELAY_MILLIS = 500;
static constexpr float IDLE_CORRECTION_MAX_ANGLE_RAD = 5.0f * KNOB_PI / 180.0f;
static constexpr float IDLE_CORRECTION_RATE_ALPHA = 0.0005f;

template <typename T> static T clampValue(T v, T lo, T hi) { return v < lo ? lo : (v > hi ? hi : v); }

DetentModel::DetentModel() {
    // SmartKnob's boot config: two positions, 60° wide, no detent torque.
    cfg.position = 0;
    cfg.minPosition = 0;
    cfg.maxPosition = 1;
    cfg.positionWidthRadians = degToRad(60.0f);
    cfg.detentStrengthUnit = 0.0f;
    cfg.endstopStrengthUnit = 1.0f;
    cfg.snapPoint = 1.1f;
}

bool DetentModel::applyConfig(const HapticConfig &newConfig, float shaftAngle) {
    if (!newConfig.valid())
        return false;

    bool positionUpdated = false;
    if (newConfig.position != cfg.position || newConfig.positionNonce != cfg.positionNonce) {
        currentPosition = newConfig.position;
        positionUpdated = true;
    }

    if (newConfig.bounded()) {
        currentPosition = clampValue(currentPosition, newConfig.minPosition, newConfig.maxPosition);
    }

    if (positionUpdated || newConfig.positionWidthRadians != cfg.positionWidthRadians) {
        const float newSubPosition = positionUpdated ? 0.0f : latestSubPositionUnit;
        currentDetentCenter = shaftAngle + newSubPosition * newConfig.positionWidthRadians;
    }
    cfg = newConfig;

    // Derivative factor of the torque controller, piecewise linear in detent width:
    // fine detents need some D to "click", coarse detents get little D (sensor noise).
    const float derivativeLowerStrength = cfg.detentStrengthUnit * 0.08f;
    const float derivativeUpperStrength = cfg.detentStrengthUnit * 0.02f;
    const float derivativePositionWidthLower = degToRad(3.0f);
    const float derivativePositionWidthUpper = degToRad(8.0f);
    const float raw = derivativeLowerStrength + (derivativeUpperStrength - derivativeLowerStrength) /
                                                    (derivativePositionWidthUpper - derivativePositionWidthLower) *
                                                    (cfg.positionWidthRadians - derivativePositionWidthLower);
    dGain = clampValue(raw, std::min(derivativeLowerStrength, derivativeUpperStrength),
                       std::max(derivativeLowerStrength, derivativeUpperStrength));
    return true;
}

float DetentModel::proportionalGain(bool outOfBounds) const {
    return (outOfBounds ? cfg.endstopStrengthUnit : cfg.detentStrengthUnit) * 4.0f;
}

DetentModel::Output DetentModel::update(float shaftAngle, float shaftVelocity, uint32_t nowMs) {
    // When idle and close to (but not exactly at) the detent centre, slowly move the
    // centre to the resting angle so the knob doesn't fight a small offset forever.
    idleVelocityEwma = shaftVelocity * IDLE_VELOCITY_EWMA_ALPHA + idleVelocityEwma * (1.0f - IDLE_VELOCITY_EWMA_ALPHA);
    if (std::fabs(idleVelocityEwma) > IDLE_VELOCITY_RAD_PER_SEC) {
        lastIdleStart = 0;
    } else if (lastIdleStart == 0) {
        lastIdleStart = nowMs == 0 ? 1 : nowMs;
    }
    if (lastIdleStart > 0 && nowMs - lastIdleStart > IDLE_CORRECTION_DELAY_MILLIS &&
        std::fabs(shaftAngle - currentDetentCenter) < IDLE_CORRECTION_MAX_ANGLE_RAD) {
        currentDetentCenter = shaftAngle * IDLE_CORRECTION_RATE_ALPHA + currentDetentCenter * (1.0f - IDLE_CORRECTION_RATE_ALPHA);
    }

    // Where are we relative to the nearest detent? Snap to the neighbour once past the snap point.
    float angleToDetentCenter = shaftAngle - currentDetentCenter;
    const float width = cfg.positionWidthRadians;
    const float snapPointRadians = width * cfg.snapPoint;
    const bool bounded = cfg.bounded();

    if (angleToDetentCenter > snapPointRadians && (!bounded || currentPosition > cfg.minPosition)) {
        currentDetentCenter += width;
        angleToDetentCenter -= width;
        currentPosition--;
    } else if (angleToDetentCenter < -snapPointRadians && (!bounded || currentPosition < cfg.maxPosition)) {
        currentDetentCenter -= width;
        angleToDetentCenter += width;
        currentPosition++;
    }

    latestSubPositionUnit = -angleToDetentCenter / width;

    const float deadZoneAdjustment = clampValue(angleToDetentCenter, std::max(-width * DEAD_ZONE_DETENT_PERCENT, -DEAD_ZONE_RAD),
                                                std::min(width * DEAD_ZONE_DETENT_PERCENT, DEAD_ZONE_RAD));

    Output out;
    out.outOfBounds = bounded && ((angleToDetentCenter > 0 && currentPosition == cfg.minPosition) ||
                                  (angleToDetentCenter < 0 && currentPosition == cfg.maxPosition));
    out.torqueEnabled = std::fabs(shaftVelocity) <= MAX_VELOCITY_RAD_PER_SEC;
    out.pidInput = -angleToDetentCenter + deadZoneAdjustment;
    return out;
}

int32_t DetentModel::stepClamped(const HapticConfig &config, int32_t position, int32_t delta) {
    int64_t next = static_cast<int64_t>(position) + delta;
    if (config.bounded()) {
        next = clampValue<int64_t>(next, config.minPosition, config.maxPosition);
    }
    return static_cast<int32_t>(next);
}

} // namespace knob

#endif // GAGGIMATE_KNOB_LOGIC
