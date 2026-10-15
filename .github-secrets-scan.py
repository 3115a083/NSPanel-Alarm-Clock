#!/usr/bin/env python3
"""Dependency-free repository secret hygiene guard.

This is a best-effort check, not a substitute for GitHub secret scanning.
Avoid printing suspicious lines or credentials into public CI logs.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
EXCLUDED = {'.git', '.esphome', '__pycache__', '.pytest_cache'}
SUSPECT_NAMES = {'secrets.yaml', 'secrets.yml', '.env', 'credentials.json', 'service_account.json', 'id_rsa', 'id_ed25519'}
RULES = [
    re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(r'gh[pousr]_[a-zA-Z0-9]{35,}'),
    re.compile(r'github_pat_[a-zA-Z0-9_]{20,}'),
    re.compile(r'(?i)\b(?:password|token|api_key|api_encryption_key|secret_key)\s*:\s*(?![\\!]secret\b)["\']?[a-zA-Z0-9_@!#$%^&*+=:/.-]{16,}'),
]

def main():
    violations = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        rel = path.relative_to(ROOT)
        if (path.name in SUSPECT_NAMES or
                (path.name.startswith('.env.') and path.name != '.env.example') or
                path.suffix.lower() in {'.p12', '.pfx', '.jks'}):
            violations.append((rel, 'credential file'))
            continue
        # Scan every small UTF-8 file, including extensionless and C++/JS sources.
        if path.stat().st_size > 1024 * 1024:
            continue
        try:
            raw = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        if any(rule.search(raw) for rule in RULES):
            violations.append((rel, 'possible embedded secret'))
    for rel, reason in violations:
        print(f'{rel}: {reason}. Inspect locally; do not copy secret into a ticket.')
    if violations:
        return 1
    print('No obvious committed credentials detected (heuristic only).')
    return 0

if __name__ == '__main__':
    sys.exit(main())
