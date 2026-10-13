"""Shallow static YAML checks, not an ESPHome/HA configuration validator."""
import pathlib
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Loader(yaml.SafeLoader):
    pass

Loader.add_multi_constructor("!", lambda loader, tag, node:
    loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode)
    else loader.construct_sequence(node))

class ConfigTests(unittest.TestCase):
    def test_all_yamls_syntactically_valid(self):
        for p in ROOT.rglob('*.yaml'):
            with self.subTest(file=str(p)):
                with p.open() as f:
                    self.assertIsNotNone(yaml.load(f, Loader=Loader))

    def test_local_alarm_does_not_depend_on_ha_time(self):
        d = yaml.load((ROOT/'esphome/nspanel_alarm_local.yaml').read_text(), Loader=Loader)
        self.assertEqual(d['time'][0]['platform'], 'sntp')
        self.assertEqual(d['time'][0]['timezone'], '${alarm_timezone}')
        self.assertEqual(d['globals'][3]['initial_value'], 'false')

    def test_mandatory_buzzer_not_suppressed_by_audio_status(self):
        alarm = (ROOT/'esphome/nspanel_alarm_local.yaml').read_text()
        self.assertIn('id(buzzer).play(', alarm)
        self.assertNotIn('media_player.playing', alarm)
        self.assertIn('wa_unacknowledged', alarm)

if __name__ == '__main__':
    unittest.main()
