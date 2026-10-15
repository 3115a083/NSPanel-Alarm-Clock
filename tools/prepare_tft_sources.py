"""Stage verified upstream HMI sources; never compile, execute or flash software."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "hmi/upstream.json"


def verify(data, item):
    if len(data) != item["size"]:
        raise ValueError("Unexpected source size: " + item["name"])
    git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if git_blob != item["git_blob"]:
        raise ValueError("Git blob mismatch: " + item["name"])
    if "sha256" in item and hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise ValueError("SHA-256 mismatch: " + item["name"])


def prepare(destination, cache=None):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    upstream = destination / "upstream"
    working = destination / "working"
    upstream.mkdir(parents=True, exist_ok=True)
    working.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        target = upstream / item["name"]
        if target.exists():
            verify(target.read_bytes(), item)  # Never erase modified reference files.
            continue
        if cache is not None:
            data = (cache / item["name"]).read_bytes()
        else:
            url = ("https://raw.githubusercontent.com/" + manifest["repository"]
                   + "/" + manifest["commit"] + "/" + item["path"])
            with urlopen(url, timeout=30) as response:
                data = response.read(item["size"] + 1)
        verify(data, item)
        target.write_bytes(data)  # Only verified bytes become a reference file.
    draft = working / "nspanel_alarm_eu.hmi"
    if not draft.exists():
        shutil.copyfile(upstream / "nspanel_landscape.hmi", draft)
    print("Verified source: " + str(upstream))
    print("Working HMI: " + str(draft))
    print("The initial working copy is unchanged Easy HMI, not a custom alarm TFT.")
    print("Open in Nextion Editor >=1.68.2; save/compile and use File > TFT file output.")
    return draft


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/tft")
    parser.add_argument("--cache", type=Path, help="Use predownloaded, verified source filenames")
    args = parser.parse_args()
    prepare(args.output, args.cache)


if __name__ == "__main__":
    main()
