"""Integrity and preservation checks for external HMI source staging."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_tft", ROOT / "tools/prepare_tft_sources.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TftSourceTests(unittest.TestCase):
    def test_integrity_rejects_changed_content_of_same_size(self):
        data = b"source"
        item = {"name": "test", "size": len(data), "git_blob": hashlib.sha1(
            b"blob 6\0" + data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest()}
        MODULE.verify(data, item)
        with self.assertRaises(ValueError):
            MODULE.verify(b"Source", item)
        with self.assertRaises(ValueError):
            MODULE.verify(b"short", item)

    def test_repeated_staging_preserves_working_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            cache = base / "cache"
            cache.mkdir()
            files = []
            for name in ("nspanel_landscape.hmi", "LICENSE.NSPanel-Easy"):
                data = name.encode()
                (cache / name).write_bytes(data)
                files.append({"name": name, "path": name, "size": len(data),
                    "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()})
            manifest = base / "manifest.json"
            manifest.write_text(json.dumps({"files": files}), encoding="utf-8")
            with patch.object(MODULE, "MANIFEST", manifest):
                draft = MODULE.prepare(base / "build", cache)
                draft.write_bytes(b"user edits")
                MODULE.prepare(base / "build", cache)
                self.assertEqual(draft.read_bytes(), b"user edits")
                reference = base / "build/upstream/nspanel_landscape.hmi"
                reference.write_bytes(b"corrupt")
                with self.assertRaises(ValueError):
                    MODULE.prepare(base / "build", cache)


if __name__ == "__main__":
    unittest.main()
