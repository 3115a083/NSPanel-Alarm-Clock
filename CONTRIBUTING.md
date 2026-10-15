# Contributing

Please open a pull request for changes. The alarm safety path must remain independent from Home Assistant and media-player acknowledgements.

Before proposing a change:

1. Run `python3 -m unittest discover -s tests -v` and `python3 .github-secrets-scan.py`.
2. Do not add secrets, sample real IP addresses, site-specific entity IDs, personal information, or compiled firmware.
3. Do not add public API endpoints, HTTP control servers, or arbitrary `shell_command` / webhooks to the alarm path.
4. Keep the upstream NSPanel Easy version pinned, and test new upstream releases separately.
5. Document all changes to the offline alarm, persistence, button mapping, and DST behavior.
6. Never weaken the audible buzzer fallback based on reported media player state.
7. PRs modifying `.github/`, `esphome/`, or `homeassistant/` need explicit human review before merge.
