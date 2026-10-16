"""Build a temporary example using generated, non-production test credentials."""
from pathlib import Path
import base64
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="alarm-firmware-") as temp:
    config = Path(temp)
    # Test the actual consumer path. Never copy an alarm YAML/header beside the
    # device config: ESPHome prefers a local header over the remote package's.
    # CI must fetch the tested commit, including PR code, rather than old main.
    package_ref = os.environ.get("GITHUB_SHA", "main")
    if package_ref != "main" and not re.fullmatch(r"[0-9a-f]{40}", package_ref):
        raise RuntimeError("Expected a full Git commit SHA for the remote build")
    # Preserve !secret tags in the written example rather than inline credentials.
    device_text = (ROOT / "esphome/nspanel-schlafzimmer.yaml").read_text(encoding="utf-8")
    device_text = device_text.replace("ref: main", "ref: " + package_ref)
    (config / "nspanel-schlafzimmer.yaml").write_text(device_text, encoding="utf-8")
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
                            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sys.stderr.write(result.stderr)
    if result.returncode:
        print(result.stdout)
    result.check_returncode()
    if 'update_interval of 0ms is not supported' in result.stderr:
        raise RuntimeError('Zero-period scheduler warning in merged firmware configuration')
    class ConfigLoader(yaml.SafeLoader):
        pass
    ConfigLoader.add_multi_constructor("!", lambda loader, tag, node:
        loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode)
        else loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode)
        else loader.construct_mapping(node))
    merged = yaml.load(result.stdout, Loader=ConfigLoader)
    includes = [Path(p) for p in merged["esphome"]["includes"]]
    header_name = "nspanel_alarm_schedule_v2.h"
    headers = [p for p in includes if p.name == header_name]
    if len(headers) != 1 or headers[0].parent == config:
        raise RuntimeError("Alarm header must resolve from the remote package checkout")
    if headers[0].read_bytes() != (ROOT / "esphome" / header_name).read_bytes():
        raise RuntimeError("Remote package header differs from the tested source")
    print("Remote YAML and matching C++ header resolved without local alarm files.")
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

    # Reproduce an existing installation, including both possible stale paths.
    # The old header is deliberately left untouched throughout the full build.
    legacy = (ROOT / "tests/fixtures/alarm_schedule_v1.h").read_bytes()
    (config / "alarm_schedule.h").write_bytes(legacy)
    source_dir = config / ".esphome/build/nspanel-schlafzimmer/src"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "alarm_schedule.h").write_bytes(legacy)

    # The previously published combined entry must keep the same behavior.
    prefix = device_text.split("packages:\n", 1)[0]
    suffix = device_text[device_text.index("# Long-lived"):]
    compatibility = prefix + (
        "packages:\n"
        "  alarm_clock:\n"
        "    url: https://github.com/3115a083/NSPanel-Alarm-Clock\n"
        f"    ref: {package_ref}\n"
        "    refresh: always\n"
        "    files: [nspanel_alarm.yaml]\n\n"
    ) + suffix
    compat_path = config / "combined-compatibility.yaml"
    compat_path.write_text(compatibility, encoding="utf-8")
    compat_result = subprocess.run(
        [sys.executable, "-m", "esphome", "config", str(compat_path)],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sys.stderr.write(compat_result.stderr)
    if compat_result.returncode:
        print(compat_result.stdout)
    compat_result.check_returncode()
    compat_merged = yaml.load(compat_result.stdout, Loader=ConfigLoader)
    for key in ("script", "globals", "api", "ota", "wifi", "time"):
        if compat_merged[key] != merged[key]:
            raise RuntimeError("Combined entry differs from split setup: " + key)
    print("Combined compatibility entry matches split alarm/base behavior.")

    # Compile the optional UI too, from the same remote commit and isolated
    # consumer directory. The default entry remains unchanged/opt-in.
    ui_text = device_text.replace("      - nspanel_alarm_addon.yaml",
                                  "      - nspanel_alarm_addon.yaml\n      - nspanel_alarm_ui.yaml")
    if ui_text == device_text:
        raise RuntimeError("Cannot inject optional UI package into consumer fixture")
    Path(path).write_text(ui_text, encoding="utf-8")
    ui_result = subprocess.run([sys.executable, "-m", "esphome", "config", path],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sys.stderr.write(ui_result.stderr)
    if ui_result.returncode:
        print(ui_result.stdout)
    ui_result.check_returncode()
    ui_merged = yaml.load(ui_result.stdout, Loader=ConfigLoader)
    schedule_headers = [Path(p) for p in ui_merged["esphome"]["includes"]
                        if Path(p).name == header_name]
    if (len(schedule_headers) != 1 or schedule_headers[0].parent == config
            or schedule_headers[0].read_bytes() != (ROOT / "esphome" / header_name).read_bytes()
            or any(Path(p).name == "alarm_schedule.h" for p in ui_merged["esphome"]["includes"])):
        raise RuntimeError("Legacy local header shadows the remote scheduler")
    ui_headers = [Path(p) for p in ui_merged["esphome"]["includes"] if Path(p).name == "alarm_ui.h"]
    if len(ui_headers) != 1 or ui_headers[0].parent == config or ui_headers[0].read_bytes() != (ROOT / "esphome/alarm_ui.h").read_bytes():
        raise RuntimeError("Optional UI header must resolve from the tested remote checkout")
    for key in ("api", "ota", "wifi", "time"):
        if ui_merged[key] != merged[key]:
            raise RuntimeError("Optional UI changes core safety configuration: " + key)
    print("Optional clock UI and matching header resolve remotely; core safety configuration unchanged.")
    build = subprocess.run([sys.executable, "-m", "esphome", "compile", path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    print(build.stdout)
    build.check_returncode()
    plain_log = re.sub(r"\x1b\[[0-9;]*m", "", build.stdout)
    if re.search(r"nspanel_alarm_local\.yaml:\d+(?::\d+)?: warning:.*format", plain_log):
        raise RuntimeError("Alarm logging has a target compiler format warning")
    if (source_dir / header_name).read_bytes() != (ROOT / "esphome" / header_name).read_bytes():
        raise RuntimeError("Generated scheduler header differs from the tested remote source")
    generated = (source_dir / "main.cpp").read_text(encoding="utf-8")
    if ('#include "' + header_name + '"' not in generated
            or '#include "alarm_schedule.h"' in generated):
        raise RuntimeError("Generated firmware includes the legacy scheduler")
    if (config / "alarm_schedule.h").read_bytes() != legacy:
        raise RuntimeError("Migration test unexpectedly changed the user's legacy file")
    print("Legacy local/build header migration compiled successfully without deleting the local file.")

    defines = config / ".esphome/build/nspanel-schlafzimmer/src/esphome/core/defines.h"
    flags = defines.read_text(encoding="utf-8")
    if "#define USE_OTA_ENCRYPTION_REQUIRED" not in flags or "#define USE_OTA_PASSWORD" in flags:
        raise RuntimeError("Generated firmware does not require password-free encrypted OTA")
    print("Generated firmware requires encrypted OTA and excludes OTA password authentication.")
