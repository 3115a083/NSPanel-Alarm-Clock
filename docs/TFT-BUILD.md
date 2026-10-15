# Prepare the custom clock TFT

Status: protocol-v2 HMI source and an opt-in local renderer are available for
Editor/device testing. No compiled clock TFT has been validated or released.
The default alarm add-on does not enable the UI or upload a TFT.

## Reproducible source preparation

From a checkout of this repository, run:

```text
python tools/prepare_tft_sources.py
```

This downloads the EU landscape HMI and Easy's MIT license from the exact
reviewed Easy commit. hmi/upstream.json records the commit, source sizes,
Git blob identities and the HMI SHA-256. Unexpected content is rejected before
it becomes a source file. No downloaded program is executed.

Files are staged under ignored build/tft:

- upstream/nspanel_landscape.hmi: verified reference. Keep unchanged.
- upstream/LICENSE.NSPanel-Easy: retain with derivatives.
- working/nspanel_alarm_eu.hmi: initial unmodified copy, reserved for editing.

Running preparation again preserves an existing working HMI. A modified reference
is rejected rather than silently overwritten. To work offline, download the
manifest files into a cache directory using their listed name fields, then run
python tools/prepare_tft_sources.py --cache PATH.

## Editor and baseline gate

Use Nextion Editor **1.68.2 or later**, required by Easy's macros. Obtain it from
the official https://nextion.tech/nextion-editor/ page. Portable ZIP is supported.
The repository does not redistribute or automatically run the proprietary editor.

1. Open the working HMI. Keep the model/orientation from the known EU source.
   Do not substitute an approximately similar retail Nextion model.
2. Record the Editor version and confirm existing pages/resources load.
3. Save, Compile, and inspect all errors. A source or syntax check is not a TFT build.
4. Use **File > TFT file output** to produce the baseline artifact. Compile alone
   does not establish that a new TFT file was exported.
5. Record output SHA-256, size, source revision and Editor version.
6. Do not flash this baseline clone as a new clock UI. It is unchanged Easy.

Official reference: https://nextion.tech/editor_guide/ . The Editor simulator
assists development; it does not prove real-device rendering or timing.

## First local clock page contract

### Experimental layout candidate

After preparing sources, run:

```text
python tools/build_clock_hmi.py build/tft/upstream/nspanel_landscape.hmi --output build/tft/working/nspanel_alarm_eu_preview.hmi
```

Open the generated HMI in the Editor and select **home_smpl**. This existing
offline-capable page is repurposed for a dedicated clock view, preserving page
registration and every other resource. Its original named components remain
available but hidden; old touch/navigation actions and timers on this page are
disabled. New wa_ components show placeholders until the optional firmware
renderer is connected. This is a read-only clock view, not working touchscreen
controls or a replacement for the already tested local alarm core.

CI provides an **eu-clock-hmi-preview** source artifact with the HMI, upstream
license, source manifest and these instructions. The source is generated from
the pinned HMI, not from your local device configuration. No credentials enter it.
Artifacts are retained for 14 days; this is not a stable TFT release URL.

The generator verifies the pinned source SHA-256, original page/directory
checksums and lossless component parsing. It rebuilds home_smpl and appends a
protocol announcement to the existing boot acknowledgement timer. All other
live resources stay byte-for-byte identical.
An independent Nextion2Text read also succeeded locally. These checks do not
prove Nextion Editor acceptance or device rendering. Compile in Editor and
inspect home_smpl before firmware integration. **Do not flash this preview.**

### Optional firmware renderer, protocol v2

After Editor acceptance, add `nspanel_alarm_ui.yaml` immediately after
`nspanel_alarm_addon.yaml` in the same GitHub package `files` list. Keep Easy
and the regular alarm add-on. Do not replace the complete device YAML or secrets.
The UI is separate and is not enabled by updating the alarm add-on.

The boot page announces `wa_hmi_v2` using Nextion custom binary event 0x93.
The clock page announces `wa_clock_v2` on entry. The earlier v1 preview is
incompatible with this renderer. On an unmodified TFT there are no new-component
writes and no automatic switch to home_smpl. Display setup clears compatibility;
every page change clears entry readiness and the write cache. Firmware requires
both compatibility and a fresh clock-page event before rendering unscoped fields.
Protocol sensors never poll the event names as Nextion variables. Setup/page
callbacks rearm their local false state so repeated true announcements can fire.

The renderer reads the existing local time/schedule/ring/snooze globals. It shows
time, ISO date, configured alarm time (not a calculated next occurrence), enabled
state and weekdays. Invalid time shows --:-- and Waiting for time sync.
Ringing and Snoozed take status priority. The 1s loop writes only changed fields
and stops during TFT/OTA upload or a display queue backlog. No UI cache or
countdown is written to flash.

`Alarm Clock Start View` selects Clock or NSPanel Easy, persisted by ESPHome.
The optional UI owns home/wake routing, superseding Easy wake-up-page settings.
Selection also opens the chosen view on the next UI tick. A ringing alarm defers
the requested view change until Stop/Snooze; the alarm page keeps priority.
A compatible display exits boot into the selected home without waiting for HA,
Wi-Fi or the Blueprint. It does not fake Easy readiness flags. Existing Easy
boot work may continue in the background. The clock stays visible with normal
dimming. Ringing opens it and prevents sleep/dimming. Stop/Snooze restores the
normal dim timer. Physical buttons and mandatory buzzer keep their existing path.

Still pending: Editor compile and device verification of startup, display reset,
offline operation, Stop/Snooze, routing and background Easy constructors.
Touchscreen editing, optional weather, own Blueprint, relay/sensor pages and
Music Assistant controls follow after clock acceptance. One HMI retains the
standard home, entity and media pages; two complete HMI variants are unnecessary.

### Target behavior

The design target is 480 x 320, English initially. It must display current
time, date, configured alarm time, selected days, enabled status and the next
actual alarm. Invalid local time displays --:--. Ringing and snoozed states
take priority over menus and idle display behavior. No seconds/countdown writes
to flash. Render only changed values and page-entry snapshots.

All new component names must use a wa_ prefix. Document names, actual generated
component IDs, available font glyphs and touch events from the edited HMI.
Do not hardcode guessed IDs. A new page requires matching Easy page registration
and offline-capability handling. This candidate reuses home_smpl; firmware must
still prevent constructor/refresh conflicts and provide local startup/rendering.
Easy's existing alarm page is a security system, not an alarm clock.
The unmodified canvas page redirects away when HA is offline.

Firmware owns the schedule and ring/snooze state. Future TFT touch actions call
the same validated local path as API actions. Do not introduce a second alarm
scheduler, arbitrary HA service names or relay actions into clock touches.
Keep physical right-button Stop operational independently of TFT compatibility.
Check a dedicated UI protocol version before addressing new components.

The local clock UI must initialize even when HA is unavailable at cold boot;
redirecting after Easy's Blueprint handshake is insufficient. Suspend display
updates during TFT upload through the existing upload lifecycle. Relays and
the project Blueprint follow after the clock UI's hardware acceptance.

## Release gate

Only publish a clock TFT after an actual successful Editor build and compatible
ESPHome build, simulator review and controlled EU hardware tests. Keep a known
working Easy recovery pair. A release must identify both TFT and firmware/UI
protocol versions. Do not invent a download URL for an artifact not yet built.
