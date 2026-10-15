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
        "nspanel_api_encryption_key": base64.b64encode(
            hashlib.sha256(b"public compile-only fixture").digest()).decode(),
        "local_ntp_server": "0.pool.ntp.org",
    }
    (config / "secrets.yaml").write_text(yaml.safe_dump(dummy), encoding="utf-8")
    path = str(config / "nspanel-schlafzimmer.yaml")
    result = subprocess.run([sys.executable, "-m", "esphome", "config", path],
                            check=False, stdout=subprocess.PIPE, text=True)
    if result.returncode:
        print(result.stdout)
    result.check_returncode()
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
    ota = [item for item in merged["ota"] if item["platform"] == "esphome"]
    if len(ota) != 1 or "password" in ota[0] or "encryption" not in ota[0]:
        raise RuntimeError("Expected one encrypted, password-free OTA listener")
    if "system_flags.ota_in_progress" not in str(ota[0].get("on_begin", [])):
        raise RuntimeError("NSPanel Easy OTA lifecycle hook was lost")
    if merged["api"]["reboot_timeout"] != "0s" or merged["wifi"]["reboot_timeout"] != "0s":
        raise RuntimeError("Offline alarm must not reboot for loss of API/Wi-Fi")
    print("Merged alarm hooks, encrypted OTA and offline reboot policy verified.")

    subprocess.run([sys.executable, "-m", "esphome", "compile", path], check=True)

    defines = config / ".esphome/build/nspanel-schlafzimmer/src/esphome/core/defines.h"
    flags = defines.read_text(encoding="utf-8")
    if "#define USE_OTA_ENCRYPTION_REQUIRED" not in flags or "#define USE_OTA_PASSWORD" in flags:
        raise RuntimeError("Generated firmware does not require password-free encrypted OTA")
    print("Generated firmware requires encrypted OTA and excludes OTA password authentication.")
