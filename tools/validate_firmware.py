"""Build a temporary example using generated, non-production test credentials."""
from pathlib import Path
import base64
import hashlib
import shutil
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="alarm-firmware-") as temp:
    config = Path(temp)
    shutil.copytree(ROOT / "esphome", config, dirs_exist_ok=True)
    dummy = {
        "wifi_ssid": "CI_ONLY_NOT_A_REAL_NETWORK",
        "wifi_password": "CI_ONLY_NOT_A_REAL_PASSWORD",
        "nspanel_ota_password": "CI_ONLY_NOT_A_REAL_OTA_PASSWORD",
        "nspanel_api_encryption_key": base64.b64encode(
            hashlib.sha256(b"public compile-only fixture").digest()).decode(),
        "local_ntp_server": "0.pool.ntp.org",
    }
    (config / "secrets.yaml").write_text(yaml.safe_dump(dummy), encoding="utf-8")
    path = str(config / "nspanel-schlafzimmer.yaml")
    subprocess.run([sys.executable, "-m", "esphome", "config", path], check=True)
    subprocess.run([sys.executable, "-m", "esphome", "compile", path], check=True)
