// Haptic knob configuration: the subset of SmartKnob's PB::SmartKnobConfig that
// GaggiMate needs, as a plain struct (no nanopb). Hardware-free; shared by the
// navigator (UI thread), the motor task (core 1), the simulator and the tests.
//
// Field semantics follow SmartKnob (Copyright 2022 Scott Bezek, Apache-2.0):
//  - position / minPosition / maxPosition: detent index and its end stops.
//    minPosition > maxPosition means "unbounded" (no end stops).
//  - positionNonce: bump it to force the motor to adopt `position` (and
//    re-centre the current detent on the shaft) even if the value is unchanged.
//  - positionWidthRadians: angle of one detent.
//  - detentStrengthUnit / endstopStrengthUnit: torque P gains (SmartKnob units).
//  - snapPoint: fraction of a detent width past which the position snaps to the
//    neighbour; must be >= 0.5 for stability (> 1 adds hysteresis).
#pragma once

#include <cstdint>

namespace knob {

constexpr float KNOB_PI = 3.14159265358979323846f;
constexpr float degToRad(float deg) { return deg * KNOB_PI / 180.0f; }

struct HapticConfig {
    int32_t position = 0;
    uint32_t positionNonce = 0;
    int32_t minPosition = 0;
    int32_t maxPosition = 0;
    float positionWidthRadians = degToRad(25.0f);
    float detentStrengthUnit = 0.0f;
    float endstopStrengthUnit = 1.0f;
    float snapPoint = 1.1f;

    bool bounded() const { return minPosition <= maxPosition; }

    // True when the two configs differ in anything but position/nonce, i.e. the
    // feel of the knob changes.
    bool sameShape(const HapticConfig &o) const {
        return minPosition == o.minPosition && maxPosition == o.maxPosition &&
               positionWidthRadians == o.positionWidthRadians && detentStrengthUnit == o.detentStrengthUnit &&
               endstopStrengthUnit == o.endstopStrengthUnit && snapPoint == o.snapPoint;
    }

    // Rejects configs SmartKnob's motor task would refuse (unstable or nonsensical).
    bool valid() const {
        return detentStrengthUnit >= 0.0f && endstopStrengthUnit >= 0.0f && snapPoint >= 0.5f && positionWidthRadians > 0.0f;
    }
};

// Initial haptic profiles from design §3 (to be tuned on hardware). Only the
// "shape" is set here; position/min/max are filled in by the navigator.
namespace haptics {

// Navigate: ~25° per item, strong detents, hard end stops.
inline HapticConfig navigate() {
    HapticConfig c;
    c.positionWidthRadians = degToRad(25.0f);
    c.detentStrengthUnit = 2.0f;
    c.endstopStrengthUnit = 1.5f;
    c.snapPoint = 0.55f;
    return c;
}

// Temperature: 1 °C per ~6°, medium detents.
inline HapticConfig temperature() {
    HapticConfig c;
    c.positionWidthRadians = degToRad(6.0f);
    c.detentStrengthUnit = 1.0f;
    c.endstopStrengthUnit = 1.0f;
    c.snapPoint = 1.1f;
    return c;
}

// Weight / time: 1 unit per ~5°, light detents.
inline HapticConfig weightTime() {
    HapticConfig c;
    c.positionWidthRadians = degToRad(5.0f);
    c.detentStrengthUnit = 0.4f;
    c.endstopStrengthUnit = 1.0f;
    c.snapPoint = 1.1f;
    return c;
}

// Profile: ~20° per profile, strong detents, end stops at first/last.
inline HapticConfig profile() {
    HapticConfig c;
    c.positionWidthRadians = degToRad(20.0f);
    c.detentStrengthUnit = 2.0f;
    c.endstopStrengthUnit = 1.5f;
    c.snapPoint = 0.55f;
    return c;
}

// Standby: free-ish rotation with light detents; any detent wakes the machine.
inline HapticConfig wake() {
    HapticConfig c;
    c.positionWidthRadians = degToRad(10.0f);
    c.detentStrengthUnit = 0.5f;
    c.endstopStrengthUnit = 1.0f;
    c.snapPoint = 1.1f;
    c.minPosition = 0;
    c.maxPosition = -1; // unbounded
    return c;
}

// A single locked position (turning does nothing, the knob springs back).
inline HapticConfig locked() {
    HapticConfig c;
    c.positionWidthRadians = degToRad(25.0f);
    c.detentStrengthUnit = 1.0f;
    c.endstopStrengthUnit = 1.0f;
    c.snapPoint = 0.55f;
    c.minPosition = 0;
    c.maxPosition = 0;
    return c;
}

} // namespace haptics
} // namespace knob
