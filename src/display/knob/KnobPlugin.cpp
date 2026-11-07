#include "KnobPlugin.h"
#ifdef GAGGIMATE_KNOB

#include <Arduino.h>
#include <Preferences.h>
#include <display/knob/KnobPins.h>
#include <display/knob/KnobUi.h>
#include <display/knob/MotorTask.h>

static const char *TAG = "KnobPlugin";
static constexpr const char *NVS_NAMESPACE = "knob";

static constexpr unsigned long BOOT_PRESS_CAL_MS = 2000;
static constexpr unsigned long BOOT_MOTOR_CAL_MS = 6000;

namespace knob {

KnobSettings loadKnobSettings() {
    KnobSettings s;
    Preferences prefs;
    if (!prefs.begin(NVS_NAMESPACE, true))
        return s; // nothing stored yet: defaults (motor calibration runs on first boot)
    s.motorCalibrated = prefs.getBool("mcal", s.motorCalibrated);
    s.zeroElectricAngle = prefs.getFloat("zea", s.zeroElectricAngle);
    s.sensorDirection = prefs.getChar("sdir", s.sensorDirection);
    s.polePairs = prefs.getUChar("pp", s.polePairs);
    s.invertRotation = prefs.getBool("inv", s.invertRotation);
    s.press.pressDelta = prefs.getInt("pdelta", s.press.pressDelta);
    s.press.pressThreshold = prefs.getFloat("pon", s.press.pressThreshold);
    s.press.releaseThreshold = prefs.getFloat("poff", s.press.releaseThreshold);
    s.press.longPressMs = prefs.getUInt("plong", s.press.longPressMs);
    s.press.debounceSamples = prefs.getUChar("pdeb", s.press.debounceSamples);
    prefs.end();
    return s;
}

void saveKnobSettings(const KnobSettings &s) {
    Preferences prefs;
    if (!prefs.begin(NVS_NAMESPACE, false)) {
        ESP_LOGE(TAG, "Cannot open NVS namespace %s", NVS_NAMESPACE);
        return;
    }
    prefs.putBool("mcal", s.motorCalibrated);
    prefs.putFloat("zea", s.zeroElectricAngle);
    prefs.putChar("sdir", s.sensorDirection);
    prefs.putUChar("pp", s.polePairs);
    prefs.putBool("inv", s.invertRotation);
    prefs.putInt("pdelta", s.press.pressDelta);
    prefs.putFloat("pon", s.press.pressThreshold);
    prefs.putFloat("poff", s.press.releaseThreshold);
    prefs.putUInt("plong", s.press.longPressMs);
    prefs.putUChar("pdeb", s.press.debounceSamples);
    prefs.end();
}

} // namespace knob

void KnobPlugin::setup(Controller *controller, PluginManager *pluginManager) {
    (void)controller;
    (void)pluginManager;
    const knob::KnobSettings settings = knob::loadKnobSettings();
    ESP_LOGI(TAG, "Starting knob (motor %s, pressDelta %d, invert %d)", settings.motorCalibrated ? "calibrated" : "UNCALIBRATED",
             static_cast<int>(settings.press.pressDelta), settings.invertRotation);
    pinMode(knob::pins::BOOT_BUTTON, INPUT_PULLUP);
    knob::MotorTask::instance().begin(settings);
    knob::KnobUi::instance().attach(&knob::MotorTask::instance());
}

void KnobPlugin::loop() {
    knob::KnobSettings updated;
    if (knob::MotorTask::instance().takeSettingsUpdate(updated)) {
        knob::saveKnobSettings(updated);
        ESP_LOGI(TAG, "Knob calibration saved");
    }

    // BOOT button maintenance gestures, decided on release.
    const bool pressed = digitalRead(knob::pins::BOOT_BUTTON) == LOW;
    const unsigned long now = millis();
    if (pressed && !bootWasPressed) {
        bootPressedAt = now;
    } else if (!pressed && bootWasPressed) {
        const unsigned long held = now - bootPressedAt;
        if (held >= BOOT_MOTOR_CAL_MS) {
            ESP_LOGW(TAG, "BOOT held %lu ms: motor recalibration", held);
            knob::MotorTask::instance().requestCalibration(knob::MotorTask::Calibration::Motor);
        } else if (held >= BOOT_PRESS_CAL_MS) {
            ESP_LOGI(TAG, "BOOT held %lu ms: press + direction calibration", held);
            knob::MotorTask::instance().requestCalibration(knob::MotorTask::Calibration::PressAndDirection);
        }
    }
    bootWasPressed = pressed;
}

#endif // GAGGIMATE_KNOB
