#pragma once
#include <array>
#include <cstdio>
#include <string>

namespace wake_alarm {
// Fixed English strings/numeric fields only. Never interpolate HA text into
// Nextion commands. Scheduler globals remain the single source of truth.
struct ClockView {
  std::array<std::string, 7> text;
};
inline ClockView clock_view(bool valid, int hour, int minute, int year, int month,
                            int day, bool enabled, int alarm_hour, int alarm_minute,
                            int mask, bool ringing, bool pending) {
  ClockView view;
  char buf[40];
  view.text[0] = ringing ? "Ringing" : pending ? "Snoozed" :
                 !valid ? "No time" : enabled && mask ? "Armed" : "Off";
  if (valid) {
    snprintf(buf, sizeof(buf), "%02d:%02d", hour, minute);
    view.text[1] = buf;
    snprintf(buf, sizeof(buf), "%04d-%02d-%02d", year, month, day);
    view.text[2] = buf;
  } else {
    view.text[1] = "--:--";
    view.text[2] = "Waiting for time sync";
  }
  view.text[3] = "ALARM TIME";
  snprintf(buf, sizeof(buf), "%02d:%02d", alarm_hour, alarm_minute);
  view.text[4] = enabled ? buf : "--:--";
  view.text[5] = enabled ? "On" : "Off";
  static const char *const days[] = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"};
  for (int i = 0; i < 7; ++i) {
    if (mask & (1 << i)) {
      if (!view.text[6].empty()) view.text[6] += ' ';
      view.text[6] += days[i];
    }
  }
  if (view.text[6].empty()) view.text[6] = "No days selected";
  return view;
}
struct ClockRenderer {
  std::array<std::string, 7> previous{};
  bool fresh{true};
  void reset() { fresh = true; }
  // Never write hidden native fields: Nextion text updates can repaint the
  // background beneath our coordinate-drawn controls.
  template<typename Writer> bool render(const ClockView &view, Writer write, unsigned visible = 127) {
    bool changed = false;
    static const char *const names[] = {"wa_state", "wa_time", "wa_date", "wa_label",
                                       "wa_alarm", "wa_enabled", "wa_days"};
    for (size_t i = 0; i < previous.size(); ++i) {
      if ((visible & (1u << i)) && (fresh || view.text[i] != previous[i])) {
        write(names[i], view.text[i]);
        previous[i] = view.text[i];
        changed = true;
      }
    }
    fresh = false;
    return changed;
  }
};
// ESPHome emits globals<T> storage before user includes in main.cpp. Keep the
// custom type out of YAML globals; lambdas see this header after it is included.
inline ClockRenderer &clock_renderer() {
  static ClockRenderer renderer;
  return renderer;
}
}  // namespace wake_alarm
