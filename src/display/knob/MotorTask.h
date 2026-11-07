// Haptic motor task of the GaggiMate Knob: SimpleFOC torque loop with
// software-defined detents on its own FreeRTOS task pinned to core 1, plus the
// HX711 press sensing (sampled in the same loop so presses can be ignored while
// the knob turns, and the press "click" is played with no extra latency).
//
// Ported from smartknob firmware/src/motor_task.{h,cpp}
//   smartknob - Copyright 2022 Scott Bezek
//   Licensed under the Apache License, Version 2.0 (the "License"); you may not use
//   this file except in compliance with the License. You may obtain a copy of the
//   License at http://www.apache.org/licenses/LICENSE-2.0
//   Unless required by applicable law or agreed to in writing, software distributed
//   under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//   CONDITIONS OF ANY KIND, either express or implied. See the License for the
//   specific language governing permissions and limitations under the License.
// Modifications for GaggiMate: DRV8311H 3x-PWM driver (BLDCDriver3PWM + shared
// enable, nSLEEP/nFAULT handling), SimpleFOC 2.3 API, detent maths moved to the
// hardware-free DetentModel, calibration stored in NVS via KnobPlugin, HX711 press
// classification and guided press/direction calibration added, events to the UI as
// absolute positions tagged with the config nonce.
#pragma once

#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB

#include "DetentModel.h"
#include "HX711Reader.h"
#include "KnobInput.h"
#include "KnobPins.h"
#include "KnobSettings.h"
#include "MT6701Sensor.h"
#include "PressClassifier.h"
#include <SimpleFOC.h>
#include <atomic>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>

namespace knob {

// Motor tuning for the SparkFun ROB-20441 (Wanzhida/Oncetop OT-EM3215D2450Y1R),
// values from SmartKnob's motors/wanzhida_once_top.h.
constexpr float FOC_PID_P = 4.0f;
constexpr float FOC_PID_I = 0.0f;
constexpr float FOC_PID_D = 0.04f;
constexpr float FOC_PID_OUTPUT_RAMP = 10000.0f;
constexpr float FOC_PID_LIMIT = 10.0f;
constexpr float FOC_VOLTAGE_LIMIT = 5.0f; // V, phase voltage limit (same as SmartKnob for this motor)
constexpr float SUPPLY_VOLTAGE = 5.0f;    // DRV8311H runs from the 5 V rail
constexpr int DEFAULT_POLE_PAIRS = 7;

class MotorTask : public KnobInput {
  public:
    enum class Calibration : uint8_t { None, PressAndDirection, Motor };

    static MotorTask &instance();

    // Spawns the task on core 1. `settings` are the persisted calibration/thresholds.
    void begin(const KnobSettings &settings);
    bool isRunning() const { return task != nullptr; }

    // Requests from other tasks (KnobPlugin, core 0).
    void requestCalibration(Calibration which) { pendingCalibration.store(static_cast<uint8_t>(which)); }
    // New calibration results to persist (KnobPlugin saves them to NVS).
    bool takeSettingsUpdate(KnobSettings &out);

    // KnobInput (UI task)
    bool pollEvent(KnobEvent &event) override;
    void applyHaptic(const HapticConfig &config) override;

  private:
    MotorTask();
    static void taskEntry(void *arg);
    void run();
    void loopOnce();
    void applyMotorCalibration();
    bool calibrateMotor();
    void runPressCalibration();
    void restoreDetents(const HapticConfig &keep, int32_t position);
    void serviceStrain(uint32_t now, bool rotating);
    void checkDriverFault(uint32_t now);
    void playClick(float strength);
    void publishPosition(int32_t position);
    void publishPress(PressType type);
    void publishSettings();
    float knobAngle() const { return settings.invertRotation ? -motor.shaft_angle : motor.shaft_angle; }
    float knobVelocity() const { return settings.invertRotation ? -motor.shaft_velocity : motor.shaft_velocity; }

    TaskHandle_t task = nullptr;
    QueueHandle_t eventQueue = nullptr;  // motor -> UI (KnobEvent)
    QueueHandle_t configQueue = nullptr; // UI -> motor (HapticConfig, length 1, overwrite)
    SemaphoreHandle_t settingsMutex = nullptr;
    std::atomic<uint8_t> pendingCalibration{0};
    std::atomic<bool> settingsDirty{false};
    KnobSettings settings;       // owned by the motor task
    KnobSettings settingsOut;    // guarded by settingsMutex

    BLDCMotor motor = BLDCMotor(DEFAULT_POLE_PAIRS);
    BLDCDriver3PWM driver = BLDCDriver3PWM(pins::DRV_INHA, pins::DRV_INHB, pins::DRV_INHC, pins::DRV_EN);
    MT6701Sensor encoder = MT6701Sensor(pins::ENC_CS, pins::ENC_CLK, pins::ENC_DO);
    HX711Reader strain = HX711Reader(pins::HX_DOUT, pins::HX_SCK);
    DetentModel detents;
    PressClassifier press;

    int32_t lastPosition = 0;
    uint32_t lastDetentChange = 0;
    uint32_t lastStrainSample = 0;
    bool strainMissingLogged = false;
    uint32_t lastFaultCheck = 0;
    uint8_t faultRecoveries = 0;
    uint32_t lastSensorErrorLog = 0;
};

} // namespace knob

#endif // GAGGIMATE_KNOB
