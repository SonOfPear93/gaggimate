// LVGL/EEZ glue for the knob: runs on the UI (LVGL) task from DefaultUI::loop,
// feeds knob events into the KnobNavigator, performs its actions through the
// existing EEZ action_* handlers (so limits, dirty-profile marking and BLE sync
// stay in one place), pushes haptic configs back to the knob and draws the focus
// highlight. Shared by the knob board (GAGGIMATE_KNOB) and the simulator.
#pragma once

#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB_UI

#include "KnobInput.h"
#include "KnobNavigator.h"
#include <atomic>
#include <lvgl.h>

class Controller;
class DefaultUI;

namespace knob {

class KnobUi : public NavigatorHost {
  public:
    static KnobUi &instance();

    // Start routing knob input to the UI. Safe to call from any task once.
    void attach(KnobInput *input) { this->input.store(input); }
    bool isAttached() const { return input.load() != nullptr; }

    // Called from DefaultUI::loop on the LVGL task.
    void loop(DefaultUI *ui, Controller *controller);

    const KnobNavigator &navigator() const { return nav; }

    // NavigatorHost
    bool isAvailable(Item item) const override;
    ValueRange valueRange(Item item) const override;

  private:
    KnobUi() : nav(*this) {}

    Screen detectScreen() const;
    void perform(const Action &action);
    void step(Item item, int32_t delta);
    lv_obj_t *objectFor(Item item) const;
    void updateHighlight();
    void hideRing();

    std::atomic<KnobInput *> input{nullptr};
    KnobNavigator nav;
    DefaultUI *ui = nullptr;
    Controller *controller = nullptr;

    // Focus ring: one object on LVGL's top layer that tracks the focused widget's
    // bounds (drawn above the screen, so parents never clip it and the widget's own
    // styles/layout are untouched).
    lv_obj_t *ring = nullptr;
    lv_area_t ringArea{};
    bool ringEdit = false;
    uint32_t ringTheme = UINT32_MAX;
};

} // namespace knob

#endif // GAGGIMATE_KNOB_UI
