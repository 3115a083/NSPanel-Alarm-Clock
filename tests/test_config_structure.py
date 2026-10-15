"""Shallow static YAML checks, not an ESPHome/HA configuration validator."""
import pathlib
import re
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Loader(yaml.SafeLoader):
    pass

def construct_tag(loader, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)

for tag in ("!secret", "!include", "!extend", "!remove", "!lambda", "!env_var"):
    Loader.add_constructor(tag, construct_tag)

class ConfigTests(unittest.TestCase):
    def test_clock_handshake_never_polls_virtual_event_names_and_rearms(self):
        d = yaml.load((ROOT/'esphome/nspanel_alarm_ui_local.yaml').read_text(encoding='utf-8'), Loader=Loader)
        for sensor in d['binary_sensor']:
            self.assertEqual(sensor['update_interval'], 'never')
        display = d['display'][0]
        setup = display['on_setup']['then'][0]['lambda']
        page = display['on_page']['then'][0]['lambda']
        self.assertIn('id(wa_hmi_protocol).publish_state(false)', setup)
        self.assertIn('id(wa_clock_protocol).publish_state(false)', setup)
        self.assertIn('id(wa_clock_protocol).publish_state(false)', page)
        # UI stays opt-in when an existing installation refreshes GitHub main.
        addon = yaml.load((ROOT/'nspanel_alarm_addon.yaml').read_text(encoding='utf-8'), Loader=Loader)
        self.assertNotIn('alarm_ui', addon['packages'])

    def test_custom_clock_type_is_not_declared_before_user_header(self):
        d = yaml.load((ROOT/'esphome/nspanel_alarm_ui_local.yaml').read_text(encoding='utf-8'), Loader=Loader)
        self.assertTrue(all(g['type'] == 'bool' for g in d['globals']))
        self.assertIn('wake_alarm::clock_renderer().render(', str(d['interval']))

    def test_all_yamls_syntactically_valid(self):
        for p in list(ROOT.rglob('*.yaml')) + list(ROOT.rglob('*.yml')):
            with self.subTest(file=str(p)):
                with p.open(encoding='utf-8') as f:
                    self.assertIsNotNone(yaml.load(f, Loader=Loader))

    def test_local_alarm_does_not_depend_on_ha_time(self):
        d = yaml.load((ROOT/'esphome/nspanel_alarm_local.yaml').read_text(encoding='utf-8'), Loader=Loader)
        self.assertEqual(d['time'][0]['platform'], 'sntp')
        self.assertEqual(d['time'][0]['timezone'], '${alarm_timezone}')
        self.assertEqual(d['globals'][3]['initial_value'], 'false')

    def test_mandatory_buzzer_not_suppressed_by_audio_status(self):
        alarm = (ROOT/'esphome/nspanel_alarm_local.yaml').read_text(encoding='utf-8')
        self.assertIn('id(buzzer).play(', alarm)
        self.assertNotIn('media_player.playing', alarm)
        self.assertIn('wa_unacknowledged', alarm)

    def test_alarm_button_hooks_replace_upstream_relay_actions(self):
        alarm = (ROOT/'esphome/nspanel_alarm_local.yaml').read_text(encoding='utf-8')
        for hook in ['button_left_press_short', 'button_right_press_short', 'button_right_press_long']:
            self.assertIn('id: !extend ' + hook + '\n    then: !remove', alarm)

    def test_dashboard_buttons_remain_available(self):
        d = yaml.load((ROOT/'esphome/nspanel_alarm_local.yaml').read_text(encoding='utf-8'), Loader=Loader)
        self.assertEqual({b['name'] for b in d['button']},
                         {'Alarm Clock Test', 'Alarm Clock Snooze', 'Alarm Clock Stop'})

    def test_flash_sync_is_not_faster_than_restored_globals_poll(self):
        d = yaml.load((ROOT/'esphome/nspanel_alarm_local.yaml').read_text(encoding='utf-8'), Loader=Loader)
        value = d['preferences']['flash_write_interval']
        match = re.fullmatch(r'(\d+(?:\.\d+)?)(ms|s)', str(value))
        self.assertIsNotNone(match, value)
        seconds = float(match.group(1)) / (1000 if match.group(2) == 'ms' else 1)
        # ESPHome RestoringGlobalsComponent polls changes once per second.
        # Faster preference sync wastes scheduler cycles without reducing that delay.
        self.assertGreaterEqual(seconds, 1.0)

    def test_unsupported_override_tag_is_rejected(self):
        with self.assertRaises(yaml.constructor.ConstructorError):
            yaml.load("then: !override []", Loader=Loader)

    def test_remote_entry_keeps_upstream_pinned_and_alarm_in_same_checkout(self):
        entry = yaml.load((ROOT/'nspanel_alarm.yaml').read_text(encoding='utf-8'), Loader=Loader)
        upstream = entry['packages']['nspanel_easy']
        self.assertRegex(upstream['ref'], r'^[0-9a-f]{40}$')
        self.assertEqual(entry['substitutions']['ref_name'], upstream['ref'])
        self.assertEqual(entry['packages']['alarm_addon'], 'nspanel_alarm_addon.yaml')
        self.assertFalse(entry['substitutions']['upload_tft_automatically'])

    def test_device_fetches_separate_base_and_alarm_packages(self):
        device = yaml.load((ROOT/'esphome/nspanel-schlafzimmer.yaml').read_text(encoding='utf-8'), Loader=Loader)
        self.assertEqual(set(device['packages']), {'nspanel_easy', 'alarm_addon'})
        base = device['packages']['nspanel_easy']
        self.assertEqual(base['url'], 'https://github.com/edwardtfn/NSPanel-Easy')
        self.assertRegex(base['ref'], r'^[0-9a-f]{40}$')
        self.assertEqual(device['substitutions']['ref_name'], base['ref'])
        self.assertEqual(base['refresh'], 'never')
        package = device['packages']['alarm_addon']
        self.assertEqual(package['url'], 'https://github.com/3115a083/NSPanel-Alarm-Clock')
        self.assertEqual(package['files'], ['nspanel_alarm_addon.yaml'])
        self.assertEqual(package['refresh'], 'always')
        self.assertNotIn('includes', device.get('esphome', {}))

    def test_alarm_addon_does_not_load_or_repin_the_base(self):
        addon = yaml.load((ROOT/'nspanel_alarm_addon.yaml').read_text(encoding='utf-8'), Loader=Loader)
        self.assertEqual(addon['packages'], {'alarm_core': 'esphome/nspanel_alarm_local.yaml'})
        self.assertNotIn('ref_name', addon['substitutions'])
        self.assertNotIn('ref_url', addon['substitutions'])
        self.assertEqual(addon['api']['reboot_timeout'], '0s')
        self.assertEqual(addon['wifi']['reboot_timeout'], '0s')
        self.assertEqual(addon['ota'][0]['encryption'], {})

if __name__ == '__main__':
    unittest.main()

