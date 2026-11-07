// Unit tests for the GaggiMate Knob's hardware-free logic: SmartKnob detent maths,
// HX711 press classification and the KnobNavigator interaction model (design §3).
// Host-side, no ESP32/Arduino/LVGL runtime — pio test -e native -f test_knob.

#ifndef PIO_UNIT_TESTING
#define PIO_UNIT_TESTING 1 // enables the knob sources (see src/display/knob/KnobBuild.h)
#endif

#include <unity.h>

#include <cmath>
#include <map>
#include <set>
#include <vector>

#include "display/knob/DetentModel.cpp"
#include "display/knob/KnobNavigator.cpp"
#include "display/knob/PressClassifier.cpp"

using namespace knob;

void setUp() {}
void tearDown() {}

// ---------------------------------------------------------------------------
// DetentModel
// ---------------------------------------------------------------------------

static HapticConfig navCfg(int32_t pos, int32_t min, int32_t max, uint32_t nonce = 1) {
    HapticConfig c = haptics::navigate();
    c.position = pos;
    c.minPosition = min;
    c.maxPosition = max;
    c.positionNonce = nonce;
    return c;
}

// Drive the model to an angle in small steps (as the 1 kHz loop would).
static DetentModel::Output driveTo(DetentModel &m, float &angle, float target, uint32_t &now) {
    DetentModel::Output out;
    const float step = degToRad(0.5f) * (target > angle ? 1.0f : -1.0f);
    while (std::fabs(target - angle) > std::fabs(step)) {
        angle += step;
        out = m.update(angle, 0.0f, now++);
    }
    angle = target;
    return m.update(angle, 0.0f, now++);
}

static void test_detent_snaps_past_snap_point() {
    DetentModel m;
    float angle = 0.0f;
    uint32_t now = 1;
    TEST_ASSERT_TRUE(m.applyConfig(navCfg(0, 0, 5), angle));
    const float w = m.config().positionWidthRadians;
    // SmartKnob convention: decreasing angle increases the position.
    driveTo(m, angle, -0.5f * w, now);
    TEST_ASSERT_EQUAL_INT32(0, m.position()); // not past the 0.55 snap point yet
    driveTo(m, angle, -0.6f * w, now);
    TEST_ASSERT_EQUAL_INT32(1, m.position());
    driveTo(m, angle, -2.6f * w, now);
    TEST_ASSERT_EQUAL_INT32(3, m.position());
    driveTo(m, angle, -0.5f * w, now);
    TEST_ASSERT_EQUAL_INT32(1, m.position()); // hysteresis: snaps back only 0.55 w past the detent centre
    driveTo(m, angle, -0.4f * w, now);
    TEST_ASSERT_EQUAL_INT32(0, m.position());
}

static void test_detent_endstop() {
    DetentModel m;
    float angle = 0.0f;
    uint32_t now = 1;
    m.applyConfig(navCfg(0, 0, 2), angle);
    const float w = m.config().positionWidthRadians;
    DetentModel::Output out = driveTo(m, angle, -6.0f * w, now);
    TEST_ASSERT_EQUAL_INT32(2, m.position());
    TEST_ASSERT_TRUE(out.outOfBounds);
    TEST_ASSERT_EQUAL_FLOAT(m.config().endstopStrengthUnit * 4.0f, m.proportionalGain(out.outOfBounds));
    TEST_ASSERT_TRUE(out.pidInput > 0.0f); // torque pushes back towards the last detent
    out = driveTo(m, angle, 6.0f * w, now);
    TEST_ASSERT_EQUAL_INT32(0, m.position());
    TEST_ASSERT_TRUE(out.outOfBounds);
}

static void test_detent_unbounded() {
    DetentModel m;
    float angle = 0.0f;
    uint32_t now = 1;
    HapticConfig c = haptics::wake();
    c.positionNonce = 7;
    m.applyConfig(c, angle);
    const float w = m.config().positionWidthRadians;
    driveTo(m, angle, 5.0f * w, now);
    TEST_ASSERT_TRUE(m.position() <= -4);
}

