# Blueprint and UI review

Standalone 0.3.3-dev and the device Blueprint from the same revision retain the
existing protocol-v2 clock TFT. No new HMI export is needed. Firmware CI does not
replace physical acceptance on the panel.

## Settings and navigation

The Blueprint separates display pages, agenda, calendar wake adjustment, night
settings, tone preview, normal buttons, alarm buttons, custom actions and each
relay. Optional sections are collapsed. Input identifiers remain stable, so retain
existing helper selections when re-importing. Source-helper mappings are still
required for compatibility; leave their enable helpers off if unused.

Tap the top title for a **Pages** menu. Arrows, swipes and default physical holds
cycle through configured display pages, skipping the alarm editor. Previously
navigation entered the editor and its arrows adjusted time instead of advancing.
Page availability is now sent before optional calendar queries and helper
synchronization and persists locally. Enabled pages can still contain stale data.

The editor offers **Hour - / Hour + / Min - / Min +**. Hold to repeat after 0.5 s.
Tap the large time to choose the field for configured physical decrease/increase
actions. **Save** commits; **Cancel** or navigating away discards the draft.
The draft On/Off switch controls the master for weekly, app and calendar alarms.
Weekdays remain in the Blueprint. Agenda calendars only affect display content;
wake calendars can alter wake times. Master Off does not stop an unanswered alarm.

## Optional physical-button labels

Enable **Show physical button functions** in the normal-buttons section. Labels
appear above the left/right physical buttons, below touch navigation. `S:` means
short press and `H:` means hold (0.8 s). They follow the current normal/alarm
mapping. Inactive contextual actions show None; Snooze is inactive while snoozed.
Custom actions can have separate names for all four gestures, limited to eight
printable ASCII characters on the panel. These describe the configuration, not
confirmed success on the target. Custom actions require Home Assistant.

Labels are hidden in night mode and can be disabled entirely. Their area is not
a touch target. Right hold for five seconds remains the reserved local emergency
Stop, regardless of its configurable 0.8-second action.

Alarm mappings now offer only supported choices: None, Snooze, Stop and Custom.
If an older automation selected navigation/editor/decrease/increase during pending
alarms, select a supported value when editing. Those actions were already ignored
in that state. Normal mappings retain them.

## Tone preview

On the ESPHome device choose **Alarm Clock Preview Tone**, then press **Preview
Selected Tone**. **Preview Configured Tone** and the editor's **Preview tone** use
the saved preset. **Stop Tone Preview** stops it, otherwise it ends within five
seconds. An optional input_button in the Blueprint previews its selected preset;
stale/restored helper values do not start sound.

Preview changes no schedule, arms no alarm and runs no relay rule. It is refused
during pending alarms or updates. A real alarm cancels preview ownership so its
timeout cannot silence the alarm. **Alarm Clock Test** still starts a real alarm
and can activate enabled relay rules.

## Updating and diagnosing missing pages

Update/compile/install standalone firmware, re-import the device Blueprint and
save the existing automation with its helper mappings. Check **Alarm Clock
Available Pages** and **Current View** in ESPHome. **Pages Menu / Next Page /
Previous Page** buttons allow testing navigation without relying on touch.
If a configured page is absent from Available Pages, inspect the automation trace
and source selections. If present but touch cannot select it, capture panel logs
for hardware coordinate/queue testing. Pending alarms and notices take priority.

## Recommendations, not implemented here

1. Separate weekly enable from the global master so local edits cannot disable
   imported or calendar alarms unintentionally.
2. Add confirmed target-state feedback for appliance/custom actions. Requested
   means a command was sent, not that a lamp or thermostat changed.
3. Add firmware/TFT/Blueprint setup diagnostics, then extend agenda paging and
   implement Music Assistant as a separate optional module. Music playback is
   not currently provided by selecting display data.

Reference: [HA Blueprint sections](https://www.home-assistant.io/docs/blueprint/schema/)
and [selectors](https://www.home-assistant.io/docs/blueprint/selectors/).
