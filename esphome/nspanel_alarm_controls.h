#pragma once
#include <array>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace wake_alarm {
inline bool ui_edit_pending(int profile, uint32_t revision, uint32_t acknowledged) {
  return profile == 2 && revision != acknowledged;
}
enum class PanelPage : uint8_t { CLOCK, ALARM, WEATHER, ENTITIES, CLIMATE, HUMIDIFIER, AGENDA };
inline std::string safe_text(const std::string &raw, size_t max = 48) {
  std::string result;
  for (unsigned char c : raw) {
    if (result.size() >= max) break;
    // Nextion set_component_text inserts a quoted command. Never pass raw HA text.
    result += c >= 32 && c < 127 && c != '"' && c != '\\' ? char(c) : ' ';
  }
  return result;
}
inline std::string clock_digits(int hour, int minute, bool twelve) {
  char text[12];
  snprintf(text, sizeof(text), "%02d:%02d", twelve ? (hour % 12 ? hour % 12 : 12) : hour, minute);
  return text;
}
inline std::string remaining_seconds(uint32_t deadline, uint32_t now) {
  const uint32_t left = deadline > now ? deadline - now : 0;
  char text[20];
  snprintf(text, sizeof(text), "%02lu:%02lu", (unsigned long)(left / 60), (unsigned long)(left % 60));
  return text;
}
// Civil wall-clock ranges, including overnight and equal-endpoint all-day ranges.
inline bool in_clock_window(int minute, int start, int end) {
  return start == end || (start < end ? minute >= start && minute < end : minute >= start || minute < end);
}
struct NightSchedule {
  bool enabled{false}, blackout{false}, requires_light{false};
  int start{1320}, end{420}, black_start{1380}, black_end{360};
  int mode(int base, int minute, bool clock_valid, bool light_off, bool light_valid) const {
    if (blackout && clock_valid && in_clock_window(minute, black_start, black_end) &&
        (!requires_light || (light_valid && light_off))) return 2;
    if (enabled && (!clock_valid || !in_clock_window(minute, start, end))) return 0;
    return base;
  }
};
struct PanelControls {
  PanelPage page{PanelPage::CLOCK};
  uint8_t pages{3};  // Clock + regular alarm editor, other pages explicitly enabled.
  NightSchedule night_schedule;
  bool light_off{false}, light_valid{false};
  uint32_t light_ms{0};
  bool dark{false};
  bool twelve{false};
  int night_mode{1};  // 0 disabled, 1 dim clock, 2 black.
  uint32_t timeout_s{30};
  int night_brightness{1};
  int prewake_minutes{0};
  int agenda_after_stop_s{0};
  uint32_t activity_ms{0};
  uint32_t agenda_started{0};
  bool auto_agenda{false};
  bool alarm_seen{false};
  bool consumed[2]{false, false};
  bool edit_minute{false};
  bool editing{false};
  int draft_hour{0}, draft_minute{0};
  bool draft_enabled{false};
  bool touch_down{false}, touch_consumed{false};
  uint16_t press_x{0}, press_y{0};
  uint32_t press_ms{0};
  std::array<std::string, 12> cards{};
  uint32_t cards_ms{0};
  bool agenda_error{false};
  std::string notice;
  uint32_t notice_ms{0};
  void wake(uint32_t now) { activity_ms = now; dark = false; }
  void tick(uint32_t now, bool ringing, bool prewake) {
    if (prewake && dark) { page = PanelPage::CLOCK; editing = false; }
    if (ringing) { wake(now); page = PanelPage::CLOCK; editing = false; auto_agenda = false; }
    if (auto_agenda && uint32_t(now - agenda_started) >= uint32_t(agenda_after_stop_s) * 1000) {
      page = PanelPage::CLOCK; auto_agenda = false;
    }
    dark = !ringing && !prewake && !auto_agenda && night_mode != 0 && timeout_s != 0 &&
           uint32_t(now - activity_ms) >= timeout_s * 1000;
    if (!notice.empty() && uint32_t(now - notice_ms) >= 4000) notice.clear();
  }
  void begin_edit(int hour, int minute, bool enabled) {
    page = PanelPage::ALARM; editing = true; edit_minute = false;
    draft_hour = hour; draft_minute = minute; draft_enabled = enabled;
  }
  void navigate(int direction) {
    editing = false; auto_agenda = false;
    for (int i = 0; i < 7; ++i) {
      page = PanelPage((int(page) + direction + 7) % 7);
      if (pages & (1 << int(page))) return;
    }
    page = PanelPage::CLOCK;
  }
  void stopped(uint32_t now) {
    if (alarm_seen && agenda_after_stop_s > 0 && (pages & (1 << int(PanelPage::AGENDA)))) {
      page = PanelPage::AGENDA; auto_agenda = true; agenda_started = now; wake(now);
    }
    alarm_seen = false;
  }
  const char *input(const std::string &key, int hour, int minute, bool enabled, uint32_t now) {
    wake(now);
    if (key == "back" || key == "forward") { navigate(key == "back" ? -1 : 1); return ""; }
    if (page == PanelPage::ALARM && !editing) begin_edit(hour, minute, enabled);
    if (page == PanelPage::ALARM) {
      if (key == "focus") edit_minute = !edit_minute;
      if (key == "enabled") draft_enabled = !draft_enabled;
      if (key == "prev" || key == "next") {
        const int delta = key == "next" ? 1 : -1;
        if (edit_minute) draft_minute = (draft_minute + delta + 60) % 60;
        else draft_hour = (draft_hour + delta + 24) % 24;
      }
      if (key == "action") return "save";
    } else if (key == "prev" || key == "next") navigate(key == "next" ? 1 : -1);
    else if (key == "edit" || (key == "action" && page == PanelPage::CLOCK)) begin_edit(hour, minute, enabled);
    else if (page == PanelPage::CLIMATE || page == PanelPage::HUMIDIFIER) {
      if (key == "minus") return page == PanelPage::CLIMATE ? "climate_down" : "humidity_down";
      if (key == "plus") return page == PanelPage::CLIMATE ? "climate_up" : "humidity_up";
      if (key == "action") return page == PanelPage::CLIMATE ? "climate_toggle" : "humidity_toggle";
    }
    return "";
  }
  const char *touch(const std::vector<uint8_t> &bytes, uint32_t now) {
    // sendxy=1 produces 0x67/0x68, Xhi,Xlo,Yhi,Ylo,event,FF,FF,FF.
    if (bytes.size() != 9 || (bytes[0] != 0x67 && bytes[0] != 0x68) ||
        bytes[6] != 255 || bytes[7] != 255 || bytes[8] != 255 || bytes[5] > 1) return "";
    const uint16_t x = (uint16_t(bytes[1]) << 8) | bytes[2];
    const uint16_t y = (uint16_t(bytes[3]) << 8) | bytes[4];
    if (x >= 480 || y >= 320) { touch_down = false; return ""; }
    if (bytes[5]) {
      touch_consumed = dark; wake(now); touch_down = true;
      press_x = x; press_y = y; press_ms = now; return "";
    }
    if (!touch_down) return "";
    touch_down = false; wake(now);
    if (touch_consumed || uint32_t(now - press_ms) > 3000) return "";
    const int dx = int(x) - press_x;
    if (dx > 100) return "back";
    if (dx < -100) return "forward";
    if (y >= 278) return x < 100 ? "prev" : x > 380 ? "next" : "action";
    if (page == PanelPage::ALARM) return y < 170 ? "focus" : x > 260 ? "enabled" : "";
    if (page == PanelPage::CLIMATE || page == PanelPage::HUMIDIFIER)
      return x < 240 ? "minus" : "plus";
    return y >= 190 && page == PanelPage::CLOCK ? "edit" : "";
  }
};
inline PanelControls &panel_controls() { static PanelControls controls; return controls; }
}  // namespace wake_alarm
