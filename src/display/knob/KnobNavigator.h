// KnobNavigator: the knob's interaction model (design doc §3), hardware- and
// LVGL-free so it runs in the native unit tests.
//
// Inputs (all on the UI thread):
//   update(screen)        every UI loop, with the screen/sub-state the UI shows
//   onPosition(pos,nonce) detent position reported by the motor (or simulator)
//   onPress(short|long)   classified knob presses
// Outputs:
//   takeActions()         what the UI glue must do (activate an item, step a
//                         value, go back to the menu, ...); the glue maps these to
//                         the existing EEZ action_* / Controller functions
//   takeHapticConfig()    a new haptic config for the motor, whenever the
//                         screen, focus list or mode changes
//   focusedItem()/mode()  what to highlight
//
// The motor owns the absolute detent position. In Navigate mode the position is
// the focus index (end stops at first/last item); in Edit mode it starts at the
// current value (end stops at the value's limits when known) and every detent
// becomes one Step action. Every pushed config carries a new nonce, and position
// reports tagged with an older nonce are dropped, so a report that crosses a
// config change in the queue can't be misapplied.
#pragma once

#include "HapticConfig.h"
#include <cstdint>
#include <vector>

namespace knob {

// What the UI is showing, as far as the knob cares.
enum class Screen : uint8_t {
    None,         // unknown / not handled (knob does nothing)
    Standby,      // any turn or press wakes
    Menu,         // main menu
    Brew,         // brew screen, normal view
    BrewSettings, // brew screen, adjustments view (temperature/target/save)
    BrewRunning,  // status screen while (or right after) brewing
    BrewConfirm,  // warning dialog on the brew screen
    Steam,
    Water,
    Grind,
    Info,
    Profile, // profile chooser (opened from Brew > Profile)
};

// Focusable things across all screens.
enum class Item : uint8_t {
    None,
    MenuBrew,
    MenuSteam,
    MenuWater,
    MenuGrind,
    MenuInfo,
    MenuStandby,
    BrewProfile,
    BrewTemp,
    BrewTarget,
    BrewStart,
    BrewSave,
    BrewSaveAsNew,
    BrewAccept,
    SteamTemp,
    WaterStartStop,
    GrindTarget,
    GrindStartStop,
    ConfirmBack,
    ConfirmIgnore,
    ProfileChoice, // the profile chooser's list (always in Edit mode)
    Count
};

enum class Mode : uint8_t { Navigate, Edit };

enum class ValueKind : uint8_t { None, Temperature, WeightTime, Profile };

enum class PressType : uint8_t { Short, Long };

enum class ActionType : uint8_t {
    Wake,       // leave standby
    Activate,   // "click" the item
    EnterEdit,  // started editing `item` (glue may need to reveal it)
    LeaveEdit,  // finished editing `item`
    Step,       // change `item` by `delta` steps (one per detent, signed)
    BackToMenu, // long press: go to the menu screen
    Dismiss,    // long press on a dialog / sub-view: cancel it
    Stop,       // stop the running process (status screen)
};

struct Action {
    ActionType type;
    Item item;
    int32_t delta;
    bool operator==(const Action &o) const { return type == o.type && item == o.item && delta == o.delta; }
};

// Current value + limits of an editable item. min > max = no end stops.
struct ValueRange {
    int32_t value = 0;
    int32_t min = 0;
    int32_t max = -1;
};

// Queries the navigator needs from the UI (implemented by the LVGL glue, faked in tests).
class NavigatorHost {
  public:
    virtual ~NavigatorHost() = default;
    // Is the item visible/enabled right now (e.g. Grind only when a grinder is set up,
    // Save only when the profile is dirty)?
    virtual bool isAvailable(Item item) const = 0;
    // Current value and limits, sampled when Edit mode starts.
    virtual ValueRange valueRange(Item item) const = 0;
};

class KnobNavigator {
  public:
    explicit KnobNavigator(NavigatorHost &host);

    // Call every UI loop with the current screen. Handles screen changes and items
    // appearing/disappearing.
    void update(Screen screen, uint32_t nowMs);

    void onPosition(int32_t position, uint32_t nonce, uint32_t nowMs);
    void onPress(PressType type, uint32_t nowMs);

    // Pending actions for the glue (cleared by the call).
    std::vector<Action> takeActions();
    // True (and fills `out`) when a new haptic config must be sent to the motor.
    bool takeHapticConfig(HapticConfig &out);
    // The last config handed out (or pending).
    const HapticConfig &hapticConfig() const { return haptic; }

    Screen screen() const { return currentScreen; }
    Mode mode() const { return currentMode; }
    Item focusedItem() const;
    const std::vector<Item> &items() const { return focusList; }

    // Static description of the design's per-screen focus lists (unfiltered).
    static const std::vector<Item> &focusListFor(Screen screen);
    static ValueKind valueKindOf(Item item);
    static Item defaultFocusFor(Screen screen);
    static const char *itemName(Item item);
    static const char *screenName(Screen screen);

    // Minimum time between two Wake actions (turning the knob spins out many detents).
    static constexpr uint32_t WAKE_RETRY_MS = 1000;

  private:
    NavigatorHost &host;
    Screen currentScreen = Screen::None;
    Mode currentMode = Mode::Navigate;
    std::vector<Item> focusList;
    int focusIndex = 0;
    std::vector<Action> pending;

    HapticConfig haptic;
    bool hapticDirty = false;
    uint32_t nonce = 0;
    int32_t motorPosition = 0; // where the motor is (last report, or last pushed position)
    ValueRange editRange;      // sampled when Edit mode starts
    int32_t editPosition = 0;  // motor position while editing
    bool hasWoken = false;
    uint32_t lastWakeMs = 0;

    std::vector<Item> buildList(Screen screen) const;
    int indexOf(Item item) const;
    void enterScreen(Screen screen);
    void startEdit(Item item);
    void leaveEdit();
    void pushHaptics(bool forcePosition);
    HapticConfig desiredHaptics() const;
    void wake(uint32_t nowMs);
    void emit(ActionType type, Item item = Item::None, int32_t delta = 0) { pending.push_back({type, item, delta}); }
    static bool autoEdit(Screen screen) { return screen == Screen::Profile; }
};

} // namespace knob
