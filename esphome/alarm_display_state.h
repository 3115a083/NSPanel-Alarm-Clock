#pragma once
#include <cstdint>
namespace wake_alarm {
// No HA readiness or Easy global state. Capability announcements are not auth.
struct DisplayState {
  bool ready{false};
  bool busy{false};
  uint8_t attempts{0};
  uint32_t last_attempt{0};
  int brightness{-1};
  void setup() { ready = false; attempts = 0; last_attempt = 0; brightness = -1; }
  void page() {
    // A failed route may itself emit sendme. Do not restart its retry budget.
    if (ready) { attempts = 0; last_attempt = 0; }
    ready = false;
    brightness = -1;
  }
  void announce() { ready = true; attempts = 0; brightness = -1; }
  bool route(uint32_t now, bool connected) {
    if (busy || ready || !connected || attempts >= 3) return false;
    if (attempts && uint32_t(now - last_attempt) < 3000) return false;
    ++attempts;
    last_attempt = now;
    return true;
  }
  const char *status(bool connected) const {
    return busy ? "uploading" : !connected ? "display_disconnected" :
           ready ? "clock_ready_v2" : attempts >= 3 ? "incompatible_tft_or_no_ack" : "waiting_for_clock_v2";
  }
};
inline DisplayState &display_state() { static DisplayState state; return state; }
}  // namespace wake_alarm