static void test_detent_nonce_recentres() {
    DetentModel m;
    float angle = 1.0f;
    uint32_t now = 1;
    m.applyConfig(navCfg(0, 0, 5, 1), angle);
    const float w = m.config().positionWidthRadians;
    driveTo(m, angle, 1.0f - 1.2f * w, now);
    TEST_ASSERT_EQUAL_INT32(1, m.position());
    // New config, same position number but new nonce: adopt it and centre on the current angle.
    m.applyConfig(navCfg(4, 0, 5, 2), angle);
    TEST_ASSERT_EQUAL_INT32(4, m.position());
    DetentModel::Output out = m.update(angle, 0.0f, now++);
    TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, out.pidInput);
    TEST_ASSERT_EQUAL_INT32(4, m.position());
    // Same nonce + same position: keep the detent where it was.
    driveTo(m, angle, angle - 0.3f * w, now);
    m.applyConfig(navCfg(4, 0, 5, 2), angle);
    out = m.update(angle, 0.0f, now++);
    TEST_ASSERT_TRUE(std::fabs(out.pidInput) > 0.1f * w);
}

static void test_detent_rejects_invalid_and_runaway() {
    DetentModel m;
    HapticConfig bad = navCfg(0, 0, 3);
    bad.snapPoint = 0.4f;
    TEST_ASSERT_FALSE(m.applyConfig(bad, 0.0f));
    bad = navCfg(0, 0, 3);
    bad.detentStrengthUnit = -1.0f;
    TEST_ASSERT_FALSE(m.applyConfig(bad, 0.0f));
    TEST_ASSERT_TRUE(m.applyConfig(navCfg(0, 0, 3), 0.0f));
    TEST_ASSERT_FALSE(m.update(0.0f, 61.0f, 1).torqueEnabled);
    TEST_ASSERT_TRUE(m.update(0.0f, 10.0f, 2).torqueEnabled);
}

static void test_detent_derivative_gain() {
    DetentModel m;
    HapticConfig c = navCfg(0, 0, 3);
    c.detentStrengthUnit = 1.0f;
    c.positionWidthRadians = degToRad(3.0f);
    m.applyConfig(c, 0.0f);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.08f, m.derivativeGain());
    c.positionWidthRadians = degToRad(25.0f);
    m.applyConfig(c, 0.0f);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.02f, m.derivativeGain());
}

static void test_detent_step_clamped() {
    HapticConfig c = navCfg(0, 0, 3);
    TEST_ASSERT_EQUAL_INT32(3, DetentModel::stepClamped(c, 2, 5));
    TEST_ASSERT_EQUAL_INT32(0, DetentModel::stepClamped(c, 1, -5));
    c.maxPosition = -1;
    TEST_ASSERT_EQUAL_INT32(-4, DetentModel::stepClamped(c, 1, -5));
}

// ---------------------------------------------------------------------------
// PressClassifier
// ---------------------------------------------------------------------------

struct PressRig {
    PressClassifier pc;
    uint32_t now = 1000;
    std::vector<PressEvent> events;
    explicit PressRig(PressSettings s = PressSettings()) : pc(s) {}
    // Feed `ms` worth of samples at 80 Hz (HX711 RATE high) — 12.5 ms per sample.
    void feed(int32_t raw, uint32_t ms, bool rotating = false) {
        const uint32_t until = now + ms;
        while (now < until) {
            now += 12;
            const PressEvent e = pc.onSample(raw, now, rotating);
            if (e != PressEvent::None)
                events.push_back(e);
        }
    }
    void expect(std::initializer_list<PressEvent> expected) {
        TEST_ASSERT_EQUAL_MESSAGE(expected.size(), events.size(), "event count");
        size_t i = 0;
        for (PressEvent e : expected) {
            TEST_ASSERT_EQUAL_MESSAGE(static_cast<int>(e), static_cast<int>(events[i]), "event kind");
            i++;
        }
        events.clear();
    }
};

static constexpr int32_t BASE = -150000; // typical HX711 idle offset

static void test_press_short() {
    PressRig r;
    r.feed(BASE, 500);
    r.feed(BASE + 25000, 300);
    r.expect({PressEvent::Down});
    r.feed(BASE, 200);
    r.expect({PressEvent::ShortPress});
    TEST_ASSERT_FALSE(r.pc.pressed());
}

