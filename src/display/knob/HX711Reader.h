// Minimal bit-banged HX711 reader (channel A, gain 128) for the knob's strain
// gauge bridge. Non-blocking: poll ready() from the motor loop and read() only
// when it returns true, so the FOC loop never waits on the ADC (10 or 80 SPS
// depending on the board's RATE pin).
#pragma once

#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB

#include <Arduino.h>

namespace knob {

class HX711Reader {
  public:
    HX711Reader(int8_t doutPin, int8_t sckPin) : dout(doutPin), sck(sckPin) {}

    void begin() {
        pinMode(sck, OUTPUT);
        digitalWrite(sck, LOW); // SCK high > 60 us powers the HX711 down
        pinMode(dout, INPUT_PULLUP); // absent chip reads "never ready"
    }

    // DOUT low = a conversion is ready.
    bool ready() const { return digitalRead(dout) == LOW; }

    // 24 data clocks + 1 (selects channel A / gain 128 for the next conversion).
    // Runs with interrupts masked on this core (~55 us) so SCK never stays high
    // long enough to power the chip down mid-read.
    int32_t read() {
        uint32_t value = 0;
        portDISABLE_INTERRUPTS();
        for (int i = 0; i < 24; i++) {
            digitalWrite(sck, HIGH);
            delayMicroseconds(1);
            value = (value << 1) | (digitalRead(dout) ? 1u : 0u);
            digitalWrite(sck, LOW);
            delayMicroseconds(1);
        }
        digitalWrite(sck, HIGH);
        delayMicroseconds(1);
        digitalWrite(sck, LOW);
        delayMicroseconds(1);
        portENABLE_INTERRUPTS();
        // Sign-extend the 24-bit two's complement result.
        if (value & 0x800000u)
            value |= 0xFF000000u;
        return static_cast<int32_t>(value);
    }

  private:
    int8_t dout;
    int8_t sck;
};

} // namespace knob

#endif // GAGGIMATE_KNOB
