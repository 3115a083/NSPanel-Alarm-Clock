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
    result = subprocess.run([sys.executable, "-m", "esphome", "config", path],
                            check=True, stdout=subprocess.PIPE, text=True)
    print(result.stdout)
    class ConfigLoader(yaml.SafeLoader):
        pass
    ConfigLoader.add_multi_constructor("!", lambda loader, tag, node:
        loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode)
        else loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode)
        else loader.construct_mapping(node))
    merged = yaml.load(result.stdout, Loader=ConfigLoader)
    for hook in ["button_left_press_short", "button_right_press_short", "button_right_press_long"]:
        handlers = [item for item in merged["script"] if str(item["id"]) == hook]
        if len(handlers) != 1:
            raise RuntimeError("Missing or duplicate alarm hook: " + hook)
        actions = handlers[0]["then"]
        if len(actions) != 1 or "if" not in actions[0] or "relay_" in str(actions):
            raise RuntimeError("Upstream actions remain on alarm hook: " + hook)
    print("Merged alarm button hooks verified: no upstream local relay actions.")

    subprocess.run([sys.executable, "-m", "esphome", "compile", path], check=True)
