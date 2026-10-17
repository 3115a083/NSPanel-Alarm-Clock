"""Render actual blueprint identity guards with two device registry fixtures."""
import ast
from pathlib import Path
import re
import unittest
import yaml
from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment
from test_config_structure import Loader

ROOT = Path(__file__).resolve().parents[1]
OLD = yaml.load((ROOT/'homeassistant/blueprints/nspanel_alarm_settings.yaml').read_text(), Loader=Loader)
NEW = yaml.load((ROOT/'homeassistant/blueprints/nspanel_alarm_device.yaml').read_text(), Loader=Loader)

def render(source, values):
    env = NativeEnvironment(undefined=StrictUndefined)
    env.filters['regex_match'] = lambda v,p: bool(re.match(p,v))
    value = env.from_string(source).render(**values)
    try:
        return ast.literal_eval(value.strip()) if isinstance(value,str) else value
    except (ValueError,SyntaxError):
        return value.strip()

class DeviceIsolationTests(unittest.TestCase):
    def fixture(self):
        # Entity IDs deliberately have no relation to original labels or names.
        owners = {'sensor.renamed_a':'a', 'sensor.unrelated':'b'}
        states = {
            'sensor.renamed_a':'NSPALARM1|panel-a|aa0011223344|0:31:6:30:9:15|0:0:0:0:0:0',
            'sensor.unrelated':'NSPALARM1|panel-b|bb0011223344|0:31:7:30:9:15|0:0:0:0:0:0'}
        values = dict(panel_device='a', device_entities=lambda d:[e for e in owners if owners[e]==d],
            integration_entities=lambda _:list(owners), states=lambda e:states.get(e,'unavailable'),
            device_id=lambda e:owners.get(e),
            device_attr=lambda d,_:[('mac',('aa' if d=='a' else 'bb')+':00:11:22:33:44')])
        return values, owners, states

    def resolve(self, values):
        values['snapshots'] = render(NEW['actions'][0]['variables']['snapshots'], values)
        if len(values['snapshots']) != 1:
            return False
        for key,source in NEW['actions'][2]['variables'].items():
            values[key] = render(source,values)
        return not render(NEW['actions'][3]['if'],values)

    def test_two_devices_and_renamed_entities_resolve_independently(self):
        values,_,_ = self.fixture()
        self.assertTrue(self.resolve(values))
        self.assertEqual(values['snapshot'][1],'panel-a')
        values['panel_device']='b'
        self.assertTrue(self.resolve(values))
        self.assertEqual(values['snapshot'][1],'panel-b')

    def test_foreign_mac_duplicate_missing_disabled_and_malformed_rejected(self):
        for failure in ['foreign','duplicate','missing','malformed','disabled']:
            with self.subTest(failure=failure):
                values,owners,states = self.fixture()
                if failure=='foreign': states['sensor.renamed_a']=states['sensor.unrelated']
                if failure=='duplicate': owners['sensor.copy']='a'; states['sensor.copy']=states['sensor.renamed_a']
                if failure=='missing': owners.clear()
                if failure=='disabled': states['sensor.renamed_a']='unavailable'
                if failure=='malformed': states['sensor.renamed_a']='NSPALARM1|broken'
                self.assertFalse(self.resolve(values))

    def test_legacy_sensor_mixing_is_rejected_before_disable_or_plan(self):
        values,owners,_=self.fixture()
        values.update(panel_name_entity='sensor.renamed_a',config_signature='sensor.renamed_a',day_plan_signature='sensor.unrelated')
        guard=OLD['actions'][0]['if']
        self.assertTrue(render(guard,values))
        values['day_plan_signature']='sensor.renamed_a'
        self.assertFalse(render(guard,values))
        owners.clear()
        self.assertTrue(render(guard,values))

    def test_new_blueprint_preserves_planner_and_binds_both_writes(self):
        pick=lambda b,k:next(a['variables'][k] for a in b['actions'] if k in a.get('variables',{}))
        self.assertEqual(pick(NEW,'day_plans'),pick(OLD,'day_plans'))
        for action in [a for a in NEW['actions'] if 'if' in a]:
            for step in action.get('then',[]):
                if step.get('action') in ['{{ disable_action }}','{{ plans_action }}']:
                    self.assertEqual(step['data']['expected_device'],'{{ snapshot[1] }}')
                    self.assertEqual(step['data']['expected_mac'],'{{ snapshot[2] }}')
        self.assertNotIn('panel_name_entity',NEW['variables'])
        self.assertIn('panel_device',NEW['variables'])
