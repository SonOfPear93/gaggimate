#include "SimKnob.h"

#include <cstdio>
#include <display/knob/DetentModel.h>
#include <display/knob/KnobUi.h>

SimKnob &SimKnob::instance() {
    static SimKnob knob;
    return knob;
}

void SimKnob::activate() {
    if (active)
        return;
    active = true;
    knob::KnobUi::instance().attach(this);
    printf("[sim-knob] knob emulation on: wheel/arrows = turn, Enter = press (hold 0.6 s = long press)\n");
}

void SimKnob::turn(int detents) {
    activate();
    const int dir = detents > 0 ? 1 : -1;
    for (int i = 0; i < (detents > 0 ? detents : -detents); i++) {
        const int32_t next = knob::DetentModel::stepClamped(config, position, dir);
        if (next == position)
            continue; // end stop
        position = next;
        knob::KnobEvent e;
        e.type = knob::KnobEvent::Type::Position;
        e.position = position;
        e.nonce = config.positionNonce;
        events.push_back(e);
    }
}

void SimKnob::pushPress(knob::PressEvent pe) {
    knob::KnobEvent e;
    e.type = knob::KnobEvent::Type::Press;
    if (pe == knob::PressEvent::ShortPress) {
        e.press = knob::PressType::Short;
    } else if (pe == knob::PressEvent::LongPress) {
        e.press = knob::PressType::Long;
    } else {
        return; // Down / Cancelled: the hardware plays a click, nothing for the UI
    }
    events.push_back(e);
}

void SimKnob::setPressed(bool pressed, uint32_t now) {
    activate();
    keyDown = pressed;
    pushPress(timer.update(pressed, now));
}

void SimKnob::tick(uint32_t now) {
    if (active)
        pushPress(timer.update(keyDown, now));
}

void SimKnob::injectPress(knob::PressType type) {
    activate();
    pushPress(type == knob::PressType::Long ? knob::PressEvent::LongPress : knob::PressEvent::ShortPress);
}

bool SimKnob::pollEvent(knob::KnobEvent &event) {
    if (events.empty())
        return false;
    event = events.front();
    events.pop_front();
    return true;
}

void SimKnob::applyHaptic(const knob::HapticConfig &c) {
    // Same position semantics as the motor task: a new nonce adopts the config's position.
    if (c.positionNonce != config.positionNonce)
        position = c.position;
    config = c;
    if (config.bounded())
        position = knob::DetentModel::stepClamped(config, position, 0);
}
