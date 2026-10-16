"""Compile and exercise the exact C++ scheduler included in firmware (Linux libc).
This validates scheduler code, not ESP32 hardware, Newlib behavior or flash durability.
"""
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
BERLIN = ZoneInfo("Europe/Berlin")

class NativeSchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++")
        if compiler is None:
            raise RuntimeError("g++ required to test actual firmware scheduler")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        source = pathlib.Path(cls.tmp.name) / "main.cpp"
        source.write_text("""
#include <cstdlib>
#include <iostream>
#include "nspanel_alarm_schedule_v2.h"
int main(int argc, char **argv) {
  if (argc != 7 && argc != 13) return 2;
  setenv("TZ", "CET-1CEST,M3.5.0,M10.5.0/3", 1);
  tzset();
  std::array<wake_alarm::DayPlan,2> plans{};
  if (argc == 13) {
    plans = {{{std::stoi(argv[7]), std::stoll(argv[8]), std::stoi(argv[9])},
              {std::stoi(argv[10]), std::stoll(argv[11]), std::stoi(argv[12])}}};
  }
  if (std::stoi(argv[6]) == 2)
    std::cout << wake_alarm::valid_plan(plans[0], std::stoll(argv[1]));
  else if (std::stoi(argv[6]) == 1)
    std::cout << wake_alarm::next_alarm(std::stoll(argv[1]), std::stoi(argv[2]),
        std::stoi(argv[3]), std::stoi(argv[4]), std::stoi(argv[5]), plans).epoch;
  else
    std::cout << wake_alarm::due_date(std::stoll(argv[1]), std::stoi(argv[2]),
        std::stoi(argv[3]), std::stoi(argv[4]), std::stoi(argv[5]), plans);
  return 0;
}
""", encoding="utf-8")
        cls.exe = pathlib.Path(cls.tmp.name) / "scheduler"
        subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-I", str(ROOT / "esphome"), str(source), "-o", str(cls.exe)], check=True)

    def due(self, date, hour=6, minute=30, mask=127, last=0, fold=0):
        now = datetime.fromisoformat(date).replace(tzinfo=BERLIN, fold=fold)
        args = [int(now.timestamp()), hour, minute, mask, last, 0]
        return int(subprocess.check_output([str(self.exe), *map(str, args)], text=True))

    def test_never_early_and_exact_time(self):
        self.assertEqual(self.due("2026-10-12T06:29:59"), 0)
        self.assertEqual(self.due("2026-10-12T06:30:00"), 20261012)

    def test_catchup_boundary(self):
        self.assertEqual(self.due("2026-10-12T06:45:00"), 20261012)
        self.assertEqual(self.due("2026-10-12T06:45:01"), 0)

    def test_weekmask_and_duplicate(self):
        self.assertEqual(self.due("2026-10-18T06:30:00", mask=31), 0)
        self.assertEqual(self.due("2026-10-18T06:30:00", mask=64), 20261018)
        self.assertEqual(self.due("2026-10-18T06:30:00", last=20261018), 0)

    def test_midnight_after_short_spring_day(self):
        # Subtracting 86400 seconds incorrectly selects Saturday here.
        self.assertEqual(self.due("2027-03-29T00:03:00", 23, 59, 64), 20270328)

    def test_ordinary_midnight(self):
        self.assertEqual(self.due("2026-10-13T00:03:00", 23, 59, 1), 20261012)

    def test_spring_missing_time_is_skipped(self):
        self.assertEqual(self.due("2027-03-28T03:30:00", 2, 30), 0)

    def test_fall_first_occurrence_only_even_without_saved_date(self):
        self.assertEqual(self.due("2026-10-25T02:30:00", 2, 30, fold=0), 20261025)
        self.assertEqual(self.due("2026-10-25T02:30:00", 2, 30, fold=1), 0)

    def test_backward_date_correction_does_not_repeat(self):
        self.assertEqual(self.due("2026-10-12T06:30:00", last=20261013), 0)

    def test_invalid_config_fails_closed(self):
        for hour, minute, mask in [(24, 30, 127), (6, 60, 127), (6, 30, 128), (6, 30, 0)]:
            self.assertEqual(self.due("2026-10-12T06:30:00", hour, minute, mask), 0)

    def with_plan(self, now, planned='2026-10-19T07:30:00', date=20261019, mask=31, last=0, next_alarm=False):
        stamp = lambda s: int(datetime.fromisoformat(s).replace(tzinfo=BERLIN).timestamp())
        args = [stamp(now), 7, 0, mask, last, int(next_alarm), date, stamp(planned), 2, 0, 0, 0]
        return int(subprocess.check_output([str(self.exe), *map(str,args)], text=True))

    def test_dated_later_alarm_suppresses_regular_only_on_that_date(self):
        self.assertEqual(self.with_plan('2026-10-19T07:00:00'), 0)
        self.assertEqual(self.with_plan('2026-10-19T07:30:00'), 20261019)
        self.assertEqual(self.with_plan('2026-10-20T07:00:00'), 20261020)

    def test_dated_alarm_works_without_weekdays_but_does_not_repeat_after_stop(self):
        self.assertEqual(self.with_plan('2026-10-19T07:30:00', mask=0), 20261019)
        self.assertEqual(self.with_plan('2026-10-19T07:30:00', last=20261019), 0)

    def test_corrupt_restored_date_does_not_suppress_regular_alarm(self):
        self.assertEqual(self.with_plan('2026-10-19T07:00:00', date=20261020), 20261019)

    def test_next_alarm_uses_same_exception_as_scheduler(self):
        expected = int(datetime(2026,10,19,7,30,tzinfo=BERLIN).timestamp())
        self.assertEqual(self.with_plan('2026-10-19T06:00:00', next_alarm=True), expected)

    def test_plan_validation_rejects_date_mismatch_expired_far_future_and_source(self):
        now = int(datetime(2026,10,19,6,tzinfo=BERLIN).timestamp())
        planned = now + 3600
        def valid(date, stamp, source):
            args = [now,7,0,31,0,2,date,stamp,source,0,0,0]
            return int(subprocess.check_output([str(self.exe), *map(str,args)], text=True))
        self.assertEqual(valid(0,0,0), 1)
        self.assertEqual(valid(20261019,planned,1), 1)
        self.assertEqual(valid(20261020,planned,1), 0)
        self.assertEqual(valid(20261019,now-901,1), 0)
        self.assertEqual(valid(20261023,now+4*86400,2), 0)
        self.assertEqual(valid(20261019,planned,3), 0)

