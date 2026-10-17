# Local relay rules, tones and event screens

Experimental standalone EU firmware 0.3.2-dev, using the existing v2 clock TFT.
No TFT export is needed. Re-import the device Blueprint for new relay/tone inputs.
The optional `nspanel_alarm_events.yaml` Blueprint is a separate automation with
its own panel selection and zero/one doorbell and alert sources. It requires no
alarm helpers. The Easy add-on gains alarm tone presets; local relay rules and
notification screens belong to the standalone profile only.

## Relay rules

Both relays still boot OFF. Rules are OFF by default. Enabling a rule explicitly
also makes **Test Alarm** trigger that output. Configure and check each rule
without connected loads first. No real relay is actuated by tests or this change.

| Mode | Behavior |
|---|---|
| off | Alarm does not acquire the relay |
| pulse | Switch on after delay, switch off after selected pulse duration |
| until_stop | Remain on until Stop |
| latch | Remain on after Stop, until manual takeover or maximum automatic on-time |
| after_stop | Remain on during alarm, then for selected duration after Stop |

Each output has delay 0–600 seconds, pulse/tail duration 1–3600 seconds and a
maximum automatic on-time of 1–86400 seconds. The maximum always wins, including
over a tail or latch. An output marked **auxiliary buzzer** is additionally capped
at 60 seconds. These outputs never replace the mandatory internal alarm buzzer.
Deadlines run locally, at 100 ms resolution. They do not use HA delay chains.
Changing a rule releases a currently owned output. Identical periodic settings
updates preserve its running deadline. Stop cancels a delayed start; it never
switches a not-yet-started light on later. Repeated ringing/Stop does not extend
an existing pulse or tail. Reboot restores configuration, not output ownership.
TFT transfer is refused while an automatic output is active or waiting. Starting
firmware OTA releases automatic output ownership and turns those outputs off
before transfer, so a blocking update cannot extend a pulse or tail.

Choose whether Snooze releases the output and whether a resumed alarm triggers
it again. Up to four explicit on/off conditions can be combined with **all**
(AND) or **any** (OR). Empty means unconditional. All selected states must be
known; unknown/unavailable denies a new start even in OR mode. Conditions are
checked at alarm start and again before a delayed switch-on. Their HA snapshot
expires after ten minutes. A later condition change does not retrospectively
start an output for the current alarm. Unconditional rules work without HA.

An already manually ON output is never acquired. A manual state change cancels
its old alarm timers. ESPHome deduplicates identical state publications, so
another ON command while already ON cannot itself prove manual takeover. Use
**Relay 1/2 Cancel Alarm Timer** to retain its current state and cancel ownership,
or device-bound `alarm_manual_relay` with `relay` 1/2 and `target_on` true/false.
Manual control has no alarm-owned automatic deadline. These explicit paths also
cancel a pending delayed start. A fresh later alarm can acquire a manually OFF
output again; an already ON output remains manual.

## Tone presets

Mandatory alarm: Wake, Classic, Gentle, Signal. No silent alarm preset exists;
invalid preset indexes fall back to Wake. Existing grace and local buzzer loop
remain authoritative. Optional notices: mute, door, beep, alert, soft. Notice
sounds are finite and never start while a wake alarm is pending, including
Snooze. There is no arbitrary uploaded RTTTL, streaming audio or ringtone loop.

## Doorbell and alert screens

Select one doorbell binary sensor and/or one binary sensor/alarm-control-panel
for alerts. A source becoming on/triggered requests a bounded 5–300 second screen.
Configure message, action label, brightness, cooldown and tone. Text is sanitized
before Nextion commands. Empty action sequences produce a display-only notice.
An action is the explicitly configured HA sequence or script, not an implicit
unlock/disarm service guessed from the source. Enable this panel's ESPHome option
to perform Home Assistant actions for touch confirmation events.

First tap **Open door / Cancel alarm** opens confirmation. A second tap within
five seconds emits once. Dismiss and expiry only close the display. The two-tap
confirmation is an accidental-touch guard, not authentication. Keep credentials
inside the authorized HA integration/script. No access codes go to the TFT.

The event automation captures the source's activation context while waiting for
the corresponding device/MAC/token-bound confirmation. A short doorbell pulse
can end before the user responds. A newer activation replaces the old wait;
stale tokens and foreign panels are rejected. Alert actions additionally require
the alert still active with the matching context. Waits have the screen timeout,
run in parallel with a hard maximum of four, and perform no polling. Delegate
long confirmed action sequences to separate HA scripts.

There is one local notice slot. Alert replaces doorbell; lower priority notices
are discarded while an alert occupies it. Per-kind cooldown suppresses repeated
sound; an updated currently visible same-kind notice gets a new token without
extending its original expiry. Replayed tokens cannot reopen the same notice.
No unbounded popup queue exists. Wake alarm/Snooze acknowledgement takes priority
over every notice; expiry continues while a notice is hidden. No popup dismiss,
door action or security action acknowledges the wake alarm. After dismissal or
expiry, the underlying page and ordinary inactivity rules resume.

Door/security sources and their actions need HA. Local alarms, unconditional
relay deadlines and the reserved right-button emergency Stop remain local.

## Acceptance still required

Native tests and full builds do not verify actual wiring, sound level, display
coordinates, door hardware or a security integration. Check relay ownership,
manual takeover, delay cancellation, Snooze/resume, maximum-on caps, short door
pulses, two taps, stale tokens, simultaneous alarm/doorbell and HA outage on the
real installation. Music Assistant and a richer media page remain later work.
