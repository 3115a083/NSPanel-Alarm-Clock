"""Host-side model tests for the intended ESPHome local scheduler.
These DO NOT compile ESPHome and are NOT a substitute for hardware fault injection.
Run: python -m unittest discover -s tests -v
"""
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


class LocalAlarmModel:
    def __init__(self, hour=6, minute=30, weekmask=31, enabled=True):
        self.hour = hour
        self.minute = minute
        self.weekmask = weekmask
        self.enabled = enabled
        self.last_date = 0
        self.pending = False
        self.ringing = False
        self.snooze_utc = None

    def tick(self, instant):
        """Mirrors the 15 minute catch-up and pending/snooze state machine."""
        if self.pending:
            if not self.ringing and (self.snooze_utc is None or instant >= self.snooze_utc):
                self.ringing = True
                self.snooze_utc = None
            return
        if not self.enabled:
            return
        local_now = instant.astimezone(BERLIN)
        for delta in (0, 1):
            candidate_day = (local_now - timedelta(days=delta)).date()
            if not (self.weekmask & 1 << candidate_day.weekday()):
                continue
            key = int(candidate_day.strftime("%Y%m%d"))
            if key == self.last_date:
                continue
            candidate = datetime(candidate_day.year, candidate_day.month, candidate_day.day,
                                 self.hour, self.minute, tzinfo=BERLIN)
            seconds = (instant - candidate.astimezone(timezone.utc)).total_seconds()
            if 0 <= seconds <= 900:
                self.last_date = key
                self.pending = self.ringing = True
                break

    def snooze(self, now, minutes=9):
        if self.pending:
            self.snooze_utc = now + timedelta(minutes=minutes)
            self.ringing = False

    def reboot(self):
        self.ringing = False  # volatile; pending and snooze are flash-backed

    def stop(self):
        self.pending = self.ringing = False
        self.snooze_utc = None


def berlin(y, m, d, h, minute, fold=0):
    return datetime(y, m, d, h, minute, tzinfo=BERLIN, fold=fold).astimezone(timezone.utc)


class AlarmTests(unittest.TestCase):
    def test_monday_triggers_exactly_once(self):
        a = LocalAlarmModel()
        now = berlin(2026, 10, 12, 6, 30)
        a.tick(now)
        self.assertTrue(a.ringing)
        a.stop()
        a.tick(now + timedelta(seconds=5))
        self.assertFalse(a.ringing)

    def test_never_early(self):
        a = LocalAlarmModel()
        a.tick(berlin(2026, 10, 12, 6, 29))
        self.assertFalse(a.ringing)

    def test_catchup_restart(self):
        a = LocalAlarmModel()
        a.tick(berlin(2026, 10, 12, 6, 42))
        self.assertTrue(a.ringing)

    def test_no_unbounded_catchup(self):
        a = LocalAlarmModel()
        a.tick(berlin(2026, 10, 12, 6, 46))
        self.assertFalse(a.ringing)

    def test_weekend_omitted(self):
        a = LocalAlarmModel()
        a.tick(berlin(2026, 10, 17, 6, 30))
        self.assertFalse(a.ringing)

    def test_sunday_selected(self):
        a = LocalAlarmModel(weekmask=64)
        a.tick(berlin(2026, 10, 18, 6, 30))
        self.assertTrue(a.ringing)

    def test_disabled(self):
        a = LocalAlarmModel(enabled=False)
        a.tick(berlin(2026, 10, 12, 6, 30))
        self.assertFalse(a.ringing)

    def test_snooze_without_ha(self):
        a = LocalAlarmModel()
        start = berlin(2026, 10, 12, 6, 30)
        a.tick(start)
        a.snooze(start, 9)
        a.tick(start + timedelta(minutes=8))
        self.assertFalse(a.ringing)
        a.tick(start + timedelta(minutes=9))
        self.assertTrue(a.ringing)

    def test_unacknowledged_restarts_after_reboot(self):
        a = LocalAlarmModel()
        start = berlin(2026, 10, 12, 6, 30)
        a.tick(start)
        a.reboot()
        a.tick(start + timedelta(minutes=2))
        self.assertTrue(a.ringing)

    def test_snooze_survives_reboot(self):
        a = LocalAlarmModel()
        start = berlin(2026, 10, 12, 6, 30)
        a.tick(start)
        a.snooze(start)
        a.reboot()
        a.tick(start + timedelta(minutes=8))
        self.assertFalse(a.ringing)
        a.tick(start + timedelta(minutes=9))
        self.assertTrue(a.ringing)

    def test_cross_midnight_catchup(self):
        a = LocalAlarmModel(hour=23, minute=59, weekmask=1)
        a.tick(berlin(2026, 10, 13, 0, 3))
        self.assertTrue(a.ringing)

    def test_spring_dst_weekday(self):
        a = LocalAlarmModel(hour=7, minute=0, weekmask=64)
        a.tick(berlin(2027, 3, 28, 7, 0))
        self.assertTrue(a.ringing)

    def test_fall_dst_duplicate_prevented(self):
        a = LocalAlarmModel(hour=2, minute=30, weekmask=64)
        a.tick(berlin(2026, 10, 25, 2, 30, fold=0))
        self.assertTrue(a.ringing)
        a.stop()
        a.tick(berlin(2026, 10, 25, 2, 30, fold=1))
        self.assertFalse(a.ringing)


if __name__ == "__main__":
    unittest.main()
