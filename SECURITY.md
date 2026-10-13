# Security policy

## Supported versions

This repository is an **unverified prototype**. No version is security-certified or production approved.
Never rely on this project as the only wake-up mechanism until real hardware and fault tests pass.

## Reporting a vulnerability

Prefer GitHub's **Report a vulnerability** / private vulnerability reporting option on the Security tab, if enabled. Do not publish exploitable details, API encryption keys, Wi-Fi credentials, credentials of Home Assistant, or home network details in a public issue.
If private vulnerability reporting is unavailable, ask the repository owner for a private contact route without posting the exploit.

## Security model

- The device is on a trusted home network. ESPHome API uses a unique secret encryption key.
- Local OTA update should use a unique strong password and is only reachable from trusted hosts.
- No cloud credentials, device secrets, `.env` files, production configurations, compiled firmware, or local tokens belong in Git.
- `NSPanel Easy` upstream release is pinned; updates require review and regression testing. An upstream tag is not an immutable commit. For stronger supply-chain protection, replace the tag with a reviewed commit SHA.
- Avoid publicly exposing ESPHome native API (TCP 6053), OTA, Home Assistant, or NTP management.
- `main` requires a GitHub ruleset. The ruleset must be enabled in repository settings; CODEOWNERS alone cannot enforce reviews.
- GitHub Actions jobs have read-only token access, no pull_request_target event, no self-hosted runner and no secrets.

## Incident response

If credentials are leaked, rotate the credentials immediately in ESPHome/Home Assistant and any affected accounts; deleting a committed secret does not remove it from Git history.
