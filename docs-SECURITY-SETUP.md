# Repository protection: owner checklist

**Audit on 2026-10-13:** the public repo `3115a083/NSPanel-Alarm-Clock` had an unprotected `main` branch and no rulesets. The connected GitHub app cannot modify branch protection or Advanced Security configuration. These settings must be saved by the repository owner.

## Branch ruleset

Open `https://github.com/3115a083/NSPanel-Alarm-Clock/settings/rules` -> New branch ruleset:

- Name: `Protect main`; Enforcement status: **Active**; target default branch `main`.
- Require a pull request before merging, with **1 approving review**. Require review from CODEOWNERS and dismiss stale approvals when new commits appear.
- Require status check: **`unit-security-checks`** (after workflow has run once). Require branches to be up to date.
- Block force pushes and branch deletions. Block bypass including administrators if supported.
- Require conversation resolution; consider requiring signed commits after checking installed tooling.
- Restrict GitHub Actions workflow changes to owner-reviewed PRs. Never allow untrusted forks to access repository secrets.

## Security settings

Open `.../settings/security_analysis` or `Settings > Advanced Security` (UI labels vary):

- Enable dependency graph, Dependabot alerts, Dependabot security updates.
- Enable secret scanning and push protection where available (including validity checks).
- Enable private vulnerability reporting, where available.
- Review Settings > Collaborators and teams: remove unused write/admin access, require 2FA/passkeys and account recovery protections.
- Review Settings > Actions > General: disallow unnecessary third-party actions; restrict workflow permissions to **read only** by default; require approval for first-time contributors; do not allow Actions to create/approve PRs.
- Remove stale deploy keys, GitHub Apps, webhooks, and unused secrets; grant least privilege.

## Network and ESPHome

- Put NSPanel into isolated IoT VLAN; only allow local NTP/DNS, Home Assistant TCP 6053, and controlled OTA from a trusted admin host. Do not port-forward device services.
- Put credentials only in `/config/esphome/secrets.yaml`, which must never be committed.
- Firmware and TFT flashing must be performed during a maintenance window, not around the next alarm.
- For loss of power and time source, keep an independently powered alarm or provide UPS plus independent RTC. No software-only solution guarantees an alarm under every failure.

## Verify

`Settings > Rules > Rulesets` should show an active rule for `main`. A test PR should be blocked until the `unit-security-checks` workflow succeeds and approval is recorded. A force push to `main` should be rejected.

## Verified follow-up, 2026-10-15

Ruleset `main` (ID 25165128) is active on the default branch. It requires a PR,
linear history, blocks deletion/force pushes, and requires `unit-security-checks`
from GitHub Actions (integration 15368).

Still open: approvals=0, code-owner review=false, stale dismissal=false,
last-push approval=false, conversation resolution=false, strict status checks=false.
Integration 1144995 has `always` bypass. No release-tag ruleset was returned.
Identify and remove unnecessary standing app bypass. Add `firmware-build` as a
required check after the first successful run. Independent review requires a
second trusted person; document the solo-maintainer decision without self-approval.

Classic branch protection could not be read (403). Secret scanning/push protection,
Dependabot alerts/security updates, private reporting, default Actions permissions,
account 2FA and collaborator/deploy-key settings remain unverified. Missing access
does not mean these features are disabled. No administrative rule was changed by
this code review.
