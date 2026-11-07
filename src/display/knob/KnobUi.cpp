#include "KnobUi.h"
#ifdef GAGGIMATE_KNOB_UI

#include <Arduino.h>
#include <cstdint>
#include <cstring>
#include <display/core/Controller.h>
#include <display/core/constants.h>
#include <display/ui/default/DefaultUI.h>
#include <display/ui/default/eez/actions.h>
#include <display/ui/default/eez/eez-flow.h>
#include <display/ui/default/eez/screens.h>

namespace knob {

static constexpr lv_coord_t FOCUS_OUTLINE_WIDTH = 3;
static constexpr lv_coord_t EDIT_OUTLINE_WIDTH = 4;
static constexpr lv_coord_t FOCUS_OUTLINE_PAD = 6;

KnobUi &KnobUi::instance() {
    static KnobUi ui;
    return ui;
}

// Visible = valid, not hidden itself and no hidden ancestor.
static bool isVisible(lv_obj_t *obj) {
    if (obj == nullptr || !lv_obj_is_valid(obj))
        return false;
    for (lv_obj_t *o = obj; o != nullptr; o = lv_obj_get_parent(o)) {
        if (lv_obj_has_flag(o, LV_OBJ_FLAG_HIDDEN))
            return false;
    }
    return true;
}

static bool isEnabled(lv_obj_t *obj) { return isVisible(obj) && !lv_obj_has_state(obj, LV_STATE_DISABLED); }

Screen KnobUi::detectScreen() const {
    if (controller == nullptr || ui == nullptr)
        return Screen::None;
    switch (static_cast<ScreensEnum>(eez_flow_get_current_screen())) {
    case SCREEN_ID_STANDBY_SCREEN:
        return Screen::Standby;
    case SCREEN_ID_MENU_SCREEN_NEW:
        return Screen::Menu;
    case SCREEN_ID_BREW_SCREEN:
        if (ui->isBrewConfirmVisible())
            return Screen::BrewConfirm;
        return ui->getBrewScreenState() == BrewScreenState::Settings ? Screen::BrewSettings : Screen::Brew;
    case SCREEN_ID_STATUS_SCREEN:
        return Screen::BrewRunning;
    case SCREEN_ID_STEAM_SCREEN:
        return Screen::Steam;
    case SCREEN_ID_WATER_SCREEN:
        return Screen::Water;
    case SCREEN_ID_GRIND_SCREEN:
        return Screen::Grind;
    case SCREEN_ID_INFO_SCREEN:
        return Screen::Info;
    case SCREEN_ID_NEW_PROFILE_SCREEN:
        return Screen::Profile;
    default:
        return Screen::None;
    }
}

// The LVGL object that represents an item (gets the focus outline).
lv_obj_t *KnobUi::objectFor(Item item) const {
    const bool settingsView = nav.screen() == Screen::BrewSettings;
    switch (item) {
    case Item::MenuBrew:
        return objects.btn_brew_1;
    case Item::MenuSteam:
        return objects.btn_steam_1;
    case Item::MenuWater:
        return objects.btn_water_1;
    case Item::MenuGrind:
        return objects.btn_grind_1;
    case Item::MenuInfo:
        return objects.info_btn;
    case Item::MenuStandby:
        return objects.standby_btn;
    case Item::BrewProfile:
        return objects.profile_select_button;
    case Item::BrewTemp:
        // Normal brew view has no temperature widget of its own; the dial's readout stands in.
        return settingsView ? objects.temp_container : objects.brew_dials__temp_text;
    case Item::BrewTarget:
        if (!settingsView)
            return objects.mode_switch; // shows the active target (weight / time)
        return isVisible(objects.brew_target_weight_container) ? objects.brew_target_weight_container
                                                               : objects.brew_target_time_container;
    case Item::BrewStart:
        return objects.start_button;
    case Item::BrewSave:
        return objects.save_button;
    case Item::BrewSaveAsNew:
        return objects.save_as_new_button;
    case Item::BrewAccept:
        return objects.accept_button;
    case Item::SteamTemp:
        return objects.target_temp2;
    case Item::WaterStartStop:
        return objects.water_start_button;
    case Item::GrindTarget:
        return isVisible(objects.target_weight) ? objects.target_weight : objects.target_time;
    case Item::GrindStartStop:
        return objects.grind_start_button;
    case Item::ConfirmBack:
        return objects.confirm_back_button;
    case Item::ConfirmIgnore:
        return objects.confirm_ignore_button;
    case Item::ProfileChoice:
        return objects.select_profile_1;
    default:
        return nullptr;
    }
}

bool KnobUi::isAvailable(Item item) const {
    switch (item) {
    case Item::MenuGrind:
        return isVisible(objects.btn_grind_1);
    case Item::BrewSave:
    case Item::BrewSaveAsNew:
        return isEnabled(objectFor(item));
    case Item::BrewTarget:
        if (nav.screen() != Screen::BrewSettings)
            return true;
        return isVisible(objects.brew_target_weight_container) || isVisible(objects.brew_target_time_container);
    case Item::GrindTarget:
        return isVisible(objects.target_weight) || isVisible(objects.target_time);
    default:
        return true;
    }
}

ValueRange KnobUi::valueRange(Item item) const {
    ValueRange r; // unbounded by default: the controller clamps weight/time targets itself
    if (controller == nullptr)
        return r;
    switch (item) {
    case Item::BrewTemp:
        r.value = static_cast<int32_t>(lroundf(controller->getTargetTemp()));
        r.min = MIN_TEMP;
        r.max = MAX_TEMP;
        break;
    case Item::SteamTemp: {
        const bool dualBoiler = controller->getSystemInfo().capabilities.dualBoiler;
        r.value = static_cast<int32_t>(lroundf(dualBoiler ? controller->getTargetSteamTemp() : controller->getTargetTemp()));
        r.min = MIN_TEMP;
        r.max = MAX_TEMP;
        break;
    }
    case Item::ProfileChoice:
        if (ui != nullptr) {
            r.value = ui->getProfileIndex();
            r.min = 0;
            r.max = ui->getProfileCount() - 1;
            if (r.max < 0)
                r.max = 0;
        }
        break;
    default:
        break;
    }
    return r;
}

void KnobUi::step(Item item, int32_t delta) {
    const bool up = delta > 0;
    const int32_t count = delta > 0 ? delta : -delta;
    for (int32_t i = 0; i < count; i++) {
        switch (item) {
        case Item::BrewTemp:
            up ? action_on_brew_temp_raise(nullptr) : action_on_brew_temp_lower(nullptr);
            break;
        case Item::BrewTarget:
            up ? action_on_brew_time_raise(nullptr) : action_on_brew_time_lower(nullptr);
            break;
        case Item::SteamTemp:
            up ? action_on_steam_temp_raise(nullptr) : action_on_steam_temp_lower(nullptr);
            break;
        case Item::GrindTarget:
            up ? action_on_grind_time_raise(nullptr) : action_on_grind_time_lower(nullptr);
            break;
        case Item::ProfileChoice:
            up ? action_on_next_profile(nullptr) : action_on_previous_profile(nullptr);
            break;
        default:
            return;
        }
    }
    if (ui != nullptr)
        ui->markDirty();
}

void KnobUi::perform(const Action &action) {
    ESP_LOGD("KnobUi", "action %d item %s delta %d", static_cast<int>(action.type), KnobNavigator::itemName(action.item),
             static_cast<int>(action.delta));
    switch (action.type) {
    case ActionType::Wake:
        action_on_wakeup(nullptr);
        break;
    case ActionType::BackToMenu:
        action_on_menu_click(nullptr);
        break;
    case ActionType::Stop:
        action_on_brew_cancel(nullptr);
        break;
    case ActionType::Step:
        step(action.item, action.delta);
        break;
    case ActionType::EnterEdit:
        // Brew temperature/target live in the brew screen's adjustments view: reveal it while editing.
        if ((action.item == Item::BrewTemp || action.item == Item::BrewTarget) && nav.screen() == Screen::Brew)
            action_on_profile_settings(nullptr);
        break;
    case ActionType::LeaveEdit:
        break;
    case ActionType::Dismiss:
        switch (nav.screen()) {
        case Screen::BrewSettings:
            action_on_profile_accept(nullptr);
            break;
        case Screen::BrewConfirm:
            action_on_warning_back(nullptr);
            break;
        case Screen::Profile:
            if (ui != nullptr)
                ui->changeScreen(SCREEN_ID_BREW_SCREEN);
            break;
        default:
            break;
        }
        break;
    case ActionType::Activate:
        switch (action.item) {
        case Item::MenuBrew:
            action_on_brew_screen(nullptr);
            break;
        case Item::MenuSteam:
            action_on_steam_screen(nullptr);
            break;
        case Item::MenuWater:
            action_on_water_screen(nullptr);
            break;
        case Item::MenuGrind:
            action_on_grind_screen(nullptr);
            break;
        case Item::MenuInfo:
            action_on_info_screen(nullptr);
            break;
        case Item::MenuStandby:
            action_on_standby(nullptr);
            break;
        case Item::BrewProfile:
            action_on_profile_select(nullptr);
            break;
        case Item::BrewStart:
            action_on_brew_start(nullptr);
            break;
        case Item::BrewSave:
            action_on_profile_save(nullptr);
            break;
        case Item::BrewSaveAsNew:
            action_on_profile_save_as_new(nullptr);
            break;
        case Item::BrewAccept:
            action_on_profile_accept(nullptr);
            break;
        case Item::WaterStartStop:
            action_on_simple_process_toggle(nullptr);
            break;
        case Item::GrindStartStop:
            action_on_grind_toggle(nullptr);
            break;
        case Item::ConfirmBack:
            action_on_warning_back(nullptr);
            break;
        case Item::ConfirmIgnore:
            action_on_warning_ignore(nullptr);
            break;
        case Item::ProfileChoice:
            action_on_profile_load(nullptr);
            break;
        default:
            break;
        }
        break;
    }
}

void KnobUi::hideRing() {
    if (ring != nullptr && lv_obj_is_valid(ring))
        lv_obj_add_flag(ring, LV_OBJ_FLAG_HIDDEN);
}

void KnobUi::updateHighlight() {
    lv_obj_t *target = objectFor(nav.focusedItem());
    if (target == nullptr || !isVisible(target) || lv_obj_get_screen(target) != lv_scr_act()) {
        hideRing();
        return;
    }
    if (ring == nullptr || !lv_obj_is_valid(ring)) {
        ring = lv_obj_create(lv_layer_top());
        lv_obj_remove_style_all(ring);
        lv_obj_clear_flag(ring, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_clear_flag(ring, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_opa(ring, LV_OPA_TRANSP, LV_PART_MAIN);
        lv_obj_set_style_border_opa(ring, LV_OPA_COVER, LV_PART_MAIN);
        ringTheme = UINT32_MAX;
        ringArea = {};
    }

    const uint32_t theme = eez_flow_get_selected_theme_index();
    const bool edit = nav.mode() == Mode::Edit;
    if (theme != ringTheme || edit != ringEdit) {
        ringTheme = theme;
        ringEdit = edit;
        const lv_color_t accent = lv_color_hex(theme_colors[theme < 3 ? theme : 0][COLOR_ID_PROGRESS]);
        lv_obj_set_style_border_color(ring, accent, LV_PART_MAIN);
        lv_obj_set_style_border_width(ring, edit ? EDIT_OUTLINE_WIDTH : FOCUS_OUTLINE_WIDTH, LV_PART_MAIN);
        // Edit mode adds a glow, so "turning changes the value" is obvious.
        lv_obj_set_style_shadow_color(ring, accent, LV_PART_MAIN);
        lv_obj_set_style_shadow_width(ring, edit ? 24 : 0, LV_PART_MAIN);
        lv_obj_set_style_shadow_spread(ring, edit ? 2 : 0, LV_PART_MAIN);
        lv_obj_set_style_shadow_opa(ring, edit ? LV_OPA_70 : LV_OPA_TRANSP, LV_PART_MAIN);
    }

    lv_area_t area;
    lv_obj_get_coords(target, &area);
    lv_area_increase(&area, FOCUS_OUTLINE_PAD, FOCUS_OUTLINE_PAD);
    if (memcmp(&area, &ringArea, sizeof(area)) != 0) {
        ringArea = area;
        const lv_coord_t w = lv_area_get_width(&area);
        const lv_coord_t h = lv_area_get_height(&area);
        lv_obj_set_pos(ring, area.x1, area.y1);
        lv_obj_set_size(ring, w, h);
        // Round icons get a round ring, everything else a rounded rectangle.
        lv_obj_set_style_radius(ring, LV_ABS(w - h) < 8 ? LV_RADIUS_CIRCLE : 14, LV_PART_MAIN);
    }
    lv_obj_clear_flag(ring, LV_OBJ_FLAG_HIDDEN);
}

void KnobUi::loop(DefaultUI *ui, Controller *controller) {
    KnobInput *in = input.load();
    if (in == nullptr)
        return;
    this->ui = ui;
    this->controller = controller;
    const uint32_t now = millis();

    nav.update(detectScreen(), now);

    KnobEvent event;
    int budget = 32; // bounded per frame; the rest waits for the next loop
    bool screenMayChange = false;
    while (!screenMayChange && budget-- > 0 && in->pollEvent(event)) {
        if (event.type == KnobEvent::Type::Position)
            nav.onPosition(event.position, event.nonce, now);
        else
            nav.onPress(event.press, now);
        for (const Action &action : nav.takeActions()) {
            perform(action);
            // Let the UI settle (and the navigator see the new screen) before the next event.
            screenMayChange |= action.type != ActionType::Step && action.type != ActionType::LeaveEdit;
        }
    }

    HapticConfig config;
    if (nav.takeHapticConfig(config))
        in->applyHaptic(config);

    updateHighlight();
}

} // namespace knob

#endif // GAGGIMATE_KNOB_UI
