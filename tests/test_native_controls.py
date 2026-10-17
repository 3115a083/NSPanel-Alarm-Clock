"""Execute the actual screen controller, gesture decoder and formatting headers."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
class NativeControlsTests(unittest.TestCase):
    def test_night_gestures_editor_and_remote_write_protection(self):
        compiler=shutil.which('g++')
        if not compiler: raise RuntimeError('g++ required')
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'controls.cpp'
            source.write_text(r'''
#include <cassert>
#include "nspanel_alarm_controls.h"
#include "nspanel_alarm_identity.h"
using namespace wake_alarm;
std::vector<uint8_t> packet(int x, int y, bool down) {
  return {0x67,uint8_t(x>>8),uint8_t(x),uint8_t(y>>8),uint8_t(y),uint8_t(down),255,255,255};
}
int main() {
  assert(clock_digits(0,5,true)=="12:05");
  assert(clock_digits(12,5,true)=="12:05");
  assert(clock_digits(23,59,true)=="11:59");
  assert(clock_digits(23,59,false)=="23:59");
  assert(remaining_seconds(700,160)=="09:00");
  assert(remaining_seconds(700,701)=="00:00");
  assert(safe_text("a\"b\\c\nd",20)=="a b c d");
  assert(safe_text(std::string(100,'x')).size()==48);
  assert(!ui_edit_pending(0,2,1));
  assert(!ui_edit_pending(2,2,2));
  assert(ui_edit_pending(2,2,1));
  PanelControls ui;
  ui.tick(29999,false,false); assert(!ui.dark);
  ui.tick(30000,false,false); assert(ui.dark);
  ui.touch(packet(240,295,true),30001);
  assert(!ui.dark);
  assert(std::string(ui.touch(packet(240,295,false),30002)).empty()); // Wake only.
  ui.touch(packet(240,295,true),30003);
  assert(std::string(ui.touch(packet(240,295,false),30004))=="action");
  ui.input("action",6,30,false,30004);
  assert(ui.page==PanelPage::ALARM && ui.editing && !ui.draft_enabled);
  ui.input("prev",0,0,false,30005); assert(ui.draft_hour==5);
  ui.input("focus",0,0,false,30006);
  ui.input("next",0,0,false,30007); assert(ui.draft_minute==31);
  ui.input("enabled",0,0,false,30008); assert(ui.draft_enabled);
  assert(std::string(ui.input("action",0,0,false,30009))=="save");
  ui.input("forward",0,0,false,30010);
  assert(!ui.editing && ui.page==PanelPage::CLOCK); // Disabled pages skipped, draft discarded.
  ui.pages=3|16|32|64;
  ui.input("forward",0,0,false,30011); assert(ui.page==PanelPage::ALARM);
  ui.input("forward",0,0,false,30012); assert(ui.page==PanelPage::CLIMATE);
  assert(std::string(ui.input("plus",0,0,false,30013))=="climate_up");
  ui.touch(packet(100,100,true),30014);
  assert(std::string(ui.touch(packet(400,100,false),30015))=="back");
  assert(std::string(ui.touch(packet(400,100,false),30016)).empty()); // Unpaired release.
  assert(std::string(ui.touch({0x67,0,0},30017)).empty());
  ui.tick(90000,false,false); assert(ui.dark);
  ui.tick(90001,false,true); assert(!ui.dark && ui.page==PanelPage::CLOCK);
  ui.tick(90002,true,false); assert(!ui.dark);
  ui.night_mode=0; ui.tick(200000,false,false); assert(!ui.dark);
  ui.night_mode=2; ui.tick(200001,false,false); assert(ui.dark);
  ui.alarm_seen=true; ui.agenda_after_stop_s=60;
  ui.stopped(200002); assert(ui.page==PanelPage::AGENDA && !ui.alarm_seen);
  ui.tick(260001,false,false); assert(ui.page==PanelPage::AGENDA);
  ui.tick(260002,false,false); assert(ui.page==PanelPage::CLOCK);
  ui.activity_ms=UINT32_MAX-10000; ui.tick(19998,false,false); assert(!ui.dark);
  ui.tick(20000,false,false); assert(ui.dark); // millis rollover.
}
''')
            exe=Path(temp)/'controls'
            subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'esphome'),str(source),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
