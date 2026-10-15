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
#include "alarm_schedule.h"
int main(int argc, char **argv) {
  if (argc != 7) return 2;
  setenv("TZ", "CET-1CEST,M3.5.0,M10.5.0/3", 1);
  tzset();
  std::cout << wake_alarm::due_date(std::stoll(argv[1]), std::stoi(argv[2]),
      std::stoi(argv[3]), std::stoi(argv[4]), std::stoi(argv[5]));
  return std::stoi(argv[6]);
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
