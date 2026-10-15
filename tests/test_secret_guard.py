"""Secret guard regressions. Test values are deliberately constructed dummy strings."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("secret_guard", Path(__file__).resolve().parents[1] / ".github-secrets-scan.py")
SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAN)

class SecretGuardTests(unittest.TestCase):
    def scan(self, name, content):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            original = SCAN.ROOT
            output = io.StringIO()
            try:
                SCAN.ROOT = root
                with contextlib.redirect_stdout(output):
                    code = SCAN.main()
                return code, output.getvalue()
            finally:
                SCAN.ROOT = original

    def test_env_variants_and_keystores_rejected(self):
        for name in [".env.production", ".env.local", "secrets.yaml", "device.p12", "id_ed25519"]:
            with self.subTest(name=name):
                self.assertEqual(self.scan(name, "fixture")[0], 1)

    def test_source_and_extensionless_tokens_rejected_without_logging_value(self):
        dummy = "gh" + "p_" + "x" * 40
        for name in ["firmware.h", "ui.ts", "KEY"]:
            code, output = self.scan(name, dummy)
            self.assertEqual(code, 1)
            self.assertNotIn(dummy, output)

    def test_pem_private_keys_rejected(self):
        dummy = "-----BEGIN " + "PRIVATE KEY-----"
        self.assertEqual(self.scan("device.pem", dummy)[0], 1)

    def test_clean_example_and_secret_reference_allowed(self):
        self.assertEqual(self.scan(".env.example", "# Fill locally")[0], 0)
        self.assertEqual(self.scan("panel.yaml", "password: !secret wifi_password")[0], 0)

    def test_git_metadata_is_excluded(self):
        self.assertEqual(self.scan(".git/config", "gh" + "p_" + "x" * 40)[0], 0)
