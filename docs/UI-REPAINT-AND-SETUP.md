# Display controls and setup, blueprint 0.3.5

Update the standalone firmware and re-import the device blueprint. The existing
clock protocol-v2 TFT remains compatible; no new TFT export is needed.

## Setup order

1. Select the device and map the required helpers (existing mappings are retained).
2. Set the weekly time, weekdays, master switch, sound and snooze duration.
3. Select the optional weather, entity, thermostat and humidifier pages.
4. Configure screensaver brightness and lights-out rules.
5. Select calendars for the calendar page and its optional after-Stop duration.
6. Optionally configure app import and calendar-based wake adjustments.
7. Change physical-button mappings and names, then optional relay outputs.

Number prefixes were removed from section titles: Markdown can render each
separate numbered heading as “1”. Nine thematic groups replace thirteen sections.
Tone choices live with the alarm settings; normal/alarm/custom button actions
share one section. Relay settings share another. Existing input IDs are retained.

Empty display-calendar selection now uses the wake calendars for display. This
does not enable calendar alarms: their enable helper still controls scheduling.
An explicit display-calendar selection takes precedence. Weather has its own
page; selecting a weather entity does not replace the clock with the stock home.

## Repaint and navigation corrections

Native text updates and coordinate graphics previously had separate caches.
Invisible text fields could still be updated over the menu/editor drawings;
coordinate buttons were then considered unchanged and remained invisible.
Only visible native fields are updated now. Controls are restored after native
text changes, plus bounded once-per-second repair for display-side repainting.
The existing queue guard prevents flooding the display.

A deliberate physical hold now runs its configured action even if the initial
press woke a sleeping display. A short press still only wakes it. An empty extra
page selection displays a setup hint when Next/Previous is pressed.

Device-scoped service-registration triggers retry page/card setup when ESPHome
services become available after the identity sensor. Unrelated devices/services
are filtered before the restart-mode automation starts. Page setup waits at most
20 seconds for its API, rather than silently skipping it. Card delivery precedes
optional relay setup, so an unrelated output error cannot suppress weather data.

The redundant Stop Tone Preview device button is removed. Short previews retain
their timeout and alarm-priority cancellation; internal stop API remains compatible.

## Hardware acceptance still required

After updating firmware and re-importing/saving the blueprint, check:

- **Available Pages** contains every selected page; **Version - Blueprint** is 0.3.5.
- Editor +/- and menu rows stay visible while tapping, waiting and changing time.
- Right hold, Next Page, touch arrows and swipes reach weather/thermostat/calendar.
- A short sleeping-screen press wakes; a deliberate hold wakes and navigates.
- Weather values refresh, including when a selected calendar is unavailable.
- Night mode, alarm Snooze/Stop and configured custom button actions still work.

Automated command/cache and controller tests plus firmware compilation cannot
prove the physical Nextion repaint behavior. Record the hardware result separately.
