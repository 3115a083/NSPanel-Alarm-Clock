"""Run the production local relay/notice controller, including manual overrides."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class NativeEffectsTests(unittest.TestCase):
    def test_output_lifecycles_and_confirmed_notices(self):
        compiler = shutil.which('g++')
        if not compiler:
            raise RuntimeError('g++ required')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'effects.cpp'
            source.write_text(r'''
#include <cassert>
#include <vector>
#include "nspanel_alarm_effects_v1.h"
using namespace wake_alarm;
int main() {
  std::vector<bool> writes;
  auto write=[&](bool on){writes.push_back(on);};
  AlarmRelay r;
  r.start(0,false); r.tick(0,write); assert(writes.empty()); // Opt-in.
  RelayRule rule; rule.mode=1; rule.delay_s=1;
  r.configure(rule,write); r.start(0,false);
  r.tick(999,write); assert(writes.empty());
  r.tick(1000,write); assert(r.owned && writes.back());
  r.start(2000,false); r.tick(2999,write); assert(r.owned); // No deadline extension.
  r.tick(3000,write); assert(!r.owned && !writes.back());
  rule.mode=2; rule.delay_s=0; r.configure(rule,write);
  r.start(4000,false); r.tick(4000,write); r.stop(4100,write); assert(!r.owned && !writes.back());
  rule.mode=3; r.configure(rule,write); r.start(5000,false); r.tick(5000,write);
  r.stop(5100,write); assert(r.owned && writes.back());
  r.manual(); const auto manual_count=writes.size();
  r.tick(4000000,write); assert(writes.size()==manual_count); // Old timer cannot switch manual output.
  rule.mode=4; rule.duration_s=300; r.configure(rule,write);
  r.start(0,false); r.tick(0,write); r.stop(1000,write); r.stop(2000,write);
  r.tick(300999,write); assert(r.owned);
  r.tick(301000,write); assert(!r.owned); // Repeated Stop never extends tail.
  rule.mode=2; rule.delay_s=2; r.configure(rule,write); r.start(0,false); r.stop(1000,write);
  const auto stopped_count=writes.size(); r.tick(3000,write); assert(writes.size()==stopped_count);
  rule.delay_s=0; r.configure(rule,write); r.start(0,false); r.tick(0,write); r.snooze(write); assert(!r.owned);
  rule.retrigger=false; r.configure(rule,write); r.start(10,true); assert(!r.waiting);
  rule.retrigger=true; rule.off_on_snooze=false; r.configure(rule,write);
  r.start(20,true); r.tick(20,write); r.snooze(write); assert(r.owned);
  rule.mode=3; rule.auxiliary_buzzer=true; rule.max_on_s=86400; r.configure(rule,write);
  r.start(0,false); r.tick(0,write); r.tick(59999,write); assert(r.owned);
  r.tick(60000,write); assert(!r.owned); // Auxiliary buzzer hard cap.
  rule.mode=1; rule.delay_s=1; rule.require_gate=true; r.configure(rule,write);
  r.start(0,false); assert(!r.waiting); // Unknown at boot.
  r.gate=true; r.gate_valid=true; r.gate_ms=0; r.start(600001,false); assert(!r.waiting);
  r.gate_ms=600001; r.start(600001,false); assert(r.waiting);
  r.gate=false; r.tick(601001,write); assert(!r.owned && !r.waiting); // Recheck before delayed ON.
  rule.require_gate=false; rule.delay_s=0; rule.duration_s=2; rule.auxiliary_buzzer=false; r.configure(rule,write);
  r.start(UINT32_MAX-1000,false); r.tick(UINT32_MAX-1000,write); r.tick(999,write); assert(!r.owned);
  AlarmEffects effects;
  std::array<bool,2> actual{true,false};
  auto physical=[&](int index,bool on){assert(effects.writing); actual[index]=on;};
  rule.mode=1; effects.configure(0,rule,physical);
  effects.tick(0,true,true,physical,actual); effects.tick(3000,true,true,physical,actual);
  assert(actual[0] && !effects.relays[0].owned); // Already manually ON is never acquired.
  actual[0]=false; effects.tick(4000,false,false,physical,actual);
  effects.tick(5000,true,true,physical,actual); assert(actual[0]);
  effects.relays[0].manual(); actual[0]=true;
  effects.tick(9000,true,true,physical,actual); assert(actual[0] && !effects.writing);
  Notice n;
  assert(!n.show(1,"bad\"token","Door","text",30,1,25,5,0));
  assert(!n.show(1,"one","Door","text",301,1,25,5,0));
  assert(n.show(1,"one","Door","text",30,1,25,5,0));
  assert(!n.action(0) && !n.confirming); // Empty action is display-only.
  n.action_enabled=true;
  assert(!n.action(1) && n.confirming);
  assert(n.action(2) && n.kind==0); // Exactly one confirmed action.
  assert(!n.action(3));
  assert(!n.show(1,"one","Door","text",30,1,25,5,6000)); // Token replay ignored.
  assert(n.show(1,"two","Door","text",30,1,25,5,6000));
  assert(n.show(2,"alert","Alarm","text",30,3,25,5,6001)); // Alert preempts door.
  assert(!n.show(1,"three","Door","text",30,1,25,0,6002));
  n.clear_if(1,"two"); assert(n.kind==2); // Foreign clear cannot erase alert.
  assert(!n.action(6003)); n.tick(11003); assert(!n.confirming && n.kind==2);
  assert(!n.action(11004)); n.tick(36001); assert(n.kind==0); // Expiry never executes action.
  Notice refresh;
  assert(refresh.show(1,"first","Door","text",30,1,25,5,0));
  assert(refresh.sound_allowed);
  assert(refresh.show(1,"updated","Door","text",30,1,25,5,1000));
  assert(!refresh.sound_allowed && refresh.token=="updated" && refresh.started==0);
  refresh.tick(30000); assert(refresh.kind==0); // No indefinite renewal in cooldown.
  assert(n.show(1,"wrap","Door","text",5,1,25,0,UINT32_MAX-1000));
  n.tick(3999); assert(n.kind==0);
  for(int i=0;i<4;++i) assert(std::string(alarm_tone(i)).find(':')!=std::string::npos);
  assert(std::string(alarm_tone(99))==alarm_tone(0));
  assert(std::string(notice_tone(0)).empty());
}
''')
            exe = Path(temp) / 'effects'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-I', str(ROOT/'esphome'), str(source), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
