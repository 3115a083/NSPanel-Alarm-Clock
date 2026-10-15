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
int main() {
  using namespace wake_alarm;
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
  assert(make(true, true, 0, false, false).text[0] == "Disarmed");
  assert(make(true, true, 0, false, false).text[6] == "No days selected");
  assert(make(true, false, 127, false, false).text[5] == "Disabled");
  ClockRenderer renderer;
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
