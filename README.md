# NSPanel Alarm Clock

**Status: prototype v0.2. Not tested on actual NSPanel hardware. Do not use as your only alarm.**

Open source Home Assistant alarm-clock experiment for original Sonoff NSPanel EU/US (not Pro). It reuses [NSPanel Easy](https://github.com/edwardtfn/NSPanel-Easy) ESPHome firmware **v2026.10.0**, with a local persisted scheduler and buzzer that does not require Home Assistant at the moment of triggering.

## What is implemented

- Locally persisted enabled/disabled alarm, clock time, seven weekdays, snooze length and buzzer grace period.
- Offline-capable local buzzer and panel-button Snooze/Stop; mandatory buzzer even if a speaker reports `playing`.
- 15-minute catch-up window, persisted unacknowledged alarm and snooze time, startup recovery.
- Home Assistant package providing day/time selectors, audio player/URI, volume ramp, status and synchronization.
- Lovelace dashboard excerpt, host-side model tests, secret hygiene check and read-only CI workflow.
- Explicit Wi-Fi/API no-reboot settings for planned Home Assistant/Wi-Fi outages, plus encrypted native API and password-protected OTA.

**Constraints:** No battery-backed RTC or hardware power redundancy; timing after power loss without a working time source is not guaranteed. A dead buzzer or locked-up ESP32 also defeats local alarms. Software-only safeguards cannot guarantee waking under all failures. Configuration and runtime integration have **not** been compiled, flashed, or tested on a physical panel. Model tests do not verify generated firmware behavior.

## Files

| Path | Purpose |
|---|---|
| `esphome/nspanel-schlafzimmer.yaml` | Panel configuration, upstream version pin, API/Wi-Fi policies |
| `esphome/nspanel_alarm_local.yaml` | Offline-capable scheduler, buzzer, Snooze/Stop, and status |
| `homeassistant/wecker_package.yaml` | HA helpers, synchronization, audio and alerts |
| `lovelace/wecker_view.yaml` | Dashboard excerpt |
| `tests/` | Scheduler model and structural tests |
| `SECURITY.md` | Vulnerability reporting and security assumptions |
| `docs-SECURITY-SETUP.md` | **Owner actions needed to protect the GitHub repository** |

## Installation planning

1. Acquire original Sonoff NSPanel EU/US, not Pro. Flash only the powered-off controller with a **3.3V** UART adapter as specified in [NSPanel Easy installation](https://github.com/edwardtfn/NSPanel-Easy/blob/main/docs/install.md).
2. Copy both `esphome/*.yaml` into `/config/esphome/`. Add unique values for `wifi_ssid`, `wifi_password`, `nspanel_ota_password`, `nspanel_api_encryption_key`, and `local_ntp_server` to your **local** `/config/esphome/secrets.yaml`, never to Git.
3. Run `esphome config nspanel-schlafzimmer.yaml`, then `esphome compile nspanel-schlafzimmer.yaml` with a supported ESPHome version. Resolve any upstream compatibility conflicts first. Import the matching NSPanel Easy Blueprint and TFT from its tagged release.
4. Configure `homeassistant: packages: !include_dir_named packages` and copy `homeassistant/wecker_package.yaml` into the HA packages folder. Check configuration in HA before restart.
5. Verify the entity/service IDs after pairing the device. This prototype uses `nspanel_schlafzimmer` identifiers as examples; device ID slugs can differ. A missing service means schedule synchronization is not occurring.
6. Perform the fault-injection checks below before any alarm could become critical. Keep a separate, dependable clock throughout development.

For full integration and fault-injection steps, see [the original development notes](#hardware-acceptance-gate).

## Tests

```bash
python3 -m pip install PyYAML==6.0.2
python3 -m unittest discover -s tests -v
python3 .github-secrets-scan.py
```

## Hardware acceptance gate

A physical panel is still required to check and sign off:

- Real firmware compile, screen and TFT compatibility, button-to-relay side effects and API encryption handshake.
- Actual audible buzzer on schedule with HA online; HA disconnected; Wi-Fi disconnected after initial NTP sync.
- Silent/offline player, Snooze/Stop locally, a reboot during an unanswered alarm and after a Snooze.
- Summer-/Winterzeit transitions, cold boot without NTP, and an interrupted firmware update.
- Complete power outage, hardware hang, speaker or buzzer failure (separate alarm must cover such cases).

> **Never treat a test suite passing or media_player reporting `playing` as proof that an audible alarm will sound.**

## GitHub repository protection

The repository started with an **unprotected `main` branch**. Review [docs-SECURITY-SETUP.md](docs-SECURITY-SETUP.md) and enable branch rulesets, code-owner review, required CI checks, security scanning, and least-privilege access. A CODEOWNERS file or CI workflow without a configured ruleset does not protect `main` from privileged direct pushes.
