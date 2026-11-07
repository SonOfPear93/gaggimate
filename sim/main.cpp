// Desktop simulator entry point. Runs the real display Controller on a single
// cooperative loop on the main thread (LVGL/SDL must stay on the main thread on
// macOS), driving the firmware's loop methods directly since the FreeRTOS tasks
// are no-ops in the simulator.
#include "ESPAsyncWebServer.h"
#include "SdlDriver.h"
#include "SimKnob.h"
#include <Arduino.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <display/core/Controller.h>
#include <display/plugins/ShotHistoryPlugin.h>
#include <display/ui/default/DefaultUI.h>

// The generated UI event handlers reference this global (see main.h on device).
Controller controller;

int main(int argc, char **argv) {
    // Optional: `--screenshot <path> [delayMs]` renders for a bit, saves a BMP, exits.
    const char *shotPath = nullptr;
    unsigned long shotDelayMs = 4000;
    // GaggiMate Knob emulation: `--knob` turns it on at start (otherwise the first
    // wheel/arrow/Enter does); `--knob-script <keys>` replays knob input once the UI
    // is up, one key every 300 ms: r/l = turn +1/-1, p = press, P = long press,
    // . = wait, s = save a screenshot to <prefix>-<n>.bmp (`--knob-shots <prefix>`).
    bool knobOn = false;
    std::string knobScript;
    std::string knobShots = "knob";
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            shotPath = argv[++i];
            if (i + 1 < argc && argv[i + 1][0] != '-')
                shotDelayMs = strtoul(argv[++i], nullptr, 10);
        } else if (strcmp(argv[i], "--knob") == 0) {
            knobOn = true;
        } else if (strcmp(argv[i], "--knob-script") == 0 && i + 1 < argc) {
            knobOn = true;
            knobScript = argv[++i];
        } else if (strcmp(argv[i], "--knob-shots") == 0 && i + 1 < argc) {
            knobShots = argv[++i];
        }
    }

    controller.setup(); // builds the UI, installs the SDL driver, marks screen ready

    // The sim has a real network (the WebUI is reachable), so present as Wi-Fi
    // connected: seeding credentials sends setupWifi() down the STA path, and the
    // WiFi shim's begin() reports WL_CONNECTED. This makes the standby screen show
    // the clock and Wi-Fi icon (and avoids captive-portal AP mode). Seed only once.
    Settings &settings = controller.getSettings();
    if (settings.getWifiSsid().isEmpty())
        settings.setWifiSsid("GaggiMate-Sim");
    if (settings.getWifiPassword().isEmpty())
        settings.setWifiPassword("simulator");

    SdlDriver *drv = SdlDriver::getInstance();
    DefaultUI *ui = controller.getUI();
    const unsigned long start = millis();
    bool shotTaken = false;
    if (knobOn)
        SimKnob::instance().activate();
    size_t knobScriptPos = 0;
    unsigned long knobNextKey = start + 4000; // let the mock controller connect first
    int knobShotCount = 0;

    while (!drv->shouldQuit()) {
        controller.loop();      // connection lifecycle, comms pump, plugins
        controller.loopLogic(); // process + control logic (normally a FreeRTOS task)

        // Shot history sampling normally runs in its own FreeRTOS task (a no-op in
        // the sim), so drive record() here at its native cadence.
        {
            static unsigned long lastShotSample = 0;
            if (millis() - lastShotSample >= SHOT_LOG_SAMPLE_INTERVAL_MS) {
                lastShotSample = millis();
                ShotHistory.record();
            }
        }

        if (ui) {
            ui->loop();
            ui->loopProfiles();
        }
        gm_web_pump(); // service the embedded WebUI HTTP/WS server

        // Settings persistence normally runs in a deferred save task (a no-op in the
        // sim), so flush dirty settings to NVS periodically. save(true) is a cheap
        // no-op when nothing changed.
        {
            static unsigned long lastSave = 0;
            if (millis() - lastSave >= 2000) {
                lastSave = millis();
                controller.getSettings().save(true);
            }
        }

        drv->pumpAndRender();

        if (knobScriptPos < knobScript.size() && millis() >= knobNextKey) {
            knobNextKey = millis() + 300;
            switch (knobScript[knobScriptPos++]) {
            case 'r':
                SimKnob::instance().turn(1);
                break;
            case 'l':
                SimKnob::instance().turn(-1);
                break;
            case 'p':
                SimKnob::instance().injectPress(knob::PressType::Short);
                break;
            case 'P':
                SimKnob::instance().injectPress(knob::PressType::Long);
                break;
            case 's': {
                const std::string path = knobShots + "-" + std::to_string(++knobShotCount) + ".bmp";
                drv->screenshot(path.c_str());
                printf("[sim-knob] screenshot %s\n", path.c_str());
                break;
            }
            default:
                break;
            }
            if (knobScriptPos == knobScript.size() && !shotPath)
                break; // script finished: exit (handy for headless capture)
        }

        if (shotPath && !shotTaken && millis() - start >= shotDelayMs) {
            drv->screenshot(shotPath);
            shotTaken = true;
            break;
        }
        delay(5);
    }
    return 0;
}
