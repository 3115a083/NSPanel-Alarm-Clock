# Independent EU clock profile

Status: experimental source profile, not a hardware-accepted release. Existing
Easy installations do not switch to it when updating the alarm add-on.

## What changes

`nspanel_alarm_standalone.yaml` replaces the full Easy package on **one selected
EU panel**. It reuses the local alarm core and the project's Easy-derived v2 HMI,
but runs standard ESPHome hardware/Nextion components with its own boot, page
and brightness control. There is no Easy external component, Blueprint version
handshake or Easy event traffic. Full Easy features and pages are not supported
in this profile yet. Keep the Easy add-on profile when those features are needed.

The separate `nspanel_alarm_device.yaml` Blueprint chooses the ESPHome device
once. It discovers a versioned Device Snapshot only among that device's ESPHome
entities. Discovery compares the snapshot MAC with the device registry's network
MAC and requires exactly one compatible snapshot. Entity/friendly-name changes
do not affect discovery. Calls carry the expected internal name and MAC; firmware
rejects calls delivered to another panel. This is routing protection, not a
replacement for encrypted API authentication. Disabled/unavailable snapshot or
unknown registry MAC stops synchronization with a trace error, never a guessed
fallback to a different device.

The old settings Blueprint remains available for existing input mappings and now
requires all three selected sensors to belong to the same registered device.
Only one alarm planner may write a given panel. Helpers remain explicit settings;
use a separate helper set for each panel to avoid shared schedules. Calendars and
app sources may be shared intentionally. A Blueprint cannot create helpers.

## Controlled migration

1. Back up the working device YAML and secrets. Keep its device name, friendly
   name, API key and alarm timezone. Do not edit the other panel's configuration.
2. Use `esphome/nspanel-alarm-standalone-example.yaml` as the **alternative**
   package layout. Load only `nspanel_alarm_standalone.yaml`, without the Easy,
   alarm-addon or optional Easy-UI entries. Preserve your local secret references
   and `local_ntp_server` secret from the existing setup. EU only.
3. Set `alarm_tft_url` to an accessible URL of your exported protocol-v2 EU clock
   TFT. For a local HA file, place it under `/config/www/` and use its `/local/`
   URL. The example URL is a location to populate, not a supplied download.
   The native Nextion `tft_url` uses this value. No automated TFT upload occurs.
4. Validate, clean old build files and deliberately install the firmware. Then
   disable only the Easy automation for this migrated panel. Leave the other
   panel's Easy automation enabled. No Easy automation is needed by standalone.
5. Import the device Blueprint from
   https://github.com/3115a083/NSPanel-Alarm-Clock/blob/main/homeassistant/blueprints/nspanel_alarm_device.yaml
   and create one automation with this panel and its helper settings. Disable
   the old settings automation/legacy schedule sync for this panel before
   enabling the replacement. Existing Blueprint input mappings are not silently
   rewritten. The device Blueprint can also plan updated Easy-addon firmware;
   that profile still needs its Easy base automation.
6. Verify `Alarm Clock UI Mode` is `standalone_v1` and `Alarm Clock Display Status`
   is `clock_ready_v2`. If the v2 TFT is not installed yet, deliberately press
   `Alarm Clock Upload TFT`, only when no alarm is pending. A local TFT export,
   size, hash and successful upload still require verification on your device.
7. Test a short alarm, left Snooze/right Stop, restart, display reset and HA
   disconnection. Keep the existing alarm plan until you verify its signatures.
   Shared core global IDs are preserved, but restoration across profiles is a
   hardware acceptance item, not guaranteed by a build test.

## Local display behavior

The profile requests `home_smpl` after the display connects. It writes `wa_`
fields only after the page emits `wa_clock_v2`. An incompatible TFT is limited to
three page requests, three seconds apart, and reported as
`incompatible_tft_or_no_ack`; `Alarm Clock Retry Display` restarts that budget.
Page changes reset the text/brightness cache and restore the clock locally.
There is no HA-driven screensaver or competing Easy home-page constructor.

`Alarm Clock Idle Brightness` sets idle backlight, including 0 for darkness.
An LCD clock is not readable in the dark with its backlight off. Ringing sets
100%, then Stop/Snooze restores idle brightness. Both physical buttons call local
alarm scripts; they do not switch relays. Relay boot defaults are always OFF.
Configurable gestures, relay event rules, weather/media/agenda pages, night
schedules and custom tones remain separate future modules.

Rendering pauses during OTA/TFT transfer. TFT upload is manual and rejected while
an alarm is pending. It is a maintenance operation, not an alarm-safe background
update. Time still requires initial synchronization after cold power loss.

## Version and acceptance boundary

Firmware identifies itself as `nspanel_alarm.clock` / `0.3.0-dev`, UI mode
`standalone_v1`, TFT page protocol v2 and discovery protocol `NSPALARM1`.
The already generated HMI source is unchanged by this firmware profile. No
compiled TFT release or immutable release URL is claimed. A future release must
bundle the reviewed source revision, model, TFT size/hash and compatibility
versions after Editor export and controlled device testing.

CI compiles both Easy-addon and standalone consumers from the exact tested commit,
checks encrypted OTA and safe relay defaults, and exercises device identity and
bounded display recovery. HA schema/templates and simulated registry adapters
are tested; they do not establish actual HA registry discovery or hardware
acceptance. Test the unchanged second Easy panel alongside the clock before
calling multi-device operation accepted.