static void test_press_long_fires_while_held() {
    PressRig r;
    r.feed(BASE, 500);
    r.feed(BASE + 25000, 550);
    r.expect({PressEvent::Down});
    r.feed(BASE + 25000, 150);
    r.expect({PressEvent::LongPress});
    r.feed(BASE + 25000, 1000);
    r.feed(BASE, 200);
    r.expect({}); // no short press after a long press
}

static void test_press_hysteresis_and_debounce() {
    PressRig r;
    r.feed(BASE, 500);
    // A single-sample spike is ignored (2-sample debounce).
    r.pc.onSample(BASE + 30000, r.now += 12, false);
    r.feed(BASE, 100);
    r.expect({});
    // Press, then sag to 0.7 of the press delta: still pressed (release at 0.5).
    r.feed(BASE + 25000, 100);
    r.feed(BASE + 14000, 200);
    TEST_ASSERT_TRUE(r.pc.pressed());
    r.feed(BASE + 5000, 100);
    TEST_ASSERT_FALSE(r.pc.pressed());
    r.expect({PressEvent::Down, PressEvent::ShortPress});
}

static void test_press_ignored_while_rotating() {
    PressRig r;
    r.feed(BASE, 500);
    r.feed(BASE + 25000, 300, true); // pushing while turning
    r.feed(BASE, 200);
    r.expect({});
    // Turning during a press cancels it.
    r.feed(BASE + 25000, 100);
    r.feed(BASE + 25000, 100, true);
    r.feed(BASE, 200);
    r.expect({PressEvent::Down, PressEvent::Cancelled});
}

static void test_press_baseline_tracks_drift() {
    PressRig r;
    r.feed(BASE, 300);
    // Slow drift of +12000 counts (0.6 of a press) over 6 s: tare follows, no press.
    for (int i = 0; i <= 60; i++)
        r.feed(BASE + i * 200, 100);
    r.expect({});
    TEST_ASSERT_FLOAT_WITHIN(1500.0f, BASE + 12000.0f, r.pc.baseline());
    // A real press relative to the new baseline still registers.
    r.feed(BASE + 12000 + 25000, 200);
    r.feed(BASE + 12000, 200);
    r.expect({PressEvent::Down, PressEvent::ShortPress});
}

static void test_press_negative_delta() {
    PressSettings s;
    s.pressDelta = -20000; // bridge wired the other way round
    PressRig r(s);
    r.feed(BASE, 300);
    r.feed(BASE + 25000, 200); // wrong direction: not a press
    r.feed(BASE, 300);
    r.expect({});
    r.feed(BASE - 25000, 200);
    r.feed(BASE, 200);
    r.expect({PressEvent::Down, PressEvent::ShortPress});
}

static void test_press_stuck_retares() {
    PressRig r;
    r.feed(BASE, 300);
    r.feed(BASE + 25000, 9000); // mechanical offset after a knock
    r.expect({PressEvent::Down, PressEvent::LongPress});
    TEST_ASSERT_FALSE(r.pc.pressed()); // re-tared after stuckRetareMs
    r.feed(BASE + 25000, 1000);
    r.expect({});
}

static void test_press_timer_direct() {
    PressTimer t;
    TEST_ASSERT_EQUAL(static_cast<int>(PressEvent::Down), static_cast<int>(t.update(true, 100)));
    TEST_ASSERT_EQUAL(static_cast<int>(PressEvent::None), static_cast<int>(t.update(true, 500)));
    TEST_ASSERT_EQUAL(static_cast<int>(PressEvent::ShortPress), static_cast<int>(t.update(false, 650)));
    TEST_ASSERT_EQUAL(static_cast<int>(PressEvent::Down), static_cast<int>(t.update(true, 1000)));
    TEST_ASSERT_EQUAL(static_cast<int>(PressEvent::LongPress), static_cast<int>(t.update(true, 1600)));
    TEST_ASSERT_EQUAL(static_cast<int>(PressEvent::None), static_cast<int>(t.update(false, 1700)));
}

