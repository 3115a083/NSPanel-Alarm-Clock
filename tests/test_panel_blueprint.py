"""Exercise actual optional-page templates, local-edit mirroring and control gates."""
import unittest
from test_device_isolation import NEW, render

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value,list):
        for child in value: yield from walk(child)

class PanelBlueprintTests(unittest.TestCase):
    def test_control_requires_opt_in_single_target_and_available_state(self):
        for kind,key,entity in [('climate','climate','climate.room'),('humidity','humidifier','humidifier.room')]:
            condition=next(d['conditions'] for d in walk(NEW['actions'])
                if isinstance(d.get('conditions'),str) and 'request in' in d['conditions'] and kind+'_up' in d['conditions'])
            values=dict(request=kind+'_up',states=lambda _:'on',**{key+'_control':True,key+'_entities':[entity]})
            self.assertTrue(render(condition,values))
            values[key+'_control']=False; self.assertFalse(render(condition,values))
            values[key+'_control']=True; values[key+'_entities']=[entity,entity]; self.assertFalse(render(condition,values))
            values[key+'_entities']=[entity]; values['states']=lambda _:'unavailable'; self.assertFalse(render(condition,values))

    def test_target_adjustments_clamp_to_entity_ranges(self):
        templates={key: next(d['data'][key] for d in walk(NEW['actions']) if d.get('action') == action)
                   for key,action in [('temperature','climate.set_temperature'),('humidity','humidifier.set_humidity')]}
        attrs={'temperature':29.5,'target_temp_step':1,'min_temp':5,'max_temp':30,
               'humidity':78,'min_humidity':20,'max_humidity':80}
        values=dict(target_entity='unused',state_attr=lambda _,key:attrs.get(key))
        self.assertEqual(render(templates['temperature'],dict(values,request='climate_up')),30)
        attrs['temperature']=5
        self.assertEqual(render(templates['temperature'],dict(values,request='climate_down')),5)
        self.assertEqual(render(templates['humidity'],dict(values,request='humidity_up')),80)
        attrs['humidity']=20
        self.assertEqual(render(templates['humidity'],dict(values,request='humidity_down')),20)

    def test_local_edit_time_mirror_is_idempotent_and_identity_checked(self):
        guards=[d['if'] for d in walk(NEW['actions']) if isinstance(d.get('if'),str)]
        check=next(t for t in guards if 'ui | length != 7' in t)
        values=dict(ui=['NSPUI1','aa0011223344','2','1','7','5','1'],snapshot=['NSPALARM1','panel','aa0011223344','x','y'])
        self.assertFalse(render(check,values))
        values['ui'][1]='bb0011223344'; self.assertTrue(render(check,values))
        values['ui'][1]='aa0011223344'; values['ui'][4]='24'; self.assertTrue(render(check,values))
        values['ui'][4]='7'
        mirror=next(t for t in guards if "state_attr(time_helper,'hour')" in t)
        attrs={'hour':6,'minute':30}
        values.update(time_helper='input_datetime.regular',state_attr=lambda _,k:attrs[k])
        self.assertTrue(render(mirror,values))
        attrs.update(hour=7,minute=5)
        self.assertFalse(render(mirror,values))

    def test_night_defaults_and_optional_pages_are_explicit(self):
        fields=NEW['blueprint']['input']['display']['input']
        self.assertEqual(fields['night_mode']['default'],'dim')
        self.assertEqual(fields['night_brightness']['default'],1)
        self.assertEqual(fields['clock_format']['default'],'24h')
        self.assertFalse(fields['climate_control']['default'])
        self.assertFalse(fields['humidifier_control']['default'])
        self.assertEqual(fields['agenda_calendars']['default'],[])
        self.assertIn('calendars',NEW['blueprint']['input']['calendar']['input'])
