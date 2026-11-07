// Simulator stand-in for the GaggiMate Knob: keyboard / mouse wheel emulate the
// motorised knob and feed the same KnobNavigator the hardware uses.
//   mouse wheel up / Right arrow  = one detent clockwise (+1)
//   mouse wheel down / Left arrow = one detent counter-clockwise (-1)
//   Enter                         = press (short), hold >= 0.6 s = long press
// The virtual motor honours the haptic config's end stops (a turn past the
// first/last item produces no event), like the real detents would.
#pragma once

#include <deque>
#include <display/knob/KnobInput.h>
#include <display/knob/PressClassifier.h>

class SimKnob : public knob::KnobInput {
  public:
    static SimKnob &instance();

    // Route knob input into the UI (also done implicitly by the first knob key).
    void activate();
    bool isActive() const { return active; }

    void turn(int detents);                      // +n clockwise, -n counter-clockwise
    void setPressed(bool pressed, uint32_t now); // Enter key state
    void tick(uint32_t now);                     // fires the long press while held
    void injectPress(knob::PressType type);      // scripted input

    // knob::KnobInput
    bool pollEvent(knob::KnobEvent &event) override;
    void applyHaptic(const knob::HapticConfig &config) override;

  private:
    SimKnob() = default;
    void pushPress(knob::PressEvent e);

    bool active = false;
    knob::HapticConfig config;
    int32_t position = 0;
    bool keyDown = false;
    knob::PressTimer timer;
    std::deque<knob::KnobEvent> events;
};
