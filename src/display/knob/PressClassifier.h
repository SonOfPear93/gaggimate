// Knob press detection. Hardware-free so it can be unit tested natively.
//
//  - PressTimer turns a debounced "is pressed" boolean into Down / ShortPress /
//    LongPress events (long press fires while still held, after longPressMs).
//    The simulator feeds it the Enter key directly.
//  - PressClassifier turns raw HX711 strain readings into that boolean: it tracks
//    a running baseline (tare) while idle, normalises the deviation by the
//    calibrated press delta, and applies press/release hysteresis + debouncing.
//    Presses that start while the knob is turning are ignored, and turning during
//    a press cancels it (twisting a knob loads the flexure too).
//
// Approach after SmartKnob's interface_task.cpp (Scott Bezek, Apache-2.0), which
// uses a fixed idle value + press delta with 1.0 / 0.5 hysteresis; the running
// baseline, timing and rotation lock-out are GaggiMate additions.
#pragma once

#include <cstdint>

namespace knob {

enum class PressEvent : uint8_t {
    None,
    Down,       // press registered (play the haptic click)
    ShortPress, // released before longPressMs
    LongPress,  // held for longPressMs (fires once, while still held)
    Cancelled,  // press aborted (knob turned while pressed)
};

struct PressSettings {
    // Raw HX711 counts between "idle" and "a firm press". The sign encodes the
    // direction the bridge moves when pressed. Calibrate per unit (see docs).
    int32_t pressDelta = 20000;
    float pressThreshold = 1.0f;   // press when deviation >= this fraction of pressDelta
    float releaseThreshold = 0.5f; // release when deviation < this fraction
    uint8_t debounceSamples = 2;   // consecutive samples needed to change state
    uint32_t longPressMs = 600;
    float baselineAlpha = 0.02f;  // EWMA weight per sample while idle
    float idleBand = 0.3f;        // |deviation| below this (fraction) counts as idle for tare
    uint32_t stuckRetareMs = 8000; // a "press" this long is treated as drift: re-tare
};

class PressTimer {
  public:
    void setLongPressMs(uint32_t ms) { longPressMs = ms; }

    // Feed the debounced pressed state. `cancel` aborts the current press (no
    // Short/Long event). Returns at most one event per call.
    PressEvent update(bool pressed, uint32_t nowMs, bool cancel = false);

    bool isHeld() const { return held; }

  private:
    uint32_t longPressMs = 600;
    bool held = false;
    bool longFired = false;
    bool cancelled = false;
    uint32_t downAt = 0;
};

class PressClassifier {
  public:
    explicit PressClassifier(const PressSettings &settings = PressSettings()) { configure(settings); }

    void configure(const PressSettings &settings);
    const PressSettings &settings() const { return cfg; }

    // Feed one HX711 sample. `rotating` = the knob is turning (fast enough, or a
    // detent changed recently); presses don't start while rotating and an
    // ongoing press is cancelled.
    PressEvent onSample(int32_t raw, uint32_t nowMs, bool rotating);

    // Force the baseline to the next reading (e.g. after calibration).
    void retare() { baselineValid = false; }

    // Normalised deviation from baseline (0 = idle, 1 = calibrated press).
    float pressUnit() const { return unit; }
    float baseline() const { return baselineValue; }
    bool pressed() const { return state; }

  private:
    PressSettings cfg;
    PressTimer timer;
    bool baselineValid = false;
    float baselineValue = 0.0f;
    float unit = 0.0f;
    bool state = false;
    uint8_t pendingCount = 0;
    uint32_t pressedSince = 0;
};

// Guided press calibration (no UI needed): measures the idle noise for a second,
// then the user presses the knob firmly `PEAKS` times. The calibrated pressDelta
// is PRESS_FRACTION of the average peak, so a normal press clears the 1.0
// threshold comfortably and a light touch doesn't.
class PressCalibrator {
  public:
    enum class State : uint8_t { Inactive, MeasuringNoise, Collecting, Done, Failed };

    static constexpr uint32_t NOISE_MS = 1000;
    static constexpr uint32_t TIMEOUT_MS = 20000;
    static constexpr int PEAKS = 3;
    static constexpr float PRESS_FRACTION = 0.6f;
    static constexpr float MIN_THRESHOLD = 2000.0f; // counts; floor for the peak detector

    void start(uint32_t nowMs);
    void cancel() { currentState = State::Inactive; }
    // Feed one sample; returns true when a press peak was just registered.
    bool onSample(int32_t raw, uint32_t nowMs);

    State state() const { return currentState; }
    bool active() const { return currentState == State::MeasuringNoise || currentState == State::Collecting; }
    int32_t pressDelta() const { return result; }
    int peaks() const { return peakCount; }

  private:
    State currentState = State::Inactive;
    uint32_t startedAt = 0;
    double sum = 0.0, sumSq = 0.0;
    uint32_t samples = 0;
    float mean = 0.0f;
    float threshold = 0.0f;
    bool inPeak = false;
    float peak = 0.0f;
    float peakValues[PEAKS] = {};
    int peakCount = 0;
    int32_t result = 0;
};

} // namespace knob
