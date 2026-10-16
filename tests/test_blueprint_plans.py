"""Exercise the actual embedded blueprint template, not a second plan model."""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import ast
import unittest
import yaml
from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment
from test_config_structure import Loader

ROOT = Path(__file__).resolve().parents[1]
BP = yaml.load((ROOT/'homeassistant/blueprints/nspanel_alarm_settings.yaml').read_text(encoding='utf-8'), Loader=Loader)
TEMPLATE = next(a['variables']['day_plans'] for a in BP['actions'] if 'day_plans' in a.get('variables', {}))
TZ = ZoneInfo('Europe/Berlin')

def epoch(value):
    return int(datetime.fromisoformat(value).timestamp())

def plan(events=(), app_epoch=0, **changes):
    current = datetime(2026, 10, 18, 18, tzinfo=TZ)
    values = dict(master=True, app_on=False, app_epoch=app_epoch, calendar_on=True,
        weekdays=['mon','tue','wed','thu','fri'], calendar_free_days=False,
        calendars=['calendar.fixture'], calendar_reply={'calendar.fixture': {'events': list(events)}},
        lead_minutes=30, earliest='06:00:00', latest='08:30:00',
        calendar_mode='in_range', regular_hour=7, regular_minute=0)
    current = changes.pop('current', current)
    values.update(changes)
    env = NativeEnvironment(undefined=StrictUndefined)
    def timestamp(value, default=0):
        try:
            return value.timestamp() if isinstance(value, datetime) else datetime.fromisoformat(value).timestamp()
        except (ValueError, TypeError):
            return default
    env.globals.update(now=lambda: current, timedelta=timedelta, as_timestamp=timestamp,
        today_at=lambda clock: datetime.combine(current.date(), datetime.strptime(clock, '%H:%M').time(), TZ))
    env.filters['timestamp_custom'] = lambda value, fmt, local=True: datetime.fromtimestamp(value, TZ).strftime(fmt)
    env.filters['regex_match'] = lambda value, pattern: bool(re.match(pattern, value))
    result = env.from_string(TEMPLATE).render(**values)
    # HA strips rendered output before native-result parsing. Jinja's standalone
    # NativeEnvironment leaves leading template whitespace as a string.
    return ast.literal_eval(result.strip()) if isinstance(result, str) else result

class BlueprintPlanTests(unittest.TestCase):
    def test_missing_android_source_keeps_only_acknowledged_alarm_unless_clear(self):
        template = next(a['variables']['app_epoch'] for a in BP['actions'] if 'app_epoch' in a.get('variables', {}))
        saved = epoch('2026-10-19T07:00:00+02:00')
        env = NativeEnvironment(undefined=StrictUndefined)
        attrs = {('input_datetime.fixture','timestamp'): saved}
        states = {'sensor.phone':'unavailable', 'sensor.signature': f'0:0:0:20261019:{saved}:1'}
        env.globals.update(states=lambda e: states.get(e,'unknown'),
            state_attr=lambda e,a: attrs.get((e,a)), now=lambda: datetime(2026,10,18,18,tzinfo=TZ),
            as_timestamp=lambda v,d=0: v.timestamp() if isinstance(v,datetime) else d)
        values = dict(app_on=True,app_entities=['sensor.phone'],app_package='',
            app_time_helper='input_datetime.fixture',day_plan_signature='sensor.signature',
            app_missing_policy='keep_committed')
        render = lambda: int(str(env.from_string(template).render(**values)).strip())
        self.assertEqual(render(),saved)
        values['app_missing_policy'] = 'clear'
        self.assertEqual(render(),0)
        values['app_missing_policy'] = 'keep_committed'
        states['sensor.signature'] = '0:0:0:0:0:0'
        self.assertEqual(render(),0)

    def test_eight_oclock_appointment_wakes_at_seven_thirty(self):
        result = plan([{'start': '2026-10-19T08:00:00+02:00'}])
        self.assertEqual(result, [[0,0,0], [20261019, epoch('2026-10-19T07:30:00+02:00'), 2]])

    def test_ten_oclock_and_all_day_leave_regular_schedule(self):
        self.assertEqual(plan([{'start': '2026-10-19T10:00:00+02:00'}, {'start': '2026-10-19'}]), [[0,0,0],[0,0,0]])

    def test_earliest_timed_event_wins_independent_of_order(self):
        result = plan([{'start': '2026-10-19T09:00:00+02:00'}, {'start': 'bad'},
                       {'start': '2026-10-19T08:00:00+02:00'}])
        self.assertEqual(result[1][1], epoch('2026-10-19T07:30:00+02:00'))

    def test_app_priority_is_dated_not_a_daily_time_override(self):
        app = epoch('2026-10-19T09:45:00+02:00')
        result = plan([{'start': '2026-10-19T08:00:00+02:00'}], app_epoch=app, app_on=True)
        self.assertEqual(result, [[0,0,0],[20261019,app,1]])
        self.assertEqual(plan(app_epoch=epoch('2026-10-21T07:00:00+02:00'), app_on=True), [[0,0,0],[0,0,0]])

    def test_earlier_only_mode_and_disabled_master(self):
        events = [{'start': '2026-10-19T08:00:00+02:00'}]
        self.assertEqual(plan(events, calendar_mode='earlier_only'), [[0,0,0],[0,0,0]])
        self.assertEqual(plan(events, master=False), [[0,0,0],[0,0,0]])
        self.assertEqual(plan(events, regular_hour=8, calendar_mode='earlier_only')[1][2], 2)

    def test_free_days_require_opt_in_for_calendar(self):
        events = [{'start': '2026-10-19T08:00:00+02:00'}]
        self.assertEqual(plan(events, weekdays=[]), [[0,0,0],[0,0,0]])
        self.assertEqual(plan(events, weekdays=[], calendar_free_days=True)[1][2], 2)

    def test_range_boundaries_and_cross_midnight_offset(self):
        self.assertEqual(plan([{'start':'2026-10-19T09:00:00+02:00'}])[1][2], 2)
        self.assertEqual(plan([{'start':'2026-10-19T09:01:00+02:00'}])[1][2], 0)
        result = plan([{'start':'2026-10-19T00:15:00+02:00'}], earliest='00:00:00', latest='23:59:59', calendar_free_days=True)
        self.assertEqual(result[0], [20261018,epoch('2026-10-18T23:45:00+02:00'),2])

    def test_dst_offset_uses_elapsed_minutes_and_local_date(self):
        current = datetime(2026, 10, 24, 18, tzinfo=TZ)
        result = plan([{'start':'2026-10-25T03:15:00+01:00'}], current=current,
            lead_minutes=60, earliest='00:00:00', latest='05:00:00', calendar_free_days=True)
        self.assertEqual(result[1][1], epoch('2026-10-25T02:15:00+01:00'))

    def test_one_atomic_configuration_write_after_calendar_query(self):
        actions = str(BP['actions'])
        self.assertNotIn('_alarm_configure', actions)
        self.assertIn('_alarm_apply_plan', actions)
        self.assertIn('_alarm_disable', actions)
        self.assertEqual(BP['mode'], 'restart')
