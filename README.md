# NSPanel Alarm Clock

**Status: prototype v0.2. Not tested on actual NSPanel hardware. Do not use as your only alarm.**

Home Assistant alarm-clock prototype for original Sonoff NSPanel EU/US (not Pro). It reuses [NSPanel Easy](https://github.com/edwardtfn/NSPanel-Easy) ESPHome firmware **v2026.10.2**, with a local persisted scheduler and buzzer that does not require Home Assistant at the moment of triggering.

## What is implemented

- [Blueprint and UI review](docs/BLUEPRINT-AND-UI-REVIEW.md): grouped settings,
  direct page menu, separate hour/minute controls, bounded tone preview and
  optional physical-button labels that follow normal/alarm mappings.

- Standalone [relay rules, tone presets and event screens](docs/RELAYS-AND-EVENTS.md):
  local bounded output timers, explicit HA conditions, manual takeover and
  confirmed doorbell/alert actions. Outputs remain opt-in; hardware acceptance is open.

- Standalone [night display and controls](docs/CONTROLS-AND-NIGHT.md): dim/black
  screensaver, local regular-alarm editor, gestures, long-button navigation,
  Snooze countdown, 12/24-hour display and optional selected data/appliance pages.
  New interactions and controls require separate hardware acceptance.

- Experimental [independent EU clock profile](docs/STANDALONE.md) with its own
  local display/boot path and a device-selecting Blueprint. It is an explicit
  alternative to the full Easy setup, not an automatic migration or TFT release.

- Optional [settings blueprint](docs/BLUEPRINT.md) for a weekly alarm, dated app
  imports and calendar wake ranges. Requires updated alarm firmware and helper
  setup. Runtime integration is still awaiting device/HA acceptance.
- Optional EU clock UI with local time/plan/status, changed-only display writes,
  protocol-v2 HMI detection and Clock/NSPanel Easy start-view selection.
  This UI still needs Editor and device acceptance. See [TFT build/testing](docs/TFT-BUILD.md).
- Locally persisted enabled/disabled alarm, clock time, seven weekdays, snooze length and buzzer grace period.
- Offline-capable local buzzer and panel-button Snooze/Stop; mandatory buzzer even if a speaker reports `playing`.
- 15-minute catch-up window, persisted unacknowledged alarm and snooze time, startup recovery.
- Home Assistant package providing day/time selectors, audio player/URI, volume ramp, status and synchronization.
- Lovelace dashboard excerpt, host-side model tests, secret hygiene check and read-only CI workflow.
- Explicit Wi-Fi/API no-reboot settings for planned Home Assistant/Wi-Fi outages, plus encrypted native API and required encrypted OTA using the static API key.

**Constraints:** No battery-backed RTC or hardware power redundancy; timing after power loss without a working time source is not guaranteed. A dead buzzer or locked-up ESP32 also defeats local alarms. Software-only safeguards cannot guarantee waking under all failures. The example is validated and compiled in CI. The local alarm extension and Home Assistant runtime integration have **not** been tested on a physical panel. Model tests do not verify generated firmware behavior.

## Files

| Path | Purpose |
|---|---|
| `nspanel_alarm_addon.yaml` | Remote alarm add-on, loaded alongside your pinned Easy base |
| `nspanel_alarm.yaml` | Compatible combined entry for existing users |
| `esphome/nspanel-schlafzimmer.yaml` | Panel configuration, upstream version pin, API/Wi-Fi policies |
| `esphome/nspanel_alarm_local.yaml` | Offline-capable scheduler, buzzer, Snooze/Stop, and status |
| `homeassistant/wecker_package.yaml` | HA helpers, synchronization, audio and alerts |
| `lovelace/wecker_view.yaml` | Dashboard excerpt |
| `tests/` | Scheduler model and structural tests |
| `SECURITY.md` | Vulnerability reporting and security assumptions |
| `docs-SECURITY-SETUP.md` | **Owner actions needed to protect the GitHub repository** |

## Installation planning

1. Acquire original Sonoff NSPanel EU/US, not Pro. Flash only the powered-off controller with a **3.3V** UART adapter as specified in [NSPanel Easy installation](https://github.com/edwardtfn/NSPanel-Easy/blob/main/docs/install.md).
2. Copy only `esphome/nspanel-schlafzimmer.yaml` into `/config/esphome/`. It loads a pinned Easy base plus a separately updated alarm add-on from GitHub. Add unique values for `wifi_ssid`, `wifi_password`, `nspanel_api_encryption_key`, and `local_ntp_server` to your **local** `/config/esphome/secrets.yaml`, never to Git. Existing users can follow [GitHub updates](docs/GITHUB-UPDATES.md); local-file users must move the old local header out of the active directory.
3. Run `esphome config nspanel-schlafzimmer.yaml`, then `esphome compile nspanel-schlafzimmer.yaml` with a supported ESPHome version. Resolve any upstream compatibility conflicts first. Import the matching NSPanel Easy Blueprint and TFT from its tagged release.
4. Configure `homeassistant: packages: !include_dir_named packages` and copy `homeassistant/wecker_package.yaml` into the HA packages folder. Check configuration in HA before restart.
5. Verify the entity/service IDs after pairing the device. This prototype uses `nspanel_schlafzimmer` identifiers as examples; device ID slugs can differ. A missing service means schedule synchronization is not occurring.
6. Perform the fault-injection checks below before any alarm could become critical. Keep a separate, dependable clock throughout development.

For full integration and fault-injection steps, see [the original development notes](#hardware-acceptance-gate).

## Defined timing and button behavior

The local scheduler is the only source of alarm start events. Home Assistant audio
follows the panel's ringing state, including test and Snooze alarms. Stop cancels
pending playback and the volume ramp, and targets only the captured alarm player.
Set exactly one existing `media_player.entity_id`.

On the autumn clock change, only the first occurrence of a repeated time is used.
A nonexistent spring time (for example 02:30 in Berlin) is skipped. Choose a time
outside the DST transition hour for a daily wake-up. Moving the clock back to an
already fired date suppresses that date, so reset testing data deliberately.

In this dedicated alarm profile, left short press is Snooze and right short/long
press is Stop. These hooks replace upstream local relay actions. Also remove
HA Blueprint button-to-relay or other external actions from those buttons before
hardware testing. No relay operation is needed for the alarm.

All six configuration fields, including Snooze and buzzer grace, participate in
the synchronization signature. Incomplete HA startup helper states are not sent
as a replacement schedule. For upgrades from the initial prototype, remove stale
entities/helpers if HA creates a duplicate diagnostic entity.

## English reference configuration

The reference configuration and alarm entity labels are English. NSPanel Easy
language remains selectable using its `language` substitution; alarm labels can
be adapted in the local alarm package. Existing `wecker_*` helper/script IDs are
retained for compatibility. They do not determine the visible labels.

Entity names in the HA package/dashboard now follow the English alarm labels.
On an existing installation, reconcile the entity registry and the restored
output selector (new values `Buzzer` / `Speaker + buzzer`) before enabling it.
Verify actual entity IDs after pairing instead of assuming the example prefix.

For an already running panel, follow [Add the local alarm](docs/ADDING-LOCAL-ALARM.md).
This keeps its device identity and API key.

## Tests

```bash
python3 -m pip install PyYAML==6.0.2 Jinja2==3.1.6
python3 tools/prepare_tft_sources.py
python3 -m unittest discover -s tests -v
python3 .github-secrets-scan.py
```

A C++17 compiler (`g++`) is required for native scheduler tests. CI additionally
validates and compiles the complete example with ESPHome 2026.9.1 and generated
dummy credentials. A compiled example is not a firmware image for your device.
The remote add-on fetches its alarm YAML and matching C++ header together;
see [GitHub updates](docs/GITHUB-UPDATES.md) for migration from local files.

An experimental dedicated EU clock HMI is available for Editor review through
the `eu-clock-hmi-preview` Actions artifact. Select `home_smpl` in the generated
HMI. It contains layout placeholders; live data rendering and a validated clock
TFT are still pending. See [TFT development](docs/TFT-BUILD.md). Do not flash it.

## Hardware acceptance gate

A physical panel is still required to check and sign off:

- Real firmware compile, screen and TFT compatibility, button-to-relay side effects and API encryption handshake.
- Actual audible buzzer on schedule with HA online; HA disconnected; Wi-Fi disconnected after initial NTP sync.
- Silent/offline player, Snooze/Stop locally, a reboot during an unanswered alarm and after a Snooze.
- Summer-/Winterzeit transitions, cold boot without NTP, and an interrupted firmware update.
- Complete power outage, hardware hang, speaker or buzzer failure (separate alarm must cover such cases).

> **Never treat a test suite passing or media_player reporting `playing` as proof that an audible alarm will sound.**

## GitHub repository protection

An active `main` ruleset was verified on 2026-10-15. It requires a PR and the GitHub Actions `unit-security-checks` status, blocks deletion/force-push and requires linear history. Remaining gaps: zero approvals, no required conversation resolution or up-to-date branch check, one always-bypass integration, no release-tag ruleset, and the new `firmware-build` check is not yet required. Review [docs-SECURITY-SETUP.md](docs-SECURITY-SETUP.md) and enable branch rulesets, code-owner review, required CI checks, security scanning, and least-privilege access. A CODEOWNERS file or CI workflow without a configured ruleset does not protect `main` from privileged direct pushes.

