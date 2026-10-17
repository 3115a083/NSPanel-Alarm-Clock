# Alarm settings blueprint

For a single device selection instead of three sensor selections, use the new
`nspanel_alarm_device.yaml` Blueprint with updated firmware. See
[device discovery and standalone setup](STANDALONE.md). Existing automations keep
their input schema. Disable the previous planner before enabling its replacement.

The optional settings blueprint plans locally executed alarms. Keep the existing
NSPanel Easy automation for its base settings/display handshake. Use one settings
automation per panel and disable the legacy `wecker_schedule_sync` writer if it
was installed. Do not run both planners against the same panel.

## Setup

1. Update the alarm firmware from GitHub, compile and install it deliberately.
   It must expose `alarm_apply_plan`, `alarm_disable` and the new Day Plan
   Signature sensor. This does not require a new HMI. The optional clock UI now
   displays the actual next alarm date/time and its App/Calendar/regular source.
2. On HA 2026.10.1 or newer, create the five helpers in
   `homeassistant/alarm_clock_helpers.yaml`, either in the Helpers UI or by loading
   that file as a package. A blueprint cannot create helpers automatically.
   Master/App/Calendar start disabled. Set your normal time before enabling.
   For multiple panels create separate helpers and select them in each blueprint.
3. Import the blueprint:
   https://github.com/3115a083/NSPanel-Alarm-Clock/blob/main/homeassistant/blueprints/nspanel_alarm_settings.yaml
4. Select this panel's Device Name, Configuration Signature and Day Plan Signature
   sensors. Device Name must be the Easy sensor containing its internal ESPHome
   name, not a friendly label. Actions are restricted to that name's ESPHome
   alarm endpoints. Missing old-firmware endpoints stop synchronization.
5. Select regular weekdays, snooze and mandatory buzzer delay. The master helper
   disables future alarms. Stop/Snooze still acknowledge an already active alarm.

## App import

The date-and-time helper can receive an alarm through an authenticated HA action
`input_datetime.set_datetime` with an absolute `timestamp`. Leave the sensor input
empty for this mode. For Android, select exactly one Companion `next_alarm` sensor
and enable App Import. Filter it to the intended alarm app in Companion settings;
optionally require its exact `Package` attribute in the blueprint too.
The blueprint mirrors the timestamp into the helper. By default an unknown,
unavailable or package-mismatched sensor retains only an app alarm already
acknowledged in the panel's Day Plan Signature. This covers Android clearing its
sensor at alarm time. Explicitly disable App Import to cancel it. Optional Clear
mode removes the override and uses calendar/regular instead. A helper without a
previously committed alarm cannot invent a retained alarm. The helper uses a past
sentinel when no valid/retained source exists. An explicit helper-only import is
cancelled by disabling App Import or setting its helper to a past date.

Sleep as Android must actually publish its alarm via this Android interface or an
authenticated integration that updates the helper. No special Sleep as Android
webhook, app-side setup or device interoperability has been tested here. No public
webhook, arbitrary URL execution or embedded token is supplied.

## Calendar rules

The blueprint reads events from the selected calendars for today/tomorrow, with
an extra offset horizon to cover midnight-crossing wake times. It uses every timed
event returned, not just the calendar entity's single next-event attribute.
All-day/invalid events are ignored. Choose the wake range and appointment lead.
The range is inclusive and cannot cross midnight. It applies to **wake time**,
not appointment time. The earliest eligible computed wake time wins.

Example normal time 07:00, range 06:00-08:30, lead 30 minutes:

| Appointment | Calendar wake | Result |
|---|---|---|
| 08:00 | 07:30 | Calendar alarm at 07:30 |
| 10:00 | 09:30, outside range | Normal alarm at 07:00, if that weekday is selected |
| All day | None | Normal weekly fallback |

Select **Only move the regular alarm earlier** if an in-range calendar event
must never postpone your normal time. Calendar alarms on unselected weekdays
require a separate opt-in. A valid app alarm takes priority for its exact date,
including otherwise unselected weekdays. The master helper gates all sources.

## Failure and restart behavior

Changes and HA startup/reload trigger a sync. A bounded five-minute refresh covers
calendar edits and reconnections. A failed calendar query preserves the complete
last good panel plan and reports a stopped/error trace; it does not treat a failed
query as an empty calendar. Master off bypasses calendar/helper errors and disables
future alarms through a separate endpoint. Verify acknowledgement via the two
signature sensors; a successful service call alone does not prove synchronization.

The panel validates the complete weekly plan and both dated exceptions before
applying them together, arming last. Exceptions are absolute timestamps with a
matching local date, limited to the near future, persisted alongside the weekly
plan and ignored on other dates. One scheduled alarm per local date, including
Stop/Snooze recovery, remains the rule. Past/consumed plans cannot cause a second
alarm after Stop. Ordinary weekly DST rules remain first fall occurrence only,
nonexistent spring time skipped. App/calendar timestamps identify exact instants.
HA and panel timezone must agree. Cache/flash updates are not power-loss atomic.

Once synced, the panel can execute the stored dated exceptions and weekly plan
without HA. Future calendar/app edits cannot arrive during an outage. After the
two cached dates, the ordinary weekly plan continues. No HA, app, TFT or physical
runtime acceptance is implied by CI/schema/template tests.

## Following modules

User-requested next steps, not implemented by this settings blueprint: configurable
physical short/long button actions and relay timing; doorbell/alarm overlays with
explicit screen actions; ringtone presets; night brightness/screensaver/prewake
light; optional weather; filtered calendar overview after waking; swipe/arrow/long
press navigation; sensor/media pages and Music Assistant. Calendar display sources
must be independent of calendars allowed to influence alarms. Keep a local Stop
path, prioritize the mandatory alarm buzzer over optional tones and never open a
door merely because a doorbell event arrived. These additions need separate
state/priority and hardware acceptance tests.

References: official HA blueprint schema, calendar.get_events, input_datetime and
Companion Next Alarm documentation. CI uses the actual pinned HA 2026.10.1 schema
and template engine in addition to native tests of the firmware scheduler.
