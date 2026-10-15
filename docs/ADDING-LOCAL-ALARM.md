# Add the local alarm to an existing panel

Target: original NSPanel EU/US, NSPanel Easy v2026.10.2, ESPHome 2026.9.1.
This is a prototype. Keep an independent alarm during hardware acceptance.

## 1. Save the current working configuration

Keep the existing device name, friendly name, static API key and Wi-Fi secrets.
Retain the working per-panel Easy Blueprint automation. Confirm the actual TFT
and Blueprint versions: Easy v2026.10.2 requires TFT 22.0 and Blueprint 2026.10.1
or newer. A working API connection alone does not prove display compatibility.

## 2. Add two files alongside the device YAML

Download from the same reviewed revision of this repository:

- `esphome/nspanel_alarm_local.yaml`
- `esphome/alarm_schedule.h`

Place both in `/config/esphome/`, next to your existing device YAML. Preserve the
filenames, including the `.h` suffix. This does not modify the running panel.

## 3. Extend the current device configuration

Add one entry under the existing `packages:` mapping:

```yaml
  wake_alarm: !include nspanel_alarm_local.yaml
```

Keep the working Easy package. The reviewed v2026.10.2 package/component commit is
`c9aff59c397c26b0556c4e3930827502a5836d00`. For reproducible builds, use that SHA for its package
`ref` and for the `ref_name` substitution used by the external component.
Keep `language: en` and `upload_tft_automatically: false`.

Under the existing `api:` mapping add:

```yaml
  reboot_timeout: 0s
```

Keep its existing `encryption.key` unchanged. Add or extend the top-level Wi-Fi mapping:

```yaml
wifi:
  reboot_timeout: 0s
```

Keep the tested encrypted OTA extension:

```yaml
ota:
  - id: !extend ota_std
    password: !remove
    encryption: {}
```

Set `alarm_timezone` under substitutions to the same timezone as Home Assistant.
The default is Europe/Berlin. Other timezones require their own DST acceptance tests.

In your local `secrets.yaml`, set `local_ntp_server` to a reachable NTP server.
Prefer a reliable local NTP source for independence from the internet. For an
initial internet-connected test, `0.pool.ntp.org` is a possible value.
The package also has public pool fallback servers. After a cold boot without a
working time source, it cannot guarantee a scheduled alarm.

## 4. Validate and compile before installing

Use the existing ESPHome device entry. Validate, then compile the adapted YAML.
Resolve any errors before OTA installation. No TFT upload is needed just to add
the local alarm package.

Expected new English entities include:

- Alarm Clock Time Valid, Ringing, Pending, Status and Configuration Signature.
- Alarm Clock Test, Snooze and Stop buttons.

The schedule starts disabled on the first installation. These entities and the
API configuration actions do not yet draw a custom alarm page on the TFT.

## 5. Hardware acceptance in separate steps

After controlled OTA, verify Home Assistant reconnects and the ordinary Easy
screen still works. Record actual new entity/action IDs and actual TFT/Blueprint
versions. Keep hardware-button Blueprint actions unassigned.

Test the actual buzzer, Stop and Snooze before configuring a real schedule.
Left short press is Snooze; right short/long press is Stop. The package replaces
the corresponding local relay actions, while separate HA button automations
still need to remain unassigned.

Only after local tests configure the schedule and the optional HA audio package,
then test restarts, HA/Wi-Fi loss and clock behavior. A successful compile or API
handshake is not an audible-alarm test.
