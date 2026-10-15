"""Regression tests for the HA templates and cancellation/target boundaries."""
import pathlib
import re
import unittest
import yaml
from jinja2 import Environment, StrictUndefined

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = yaml.safe_load((ROOT / "homeassistant/wecker_package.yaml").read_text(encoding="utf-8"))

def render(template, states=None, attrs=None, **variables):
    states = states or {}
    attrs = attrs or {}
    env = Environment(undefined=StrictUndefined)
    env.filters["regex_match"] = lambda value, pattern: bool(re.match(pattern, value))
    env.globals.update(states=lambda entity: states.get(entity, "unknown"),
                       is_state=lambda entity, state: states.get(entity) == state,
                       state_attr=lambda entity, attr: attrs.get((entity, attr)))
    return env.from_string(template).render(**variables).strip()

class AudioBoundaryTests(unittest.TestCase):
    def test_rejects_multiple_or_other_domain_targets(self):
        template = PACKAGE["script"]["wecker_audio_wiedergabe"]["sequence"][3]["choose"][0]["conditions"][0]["value_template"]
        for player in ["all", "media_player.one,media_player.two",
                       "media_player.one media_player.two", "switch.heater", "media_player."]:
            with self.subTest(player=player):
                self.assertEqual(render(template, {player: "idle"}, player=player,
                                        content="fixture", kind="music"), "False")
        self.assertEqual(render(template, {"media_player.one": "idle"},
                                player="media_player.one", content="fixture", kind="music"), "True")
        self.assertEqual(render(template, player="media_player.one", content="fixture", kind="music"), "False")

    def test_audio_has_no_independent_schedule_or_catchup(self):
        automation = next(a for a in PACKAGE["automation"] if a["id"] == "wecker_audio_start")
        self.assertEqual({t["trigger"] for t in automation["triggers"]}, {"state", "homeassistant"})
        self.assertEqual(automation["conditions"][0]["state"], "on")
        self.assertEqual(automation["conditions"][0]["entity_id"],
                         "binary_sensor.nspanel_schlafzimmer_wecker_klingelt")

    def test_ack_cancels_pending_playback_and_ramp(self):
        actions = PACKAGE["script"]["wecker_audio_beenden"]["sequence"]
        self.assertEqual(actions[0]["action"], "script.turn_off")
        self.assertEqual(set(actions[0]["target"]["entity_id"]),
                         {"script.wecker_audio_wiedergabe", "script.wecker_lautstaerkerampe"})
        self.assertIn("wecker_aktiver_player", actions[1]["variables"]["player"])
        self.assertNotIn("wecker_player", actions[1]["variables"]["player"])
        ramp = PACKAGE["script"]["wecker_lautstaerkerampe"]["sequence"][2]["repeat"]["sequence"]
        self.assertEqual(ramp[1]["state"], "on")
        self.assertEqual(ramp[2]["target"]["entity_id"], "{{ player }}")

    def test_snooze_does_not_stop_audio_without_panel_confirmation(self):
        actions = PACKAGE["script"]["wecker_schlummern"]["sequence"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "esphome.nspanel_schlafzimmer_alarm_snooze")

    def test_incomplete_ha_restore_cannot_overwrite_saved_schedule(self):
        sync = next(a for a in PACKAGE["automation"] if a["id"] == "wecker_schedule_sync")
        self.assertEqual(render(sync["conditions"][0]["value_template"]), "False")

    def test_signature_detects_snooze_and_grace_changes(self):
        template = PACKAGE["template"][0]["sensor"][0]["state"]
        values = {"input_boolean.wecker_aktiv": "on", "input_boolean.wecker_mo": "on",
                  "input_number.wecker_snooze": "9",
                  "input_number.wecker_summer_verzoegerung": "15",
                  "input_select.wecker_ausgabe": "Lautsprecher + Summer"}
        attrs = {("input_datetime.wecker_zeit", "hour"): 6,
                 ("input_datetime.wecker_zeit", "minute"): 30}
        self.assertEqual(render(template, values, attrs), "1:1:6:30:9:15")
        values["input_number.wecker_snooze"] = "10"
        self.assertEqual(render(template, values, attrs), "1:1:6:30:10:15")
        values["input_number.wecker_summer_verzoegerung"] = "20"
        self.assertEqual(render(template, values, attrs), "1:1:6:30:10:20")
