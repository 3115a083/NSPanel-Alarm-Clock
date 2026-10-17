"""Exercise the actual renderer header, including changed-only writes and reset."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class NativeClockUiTests(unittest.TestCase):
    def test_actual_renderer_states_and_write_cache(self):
        compiler = shutil.which('g++')
        if not compiler:
            raise RuntimeError('g++ required to test actual UI renderer')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'ui.cpp'
            source.write_text(r'''
#include <cassert>
#include "alarm_ui.h"
#include "alarm_display_state.h"
#include "nspanel_alarm_identity.h"
int main() {
  using namespace wake_alarm;
  assert(matches_identity("a", "aa0011223344", "a", "aa0011223344"));
  assert(!matches_identity("a", "aa0011223344", "b", "bb0011223344"));
  assert(!matches_identity("a", "aa0011223344", "a", "bb0011223344"));
  assert(!matches_identity("", "", "", ""));
  DisplayState state;
  assert(!state.route(1, false));  // HA is irrelevant, display must be connected.
  assert(state.route(1, true));
  state.page();  // Stock/incorrect HMI responds without the v2 announcement.
  assert(!state.route(2, true));
  assert(state.route(3001, true));
  state.page();
  assert(state.route(6001, true));
  state.page();
  assert(!state.route(9001, true));  // No endless page loop on incompatible TFT.
  assert(std::string(state.status(true)) == "incompatible_tft_or_no_ack");
  state.announce();
  assert(state.ready && !state.route(12000, true));
  state.page();  // Screensaver or display page change; recover locally.
  assert(!state.ready && state.route(12001, true));
  state.announce();
  state.busy = true;
  assert(!state.route(15001, true));
  assert(std::string(state.status(true)) == "uploading");
  state.busy = false;
  state.setup();
  assert(!state.ready && state.brightness == -1 && state.route(15002, true));
  state.page();
  state.last_attempt = UINT32_MAX - 1000;
  assert(!state.route(1000, true));
  assert(state.route(2000, true));  // millis rollover.
  auto make = [](bool valid, bool enabled, int mask, bool ring, bool pending) {
    return clock_view(valid, 7, 5, 2026, 10, 15, enabled, 6, 30, mask, ring, pending);
  };
  auto v = make(true, true, 31, false, false);
  assert(v.text[0] == "Armed" && v.text[1] == "07:05");
  assert(v.text[2] == "2026-10-15" && v.text[4] == "06:30");
  assert(v.text[6] == "Mon Tue Wed Thu Fri");
  assert(make(false, true, 31, false, false).text[1] == "--:--");
  assert(make(false, true, 31, false, false).text[0] == "No time");
  assert(make(false, false, 0, true, true).text[0] == "Ringing");
  assert(make(false, false, 0, false, true).text[0] == "Snoozed");
  assert(make(true, true, 0, false, false).text[0] == "Off");
  assert(make(true, true, 0, false, false).text[6] == "No days selected");
  assert(make(true, false, 127, false, false).text[5] == "Off");
  assert(make(true, false, 127, false, false).text[4] == "--:--");
  ClockRenderer renderer;
  assert(&clock_renderer() == &clock_renderer());
  int writes = 0;
  auto write = [&](const char *, const std::string &) { ++writes; };
  renderer.render(v, write);
  assert(writes == 7);
  renderer.render(v, write);
  assert(writes == 7);
  v.text[1] = "07:06";
  renderer.render(v, write);
  assert(writes == 8);
  renderer.reset();
  renderer.render(v, write);
  assert(writes == 15);
}
''', encoding='utf-8')
            exe = Path(temp) / 'ui'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT / 'esphome'), str(source), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
