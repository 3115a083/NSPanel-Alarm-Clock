# Standalone device entities

Requires standalone 0.3.4-dev. Update/install firmware to obtain these ESPHome
entities. Re-import the device Blueprint to report its version. Existing protocol-v2
TFT is retained. The Easy-addon profile keeps its original Easy entities.

## Easy equivalents and additions

Compared against Easy commit `c9aff59c397c26b0556c4e3930827502a5836d00`.
Names below are English entity names; Home Assistant entity IDs depend on the
device name and existing registry. No personal entity IDs are assumed.

| Easy function | Standalone entity / behavior |
|---|---|
| Temperature | Temperature, physical GPIO38 NTC, degrees Celsius |
| Temperature Correction | Temperature Correction, -10 to +10 degrees Celsius |
| Display Brightness | Existing Alarm Clock Idle Brightness, awake value 1-100% |
| Display Brightness Dimdown | Display Brightness Dimdown, 1-100% |
| Display Brightness Sleep | Display Brightness Sleep, 0-100% |
| Timeout Dimming | Timeout Dimming, seconds, 0 disables intermediate dimming |
| Timeout Sleep | Timeout Sleep, seconds, 0 disables automatic night timeout |
| Timeout Page | Timeout Page, seconds, 0 disables return to Clock |
| Wake-up page | Wake-up page, only configured logical pages can be shown |
| Sound - Notification | Sound - Notification, doorbell/alert tones only |
| Notification Unread | Notification Unread, current doorbell/alert popup active |
| Device Name | Device Name |
| Current Page | Existing Alarm Clock Current View, including Pages/Night |
| Firmware version | Version - Firmware, project version |
| Blueprint version | Version - Blueprint, last compatible device Blueprint report this boot |
| TFT version | TFT Protocol, actual Clock v2 announcement, not a guessed compiled TFT version |
| Baud rate | Baud rate, configured active standalone UART speed |
| Display model | Display Model, read-only NSPanel EU |
| Relay 1 / Relay 2 | Already present, including manual takeover of automatic timers |
| Left / Right Button | Already present, with separately configurable gestures |
| Restart | Already present |
| Display power | GPIO power stays internal, as in the reviewed Easy source; use Display Backlight |
| Background type | Dark clock UI; no unsupported Light selector is offered |
| Detailed Entity | No stock Easy detail-page lifecycle; selected clock data pages remain separate |

Additional diagnostics: WiFi Signal (60 s), Uptime (60 s), Device Online,
Display Ready and Display Brightness Target (computed backlight command, not a
measurement or confirmation from the LCD). Existing alarm status, plan/configuration
signatures and display diagnostics remain available.

## Choosing who owns brightness and sleep settings

**Display Settings from Blueprint** starts On. The device Blueprint owns awake
brightness, night brightness/mode/timeout, clock format, prewake and timed night
rules. Changing **Alarm Clock Idle Brightness**, **Display Brightness Sleep**,
**Timeout Sleep** or **Screensaver Mode** directly switches this ownership Off.
This preserves the adjustment through later Blueprint refreshes.

When Off, the last received clock/night schedules remain active locally, but new
Blueprint display settings are ignored. Light status for conditional blackout
still refreshes, and stale light status still cannot trigger blackout. Alarm
schedules, button mappings, data cards and relays remain managed independently.
Turn ownership On again to request a Blueprint refresh. An inactive or unavailable
automation can only apply its settings on a later successful run.

Intermediate dim brightness/timeout, page-return timeout, wake-up page and
temperature correction are device settings and do not change ownership. Values
persist across reboot. Dimming defaults Off to preserve existing behavior.
Sleep/night mode has priority over intermediate dimming. Ringing and prewake
illumination take priority over both. Returning to Clock discards an unsaved editor
draft; disable Timeout Page if that is unwanted.

**Display Backlight Off** temporarily blacks the display without cutting Nextion
power or disabling the alarm. Touch, a physical button, a notice or a ringing
alarm wakes it again. Use the existing night schedule for sustained quiet hours.
At 0% backlight, the LCD clock is not readable in a dark room.

**Sound - Notification Off** silences future doorbell/alert notification tones.
It never silences the mandatory alarm buzzer or tone preview. A tone already
playing finishes normally; this switch does not stop another sound owner.

## Temperature and verification

The physical conversion uses GPIO38 ADC, a downstream 11.2 kOhm resistor and
10 kOhm/25 C NTC with B=3950, matching the reviewed Easy hardware constants.
ADC samples are filtered; only meaningful changes and a five-minute heartbeat
are published. Correction applies to raw temperature, so repeated changes do not
compound the offset. The panel's internal heat can bias room temperature.
Compare against a reference thermometer after warm-up before choosing an offset.
Missing/invalid readings stay unknown, not a fabricated room temperature.

The actual merged consumer configuration and complete ESPHome firmware are
validated in CI. Native tests cover intermediate dimming, page timeout, wake-up
selection, night priority and alarm priority. Physical temperature accuracy,
brightness and gesture acceptance remain device tests.

References: [Easy temperature hardware](https://github.com/edwardtfn/NSPanel-Easy/blob/c9aff59c397c26b0556c4e3930827502a5836d00/esphome/nspanel_esphome_hw_temperature.yaml),
[ESPHome NTC](https://esphome.io/components/sensor/ntc/),
[ADC](https://esphome.io/components/sensor/adc/).
