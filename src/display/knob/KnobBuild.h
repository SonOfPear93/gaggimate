// Build gating for the knob sources. Everything under src/display/knob is picked
// up by every display env's source filter, so each .cpp wraps itself in these
// guards and compiles to nothing in the stock builds.
//  - GAGGIMATE_KNOB_LOGIC: hardware-free knob logic + LVGL glue (knob board,
//    desktop simulator, native unit tests).
//  - GAGGIMATE_KNOB: the knob board itself (motor, encoder, HX711).
#pragma once

#if defined(GAGGIMATE_KNOB) || defined(GAGGIMATE_SIM) || defined(PIO_UNIT_TESTING)
#define GAGGIMATE_KNOB_LOGIC 1
#endif

#if defined(GAGGIMATE_KNOB) || defined(GAGGIMATE_SIM)
#define GAGGIMATE_KNOB_UI 1
#endif
