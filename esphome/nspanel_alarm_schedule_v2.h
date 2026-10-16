#pragma once
#define NSPANEL_ALARM_SCHEDULE_API_VERSION 2
#include <cstdint>
#include <ctime>
#include <array>

namespace wake_alarm {
struct DayPlan { int date; time_t epoch; int source; };
inline int civil_date(time_t epoch) {
  std::tm tm{};
  localtime_r(&epoch, &tm);
  return (tm.tm_year + 1900) * 10000 + (tm.tm_mon + 1) * 100 + tm.tm_mday;
}
inline bool valid_plan(const DayPlan &plan, time_t now) {
  if (plan.date == 0 && plan.epoch == 0 && plan.source == 0) return true;
  return plan.source >= 1 && plan.source <= 2 && plan.epoch > 1735689600 &&
         plan.epoch >= now - 900 && plan.epoch <= now + 3 * 86400 &&
         civil_date(plan.epoch) == plan.date;
}
inline const DayPlan *plan_for(int date, const std::array<DayPlan, 2> &plans) {
  for (const auto &plan : plans)
    if (plan.date == date && plan.epoch > 0 && plan.source >= 1 && plan.source <= 2 &&
        civil_date(plan.epoch) == date) return &plan;
  return nullptr;
}
// The same civil-time conversion is used for both catch-up and next-alarm UI.
inline time_t civil_alarm(std::tm day, int hour, int minute) {
  time_t first = static_cast<time_t>(-1);
  for (int dst = 0; dst <= 1; ++dst) {
    auto candidate = day;
    candidate.tm_hour = hour;
    candidate.tm_min = minute;
    candidate.tm_sec = 0;
    candidate.tm_isdst = dst;
    const time_t epoch = mktime(&candidate);
    std::tm roundtrip{};
    localtime_r(&epoch, &roundtrip);
    if (roundtrip.tm_year != day.tm_year || roundtrip.tm_mon != day.tm_mon ||
        roundtrip.tm_mday != day.tm_mday || roundtrip.tm_hour != hour ||
        roundtrip.tm_min != minute) continue;
    if (first == static_cast<time_t>(-1) || epoch < first) first = epoch;
  }
  return first;
}
// First occurrence of a repeated civil time wins. A nonexistent spring time is
// skipped. Round trips reject libc's implicit normalization of invalid times.
inline int due_date(time_t now, int hour, int minute, int mask, int last_date,
                    const std::array<DayPlan, 2> &plans = {}) {
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || mask < 0 || mask > 127)
    return 0;
  std::tm today{};
  localtime_r(&now, &today);
  for (int offset = 0; offset <= 1; ++offset) {
    std::tm day = today;
    day.tm_mday -= offset;
    day.tm_hour = 12;  // Civil-day arithmetic, not a fixed 86400-second day.
    day.tm_min = day.tm_sec = 0;
    day.tm_isdst = -1;
    if (mktime(&day) == static_cast<time_t>(-1)) continue;
    const int dow = (day.tm_wday + 6) % 7;
    const int date = (day.tm_year + 1900) * 10000 + (day.tm_mon + 1) * 100 + day.tm_mday;
    // Also prevent duplicate alarms after a backward date/time correction.
    if (date <= last_date) continue;
    const auto *plan = plan_for(date, plans);
    if (!plan && !(mask & (1 << dow))) continue;
    const time_t first = plan ? plan->epoch : civil_alarm(day, hour, minute);
    if (first != static_cast<time_t>(-1)) {
      const int64_t elapsed = static_cast<int64_t>(now) - static_cast<int64_t>(first);
      if (elapsed >= 0 && elapsed <= 900) return date;
    }
  }
  return 0;
}
inline DayPlan next_alarm(time_t now, int hour, int minute, int mask, int last_date,
                           const std::array<DayPlan, 2> &plans = {}) {
  std::tm today{};
  localtime_r(&now, &today);
  for (int offset = 0; offset <= 14; ++offset) {
    auto day = today;
    day.tm_mday += offset;
    day.tm_hour = 12;
    day.tm_min = day.tm_sec = 0;
    day.tm_isdst = -1;
    const auto noon = mktime(&day);
    if (noon == static_cast<time_t>(-1)) continue;
    const int date = civil_date(noon);
    if (date <= last_date) continue;
    const auto *plan = plan_for(date, plans);
    if (!plan && !(mask & (1 << ((day.tm_wday + 6) % 7)) )) continue;
    const time_t epoch = plan ? plan->epoch : civil_alarm(day, hour, minute);
    if (epoch >= now) return {date, epoch, plan ? plan->source : 0};
  }
  return {};
}
}  // namespace wake_alarm

