#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB_LOGIC

#include "PressClassifier.h"

#include <cmath>

namespace knob {

PressEvent PressTimer::update(bool pressed, uint32_t nowMs, bool cancel) {
    if (pressed && !held) {
        held = true;
        downAt = nowMs;
        longFired = false;
        cancelled = cancel;
        return cancel ? PressEvent::None : PressEvent::Down;
    }
    if (!pressed && held) {
        held = false;
        return (cancelled || longFired) ? PressEvent::None : PressEvent::ShortPress;
    }
    if (held && !cancelled && !longFired) {
        if (cancel) {
            cancelled = true;
            return PressEvent::Cancelled;
        }
        if (nowMs - downAt >= longPressMs) {
            longFired = true;
            return PressEvent::LongPress;
        }
    }
    return PressEvent::None;
}

void PressClassifier::configure(const PressSettings &settings) {
    cfg = settings;
    if (cfg.pressDelta == 0)
        cfg.pressDelta = 1;
    if (cfg.releaseThreshold > cfg.pressThreshold)
        cfg.releaseThreshold = cfg.pressThreshold;
    if (cfg.debounceSamples == 0)
        cfg.debounceSamples = 1;
    timer.setLongPressMs(cfg.longPressMs);
}

PressEvent PressClassifier::onSample(int32_t raw, uint32_t nowMs, bool rotating) {
    if (!baselineValid) {
        baselineValue = static_cast<float>(raw);
        baselineValid = true;
        unit = 0.0f;
        pendingCount = 0;
        if (state) {
            state = false;
            const PressEvent e = timer.update(true, nowMs, true);
            timer.update(false, nowMs);
            return e;
        }
        return timer.update(false, nowMs);
    }

    unit = (static_cast<float>(raw) - baselineValue) / static_cast<float>(cfg.pressDelta);

    // Hysteresis: press above pressThreshold, release below releaseThreshold.
    const bool candidate = state ? unit >= cfg.releaseThreshold : (unit >= cfg.pressThreshold && !rotating);
    if (candidate != state) {
        if (++pendingCount >= cfg.debounceSamples) {
            state = candidate;
            pendingCount = 0;
            if (state)
                pressedSince = nowMs;
        }
    } else {
        pendingCount = 0;
    }

    // Running tare: follow slow drift (temperature, creep) whenever not pressed.
    if (!state && unit < cfg.idleBand && !rotating) {
        baselineValue += cfg.baselineAlpha * (static_cast<float>(raw) - baselineValue);
    }

    // A press that never ends is drift or a mechanical offset, not a user: re-tare.
    if (state && nowMs - pressedSince > cfg.stuckRetareMs) {
        baselineValid = false;
        return onSample(raw, nowMs, rotating);
    }

    return timer.update(state, nowMs, state && rotating);
}

void PressCalibrator::start(uint32_t nowMs) {
    *this = PressCalibrator();
    currentState = State::MeasuringNoise;
    startedAt = nowMs;
}

bool PressCalibrator::onSample(int32_t raw, uint32_t nowMs) {
    if (!active())
        return false;
    if (nowMs - startedAt > TIMEOUT_MS) {
        currentState = State::Failed;
        return false;
    }
    const float value = static_cast<float>(raw);

    if (currentState == State::MeasuringNoise) {
        sum += value;
        sumSq += static_cast<double>(value) * value;
        samples++;
        if (nowMs - startedAt >= NOISE_MS && samples >= 3) {
            mean = static_cast<float>(sum / samples);
            const double variance = sumSq / samples - (sum / samples) * (sum / samples);
            const float stddev = variance > 0.0 ? static_cast<float>(std::sqrt(variance)) : 0.0f;
            threshold = std::fmax(6.0f * stddev, MIN_THRESHOLD);
            currentState = State::Collecting;
        }
        return false;
    }

    const float dev = value - mean;
    if (!inPeak) {
        if (std::fabs(dev) > threshold) {
            inPeak = true;
            peak = dev;
        }
        return false;
    }
    if (std::fabs(dev) > std::fabs(peak))
        peak = dev;
    if (std::fabs(dev) >= threshold * 0.5f)
        return false;

    // Press released: record its peak.
    inPeak = false;
    peakValues[peakCount++] = peak;
    if (peakCount == PEAKS) {
        float total = 0.0f;
        for (int i = 0; i < PEAKS; i++) {
            if ((peakValues[i] > 0) != (peakValues[0] > 0)) {
                currentState = State::Failed; // inconsistent direction: noise or a knock
                return true;
            }
            total += peakValues[i];
        }
        result = static_cast<int32_t>(std::lround(total / PEAKS * PRESS_FRACTION));
        currentState = result == 0 ? State::Failed : State::Done;
    }
    return true;
}

} // namespace knob

#endif // GAGGIMATE_KNOB_LOGIC
