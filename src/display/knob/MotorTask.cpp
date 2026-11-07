// Ported from smartknob firmware/src/motor_task.cpp
//   smartknob - Copyright 2022 Scott Bezek
//   Licensed under the Apache License, Version 2.0 (the "License"); you may not use
//   this file except in compliance with the License. You may obtain a copy of the
//   License at http://www.apache.org/licenses/LICENSE-2.0
//   Unless required by applicable law or agreed to in writing, software distributed
//   under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//   CONDITIONS OF ANY KIND, either express or implied. See the License for the
//   specific language governing permissions and limitations under the License.
// See MotorTask.h for the GaggiMate modifications.
#include "MotorTask.h"
#ifdef GAGGIMATE_KNOB

#include <Arduino.h>

namespace knob {

static const char *TAG = "KnobMotor";

static constexpr uint32_t TASK_STACK = 8192;
static constexpr UBaseType_t TASK_PRIORITY = 2; // above the LVGL task (1) on core 1
static constexpr BaseType_t TASK_CORE = 1;
static constexpr size_t EVENT_QUEUE_LEN = 32;

static constexpr float PRESS_CLICK_STRENGTH = 5.0f;  // SmartKnob's press click
static constexpr float DETAIL_CLICK_STRENGTH = 1.5f; // lighter click (calibration feedback)
static constexpr uint32_t DETENT_LOCKOUT_MS = 200;   // no press within this long after a detent change
static constexpr float ROTATION_LOCKOUT_RAD_PER_SEC = 4.0f;
static constexpr uint32_t CLICK_QUIET_MS = 50; // a click moves the knob: don't count that as turning
static constexpr uint32_t FAULT_CHECK_MS = 50;
static constexpr uint8_t MAX_FAULT_RECOVERIES = 5;
static constexpr uint32_t DIRECTION_TIMEOUT_MS = 15000;

static uint32_t clickQuietUntil = 0;

MotorTask &MotorTask::instance() {
    static MotorTask motorTask;
    return motorTask;
}

MotorTask::MotorTask() {}

void MotorTask::begin(const KnobSettings &initial) {
    if (task != nullptr)
        return;
    settings = initial;
    settingsOut = initial;
    press.configure(settings.press);
    eventQueue = xQueueCreate(EVENT_QUEUE_LEN, sizeof(KnobEvent));
    configQueue = xQueueCreate(1, sizeof(HapticConfig));
    settingsMutex = xSemaphoreCreateMutex();
    xTaskCreatePinnedToCore(taskEntry, "knob-motor", TASK_STACK, this, TASK_PRIORITY, &task, TASK_CORE);
}

void MotorTask::taskEntry(void *arg) { static_cast<MotorTask *>(arg)->run(); }

bool MotorTask::pollEvent(KnobEvent &event) {
    return eventQueue != nullptr && xQueueReceive(eventQueue, &event, 0) == pdTRUE;
}

void MotorTask::applyHaptic(const HapticConfig &config) {
    if (configQueue != nullptr)
        xQueueOverwrite(configQueue, &config); // only the latest config matters
}

bool MotorTask::takeSettingsUpdate(KnobSettings &out) {
    if (!settingsDirty.load())
        return false;
    xSemaphoreTake(settingsMutex, portMAX_DELAY);
    out = settingsOut;
    settingsDirty.store(false);
    xSemaphoreGive(settingsMutex);
    return true;
}

void MotorTask::publishSettings() {
    xSemaphoreTake(settingsMutex, portMAX_DELAY);
    settingsOut = settings;
    settingsDirty.store(true);
    xSemaphoreGive(settingsMutex);
}

void MotorTask::publishPosition(int32_t position) {
    KnobEvent e;
    e.type = KnobEvent::Type::Position;
    e.position = position;
    e.nonce = detents.config().positionNonce;
    // Positions are absolute, so a report dropped on a full queue loses nothing.
    xQueueSend(eventQueue, &e, 0);
}

void MotorTask::publishPress(PressType type) {
    KnobEvent e;
    e.type = KnobEvent::Type::Press;
    e.press = type;
    xQueueSend(eventQueue, &e, 0);
}

void MotorTask::run() {
    // DRV8311H: wake it up (nSLEEP high), nFAULT is open drain with an external pull-up.
    pinMode(pins::DRV_NSLEEP, OUTPUT);
    digitalWrite(pins::DRV_NSLEEP, HIGH);
    pinMode(pins::DRV_NFAULT, INPUT_PULLUP);
    delay(5);

    driver.voltage_power_supply = SUPPLY_VOLTAGE;
    driver.voltage_limit = SUPPLY_VOLTAGE;
    if (!driver.init())
        ESP_LOGE(TAG, "Motor driver init failed");

    encoder.init();
    motor.linkDriver(&driver);
    motor.controller = MotionControlType::torque;
    motor.voltage_limit = FOC_VOLTAGE_LIMIT;
    motor.velocity_limit = 10000;
    motor.linkSensor(&encoder);

    // Not using SimpleFOC's velocity loop: its PID is reused as the detent torque PID.
    motor.PID_velocity.P = FOC_PID_P;
    motor.PID_velocity.I = FOC_PID_I;
    motor.PID_velocity.D = FOC_PID_D;
    motor.PID_velocity.output_ramp = FOC_PID_OUTPUT_RAMP;
    motor.PID_velocity.limit = FOC_PID_LIMIT;

    motor.init();
    encoder.update();
    delay(10);

    if (!settings.motorCalibrated) {
        ESP_LOGW(TAG, "No motor calibration stored: calibrating (don't touch the knob)");
        calibrateMotor();
    }
    applyMotorCalibration();

    strain.begin();
    lastStrainSample = millis();
    detents.applyConfig(haptics::locked(), knobAngle());
    lastPosition = detents.position();

    while (true) {
        loopOnce();
        delay(1);
    }
}

void MotorTask::applyMotorCalibration() {
    motor.controller = MotionControlType::torque;
    motor.voltage_limit = FOC_VOLTAGE_LIMIT;
    motor.pole_pairs = settings.motorCalibrated ? settings.polePairs : DEFAULT_POLE_PAIRS;
    motor.zero_electric_angle = settings.zeroElectricAngle;
    motor.sensor_direction = settings.sensorDirection >= 0 ? Direction::CW : Direction::CCW;
    motor.initFOC();
    if (settings.motorCalibrated) {
        motor.enable();
        ESP_LOGI(TAG, "Motor ready: %d pole pairs, zero %.2f, %s", motor.pole_pairs, motor.zero_electric_angle,
                 settings.sensorDirection >= 0 ? "CW" : "CCW");
    } else {
        // Without a valid calibration torque would be wrong (or spin the motor): keep it off.
        // The encoder still works, so the knob navigates without haptics.
        motor.disable();
        ESP_LOGE(TAG, "Motor not calibrated: haptics disabled (hold BOOT >= 6 s to retry)");
    }
}

void MotorTask::loopOnce() {
    motor.loopFOC();

    HapticConfig config;
    if (xQueueReceive(configQueue, &config, 0) == pdTRUE) {
        if (detents.applyConfig(config, knobAngle()))
            lastPosition = detents.position();
        else
            ESP_LOGW(TAG, "Ignoring invalid haptic config");
    }

    const auto request = static_cast<Calibration>(pendingCalibration.exchange(0));
    if (request == Calibration::Motor) {
        const HapticConfig keep = detents.config();
        const int32_t keepPosition = detents.position();
        if (calibrateMotor())
            ESP_LOGI(TAG, "Motor recalibrated");
        applyMotorCalibration();
        restoreDetents(keep, keepPosition);
    } else if (request == Calibration::PressAndDirection) {
        runPressCalibration();
    }

    const uint32_t now = millis();
    const DetentModel::Output out = detents.update(knobAngle(), knobVelocity(), now);
    if (detents.position() != lastPosition) {
        lastPosition = detents.position();
        lastDetentChange = now;
        publishPosition(lastPosition);
    }

    if (settings.motorCalibrated) {
        motor.PID_velocity.limit = FOC_PID_LIMIT;
        motor.PID_velocity.P = detents.proportionalGain(out.outOfBounds);
        motor.PID_velocity.D = detents.derivativeGain();
        if (!out.torqueEnabled) {
            motor.move(0); // spinning fast: no torque (avoids runaway)
        } else {
            float torque = motor.PID_velocity(out.pidInput);
            if (settings.invertRotation)
                torque = -torque;
            motor.move(torque);
        }
    } else {
        motor.move(0);
    }

    const bool rotating = now - lastDetentChange < DETENT_LOCKOUT_MS ||
                          (fabsf(knobVelocity()) > ROTATION_LOCKOUT_RAD_PER_SEC && now > clickQuietUntil);
    serviceStrain(now, rotating);
    checkDriverFault(now);

    if (now - lastSensorErrorLog > 5000) {
        const MT6701Error err = encoder.getAndClearError();
        if (err.error) {
            ESP_LOGW(TAG, "MT6701 CRC error (got %d, expected %d), %u total", err.receivedCrc, err.calculatedCrc,
                     static_cast<unsigned>(encoder.crcErrorCount()));
            lastSensorErrorLog = now;
        }
    }
}

void MotorTask::serviceStrain(uint32_t now, bool rotating) {
    if (!strain.ready()) {
        if (!strainMissingLogged && now - lastStrainSample > 2000) {
            ESP_LOGE(TAG, "HX711 not responding: press input unavailable");
            strainMissingLogged = true;
        }
        return;
    }
    const int32_t raw = strain.read();
    lastStrainSample = now;
    strainMissingLogged = false;

    switch (press.onSample(raw, now, rotating)) {
    case PressEvent::Down:
        playClick(PRESS_CLICK_STRENGTH);
        break;
    case PressEvent::ShortPress:
        publishPress(PressType::Short);
        break;
    case PressEvent::LongPress:
        playClick(PRESS_CLICK_STRENGTH);
        publishPress(PressType::Long);
        break;
    default:
        break;
    }
}

void MotorTask::checkDriverFault(uint32_t now) {
    if (now - lastFaultCheck < FAULT_CHECK_MS)
        return;
    lastFaultCheck = now;
    if (digitalRead(pins::DRV_NFAULT) == HIGH)
        return;
    if (faultRecoveries >= MAX_FAULT_RECOVERIES) {
        if (faultRecoveries == MAX_FAULT_RECOVERIES) {
            ESP_LOGE(TAG, "DRV8311 keeps faulting: motor disabled until reboot");
            motor.disable();
            faultRecoveries++;
        }
        return;
    }
    // A short nSLEEP low pulse clears latched DRV8311 faults.
    ESP_LOGW(TAG, "DRV8311 nFAULT asserted, resetting driver (%u)", static_cast<unsigned>(faultRecoveries + 1));
    digitalWrite(pins::DRV_NSLEEP, LOW);
    delayMicroseconds(30);
    digitalWrite(pins::DRV_NSLEEP, HIGH);
    faultRecoveries++;
}

// SmartKnob's hardcoded haptic "click": a quick burst of torque in each direction.
void MotorTask::playClick(float strength) {
    if (!settings.motorCalibrated)
        return;
    motor.move(strength);
    for (uint8_t i = 0; i < 3; i++) {
        motor.loopFOC();
        delay(1);
    }
    motor.move(-strength);
    for (uint8_t i = 0; i < 3; i++) {
        motor.loopFOC();
        delay(1);
    }
    motor.move(0);
    motor.loopFOC();
    clickQuietUntil = millis() + CLICK_QUIET_MS;
}

// Guided calibration, no UI needed (started by holding BOOT 2-6 s):
//  1. hands off for 1 s, then press the knob firmly 3 times (a click confirms each);
//  2. turn the knob clockwise a quarter turn (a double click confirms the direction).
void MotorTask::runPressCalibration() {
    ESP_LOGI(TAG, "Press calibration: hands off for 1 s, then press the knob firmly 3 times");
    const HapticConfig keep = detents.config();
    const int32_t keepPosition = detents.position();
    playClick(DETAIL_CLICK_STRENGTH);

    PressCalibrator cal;
    cal.start(millis());
    while (cal.active()) {
        motor.loopFOC();
        motor.move(0);
        if (strain.ready() && cal.onSample(strain.read(), millis()))
            playClick(DETAIL_CLICK_STRENGTH);
        delay(1);
    }
    if (cal.state() == PressCalibrator::State::Done) {
        settings.press.pressDelta = cal.pressDelta();
        press.configure(settings.press);
        press.retare();
        ESP_LOGI(TAG, "Press calibrated: pressDelta = %d counts", static_cast<int>(cal.pressDelta()));
        playClick(PRESS_CLICK_STRENGTH);
        delay(120);
        playClick(PRESS_CLICK_STRENGTH);
    } else {
        ESP_LOGW(TAG, "Press calibration failed (%d of %d presses seen), keeping %d", cal.peaks(), PressCalibrator::PEAKS,
                 static_cast<int>(settings.press.pressDelta));
    }

    ESP_LOGI(TAG, "Direction: turn the knob clockwise about a quarter turn");
    const float start = motor.shaft_angle;
    const uint32_t started = millis();
    while (millis() - started < DIRECTION_TIMEOUT_MS) {
        motor.loopFOC();
        motor.move(0); // also refreshes shaft_angle
        const float delta = motor.shaft_angle - start;
        if (fabsf(delta) > _PI_2) {
            // Positions increase when the knob angle decreases (SmartKnob convention), so
            // clockwise must decrease the knob angle.
            settings.invertRotation = delta > 0;
            ESP_LOGI(TAG, "Direction set: invertRotation = %d", settings.invertRotation);
            playClick(PRESS_CLICK_STRENGTH);
            delay(120);
            playClick(PRESS_CLICK_STRENGTH);
            break;
        }
        delay(1);
    }

    publishSettings();
    restoreDetents(keep, keepPosition);
}

// After a calibration: same config (and nonce, so the UI's view stays valid) and the
// same detent position, re-centred on the knob's current angle.
void MotorTask::restoreDetents(const HapticConfig &keep, int32_t position) {
    HapticConfig restore = keep;
    restore.position = position;
    restore.positionNonce = keep.positionNonce ^ 0x80000000u; // a different nonce forces the re-centre...
    detents.applyConfig(restore, knobAngle());
    restore.positionNonce = keep.positionNonce; // ...then put the UI's nonce back
    detents.applyConfig(restore, knobAngle());
    lastPosition = detents.position();
}

// SimpleFOC is supposed to be able to determine this automatically (if you omit params to initFOC), but
// it seems to have a bug (or I've misconfigured it) that gets both the offset and direction very wrong!
// So this value is based on experimentation. [Scott Bezek]
bool MotorTask::calibrateMotor() {
    ESP_LOGW(TAG, "Starting motor calibration, please DO NOT TOUCH THE KNOB until complete!");
    motor.enable();
    delay(1000);

    motor.controller = MotionControlType::angle_openloop;
    motor.pole_pairs = 1;
    motor.zero_electric_angle = 0;
    motor.sensor_direction = Direction::CW;
    motor.initFOC();

    float a = 0;
    motor.voltage_limit = FOC_VOLTAGE_LIMIT;
    motor.move(a);

    // #### Determine direction motor rotates relative to angle sensor
    for (uint8_t i = 0; i < 200; i++) {
        encoder.update();
        motor.move(a);
        delay(1);
    }
    float startSensor = encoder.getAngle();

    for (; a < 3 * _2PI; a += 0.01f) {
        encoder.update();
        motor.move(a);
        delay(1);
    }

    for (uint8_t i = 0; i < 200; i++) {
        encoder.update();
        delay(1);
    }
    float endSensor = encoder.getAngle();

    motor.voltage_limit = 0;
    motor.move(a);

    const float movementAngle = fabsf(endSensor - startSensor);
    if (movementAngle < radians(30) || movementAngle > radians(180)) {
        ESP_LOGE(TAG, "Calibration failed: unexpected sensor change: start=%.2f end=%.2f", startSensor, endSensor);
        return false;
    }

    const Direction direction = endSensor > startSensor ? Direction::CW : Direction::CCW;
    motor.sensor_direction = direction;
    motor.initFOC();
    ESP_LOGI(TAG, "Sensor direction: %s (start %.1f, end %.1f)", direction == Direction::CW ? "CW" : "CCW", startSensor,
             endSensor);

    // #### Determine pole-pairs
    // Rotate 20 electrical revolutions and measure mechanical angle traveled, to calculate pole-pairs
    const uint8_t electricalRevolutions = 20;
    motor.voltage_limit = FOC_VOLTAGE_LIMIT;
    motor.move(a);
    float destination = a + _2PI;
    for (; a < destination; a += 0.03f) {
        encoder.update();
        motor.move(a);
        delay(1);
    }
    for (uint16_t i = 0; i < 1000; i++) { // let momentum settle
        encoder.update();
        delay(1);
    }

    const float dir = static_cast<float>(static_cast<int8_t>(motor.sensor_direction));
    startSensor = dir * encoder.getAngle();
    destination = a + electricalRevolutions * _2PI;
    for (; a < destination; a += 0.03f) {
        encoder.update();
        motor.move(a);
        delay(1);
    }
    for (uint16_t i = 0; i < 1000; i++) {
        encoder.update();
        motor.move(a);
        delay(1);
    }
    endSensor = dir * encoder.getAngle();
    motor.voltage_limit = 0;
    motor.move(a);

    if (fabsf(motor.shaft_angle - motor.target) > 1 * PI / 180) {
        ESP_LOGE(TAG, "Calibration failed: motor did not reach target");
        return false;
    }

    const float electricalPerMechanical = electricalRevolutions * _2PI / (endSensor - startSensor);
    ESP_LOGI(TAG, "Electrical angle / mechanical angle (i.e. pole pairs) = %.2f", electricalPerMechanical);
    if (electricalPerMechanical < 3 || electricalPerMechanical > 12) {
        ESP_LOGE(TAG, "Calibration failed: unexpected pole pairs %.2f", electricalPerMechanical);
        return false;
    }
    const int measuredPolePairs = (int)round(electricalPerMechanical);
    if (measuredPolePairs != DEFAULT_POLE_PAIRS)
        ESP_LOGW(TAG, "Measured %d pole pairs (ROB-20441 has %d)", measuredPolePairs, DEFAULT_POLE_PAIRS);
    delay(1000);

    // #### Determine mechanical offset to electrical zero
    // Measure mechanical angle at every electrical zero for several revolutions
    motor.voltage_limit = FOC_VOLTAGE_LIMIT;
    motor.move(a);
    float offsetX = 0;
    float offsetY = 0;
    const float destination1 = (floor(a / _2PI) + measuredPolePairs / 2.) * _2PI;
    const float destination2 = (floor(a / _2PI)) * _2PI;
    auto sampleOffset = [&]() {
        motor.move(a);
        delay(100);
        for (uint8_t i = 0; i < 100; i++) {
            encoder.update();
            delay(1);
        }
        const float realElectricalAngle = _normalizeAngle(a);
        const float measuredElectricalAngle = _normalizeAngle((float)(dir * measuredPolePairs) * encoder.getMechanicalAngle());
        const float offsetAngle = measuredElectricalAngle - realElectricalAngle;
        offsetX += cosf(offsetAngle);
        offsetY += sinf(offsetAngle);
    };
    for (; a < destination1; a += 0.4f)
        sampleOffset();
    for (; a > destination2; a -= 0.4f)
        sampleOffset();
    motor.voltage_limit = 0;
    motor.move(a);

    const float avgOffsetAngle = atan2f(offsetY, offsetX);

    // #### Apply settings
    settings.motorCalibrated = true;
    settings.polePairs = static_cast<uint8_t>(measuredPolePairs);
    settings.zeroElectricAngle = avgOffsetAngle + _3PI_2;
    settings.sensorDirection = direction == Direction::CW ? 1 : -1;
    motor.voltage_limit = FOC_VOLTAGE_LIMIT;
    motor.controller = MotionControlType::torque;
    ESP_LOGI(TAG, "Calibration done: zero electrical offset %.2f, direction %s, %d pole pairs", settings.zeroElectricAngle,
             settings.sensorDirection > 0 ? "CW" : "CCW", settings.polePairs);
    publishSettings();
    return true;
}

} // namespace knob

#endif // GAGGIMATE_KNOB
