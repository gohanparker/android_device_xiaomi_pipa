#!/usr/bin/env python3
"""Generate a local_manifest for building crDroid pipa on the GHA runner.

Reads the crDroid manifest initialized under <base>/.repo, excludes projects
not needed for a pipa system build, and adds the pipa device/kernel/vendor
repos (including substitutions for repos that died upstream).
"""
import fnmatch, glob, os, sys
import xml.etree.ElementTree as ET

base = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
mfiles = sorted(
    glob.glob(os.path.join(base, ".repo/manifests/*.xml"))
    + glob.glob(os.path.join(base, ".repo/manifests/snippets/*.xml"))
)

remotes = {}
default_remote = None
default_fetch = "https://android.googlesource.com"
default_rev = None
projects = []  # (name, path)

for f in mfiles:
    try:
        root = ET.parse(f).getroot()
    except Exception:
        continue
    if root.tag != "manifest":
        continue
    for el in root:
        t = el.tag
        if t == "remote":
            remotes.setdefault(el.get("name"), (el.get("fetch", ""), el.get("revision")))
        elif t == "default":
            default_fetch = el.get("fetch") or default_fetch
            default_rev = el.get("revision") or default_rev
            default_remote = el.get("remote") or default_remote
        elif t == "project":
            projects.append((el.get("name"), el.get("path") or el.get("name")))

# Path patterns not needed for the pipa build
EXCLUDE = [
    "kernel/platform/*",               # 156 GKI kernel-build trees (other devices)
    "device/google*",
    "device/generic/*",
    "device/lineage/*",
    "device/sample",
    "packages/apps/Car*",
    "packages/modules/desktop*",
    "prebuilts/go/darwin*",
    "prebuilts/clang/host/darwin*",
    "prebuilts/devtools*",
    "prebuilts/ndk*",
    "prebuilts/gcc/*mingw*",
    "external/chromium-webview/prebuilt/arm",
    "external/chromium-webview/prebuilt/x86",
    "external/chromium-webview/prebuilt/x86_64",
    "test/*",
]

paths_by_name = {}
for name, path in projects:
    if name:
        paths_by_name.setdefault(name, []).append(path)

excluded = set()
for name, path in projects:
    if not name:
        continue
    for pat in EXCLUDE:
        if fnmatch.fnmatch(path, pat):
            excluded.add(name)
            break

# (path, name, revision)  - github-hosted, cloned on top of removed bases
ADD = [
    ("device/xiaomi/pipa", "gohanparker/android_device_xiaomi_pipa", "16.0"),
    ("device/xiaomi/sm8250-common", "crdroidandroid/android_device_xiaomi_sm8250-common", "16.0-pipa"),
    ("vendor/xiaomi/pipa", "crdroidandroid/android_vendor_xiaomi_pipa", "16.0"),
    ("vendor/xiaomi/sm8250-common", "crdroidandroid/proprietary_vendor_xiaomi_sm8250-common", "16.0-pipa"),
    ("kernel/xiaomi/sm8250", "crdroidandroid/android_kernel_xiaomi_sm8250", "16.0-pipa"),
    ("hardware/xiaomi", "crdroidandroid/android_hardware_xiaomi", "16.0"),
    ("vendor/qcom/wfd", "Evolution-X-Devices/vendor_qcom_wfd", "bka"),
    ("device/qcom/wfd", "Evolution-X-Devices/device_qcom_wfd", "bka"),
]

lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<manifest>"]
lines.append('  <remote name="extra" fetch="https://github.com/" />')
removed = 0
for name in sorted(excluded):
    if name and len(paths_by_name.get(name, [])) == 1:
        lines.append(f'  <remove-project name="{name}" />')
        removed += 1
print(f"remove-projects emitted: {removed}/{len(excluded)}", file=sys.stderr)
for path, name, rev in ADD:
    lines.append(f'  <project path="{path}" name="{name}" remote="extra" revision="{rev}" />')
lines.append("</manifest>")
print("\n".join(lines))