static void test_press_calibrator() {
    PressCalibrator cal;
    uint32_t now = 0;
    cal.start(now);
    auto feed = [&](int32_t raw, uint32_t ms) {
        int registered = 0;
        for (uint32_t t = 0; t < ms; t += 12) {
            now += 12;
            const int32_t noise = static_cast<int32_t>((now * 7919) % 400) - 200; // +-200 counts
            registered += cal.onSample(raw + noise, now) ? 1 : 0;
        }
        return registered;
    };
    feed(BASE, 1200);
    TEST_ASSERT_EQUAL(static_cast<int>(PressCalibrator::State::Collecting), static_cast<int>(cal.state()));
    for (int i = 0; i < 3; i++) {
        TEST_ASSERT_EQUAL(0, feed(BASE + 30000 + i * 1000, 300));
        TEST_ASSERT_EQUAL(1, feed(BASE, 300));
    }
    TEST_ASSERT_EQUAL(static_cast<int>(PressCalibrator::State::Done), static_cast<int>(cal.state()));
    // 0.6 x average peak (~31000 + noise)
    TEST_ASSERT_INT32_WITHIN(400, 18600, cal.pressDelta());

    // Mixed directions fail; so does a timeout.
    cal.start(now);
    feed(BASE, 1200);
    feed(BASE + 30000, 200);
    feed(BASE, 200);
    feed(BASE - 30000, 200);
    feed(BASE, 200);
    feed(BASE + 30000, 200);
    feed(BASE, 200);
    TEST_ASSERT_EQUAL(static_cast<int>(PressCalibrator::State::Failed), static_cast<int>(cal.state()));
    cal.start(now);
    feed(BASE, PressCalibrator::TIMEOUT_MS + 500);
    TEST_ASSERT_EQUAL(static_cast<int>(PressCalibrator::State::Failed), static_cast<int>(cal.state()));
}

// ---------------------------------------------------------------------------
// KnobNavigator
// ---------------------------------------------------------------------------

struct FakeHost : NavigatorHost {
    std::set<Item> unavailable;
    std::map<Item, ValueRange> values;
    bool isAvailable(Item item) const override { return unavailable.count(item) == 0; }
    ValueRange valueRange(Item item) const override {
        auto it = values.find(item);
        return it == values.end() ? ValueRange{} : it->second;
    }
};

// Navigator + a virtual motor that honours the pushed haptic configs.
struct NavRig {
    FakeHost host;
    KnobNavigator nav{host};
    HapticConfig motor;
    int32_t pos = 0;
    uint32_t now = 10000;
    int configs = 0;
    std::vector<Action> actions;

    void sync() {
        HapticConfig c;
        if (nav.takeHapticConfig(c)) {
            configs++;
            if (c.positionNonce != motor.positionNonce)
                pos = c.position;
            motor = c;
            if (motor.bounded())
                pos = DetentModel::stepClamped(motor, pos, 0);
        }
        auto a = nav.takeActions();
        actions.insert(actions.end(), a.begin(), a.end());
    }
    void screen(Screen s) {
        nav.update(s, now);
        sync();
    }
    void turn(int detents) {
        const int dir = detents > 0 ? 1 : -1;
        for (int i = 0; i < std::abs(detents); i++) {
            const int32_t next = DetentModel::stepClamped(motor, pos, dir);
            if (next == pos)
                continue; // end stop: the motor doesn't report a change
            pos = next;
            nav.onPosition(pos, motor.positionNonce, now);
            now += 50;
            sync();
        }
    }
    void press(PressType t = PressType::Short) {
        nav.onPress(t, now);
        sync();
    }
    std::vector<Action> take() {
        std::vector<Action> out;
        out.swap(actions);
        return out;
    }
    void expectActions(std::initializer_list<Action> expected) {
        auto got = take();
        TEST_ASSERT_EQUAL_MESSAGE(expected.size(), got.size(), "action count");
        size_t i = 0;
        for (const Action &e : expected) {
            TEST_ASSERT_EQUAL_MESSAGE(static_cast<int>(e.type), static_cast<int>(got[i].type), "action type");
            TEST_ASSERT_EQUAL_MESSAGE(static_cast<int>(e.item), static_cast<int>(got[i].item), "action item");
            TEST_ASSERT_EQUAL_MESSAGE(e.delta, got[i].delta, "action delta");
            i++;
        }
    }
    void expectFocus(Item item) {
        TEST_ASSERT_EQUAL_STRING(KnobNavigator::itemName(item), KnobNavigator::itemName(nav.focusedItem()));
    }
};

