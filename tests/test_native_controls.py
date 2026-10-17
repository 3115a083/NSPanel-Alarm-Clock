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
  assert(button_hint(1,2,"x","y")=="S:Snooze H:Stop");
  assert(button_hint(8,8,"Room lamp","Bad\"\\name")=="S:Room lam H:Bad  nam");
  PanelControls nav;
  nav.set_pages(127);
  nav.input("next",6,30,false,0); assert(nav.page==PanelPage::WEATHER); // Editor never traps navigation.
  nav.input("menu",6,30,false,1); assert(nav.menu_open);
  nav.touch(packet(200,240,true),2);
  assert(std::string(nav.touch(packet(200,240,false),3))=="page_6");
  nav.input("page_6",6,30,false,4); assert(nav.page==PanelPage::AGENDA && !nav.menu_open);
  nav.set_pages(3); assert(nav.page==PanelPage::CLOCK);
  assert(!nav.set_page(6,6,30,false));
  nav.input("edit",23,59,false,5);
  nav.input("hour_up",0,0,false,6); assert(nav.draft_hour==0);
  nav.input("minute_up",0,0,false,7); assert(nav.draft_minute==0);
  nav.touch(packet(400,200,true),100);
  assert(std::string(nav.repeat_touch(599)).empty());
  assert(std::string(nav.repeat_touch(600))=="minute_up");
  nav.input("minute_up",0,0,false,600);
  assert(std::string(nav.repeat_touch(700)).empty());
  assert(std::string(nav.touch(packet(400,200,false),800)).empty()); // No extra increment on release.
  assert(nav.draft_minute==1);
  nav.input("prev",6,30,false,801); assert(nav.page==PanelPage::CLOCK && !nav.editing); // Cancel discards.
  nav.touch(packet(20,305,true),802);
  assert(std::string(nav.touch(packet(20,305,false),803)).empty()); // Hints are not touch controls.
  nav.touch(packet(20,280,true),804);
  nav.tick(805,true,false); // Ringing render must not eat a paired touch release.
  assert(std::string(nav.touch(packet(20,280,false),806))=="prev");
  PanelControls idle;
  idle.night_mode=0; idle.dim_timeout_s=10; idle.page_timeout_s=20;
  idle.set_pages(127); idle.set_page(4,6,30,false);
  idle.tick(9999,false,false); assert(!idle.dimmed);
  idle.tick(10000,false,false); assert(idle.dimmed && idle.page==PanelPage::CLIMATE);
  idle.tick(20000,false,false); assert(idle.page==PanelPage::CLOCK);
  idle.tick(20001,true,false); assert(!idle.dimmed);
  idle.wakeup_page=2; idle.dark=true; idle.manual_black=true;
  idle.wake(20002); assert(idle.page==PanelPage::WEATHER && !idle.manual_black && !idle.dark);
  idle.set_pages(3); idle.dark=true; idle.wake(20003); assert(idle.page==PanelPage::CLOCK);
  idle.night_mode=1; idle.timeout_s=5; idle.wake(0); idle.tick(5000,false,false);
  assert(idle.dark && !idle.dimmed); // Night brightness takes priority over intermediate dimming.
  NightSchedule night;
  assert(night.mode(1,720,true,false,false)==1); // All day by default.
  night.enabled=true;
  assert(night.mode(1,1320,true,false,false)==1);
  assert(night.mode(1,419,true,false,false)==1);
  assert(night.mode(1,420,true,false,false)==0);
  assert(night.mode(1,720,true,false,false)==0);
  assert(night.mode(1,0,false,false,false)==0); // Invalid clock cannot apply schedule.
  night.blackout=true; night.requires_light=true;
  assert(night.mode(1,1380,true,true,true)==2); // Window AND selected light off.
  assert(night.mode(1,1380,true,false,true)==1);
  assert(night.mode(1,1380,true,true,false)==1); // Unknown/stale never triggers blackout.
  assert(night.mode(1,360,true,true,true)==1); // Exclusive end.
  night.requires_light=false;
  assert(night.mode(1,1380,true,false,false)==2);
  assert(in_clock_window(100,200,200)); // Equal endpoints mean 24 hours.
  assert(in_clock_window(500,400,600));
  assert(!in_clock_window(600,400,600));
  PanelControls ui;
  ui.tick(29999,false,false); assert(!ui.dark);
  ui.tick(30000,false,false); assert(ui.dark);
  ui.touch(packet(240,280,true),30001);
  assert(!ui.dark);
  assert(std::string(ui.touch(packet(240,280,false),30002)).empty()); // Wake only.
  ui.touch(packet(240,280,true),30003);
  assert(std::string(ui.touch(packet(240,280,false),30004))=="action");
  ui.input("action",6,30,false,30004);
  assert(ui.page==PanelPage::ALARM && ui.editing && !ui.draft_enabled);
  ui.input("minus",0,0,false,30005); assert(ui.draft_hour==5);
  ui.input("focus",0,0,false,30006);
  ui.input("plus",0,0,false,30007); assert(ui.draft_minute==31);
  ui.input("enabled",0,0,false,30008); assert(ui.draft_enabled);
  assert(std::string(ui.input("action",0,0,false,30009))=="save");
  ui.input("forward",0,0,false,30010);
  assert(!ui.editing && ui.page==PanelPage::CLOCK); // Disabled pages skipped, draft discarded.
  ui.pages=3|16|32|64;
  ui.input("forward",0,0,false,30011); assert(ui.page==PanelPage::CLIMATE);
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
  ui.tick(260001,false,false); assert(ui.page==PanelPage::AGENDA && !ui.dark);
  ui.tick(260002,false,false); assert(ui.page==PanelPage::CLOCK);
  ui.activity_ms=UINT32_MAX-10000; ui.tick(19998,false,false); assert(!ui.dark);
  ui.tick(20000,false,false); assert(ui.dark); // millis rollover.
}
''')
            exe=Path(temp)/'controls'
            subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'esphome'),str(source),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
