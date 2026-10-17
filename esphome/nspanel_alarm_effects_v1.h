#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <algorithm>
namespace wake_alarm {
struct TonePreview {
  bool active{false};
  uint32_t started{0};
  bool begin(int preset,uint32_t now,bool pending,bool busy) {
    if (preset<0 || preset>3 || pending || busy) return false;
    active=true; started=now; return true;
  }
  bool stop() { const bool previous=active; active=false; return previous; }
  bool tick(uint32_t now,bool pending,bool busy) {
    return active && (pending || busy || uint32_t(now-started)>=5000) ? stop() : false;
  }
};
inline TonePreview &tone_preview() { static TonePreview state; return state; }
inline const char *alarm_tone(int preset) {
  static const char *tones[] = {
    "Wake:d=8,o=6,b=175:c,p,c,p,g,p,g,p,a,p,g,p",
    "Classic:d=8,o=6,b=160:a,p,a,p,a,p,a,p",
    "Gentle:d=4,o=5,b=100:c,e,g,c6",
    "Signal:d=8,o=6,b=180:c,g,c,g,c,g"};
  return tones[preset >= 0 && preset < 4 ? preset : 0];
}
inline const char *notice_tone(int preset) {
  static const char *tones[] = {"", "Door:d=4,o=5,b=120:e,c", "Beep:d=8,o=6,b=160:c,p,c",
    "Alert:d=8,o=6,b=180:a,p,a,p,a,p", "Soft:d=4,o=5,b=120:c,e,g"};
  return tones[preset >= 0 && preset < 5 ? preset : 0];
}
struct RelayRule {
  int mode{0}, delay_s{0}, duration_s{2}, max_on_s{3600};
  bool off_on_snooze{true}, retrigger{true}, require_gate{false}, auxiliary_buzzer{false};
  bool valid() const { return mode >= 0 && mode <= 4 && delay_s >= 0 && delay_s <= 600 &&
    duration_s >= 1 && duration_s <= 3600 && max_on_s >= 1 && max_on_s <= 86400; }
  bool operator==(const RelayRule &r) const { return mode==r.mode && delay_s==r.delay_s &&
    duration_s==r.duration_s && max_on_s==r.max_on_s && off_on_snooze==r.off_on_snooze &&
    retrigger==r.retrigger && require_gate==r.require_gate && auxiliary_buzzer==r.auxiliary_buzzer; }
};
struct AlarmRelay {
  RelayRule rule;
  bool waiting{false}, owned{false}, tail{false}, gate{false}, gate_valid{false};
  uint32_t wait_ms{0}, on_ms{0}, tail_ms{0}, gate_ms{0};
  bool allowed(uint32_t now) const { return !rule.require_gate ||
    (gate_valid && gate && uint32_t(now-gate_ms) <= 600000); }
  void manual() { waiting=false; owned=false; tail=false; }
  template<class W> void release(W write) { if (owned) write(false); manual(); }
  template<class W> void configure(const RelayRule &next, W write) {
    if (!next.valid() || rule==next) return;
    release(write); rule=next;
  }
  void start(uint32_t now, bool resume) {
    if (!rule.mode || (resume && !rule.retrigger) || waiting || owned || !allowed(now)) return;
    waiting=true; wait_ms=now;
  }
  template<class W> void snooze(W write) { if (rule.off_on_snooze) release(write); }
  template<class W> void stop(uint32_t now, W write) {
    waiting=false;
    if (!owned) return;
    if (rule.mode==2) release(write);
    else if (rule.mode==4 && !tail) { tail=true; tail_ms=now; }
  }
  template<class W> void tick(uint32_t now, W write) {
    if (waiting && uint32_t(now-wait_ms) >= uint32_t(rule.delay_s)*1000) {
      waiting=false;
      if (allowed(now)) { write(true); owned=true; on_ms=now; tail=false; }
    }
    const uint32_t cap = uint32_t(rule.auxiliary_buzzer ? std::min(rule.max_on_s,60) : rule.max_on_s)*1000;
    if (owned && (uint32_t(now-on_ms) >= cap ||
        (rule.mode==1 && uint32_t(now-on_ms) >= uint32_t(rule.duration_s)*1000) ||
        (tail && uint32_t(now-tail_ms) >= uint32_t(rule.duration_s)*1000))) release(write);
  }
};
struct Notice {
  int kind{0}, brightness{25}, preset{0};
  std::string title, message, token, action_label{"Action"};
  bool action_enabled{false}, sound_allowed{false};
  std::array<std::string,2> seen{};
  std::array<uint32_t,2> last_ms{};
  std::array<bool,2> had{};
  uint32_t started{0}, ttl_ms{0}, confirm_ms{0};
  bool confirming{false};
  static bool valid_token(const std::string &value) {
    if (value.empty() || value.size()>64) return false;
    for (unsigned char c:value) if (!((c>='a'&&c<='z') || (c>='A'&&c<='Z') ||
        (c>='0'&&c<='9') || c=='_' || c=='-')) return false;
    return true;
  }
  bool show(int next_kind,const std::string &next_token,const std::string &next_title,
      const std::string &next_message,int ttl,int tone,int level,int cooldown,uint32_t now) {
    tick(now);
    if (next_kind<1 || next_kind>2 || !valid_token(next_token) || ttl<5 || ttl>300 ||
        tone<0 || tone>4 || level<1 || level>100 || cooldown<0 || cooldown>300) return false;
    const int i=next_kind-1;
    if (seen[i]==next_token || kind>next_kind) return false;
    const bool cooling=had[i] && uint32_t(now-last_ms[i])<uint32_t(cooldown)*1000;
    if (cooling && kind!=next_kind) return false;
    seen[i]=next_token;
    if (!cooling) last_ms[i]=now;
    had[i]=true; sound_allowed=!cooling;
    kind=next_kind; token=next_token; title=next_title; message=next_message;
    if (!cooling) { ttl_ms=uint32_t(ttl)*1000; started=now; }
    preset=tone; brightness=level; confirming=false;
    return true;
  }
  void clear() { kind=0; confirming=false; }
  void clear_if(int source,const std::string &value) { if (source==kind && value==token) clear(); }
  void tick(uint32_t now) {
    if (kind && uint32_t(now-started)>=ttl_ms) clear();
    if (confirming && uint32_t(now-confirm_ms)>=5000) confirming=false;
  }
  // First deliberate action opens confirmation; a second within five seconds emits once.
  bool action(uint32_t now) {
    tick(now); if (!kind || !action_enabled) return false;
    if (!confirming) { confirming=true; confirm_ms=now; return false; }
    kind=0; confirming=false; return true;
  }
};
struct AlarmEffects {
  std::array<AlarmRelay,2> relays;
  Notice notice;
  bool writing{false}, previous_ringing{false}, previous_pending{false};
  bool has_automatic_output() const {
    for (const auto &relay:relays) if (relay.waiting || relay.owned) return true;
    return false;
  }
  template<class W> void output(int index,bool on,W write) { writing=true; write(index,on); writing=false; }
  template<class W> void release_all(W write) {
    for (int i=0;i<2;++i) relays[i].release([&](bool on){output(i,on,write);});
  }
  template<class W> void configure(int index,const RelayRule &rule,W write) {
    if (index<0 || index>1) return;
    relays[index].configure(rule,[&](bool on){output(index,on,write);});
  }
  template<class W> void tick(uint32_t now,bool ringing,bool pending,W write,std::array<bool,2> actual={false,false}) {
    for (int i=0;i<2;++i) {
      auto out=[&](bool on){output(i,on,write);};
      if (ringing && !previous_ringing && (!actual[i] || relays[i].owned)) relays[i].start(now,previous_pending);
      if (!ringing && previous_ringing && pending) relays[i].snooze(out);
      if (!pending && previous_pending) relays[i].stop(now,out);
      relays[i].tick(now,out);
    }
    previous_ringing=ringing; previous_pending=pending; notice.tick(now);
  }
};
inline AlarmEffects &effects() { static AlarmEffects state; return state; }
} // namespace wake_alarm