static void test_nav_menu_focus_and_endstops() {
    NavRig r;
    r.screen(Screen::Menu);
    r.expectFocus(Item::MenuBrew);
    TEST_ASSERT_EQUAL_INT32(0, r.motor.minPosition);
    TEST_ASSERT_EQUAL_INT32(5, r.motor.maxPosition);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, degToRad(25.0f), r.motor.positionWidthRadians);
    r.turn(2);
    r.expectFocus(Item::MenuWater);
    r.turn(10); // hard end stop at the last item
    r.expectFocus(Item::MenuStandby);
    r.turn(-1);
    r.expectFocus(Item::MenuInfo);
    r.press();
    r.expectActions({{ActionType::Activate, Item::MenuInfo, 0}});
    r.press(PressType::Long); // already on the menu
    r.expectActions({});
}

static void test_nav_menu_without_grind() {
    NavRig r;
    r.host.unavailable.insert(Item::MenuGrind);
    r.screen(Screen::Menu);
    TEST_ASSERT_EQUAL_INT32(4, r.motor.maxPosition);
    r.turn(3);
    r.expectFocus(Item::MenuInfo);
    // Grind becomes available while on the menu: focus stays on Info, list grows.
    r.host.unavailable.clear();
    r.screen(Screen::Menu);
    r.expectFocus(Item::MenuInfo);
    TEST_ASSERT_EQUAL_INT32(5, r.motor.maxPosition);
    TEST_ASSERT_EQUAL_INT32(4, r.pos);
}

static void test_nav_standby_wakes_once() {
    NavRig r;
    r.screen(Screen::Standby);
    TEST_ASSERT_FALSE(r.motor.bounded());
    r.turn(5);
    r.expectActions({{ActionType::Wake, Item::None, 0}});
    r.now += KnobNavigator::WAKE_RETRY_MS;
    r.press();
    r.expectActions({{ActionType::Wake, Item::None, 0}});
}

static void test_nav_brew_edit_temperature() {
    NavRig r;
    r.host.values[Item::BrewTemp] = {93, 0, 160};
    r.screen(Screen::Brew);
    r.expectFocus(Item::BrewStart);
    TEST_ASSERT_EQUAL_INT32(3, r.pos);
    r.turn(-2);
    r.expectFocus(Item::BrewTemp);
    r.press();
    r.expectActions({{ActionType::EnterEdit, Item::BrewTemp, 0}});
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Edit), static_cast<int>(r.nav.mode()));
    TEST_ASSERT_EQUAL_INT32(93, r.pos);
    TEST_ASSERT_EQUAL_INT32(160, r.motor.maxPosition);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, degToRad(6.0f), r.motor.positionWidthRadians);
    r.turn(3);
    r.expectActions({{ActionType::Step, Item::BrewTemp, 1}, {ActionType::Step, Item::BrewTemp, 1}, {ActionType::Step, Item::BrewTemp, 1}});
    r.turn(-1);
    r.expectActions({{ActionType::Step, Item::BrewTemp, -1}});

    // The glue reveals the adjustments view: same item, still editing, knob not re-centred.
    const int before = r.configs;
    r.screen(Screen::BrewSettings);
    r.expectFocus(Item::BrewTemp);
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Edit), static_cast<int>(r.nav.mode()));
    TEST_ASSERT_EQUAL(before, r.configs);

    r.press();
    r.expectActions({{ActionType::LeaveEdit, Item::BrewTemp, 0}});
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Navigate), static_cast<int>(r.nav.mode()));
    TEST_ASSERT_EQUAL_INT32(0, r.pos);
    TEST_ASSERT_EQUAL_INT32(4, r.motor.maxPosition); // Temp, Target, Save, SaveAsNew, Accept
    r.turn(4);
    r.expectFocus(Item::BrewAccept);
    r.press();
    r.expectActions({{ActionType::Activate, Item::BrewAccept, 0}});
    r.press(PressType::Long);
    r.expectActions({{ActionType::Dismiss, Item::BrewAccept, 0}});
}

