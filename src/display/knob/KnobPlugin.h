// GaggiMate Knob plugin (display-knob build only): loads the knob settings from
// NVS, starts the haptic motor task on core 1, routes its events into the UI's
// KnobNavigator, persists calibration results, and watches the BOOT button for the
// maintenance gestures (hold 2-6 s: press + direction calibration, >= 6 s: motor
// recalibration).
#pragma once

#include <display/knob/KnobBuild.h>
#ifdef GAGGIMATE_KNOB

#include <display/core/Plugin.h>
#include <display/knob/KnobSettings.h>

class KnobPlugin : public Plugin {
  public:
    void setup(Controller *controller, PluginManager *pluginManager) override;
    void loop() override;

  private:
    unsigned long bootPressedAt = 0;
    bool bootWasPressed = false;
};

#endif // GAGGIMATE_KNOB
