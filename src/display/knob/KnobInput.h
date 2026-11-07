// The boundary between a knob "device" (the motor task on the knob board, or the
// keyboard/mouse emulation in the simulator) and the UI-thread navigator glue.
#pragma once

#include "HapticConfig.h"
#include "KnobNavigator.h"
#include <cstdint>

namespace knob {

struct KnobEvent {
    enum class Type : uint8_t { Position, Press };
    Type type = Type::Position;
    int32_t position = 0;  // Position: absolute detent position
    uint32_t nonce = 0;    // Position: positionNonce of the config it was measured under
    PressType press = PressType::Short; // Press
};

class KnobInput {
  public:
    virtual ~KnobInput() = default;
    // Next pending event (called on the UI thread; must be thread-safe w.r.t. the producer).
    virtual bool pollEvent(KnobEvent &event) = 0;
    // Hand a new haptic config to the motor (called on the UI thread).
    virtual void applyHaptic(const HapticConfig &config) = 0;
};

} // namespace knob
