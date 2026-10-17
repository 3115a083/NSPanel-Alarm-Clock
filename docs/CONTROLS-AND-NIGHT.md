# Standalone controls, night display and optional pages

Requires updated standalone firmware and the current **device** Blueprint
`nspanel_alarm_device.yaml`. Re-import that Blueprint to update its definition;
retain the selected panel and helpers when editing its automation. The legacy
three-sensor Blueprint does not configure these standalone UI features.

The existing protocol-v2 clock TFT is retained. Firmware enables Nextion
`sendxy=1` and decodes its touch-coordinate packets without consuming bytes from
the native display driver. No new TFT export is required for these controls.
Physical touch coordinates and appearance still need device acceptance.

## Screensaver first

The default is a **dim clock after 30 seconds**, 1% backlight and subdued clock
text. It shows the current time and actual next alarm, or --:-- when no alarm is
enabled. Black mode uses 0% backlight. This is an LCD: with no backlight its
time is not readable in a dark room. Adjust the lowest usable brightness on the
device; software cannot promise that every panel's minimum glow is acceptable.

Configure inactivity, dim/black/disabled mode, night brightness, awake brightness
and optional pre-alarm illumination in the Blueprint's **Screensaver and lights-out
schedule** section. Zero inactivity disables timeout. Prewake is off by
default. Ringing always wakes the clock at full brightness; Stop/Snooze returns
to ordinary inactivity behavior. A first touch/button press in night mode only
wakes the display, without accidentally editing or controlling anything.
Incoming weather/data refreshes do not count as user activity.

Screensaver availability is **all day** by default ("always"); inactivity still
allows temporary interactive use. Enable its time window, e.g. 22:00–07:00,
for scheduled operation. Brightness is selectable from 0–100%. A separate
backlight-off window, e.g. 23:00–06:00, can require one selected light to be off.
Then BOTH window and light-off must hold. No light selection makes that window
unconditional. Backlight-off wins over the dim window; outside both windows the
ordinary awake brightness applies. Windows support midnight and include their
start but exclude their end; equal endpoints mean all day. They use the panel's
configured local timezone. Without valid time, timed rules stay inactive.

Times/configuration persist locally, so the dim schedule works without HA.
The selected light is reported by HA on changes and each five-minute refresh;
unknown/unavailable or older-than-ten-minute state does not trigger conditional
blackout. It falls back to the ordinary screensaver rule. A touch/button still
wakes temporarily, and ringing/prewake illumination has priority over blackout.

Select **24h** or **12h**. In 12h mode AM/PM is placed in a text-capable field;
the large numeric fonts continue receiving only digits and a colon. Snooze
shows remaining **minutes:seconds**, independent of clock format. Countdown is
computed in RAM, never written to flash every second. Disabled alarms show
--:-- instead of presenting the stored default 06:30 as an active alarm.
Status labels use smaller fonts and short On/Off text to fit the EU viewport.

## Navigation and alarm editor

| Gesture | Result |
|---|---|
| Tap top title | Open Pages menu with every configured page |
| Swipe left/right | Next/previous enabled logical page |
| Hold right/left physical button for at least 0.8 seconds | Next/previous page |
| Bottom left/right arrow | Previous/next page |
| Clock: tap alarm area or bottom Set alarm | Open regular alarm editor |
| Editor: tap large time | Select hour or minute |
| Editor: Hour - / Hour + / Min - / Min + | Adjust directly; hold to repeat |
| Editor: configured decrease/increase physical button | Adjust selected field |
| Editor: tap On/Off | Change draft enabled state |
| Editor: Save | Save local weekly time and enabled state |
| Editor: navigate away | Discard unsaved draft |
| Thermostat/humidifier: tap left/right body or short physical button | Request lower/higher target |
| Thermostat/humidifier: bottom action | Request on/off |

