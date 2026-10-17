"""Evaluate actual gate and event-action guards, including stale/foreign requests."""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import yaml
from test_config_structure import Loader
from test_device_isolation import NEW, render
from test_panel_blueprint import walk

ROOT = Path(__file__).resolve().parents[1]
EVENTS = yaml.load((ROOT/'homeassistant/blueprints/nspanel_alarm_events.yaml').read_text(encoding='utf-8'), Loader=Loader)

class EffectBlueprintTests(unittest.TestCase):
    def test_short_pulse_uses_trigger_snapshot_even_after_source_turns_off(self):
        source=next(d['value_template'] for d in walk(EVENTS['actions'])
                    if isinstance(d.get('value_template'),str) and 'trigger.to_state.entity_id' in d['value_template'])
        values=dict(sources=['binary_sensor.door'],show_action='esphome.fixture_alarm_show_notice',
                    has_service=lambda *args:True,states=lambda e:'off',
                    trigger=NS(id='door',to_state=NS(entity_id='binary_sensor.door',state='on',context=NS(id='pulse'))))
        self.assertTrue(render(source,values))
        token=next(d['variables']['notice_token'] for d in walk(EVENTS['actions']) if 'notice_token' in d.get('variables',{}))
        self.assertEqual(render(token,values),'pulse')
        values['trigger'].to_state.entity_id='binary_sensor.other'
        self.assertFalse(render(source,values))

    def test_relay_conditions_and_or_empty_and_unknown(self):
        templates=[d['variables']['relay_gate'] for d in walk(NEW['actions']) if 'relay_gate' in d.get('variables',{})]
        for i,source in enumerate(templates,1):
            values={'states':lambda e:status[e],'is_state':lambda e,s:status[e]==s,
                    f'relay{i}_conditions':[],f'relay{i}_condition_mode':'all'}
            status={}
            self.assertEqual(render(source,values),{'valid':True,'allowed':True})
            values[f'relay{i}_conditions']=['binary_sensor.one','input_boolean.two']
            status.update({'binary_sensor.one':'on','input_boolean.two':'off'})
            self.assertFalse(render(source,values)['allowed'])
            values[f'relay{i}_condition_mode']='any'
            self.assertTrue(render(source,values)['allowed'])
            status['input_boolean.two']='unavailable'
            self.assertEqual(render(source,values),{'valid':False,'allowed':False})

    def test_event_discovery_and_identity_precede_all_actions(self):
        self.assertEqual(EVENTS['actions'][:4],NEW['actions'][:4])
        wait=next(d['wait_for_trigger'] for d in walk(EVENTS['actions']) if 'wait_for_trigger' in d)
        event=next(t for t in wait if t.get('id')=='confirmed')
        self.assertEqual(event['event_data']['device_id'],'panel_device')
        fields=EVENTS['blueprint']['input']
        self.assertEqual(fields['door_action']['default'],[])
        self.assertEqual(fields['alert_action']['default'],[])
        self.assertEqual(NEW['blueprint']['input']['outputs']['input']['relay1_mode']['default'],'off')

    def test_event_action_needs_captured_token_identity_and_confirmation(self):
        guard=next(d['value_template'] for d in walk(EVENTS['actions'])
                   if isinstance(d.get('value_template'),str) and "wait.trigger.id == 'confirmed'" in d['value_template'])
        data=NS(device_name='panel-a',mac='aa0011223344',token='activation',command='door_action')
        values=dict(snapshot=['NSPALARM1','panel-a','aa0011223344','x','y'],notice_token='activation',
                    source_kind='door',wait=NS(trigger=NS(id='confirmed',event=NS(data=data))))
        self.assertTrue(render(guard,values))
        for key,value in [('token','previous'),('mac','bb0011223344'),('command','alert_action')]:
            original=getattr(data,key); setattr(data,key,value)
            self.assertFalse(render(guard,values)); setattr(data,key,original)
        values['wait'].trigger.id='replaced'
        self.assertFalse(render(guard,values))
        # A short doorbell pulse does not require the source still to be on.
        self.assertNotIn('is_state(',guard)
        alert=next(d['conditions'] for d in walk(EVENTS['actions'])
                   if isinstance(d.get('conditions'),str) and "source_kind == 'alert'" in d['conditions'])
        class States:
            status='triggered'
            def __call__(self,e): return self.status
            def __getitem__(self,e): return NS(context=NS(id='activation'))
        state=States(); values.update(source_kind='alert',notice_source='alarm_control_panel.fixture',states=state)
        self.assertTrue(render(alert,values))
        state.status='disarmed'; self.assertFalse(render(alert,values))
