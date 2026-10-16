"""Validate the real blueprint with pinned Home Assistant, without a live device."""
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import tempfile
from zoneinfo import ZoneInfo
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA, PLATFORM_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.helpers import selector
from homeassistant.util.yaml import load_yaml_dict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'homeassistant/blueprints/nspanel_alarm_settings.yaml'
blueprint = Blueprint(load_yaml_dict(path), expected_domain='automation', schema=AUTOMATION_BLUEPRINT_SCHEMA)
assert not blueprint.validate(), blueprint.validate()
fixtures = [
    {},
    {'app_entities': ['sensor.fixture_next_alarm'], 'calendars': ['calendar.fixture']},
    {'calendars': ['calendar.one', 'calendar.two'], 'weekdays': []},
]
def schema_fixtures():
    for extra in fixtures:
        inputs = BlueprintInputs(blueprint, {'alias': 'Compile-only fixture', 'use_blueprint': {
            'path': 'fixture.yaml', 'input': {
                'panel_name_entity': 'sensor.fixture_device_name',
                'config_signature': 'sensor.fixture_config_signature',
                'day_plan_signature': 'sensor.fixture_day_plan_signature', **extra}}})
        inputs.validate()
        for key, value in inputs.inputs_with_default.items():
            definition = blueprint.inputs[key]
            if definition and 'selector' in definition:
                selector.selector(definition['selector'])(value)
        automation = inputs.async_substitute()
        PLATFORM_SCHEMA(automation)
    print('Home Assistant 2026.10.1 blueprint metadata, selectors, substitution and automation/action schema passed (3 fixtures).')

async def render_plan():
    zone = ZoneInfo('Europe/Berlin')
    dt_util.set_default_time_zone(zone)
    with tempfile.TemporaryDirectory() as temp:
        hass = HomeAssistant(temp)
        # cv.template needs the HA instance registered by its constructor,
        # not just an asyncio loop. No live integration or device is started.
        schema_fixtures()
        source = next(a['variables']['day_plans'] for a in blueprint.data['actions']
                      if 'day_plans' in a.get('variables', {}))
        current = datetime(2026,10,18,18,tzinfo=zone)
        values = dict(master=True, app_on=False, app_epoch=0, calendar_on=True,
            weekdays=['mon','tue','wed','thu','fri'], calendar_free_days=False,
            calendars=['calendar.fixture'], lead_minutes=30, earliest='06:00:00',
            latest='08:30:00', calendar_mode='in_range', regular_hour=7, regular_minute=0,
            now=lambda: current,
            today_at=lambda clock: datetime.combine(current.date(), datetime.strptime(clock,'%H:%M').time(),zone),
            timedelta=timedelta)
        for hour, expected_source in [(8,2),(10,0)]:
            values['calendar_reply'] = {'calendar.fixture': {'events': [
                {'start':f'2026-10-19T{hour:02d}:00:00+02:00'}]}}
            result = Template(source, hass).async_render(values)
            assert isinstance(result,list), type(result)
            assert result[1][2] == expected_source, result
            if expected_source:
                assert result[1][1] == int(datetime(2026,10,19,7,30,tzinfo=zone).timestamp())
        print('Actual Home Assistant template rendering passed: 08:00 -> 07:30, 10:00 -> weekly fallback.')

async def main():
    # HA template schema validation needs a running event loop as well.
    await render_plan()

asyncio.run(main())