static void test_nav_edit_respects_value_limits() {
    NavRig r;
    r.host.values[Item::SteamTemp] = {158, 0, 160};
    r.screen(Screen::Steam);
    r.expectFocus(Item::SteamTemp);
    r.press();
    r.take();
    r.turn(5);
    r.expectActions({{ActionType::Step, Item::SteamTemp, 1}, {ActionType::Step, Item::SteamTemp, 1}});
    r.press(PressType::Long); // long press also leaves Edit mode
    r.expectActions({{ActionType::LeaveEdit, Item::SteamTemp, 0}});
    r.press(PressType::Long);
    r.expectActions({{ActionType::BackToMenu, Item::None, 0}});
}

static void test_nav_ignores_stale_reports() {
    NavRig r;
    r.screen(Screen::Menu);
    const uint32_t oldNonce = r.motor.positionNonce;
    r.screen(Screen::Brew);
    r.nav.onPosition(1, oldNonce, r.now); // crossed the config change in the queue
    r.sync();
    r.expectFocus(Item::BrewStart);
    r.nav.onPosition(1, r.motor.positionNonce, r.now);
    r.sync();
    r.expectFocus(Item::BrewTemp);
}

static void test_nav_brew_running() {
    NavRig r;
    r.screen(Screen::BrewRunning);
    TEST_ASSERT_EQUAL_INT32(0, r.motor.minPosition);
    TEST_ASSERT_EQUAL_INT32(0, r.motor.maxPosition);
    r.turn(3);
    r.expectActions({});
    r.press();
    r.expectActions({{ActionType::Stop, Item::None, 0}});
    r.press(PressType::Long);
    r.expectActions({{ActionType::BackToMenu, Item::None, 0}});
}

static void test_nav_confirm_dialog() {
    NavRig r;
    r.screen(Screen::BrewConfirm);
    r.expectFocus(Item::ConfirmBack);
    r.turn(1);
    r.expectFocus(Item::ConfirmIgnore);
    r.press();
    r.expectActions({{ActionType::Activate, Item::ConfirmIgnore, 0}});
    r.press(PressType::Long);
    r.expectActions({{ActionType::Dismiss, Item::ConfirmIgnore, 0}});
}

static void test_nav_profile_chooser() {
    NavRig r;
    r.host.values[Item::ProfileChoice] = {0, 0, 2};
    r.screen(Screen::Brew);
    r.turn(-3);
    r.expectFocus(Item::BrewProfile);
    r.press();
    r.expectActions({{ActionType::Activate, Item::BrewProfile, 0}});
    r.screen(Screen::Profile);
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Edit), static_cast<int>(r.nav.mode()));
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, degToRad(20.0f), r.motor.positionWidthRadians);
    r.turn(5); // end stop at the last profile
    r.expectActions({{ActionType::Step, Item::ProfileChoice, 1}, {ActionType::Step, Item::ProfileChoice, 1}});
    r.turn(-1);
    r.expectActions({{ActionType::Step, Item::ProfileChoice, -1}});
    r.press();
    r.expectActions({{ActionType::Activate, Item::ProfileChoice, 0}});
    r.press(PressType::Long);
    r.expectActions({{ActionType::Dismiss, Item::ProfileChoice, 0}});
    // Back on the brew screen: Navigate mode on the default item.
    r.screen(Screen::Brew);
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Navigate), static_cast<int>(r.nav.mode()));
    r.expectFocus(Item::BrewStart);
}

