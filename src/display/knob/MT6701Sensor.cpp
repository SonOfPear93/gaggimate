// Ported from smartknob firmware/src/mt6701_sensor.cpp
//   smartknob - Copyright 2022 Scott Bezek
//   Licensed under the Apache License, Version 2.0 (the "License"); you may not use
//   this file except in compliance with the License. You may obtain a copy of the
//   License at http://www.apache.org/licenses/LICENSE-2.0
//   Unless required by applicable law or agreed to in writing, software distributed
//   under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//   CONDITIONS OF ANY KIND, either express or implied. See the License for the
//   specific language governing permissions and limitations under the License.
// See MT6701Sensor.h for the GaggiMate modifications.
#include "MT6701Sensor.h"
#ifdef GAGGIMATE_KNOB

namespace knob {

static constexpr float ALPHA = 0.4f;

static const uint8_t tableCRC6[64] = {
    0x00, 0x03, 0x06, 0x05, 0x0C, 0x0F, 0x0A, 0x09, 0x18, 0x1B, 0x1E, 0x1D, 0x14, 0x17, 0x12, 0x11,
    0x30, 0x33, 0x36, 0x35, 0x3C, 0x3F, 0x3A, 0x39, 0x28, 0x2B, 0x2E, 0x2D, 0x24, 0x27, 0x22, 0x21,
    0x23, 0x20, 0x25, 0x26, 0x2F, 0x2C, 0x29, 0x2A, 0x3B, 0x38, 0x3D, 0x3E, 0x37, 0x34, 0x31, 0x32,
    0x13, 0x10, 0x15, 0x16, 0x1F, 0x1C, 0x19, 0x1A, 0x0B, 0x08, 0x0D, 0x0E, 0x07, 0x04, 0x01, 0x02};

// 32-bit input data, right aligned; CRC6 (poly 0x43) over 18 bits.
static uint8_t CRC6_43_18bit(uint32_t w_InputData) {
    uint8_t b_Index = (uint8_t)(((uint32_t)w_InputData >> 12u) & 0x0000003Fu);
    uint8_t b_CRC = (uint8_t)(((uint32_t)w_InputData >> 6u) & 0x0000003Fu);
    b_Index = b_CRC ^ tableCRC6[b_Index];
    b_CRC = (uint8_t)((uint32_t)w_InputData & 0x0000003Fu);
    b_Index = b_CRC ^ tableCRC6[b_Index];
    return tableCRC6[b_Index];
}

void MT6701Sensor::init() {
    pinMode(csPin, OUTPUT);
    digitalWrite(csPin, HIGH);

    spi_bus_config_t busConfig = {};
    busConfig.mosi_io_num = -1;
    busConfig.miso_io_num = dataPin;
    busConfig.sclk_io_num = clkPin;
    busConfig.quadwp_io_num = -1;
    busConfig.quadhd_io_num = -1;
    busConfig.max_transfer_sz = 1000;
    ESP_ERROR_CHECK(spi_bus_initialize(SPI3_HOST, &busConfig, SPI_DMA_CH_AUTO));

    spi_device_interface_config_t deviceConfig = {};
    deviceConfig.mode = 1;
    deviceConfig.cs_ena_pretrans = 4;
    deviceConfig.clock_speed_hz = 4000000;
    deviceConfig.spics_io_num = csPin;
    deviceConfig.queue_size = 1;
    ESP_ERROR_CHECK(spi_bus_add_device(SPI3_HOST, &deviceConfig, &spiDevice));

    spiTransaction.flags = SPI_TRANS_USE_RXDATA;
    spiTransaction.length = 24;
    spiTransaction.rxlength = 24;
    spiTransaction.tx_buffer = nullptr;
    spiTransaction.rx_buffer = nullptr;

    // Prime the filter with a real reading, then let SimpleFOC initialise its velocity state.
    for (int i = 0; i < 10; i++) {
        lastUpdate = micros() - 1000;
        getSensorAngle();
    }
    Sensor::init();
}

float MT6701Sensor::getSensorAngle() {
    const uint32_t now = micros();
    if (now - lastUpdate > 100) {
        const esp_err_t ret = spi_device_polling_transmit(spiDevice, &spiTransaction);
        if (ret == ESP_OK) {
            const uint32_t spi32 =
                (spiTransaction.rx_data[0] << 16) | (spiTransaction.rx_data[1] << 8) | spiTransaction.rx_data[2];
            const uint32_t angleSpi = spi32 >> 10;
            const uint8_t receivedCrc = spi32 & 0x3F;
            const uint8_t calculatedCrc = CRC6_43_18bit(spi32 >> 6);

            if (receivedCrc == calculatedCrc) {
                const float newAngle = (float)angleSpi * 2 * PI / 16384;
                x = cosf(newAngle) * ALPHA + x * (1 - ALPHA);
                y = sinf(newAngle) * ALPHA + y * (1 - ALPHA);
            } else {
                lastError = {true, receivedCrc, calculatedCrc};
                crcErrors++;
            }
        }
        lastUpdate = now;
    }
    float rad = -atan2f(y, x);
    if (rad < 0) {
        rad += 2 * PI;
    }
    return rad;
}

MT6701Error MT6701Sensor::getAndClearError() {
    MT6701Error out = lastError;
    lastError = {};
    return out;
}

} // namespace knob

#endif // GAGGIMATE_KNOB
