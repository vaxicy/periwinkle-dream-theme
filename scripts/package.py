#!/usr/bin/env python3
"""Package Periwinkle Dream Theme for Chrome Web Store upload.

Chrome Web Store requirements this script respects:
  - manifest.json must sit at the ROOT of the zip (not nested in a folder)
  - every file referenced by the manifest must be present
  - no extra packaging metadata (no __MACOSX, no .DS_Store)

Excluded from the package (store-listing-only files, not the theme itself):
  .git/, .codebuddy/, .gitignore, scripts/, assets/,
  store-assets/screenshots/, store-assets/*promo.png,
  store-assets/store-listing.txt, Cached Theme.pak, *.zip

Screenshots and promo tiles are uploaded separately in the store listing
form, so they are intentionally NOT part of the extension package.

Run:  python scripts/package.py
"""
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Default drop folder for upload-ready archives, derived from the project
# location so the script stays portable and contains no hard-coded paths.
# <...>/Chrome-themes/periwinkle-dream-theme  ->  <...>/
DEFAULT_OUT = os.path.abspath(os.path.join(ROOT, os.pardir, os.pardir))

# Files included at the ROOT of the zip.
INCLUDE = [
    "manifest.json",
    "README.md",
    "LICENSE",
    "store-assets/icon.png",
]


def main():
    # 1. read + sanity-check the manifest
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        raw = f.read()
    m = json.loads(raw)
    if m.get("manifest_version") != 3:
        sys.exit("manifest_version must be 3")
    version = m.get("version")
    if not version:
        sys.exit("manifest has no version")

    # 2. verify every file the manifest references exists
    refs = list(m.get("icons", {}).values())
    refs += list(m.get("theme", {}).get("images", {}).values())
    missing = [r for r in refs if not os.path.exists(os.path.join(ROOT, r))]
    if missing:
        sys.exit("manifest references missing files: %s" % missing)

    # 3. build the zip with entries at the root level
    zip_name = "periwinkle-dream-theme-%s.zip" % version
    zip_path = os.path.join(ROOT, zip_name)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in INCLUDE:
            src = os.path.join(ROOT, rel)
            if not os.path.exists(src):
                sys.exit("INCLUDE entry missing: %s" % rel)
            z.write(src, rel)  # arcname = rel => root level, no parent folder

    # 4. read back and verify
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        bad = z.testzip()
    if bad is not None:
        sys.exit("corrupt entry: %s" % bad)
    if "manifest.json" not in names:
        sys.exit("manifest.json missing from zip")

    # re-parse the manifest straight out of the zip
    with zipfile.ZipFile(zip_path) as z:
        inside = json.loads(z.read("manifest.json").decode("utf-8"))
    if inside["name"] != m["name"]:
        sys.exit("name mismatch inside zip")
    for path in refs:
        if path not in names:
            sys.exit("referenced file not packaged: %s" % path)

    print("zip   :", zip_name)
    print("size  :", os.path.getsize(zip_path), "bytes")
    print("entries (%d):" % len(names))
    for n in sorted(names):
        print("   ", n)

    # 5. copy to the default projects folder
    dst = os.path.join(DEFAULT_OUT, zip_name)
    shutil.copy(zip_path, dst)
    print()
    print("copied to:", dst)
    print("exists   :", os.path.exists(dst), "size:", os.path.getsize(dst))

    # 6. verify byte-identical (guard against a stale/truncated copy)
    a = open(zip_path, "rb").read()
    b = open(dst, "rb").read()
    print("identical:", a == b)
    if a != b:
        sys.exit("copy mismatch")

    print()
    print("PACKAGING OK")


if __name__ == "__main__":
    main()
