// GPIO map of the GaggiMate Knob main board ("knob-main", ESP32-S3-WROOM-1-N16R8).
// Source of truth: docs/superpowers/specs/2026-11-07-smartknob-input-design.md §5.
// If the hardware map changes, update that table, this header and
// KNOB_AMOLED_175_HW_CONFIG (drivers/AmoledDisplay/pin_config.h) together.
#pragma once

#include <cstdint>

namespace knob::pins {

// DRV8311H motor driver, 3x PWM mode (INHx = PWM, all INLx tied to DRV_EN).
constexpr int8_t DRV_SOA = 1;     // current-sense out A (ADC1), unused in rev 1
constexpr int8_t DRV_SOB = 2;     // current-sense out B (ADC1), unused in rev 1
constexpr int8_t DRV_NFAULT = 3;  // input, active low, 10 k pull-up (strapping pin, input only)
constexpr int8_t DRV_INHA = 4;    // PWM phase A
constexpr int8_t DRV_INHB = 5;    // PWM phase B
constexpr int8_t DRV_INHC = 18;   // PWM phase C
constexpr int8_t DRV_NSLEEP = 21; // high = driver awake (100 k pull-down)
constexpr int8_t DRV_EN = 47;     // drives all three INLx (enable / Hi-Z)

// Touch controller (CST9217 @ 0x5A), optional.
constexpr int8_t TP_SCL = 6;
constexpr int8_t TP_SDA = 7;
constexpr int8_t TP_RST = 8;
constexpr int8_t TP_INT = 9;

// 1.75" CO5300 AMOLED over QSPI.
constexpr int8_t LCD_CS = 10;
constexpr int8_t LCD_D0 = 11;
constexpr int8_t LCD_CLK = 12;
constexpr int8_t LCD_D1 = 13;
constexpr int8_t LCD_D2 = 14;
constexpr int8_t LCD_D3 = 15;
constexpr int8_t LCD_RST = 16;
constexpr int8_t LCD_EN = 17; // high = panel power on (load switch on board B)

// MT6701 magnetic encoder, SSI.
constexpr int8_t ENC_CS = 38;
constexpr int8_t ENC_CLK = 39;
constexpr int8_t ENC_DO = 40;

// HX711 strain-gauge ADC.
constexpr int8_t HX_SCK = 41;
constexpr int8_t HX_DOUT = 42;

constexpr int8_t STATUS_LED = 48; // optional single LED
constexpr int8_t BOOT_BUTTON = 0;

} // namespace knob::pins
