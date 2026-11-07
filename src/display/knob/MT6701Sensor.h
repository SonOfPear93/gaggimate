// MT6701 magnetic angle sensor over SSI (CS/CLK/DO) as a SimpleFOC Sensor.
//
// Ported from smartknob firmware/src/mt6701_sensor.{h,cpp}
//   smartknob - Copyright 2022 Scott Bezek
//   Licensed under the Apache License, Version 2.0 (the "License"); you may not use
//   this file except in compliance with the License. You may obtain a copy of the
//   License at http://www.apache.org/licenses/LICENSE-2.0
//   Unless required by applicable law or agreed to in writing, software distributed
//   under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//   CONDITIONS OF ANY KIND, either express or implied. See the License for the
//   specific language governing permissions and limitations under the License.
// Modifications for GaggiMate: pins passed in (KnobPins.h), SimpleFOC 2.3 base
// Sensor::init() called, error counter instead of a single last error.
#pragma once

#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB

#include <SimpleFOC.h>
#include <driver/spi_master.h>

namespace knob {

struct MT6701Error {
    bool error;
    uint8_t receivedCrc;
    uint8_t calculatedCrc;
};

class MT6701Sensor : public Sensor {
  public:
    MT6701Sensor(int8_t csPin, int8_t clkPin, int8_t dataPin) : csPin(csPin), clkPin(clkPin), dataPin(dataPin) {}

    // Initialise the SPI bus (SPI3_HOST; the display's QSPI uses SPI2_HOST).
    void init() override;

    // Current shaft angle in radians, 0..2PI (filtered). Use update() from outside.
    float getSensorAngle() override;

    MT6701Error getAndClearError();
    uint32_t crcErrorCount() const { return crcErrors; }

  private:
    int8_t csPin, clkPin, dataPin;
    spi_device_handle_t spiDevice = nullptr;
    spi_transaction_t spiTransaction = {};
    float x = 1.0f;
    float y = 0.0f;
    uint32_t lastUpdate = 0;
    MT6701Error lastError = {};
    uint32_t crcErrors = 0;
};

} // namespace knob

#endif // GAGGIMATE_KNOB