Weekdays remain configured by the Blueprint and are shown in the editor.
Enabling a regular alarm with no selected weekdays is rejected. App/calendar
dated alarms remain separate; editing the regular time does not turn a dated
appointment into a repeated daily alarm.

During an unanswered alarm, local Stop/Snooze takes priority over navigation.
Default short right stops after release; short left snoozes a ringing alarm.
On-screen footer offers Snooze/Stop while ringing, Cancel snooze while snoozed.
The **Physical buttons** section independently maps left/right short/long in
normal operation and during an unanswered alarm. Choices: none, Snooze, Stop,
previous/next, editor, minus/plus or a custom Home Assistant action sequence.
Default normal gestures are minus/plus and previous/next; alarm defaults are
Snooze/Stop for both short and long. Navigation/editor actions are ignored while
an alarm is unanswered. Custom actions (for example a room light) can run then. Delegate long action
sequences to a separate HA script: this settings automation uses restart mode
and can restart when selected helpers or entities change.
Short gestures execute on release, long at 0.8 seconds, without a second short
trigger. Holding **right for five seconds always stops** an unanswered alarm,
regardless of its mapping, TFT or HA connectivity. This reserved emergency stop
cannot be remapped. Touch Snooze/Stop remains independent of button mappings.

## Local edit synchronization

Save persists the local time/enabled state and a revision. While this revision
is unacknowledged, an HA plan cannot overwrite it. The device Blueprint mirrors
the saved time and master state to the selected helpers, then acknowledges the
revision through the device-bound API. Helper writes are idempotent so automation
restart on a helper change can finish the synchronization on its next run.

Enable **Allow the device to perform Home Assistant actions** for this panel's
ESPHome integration to receive its device-filtered UI request events. This gives
immediate sync and optional external controls. Without event permission, the
Blueprint's five-minute refresh still discovers saved edits. A local edit made
while HA is unavailable stays local until HA acknowledges it. Updating firmware
without updating the Blueprint can leave edits pending; re-import and configure
the device Blueprint instead of deleting the pending state. Existing one-writer
rule still applies: disable previous alarm planners for this panel.

## Optional pages and calendar separation

Select zero or one weather entity, up to four read-only entities, zero or one
thermostat and zero or one humidifier. Only configured pages are in navigation.
Sources are selected explicitly; a data page does not grant control of arbitrary
services or relays. External strings are length-limited and stripped of control,
quote and backslash characters before being sent to the Nextion command stream.

Thermostat/humidifier control is **off by default** and has a separate opt-in for
each domain. Requests target only its selected entity, require available state
and clamp target adjustments to reported limits. Temperature uses the entity's
step, humidity uses 5 percentage points. Unsupported or unavailable controls do
not trigger a fallback device. UI shows authoritative HA values after refresh,
not an optimistic claim that an appliance actually changed.

**Calendar wake range** already selects calendars influencing alarms. The new
**Display calendars** and optional case-insensitive title filter are independent.
The agenda shows the first two matching events returned for the near horizon.
Failed agenda queries keep previous lines and mark them stale. Agenda failure
does not replace the existing wake-calendar failure policy.

Optionally show the agenda for a configured duration after **Stop**. Snooze does
not mean awake and does not open the agenda. Navigating away cancels automatic
return. Data pages mark values stale after ten minutes without refresh; they are
not an offline source of live weather or appliance state. Sensor triggers wait
five seconds for a stable change; a bounded five-minute refresh remains.

## Acceptance boundaries

The previous standalone version was deliberately read-only and had no long-press
navigation. Its working display is not proof these new interactions have passed
hardware tests. Test night glow, first-touch consumption, coordinate orientation,
swipes, long/short button separation, local edit/HA outage, AM/PM, Snooze/Stop
and each explicitly enabled appliance control separately. No physical appliance
is actuated by CI. [Relay rules and doorbell/security overlays](RELAYS-AND-EVENTS.md) now have a separate
module. Music Assistant remains later work.
