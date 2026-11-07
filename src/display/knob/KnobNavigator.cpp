#include "KnobBuild.h"
#ifdef GAGGIMATE_KNOB_LOGIC

#include "KnobNavigator.h"

namespace knob {

KnobNavigator::KnobNavigator(NavigatorHost &host) : host(host) {}

const std::vector<Item> &KnobNavigator::focusListFor(Screen screen) {
    // Design §3, per-screen focus lists in turn order.
    static const std::vector<Item> none{};
    static const std::vector<Item> menu{Item::MenuBrew,  Item::MenuSteam, Item::MenuWater,
                                        Item::MenuGrind, Item::MenuInfo,  Item::MenuStandby};
    static const std::vector<Item> brew{Item::BrewProfile, Item::BrewTemp, Item::BrewTarget, Item::BrewStart};
    static const std::vector<Item> brewSettings{Item::BrewTemp, Item::BrewTarget, Item::BrewSave, Item::BrewSaveAsNew,
                                                Item::BrewAccept};
    static const std::vector<Item> confirm{Item::ConfirmBack, Item::ConfirmIgnore};
    static const std::vector<Item> steam{Item::SteamTemp};
    static const std::vector<Item> water{Item::WaterStartStop};
    static const std::vector<Item> grind{Item::GrindTarget, Item::GrindStartStop};
    static const std::vector<Item> profile{Item::ProfileChoice};
    switch (screen) {
    case Screen::Menu:
        return menu;
    case Screen::Brew:
        return brew;
    case Screen::BrewSettings:
        return brewSettings;
    case Screen::BrewConfirm:
        return confirm;
    case Screen::Steam:
        return steam;
    case Screen::Water:
        return water;
    case Screen::Grind:
        return grind;
    case Screen::Profile:
        return profile;
    default:
        return none;
    }
}

ValueKind KnobNavigator::valueKindOf(Item item) {
    switch (item) {
    case Item::BrewTemp:
    case Item::SteamTemp:
        return ValueKind::Temperature;
    case Item::BrewTarget:
    case Item::GrindTarget:
        return ValueKind::WeightTime;
    case Item::ProfileChoice:
        return ValueKind::Profile;
    default:
        return ValueKind::None;
    }
}

// The primary action where there is one (so a press right after arriving does the
// obvious thing), the safe choice in dialogs, otherwise the first item.
Item KnobNavigator::defaultFocusFor(Screen screen) {
    switch (screen) {
    case Screen::Brew:
        return Item::BrewStart;
    case Screen::Grind:
        return Item::GrindStartStop;
    case Screen::BrewConfirm:
        return Item::ConfirmBack;
    default: {
        const auto &list = focusListFor(screen);
        return list.empty() ? Item::None : list.front();
    }
    }
}

const char *KnobNavigator::itemName(Item item) {
    static const char *const NAMES[] = {"None",        "MenuBrew",  "MenuSteam",      "MenuWater",     "MenuGrind",
                                        "MenuInfo",    "MenuStandby", "BrewProfile",  "BrewTemp",      "BrewTarget",
                                        "BrewStart",   "BrewSave",  "BrewSaveAsNew",  "BrewAccept",    "SteamTemp",
                                        "WaterStartStop", "GrindTarget", "GrindStartStop", "ConfirmBack", "ConfirmIgnore",
                                        "ProfileChoice"};
    static_assert(sizeof(NAMES) / sizeof(NAMES[0]) == static_cast<size_t>(Item::Count), "itemName table out of date");
    const auto i = static_cast<size_t>(item);
    return i < sizeof(NAMES) / sizeof(NAMES[0]) ? NAMES[i] : "?";
}

const char *KnobNavigator::screenName(Screen screen) {
    static const char *const NAMES[] = {"None",        "Standby",     "Menu",  "Brew",  "BrewSettings", "BrewRunning",
                                        "BrewConfirm", "Steam",       "Water", "Grind", "Info",         "Profile"};
    const auto i = static_cast<size_t>(screen);
    return i < sizeof(NAMES) / sizeof(NAMES[0]) ? NAMES[i] : "?";
}

std::vector<Item> KnobNavigator::buildList(Screen screen) const {
    std::vector<Item> list;
    for (Item item : focusListFor(screen)) {
        if (host.isAvailable(item))
            list.push_back(item);
    }
    return list;
}

int KnobNavigator::indexOf(Item item) const {
    for (size_t i = 0; i < focusList.size(); i++) {
        if (focusList[i] == item)
            return static_cast<int>(i);
    }
    return -1;
}

Item KnobNavigator::focusedItem() const {
    if (focusIndex < 0 || focusIndex >= static_cast<int>(focusList.size()))
        return Item::None;
    return focusList[focusIndex];
}

void KnobNavigator::update(Screen screen, uint32_t nowMs) {
    (void)nowMs;
    if (screen != currentScreen) {
        enterScreen(screen);
        return;
    }
    std::vector<Item> list = buildList(screen);
    if (list == focusList)
        return;
    const Item keep = focusedItem();
    focusList = std::move(list);
    const int idx = indexOf(keep);
    if (idx >= 0) {
        focusIndex = idx;
    } else {
        if (currentMode == Mode::Edit && !autoEdit(screen))
            currentMode = Mode::Navigate; // the item being edited went away
        const int def = indexOf(defaultFocusFor(screen));
        focusIndex = def >= 0 ? def : 0;
    }
    pushHaptics(false);
}

void KnobNavigator::enterScreen(Screen screen) {
    const Item keep = focusedItem();
    currentScreen = screen;
    focusList = buildList(screen);
    hasWoken = false;

    if (autoEdit(screen)) {
        focusIndex = 0;
        if (!focusList.empty()) {
            startEdit(focusList.front());
        } else {
            currentMode = Mode::Navigate;
            pushHaptics(true);
        }
        return;
    }

    // Same item on the new screen (e.g. Brew -> Brew settings while editing the
    // temperature): keep focus and mode, don't re-centre the knob mid-turn.
    const int kept = keep == Item::None ? -1 : indexOf(keep);
    if (kept >= 0) {
        focusIndex = kept;
        pushHaptics(false);
        return;
    }

    currentMode = Mode::Navigate;
    const int def = indexOf(defaultFocusFor(screen));
    focusIndex = def >= 0 ? def : 0;
    pushHaptics(true);
}

void KnobNavigator::startEdit(Item item) {
    currentMode = Mode::Edit;
    editRange = host.valueRange(item);
    if (editRange.min <= editRange.max) {
        if (editRange.value < editRange.min)
            editRange.value = editRange.min;
        if (editRange.value > editRange.max)
            editRange.value = editRange.max;
    }
    editPosition = editRange.value;
    pushHaptics(true);
}

void KnobNavigator::leaveEdit() {
    currentMode = Mode::Navigate;
    pushHaptics(true);
}

HapticConfig KnobNavigator::desiredHaptics() const {
    HapticConfig c;
    switch (currentScreen) {
    case Screen::None:
        c = haptics::locked();
        c.position = 0;
        return c;
    case Screen::Standby:
        c = haptics::wake();
        c.position = motorPosition;
        return c;
    default:
        break;
    }

    if (currentMode == Mode::Edit) {
        switch (valueKindOf(focusedItem())) {
        case ValueKind::Temperature:
            c = haptics::temperature();
            break;
        case ValueKind::Profile:
            c = haptics::profile();
            break;
        default:
            c = haptics::weightTime();
            break;
        }
        c.position = editPosition;
        c.minPosition = editRange.min;
        c.maxPosition = editRange.max;
        return c;
    }

    if (focusList.empty()) {
        c = haptics::locked();
        c.position = 0;
        return c;
    }
    c = haptics::navigate();
    c.minPosition = 0;
    c.maxPosition = static_cast<int32_t>(focusList.size()) - 1;
    c.position = focusIndex;
    return c;
}

void KnobNavigator::pushHaptics(bool force) {
    HapticConfig desired = desiredHaptics();
    if (!force && desired.sameShape(haptic) && desired.position == motorPosition)
        return;
    desired.positionNonce = ++nonce;
    haptic = desired;
    hapticDirty = true;
    motorPosition = desired.position;
}

bool KnobNavigator::takeHapticConfig(HapticConfig &out) {
    if (!hapticDirty)
        return false;
    hapticDirty = false;
    out = haptic;
    return true;
}

std::vector<Action> KnobNavigator::takeActions() {
    std::vector<Action> out;
    out.swap(pending);
    return out;
}

void KnobNavigator::wake(uint32_t nowMs) {
    if (hasWoken && nowMs - lastWakeMs < WAKE_RETRY_MS)
        return;
    hasWoken = true;
    lastWakeMs = nowMs;
    emit(ActionType::Wake);
}

void KnobNavigator::onPosition(int32_t position, uint32_t reportNonce, uint32_t nowMs) {
    if (reportNonce != haptic.positionNonce)
        return; // reflects an older config
    const int32_t delta = position - motorPosition;
    motorPosition = position;
    if (delta == 0)
        return;

    switch (currentScreen) {
    case Screen::None:
        return;
    case Screen::Standby:
        wake(nowMs);
        return;
    default:
        break;
    }

    if (currentMode == Mode::Edit) {
        editPosition = position;
        emit(ActionType::Step, focusedItem(), delta);
        return;
    }

    if (focusList.empty())
        return;
    int idx = position;
    const int last = static_cast<int>(focusList.size()) - 1;
    if (idx < 0)
        idx = 0;
    if (idx > last)
        idx = last;
    focusIndex = idx;
    if (idx != position)
        pushHaptics(true); // motor out of sync with the list: re-centre on the focus
}

void KnobNavigator::onPress(PressType type, uint32_t nowMs) {
    switch (currentScreen) {
    case Screen::None:
        return;
    case Screen::Standby:
        wake(nowMs);
        return;
    default:
        break;
    }

    const Item item = focusedItem();

    if (currentMode == Mode::Edit) {
        if (autoEdit(currentScreen)) {
            if (type == PressType::Short)
                emit(ActionType::Activate, item);
            else
                emit(ActionType::Dismiss, item);
            return;
        }
        emit(ActionType::LeaveEdit, item);
        leaveEdit();
        return;
    }

    if (type == PressType::Long) {
        switch (currentScreen) {
        case Screen::Menu:
            return; // already there
        case Screen::BrewSettings:
        case Screen::BrewConfirm:
        case Screen::Profile:
            emit(ActionType::Dismiss, item);
            return;
        default:
            emit(ActionType::BackToMenu);
            return;
        }
    }

    // Short press in Navigate mode.
    if (currentScreen == Screen::BrewRunning) {
        emit(ActionType::Stop);
        return;
    }
    if (item == Item::None)
        return;
    if (valueKindOf(item) != ValueKind::None) {
        emit(ActionType::EnterEdit, item);
        startEdit(item);
        return;
    }
    emit(ActionType::Activate, item);
}

} // namespace knob

#endif // GAGGIMATE_KNOB_LOGIC
