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
                 !valid ? "No time" : enabled && mask ? "Armed" : "Disarmed";
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
  view.text[4] = buf;
  view.text[5] = enabled ? "Enabled" : "Disabled";
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
  template<typename Writer> void render(const ClockView &view, Writer write) {
    static const char *const names[] = {"wa_state", "wa_time", "wa_date", "wa_label",
                                       "wa_alarm", "wa_enabled", "wa_days"};
    for (size_t i = 0; i < previous.size(); ++i) {
      if (fresh || view.text[i] != previous[i]) {
        write(names[i], view.text[i]);
        previous[i] = view.text[i];
      }
    }
    fresh = false;
  }
};
}  // namespace wake_alarm
