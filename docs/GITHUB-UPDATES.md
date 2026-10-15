# Get updates directly from GitHub

The ESPHome device YAML can fetch this complete project package, including the
alarm C++ header. Only the device YAML and `secrets.yaml` remain local.
Requires ESPHome 2026.9.1 or later. This version resolves a package's header
relative to the declaring YAML when no local file shadows it.

## One-time migration from local alarm files

1. Back up the working device YAML and secrets locally.
2. Move the old `nspanel_alarm_local.yaml` and **`alarm_schedule.h`** out of
   `/config/esphome/` into your backup folder. ESPHome checks beside the device
   YAML first, so leaving an old header there can silently build old code.
3. Replace the entire existing `packages:` mapping with:

   ```yaml
   packages:
     alarm_clock:
       url: https://github.com/3115a083/NSPanel-Alarm-Clock
       ref: main
       refresh: always
       files:
         - nspanel_alarm.yaml
   ```

   This entry already includes the pinned NSPanel Easy package. Remove the old
   Easy package entry and `wake_alarm: !include ...`; loading both duplicates
   scripts and hardware configuration. Do not replace device names or secrets.
4. Keep existing `api.encryption.key`, Wi-Fi secrets, `alarm_timezone`,
   `language: en` and `upload_tft_automatically: false`. The entry point supplies
   encrypted OTA and zero API/Wi-Fi reboot timeouts. An identical local
   `!extend ota_std` block may be removed; do not add another OTA listener.
5. Keep `local_ntp_server` in local `secrets.yaml`. Validate, then install
   wirelessly through the existing ESPHome device entry. Check the alarm's saved
   schedule and repeat a short Test/Stop check after updating.

## Subsequent firmware updates

Use **Install  Wirelessly** in ESPHome Device Builder. `refresh: always` fetches
the package at the start of configuration/build operations. Validation alone
does not change the running device; installation compiles with local credentials
and uploads through required encrypted OTA. No recurring manual file download.

`main` is the development update channel. It follows merged changes after the
required unit/security and complete firmware build checks. CI cannot prove
hardware acceptance of every change. Replace `ref: main` with a reviewed full
commit SHA to freeze or roll back to that source revision. Keep a known-working
device configuration. A frozen ref does not advance automatically.

Builds require access to GitHub and toolchain/package sources. The installed
local alarm does not need GitHub to run. This package does not install scheduled
unattended updates or publish a generic binary containing device credentials.

## Display and Home Assistant updates

ESP32 firmware, Nextion TFT and Home Assistant Blueprint are separate artifacts.
There is not yet a custom clock TFT or project Blueprint release to install.
When introduced, publish matched versions and a compatibility check, plus a
GitHub URL for TFT upload and Blueprint import. Retain controlled TFT installation:
an ESPHome package refresh alone must not upload a TFT or replace an automation.
Do not point a TFT uploader at GitHub source HTML or an uncompiled HMI file.

## Maintainer verification

CI copies only the consumer device YAML into an isolated temporary directory.
It fetches this package at the exact tested Git SHA, resolves the header from
the remote checkout, verifies it matches the candidate source, validates merged
alarm hooks and encryption policy, then compiles the complete firmware.
This prevents a local source copy from hiding a broken remote installation.
