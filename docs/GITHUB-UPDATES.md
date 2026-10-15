# Update the alarm separately from NSPanel Easy

Keep NSPanel Easy as the hardware base. Load the alarm as a separate GitHub
add-on. Only your device YAML and secrets.yaml stay local; the alarm YAML and
C++ header are fetched together. Requires ESPHome 2026.9.1 or later.

## Device configuration

Keep existing device names, Wi-Fi secrets, static API encryption key, timezone
and local_ntp_server secret. Use exactly these two package entries:

```yaml
substitutions:
  # Keep your other substitutions here.
  ref_name: c9aff59c397c26b0556c4e3930827502a5836d00
  language: en
  upload_tft_automatically: false

packages:
  nspanel_easy:
    url: https://github.com/edwardtfn/NSPanel-Easy
    ref: c9aff59c397c26b0556c4e3930827502a5836d00 # v2026.10.2
    refresh: never
    files:
      - nspanel_esphome.yaml
  alarm_addon:
    url: https://github.com/3115a083/NSPanel-Alarm-Clock
    ref: main
    refresh: always
    files:
      - nspanel_alarm_addon.yaml
```

The Easy package and its external component (ref_name) stay on the same
tested commit. Alarm updates do not change this pin. Upgrade Easy deliberately
after compatibility testing. The add-on uses Easy hardware IDs and hooks; it
is not compatible with arbitrary future Easy versions by assumption.

The add-on supplies the local scheduler, buzzer, alarm button hooks, offline
API/Wi-Fi reboot policy and required encrypted OTA through Easy's ota_std.
It does not load another Easy base or override ref_name. Existing local
API/Wi-Fi timeout settings may remain. An identical local !extend ota_std
block may be removed because the add-on supplies it. Keep the API key unchanged.

## One-time migration

1. Back up the working device YAML and secrets locally.
2. For an existing local-file setup, move both nspanel_alarm_local.yaml and
   **alarm_schedule.h** out of /config/esphome/ into the backup folder.
   ESPHome looks beside the device YAML first; an old local header can shadow
   the current remote header.
3. Replace the old packages mapping with the split mapping above. Do not keep
   a local wake_alarm include or a third package loading nspanel_alarm.yaml.
4. Validate the device YAML. Then install wirelessly, inspect the saved schedule
   and perform a short Test/Stop check.

If already using the previous combined nspanel_alarm.yaml, it remains supported.
It now composes the same base and add-on, so migration need not interrupt an
existing working setup. Use either the combined entry OR the split entries.

## Subsequent updates

Use **Install → Wirelessly** in ESPHome Device Builder. refresh: always fetches
the latest alarm source during configuration/build. The Easy base stays fixed.
Both packages are linked into **one ESP32 firmware** and uploaded together;
there is no separately installable runtime plug-in or second OTA slot for the alarm.
Validation alone does not update the running panel.

main is the development update channel. It follows merged changes after the
required unit/security and complete firmware build checks. CI does not prove
hardware acceptance of every change. Set only the alarm package ref to a
reviewed full commit SHA to freeze or roll back its source. Keep a known-working
device configuration. A frozen ref does not advance automatically.

Secrets stay local. No scheduled unattended flashing or generic device binary
is provided. GitHub and toolchain sources are needed for updates, not for the
installed local alarm to run.

## Display and Home Assistant

Keep the working Easy TFT and per-device Blueprint automation during this phase.
No project clock TFT or project Blueprint has been released yet. The custom
clock view remains a goal. A custom layout still needs a compatible TFT and
firmware protocol; keeping Easy as base does not remove that maintenance.
Future TFT download and Blueprint import URLs must name matched versions.
A source refresh must not upload a TFT or create competing base automations.

## Maintainer verification

CI copies only the consumer device YAML into an isolated directory. It fetches
the alarm at the exact tested Git SHA, verifies header origin and byte equality,
validates merged button hooks, encrypted OTA and offline timeouts, then compiles
the split configuration. It also validates the old combined entry and compares
its scripts, globals, API, OTA, Wi-Fi and time configuration with the split setup.