static void test_nav_grind_and_unbounded_target() {
    NavRig r;
    r.screen(Screen::Grind);
    r.expectFocus(Item::GrindStartStop);
    r.press();
    r.expectActions({{ActionType::Activate, Item::GrindStartStop, 0}});
    r.turn(-1);
    r.expectFocus(Item::GrindTarget);
    r.press();
    r.expectActions({{ActionType::EnterEdit, Item::GrindTarget, 0}});
    TEST_ASSERT_FALSE(r.motor.bounded());
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, degToRad(5.0f), r.motor.positionWidthRadians);
    r.turn(-30);
    auto steps = r.take();
    TEST_ASSERT_EQUAL(30, steps.size());
    TEST_ASSERT_EQUAL_INT32(-1, steps.back().delta);
}

static void test_nav_edit_item_disappears() {
    NavRig r;
    r.screen(Screen::Grind);
    r.turn(-1);
    r.press();
    r.take();
    r.host.unavailable.insert(Item::GrindTarget);
    r.screen(Screen::Grind);
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Navigate), static_cast<int>(r.nav.mode()));
    r.expectFocus(Item::GrindStartStop);
    TEST_ASSERT_EQUAL_INT32(0, r.motor.maxPosition);
}

static void test_nav_screen_change_resets_mode() {
    NavRig r;
    r.screen(Screen::Steam);
    r.press();
    r.take();
    r.screen(Screen::Menu);
    TEST_ASSERT_EQUAL(static_cast<int>(Mode::Navigate), static_cast<int>(r.nav.mode()));
    r.expectFocus(Item::MenuBrew);
    TEST_ASSERT_EQUAL_INT32(0, r.pos);
}

static void test_nav_info_and_water() {
    NavRig r;
    r.screen(Screen::Info);
    r.press();
    r.expectActions({});
    r.press(PressType::Long);
    r.expectActions({{ActionType::BackToMenu, Item::None, 0}});
    r.screen(Screen::Water);
    r.expectFocus(Item::WaterStartStop);
    r.press();
    r.expectActions({{ActionType::Activate, Item::WaterStartStop, 0}});
}

static void test_nav_save_enables_later() {
    NavRig r;
    r.host.unavailable = {Item::BrewSave, Item::BrewSaveAsNew};
    r.screen(Screen::BrewSettings);
    r.expectFocus(Item::BrewTemp);
    r.turn(2);
    r.expectFocus(Item::BrewAccept);
    r.host.unavailable.clear(); // profile became dirty
    r.screen(Screen::BrewSettings);
    r.expectFocus(Item::BrewAccept);
    TEST_ASSERT_EQUAL_INT32(4, r.pos);
}

int main(int, char **) {
    UNITY_BEGIN();
    RUN_TEST(test_detent_snaps_past_snap_point);
    RUN_TEST(test_detent_endstop);
    RUN_TEST(test_detent_unbounded);
    RUN_TEST(test_detent_nonce_recentres);
    RUN_TEST(test_detent_rejects_invalid_and_runaway);
    RUN_TEST(test_detent_derivative_gain);
    RUN_TEST(test_detent_step_clamped);
    RUN_TEST(test_press_short);
    RUN_TEST(test_press_long_fires_while_held);
    RUN_TEST(test_press_hysteresis_and_debounce);
    RUN_TEST(test_press_ignored_while_rotating);
    RUN_TEST(test_press_baseline_tracks_drift);
    RUN_TEST(test_press_negative_delta);
    RUN_TEST(test_press_stuck_retares);
    RUN_TEST(test_press_timer_direct);
    RUN_TEST(test_press_calibrator);
    RUN_TEST(test_nav_menu_focus_and_endstops);
    RUN_TEST(test_nav_menu_without_grind);
    RUN_TEST(test_nav_standby_wakes_once);
    RUN_TEST(test_nav_brew_edit_temperature);
    RUN_TEST(test_nav_edit_respects_value_limits);
    RUN_TEST(test_nav_ignores_stale_reports);
    RUN_TEST(test_nav_brew_running);
    RUN_TEST(test_nav_confirm_dialog);
    RUN_TEST(test_nav_profile_chooser);
    RUN_TEST(test_nav_grind_and_unbounded_target);
    RUN_TEST(test_nav_edit_item_disappears);
    RUN_TEST(test_nav_screen_change_resets_mode);
    RUN_TEST(test_nav_info_and_water);
    RUN_TEST(test_nav_save_enables_later);
    return UNITY_END();
}
