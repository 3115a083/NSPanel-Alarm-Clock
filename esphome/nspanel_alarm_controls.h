#pragma once
#include <array>
#include <cstdint>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace wake_alarm {
inline float corrected_temperature(float raw, float offset) {
  if (!std::isfinite(raw) || !std::isfinite(offset) || raw < -40 || raw > 125 || offset < -10 || offset > 10)
    return NAN;
  return raw+offset;
}
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
inline std::string button_hint(int short_action,int long_action,const std::string &short_custom,const std::string &long_custom) {
  static const char *names[]={"None","Snooze","Stop","Prev","Next","Edit","-","+","Custom"};
  const auto label=[&](int action,const std::string &custom){
    return action==8 ? safe_text(custom,8) : std::string(action>=0 && action<=8 ? names[action] : "None");
  };
  return "S:"+label(short_action,short_custom)+" H:"+label(long_action,long_custom);
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
  bool menu_open{false};
  bool dimmed{false}, manual_black{false};
  uint32_t dim_timeout_s{0}, page_timeout_s{0};
  int wakeup_page{0};
  bool show_button_labels{true};
  std::array<std::string,4> custom_labels{{"Custom","Custom","Custom","Custom"}};
  uint32_t repeat_ms{0};
  bool repeated{false};
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
  void wake(uint32_t now) {
    if (dark && wakeup_page>=0 && wakeup_page<=6 && wakeup_page!=1 && (pages&(1<<wakeup_page))) {
      page=PanelPage(wakeup_page); editing=false; menu_open=false;
    }
    activity_ms=now; dark=false; dimmed=false; manual_black=false;
  }
  void tick(uint32_t now, bool ringing, bool prewake) {
    if (prewake && dark) { page = PanelPage::CLOCK; editing = false; }
    if (ringing) { menu_open=false; wake(now); page = PanelPage::CLOCK; editing = false; auto_agenda = false; }
    if (auto_agenda && uint32_t(now - agenda_started) >= uint32_t(agenda_after_stop_s) * 1000) {
      page = PanelPage::CLOCK; auto_agenda = false;
    }
    dark = !ringing && !prewake && !auto_agenda && night_mode != 0 && timeout_s != 0 &&
           uint32_t(now - activity_ms) >= timeout_s * 1000;
    const uint32_t idle=uint32_t(now-activity_ms);
    dimmed=!ringing && !prewake && !auto_agenda && !dark && dim_timeout_s>0 && idle>=dim_timeout_s*1000;
    if (!ringing && !auto_agenda && page_timeout_s>0 && idle>=page_timeout_s*1000) {
      page=PanelPage::CLOCK; menu_open=false; editing=false;
    }
    if (!notice.empty() && uint32_t(now - notice_ms) >= 4000) notice.clear();
  }
  void begin_edit(int hour, int minute, bool enabled) {
    menu_open=false; page = PanelPage::ALARM; editing = true; edit_minute = false;
    draft_hour = hour; draft_minute = minute; draft_enabled = enabled;
  }
  void navigate(int direction) {
    menu_open=false; editing = false; auto_agenda = false;
    for (int i = 0; i < 7; ++i) {
      page = PanelPage((int(page) + direction + 7) % 7);
      if (page != PanelPage::ALARM && (pages & (1 << int(page)))) return;
    }
    page = PanelPage::CLOCK;
  }
  void stopped(uint32_t now) {
    if (alarm_seen && agenda_after_stop_s > 0 && (pages & (1 << int(PanelPage::AGENDA)))) {
      wake(now); page = PanelPage::AGENDA; auto_agenda = true; agenda_started = now;
    }
    alarm_seen = false;
  }
  bool set_page(int next, int hour, int minute, bool enabled) {
    if (next<0 || next>6 || !(pages & (1<<next))) return false;
    menu_open=false; auto_agenda=false; editing=false;
    if (next==1) begin_edit(hour,minute,enabled); else page=PanelPage(next);
    return true;
  }
  void set_pages(int mask) {
    pages=(mask&127)|3;
    if (!(pages & (1<<int(page)))) { page=PanelPage::CLOCK; editing=false; }
  }
  static const char *page_title(int index) {
    static const char *names[]={"Clock","Set alarm","Weather","Entities","Thermostat","Humidifier","Calendar"};
    return index>=0 && index<7 ? names[index] : "";
  }
  static const char *edit_key(int x) {
    return x<130 ? "hour_down" : x<240 ? "hour_up" : x<350 ? "minute_down" : "minute_up";
  }
  const char *repeat_touch(uint32_t now) {
    if (!touch_down || touch_consumed || menu_open || page!=PanelPage::ALARM ||
        press_y<180 || press_y>=232 || uint32_t(now-press_ms)<500 || uint32_t(now-repeat_ms)<150) return "";
    repeat_ms=now; repeated=true;
    return edit_key(press_x);
  }
  const char *input(const std::string &key, int hour, int minute, bool enabled, uint32_t now) {
    wake(now);
    if (key=="menu") { menu_open=!menu_open; return ""; }
    if (key.size()==6 && key.compare(0,5,"page_")==0) {
      set_page(key[5]-'0',hour,minute,enabled); return "";
    }
    if (menu_open) {
      if (key=="action" || key=="prev") { menu_open=false; return ""; }
      if (key!="back" && key!="forward") return "";
    }
    if (key == "back" || key == "forward") { navigate(key == "back" ? -1 : 1); return ""; }
    if (key=="edit") { begin_edit(hour,minute,enabled); return ""; }
    if (page == PanelPage::ALARM && !editing) begin_edit(hour, minute, enabled);
    if (page == PanelPage::ALARM) {
      if (key=="prev") { page=PanelPage::CLOCK; editing=false; return ""; }
      if (key=="next") { menu_open=true; return ""; }
      if (key=="hour") edit_minute=false;
      if (key=="minute") edit_minute=true;
      if (key == "focus") edit_minute = !edit_minute;
      if (key == "enabled") draft_enabled = !draft_enabled;
      if (key=="hour_up" || key=="hour_down") {
        edit_minute=false; draft_hour=(draft_hour+(key=="hour_up"?1:23))%24;
      }
      if (key=="minute_up" || key=="minute_down") {
        edit_minute=true; draft_minute=(draft_minute+(key=="minute_up"?1:59))%60;
      }
      if (key=="minus" || key=="plus") {
        const int delta=key=="plus"?1:-1;
        if (edit_minute) draft_minute=(draft_minute+delta+60)%60;
        else draft_hour=(draft_hour+delta+24)%24;
      }
      if (key == "action") return "save";
    } else if (key == "prev" || key == "next") navigate(key == "next" ? 1 : -1);
    else if (key == "action" && page == PanelPage::CLOCK) begin_edit(hour, minute, enabled);
    else if (page == PanelPage::CLIMATE || page == PanelPage::HUMIDIFIER) {
      if (key == "minus") return page == PanelPage::CLIMATE ? "climate_down" : "humidity_down";
      if (key == "plus") return page == PanelPage::CLIMATE ? "climate_up" : "humidity_up";
      if (key == "action") return page == PanelPage::CLIMATE ? "climate_toggle" : "humidity_toggle";
    } else if (key=="action") menu_open=true;
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
      touch_consumed = dark; wake(now); touch_down = true; repeated=false; repeat_ms=now;
      press_x = x; press_y = y; press_ms = now; return "";
    }
    if (!touch_down) return "";
    touch_down = false; wake(now);
    if (touch_consumed || repeated || uint32_t(now - press_ms) > 3000) return "";
    const int dx = int(x) - press_x;
    if (dx > 100) return "back";
    if (dx < -100) return "forward";
    if (y>=294) return ""; // Physical-key labels are not touch buttons.
    if (y>=264) return x<100 ? "prev" : x>380 ? "next" : "action";
    if (menu_open) {
      if (y<42) return "menu";
      const int row=(y-42)/31; int current=0;
      static const char *keys[]={"page_0","page_1","page_2","page_3","page_4","page_5","page_6"};
      for (int i=0;i<7;++i) if (pages&(1<<i)) { if(current++==row) return keys[i]; }
      return "";
    }
    if (y<40) return "menu";
    if (page == PanelPage::ALARM) {
      if (y>=44 && y<138) return x<240 ? "hour" : "minute";
      if (y>=180 && y<232) return edit_key(x);
      if (y>=234 && y<262) return x<240 ? "enabled" : "preview_tone";
      return "";
    }
    if (page == PanelPage::CLIMATE || page == PanelPage::HUMIDIFIER)
      return x < 240 ? "minus" : "plus";
    return y >= 190 && page == PanelPage::CLOCK ? "edit" : "";
  }
};
inline PanelControls &panel_controls() { static PanelControls controls; return controls; }
}  // namespace wake_alarm
