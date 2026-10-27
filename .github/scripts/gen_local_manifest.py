#!/usr/bin/env python3
"""Generate a local_manifest for building crDroid pipa on the GHA runner.

Resolves the repo manifest include-graph from <base>/.repo/manifest.xml so
only LIVE projects (those actually merged) are considered; excludes the ones
a pipa system build never needs; and adds the pipa device/kernel/vendor repos.
"""
import fnmatch, os, sys
import xml.etree.ElementTree as ET

base = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
mdir = os.path.join(base, ".repo", "manifests")


def resolve_includes(start):
    """Traverse <include name=...> from `start` (repo resolves includes
    relative to the manifests directory, wherever the root file lives)."""
    seen, order, queue = set(), [], [start]
    while queue:
        f = queue.pop(0)
        rf = os.path.realpath(f)
        if rf in seen or not os.path.exists(rf):
            continue
        seen.add(rf)
        order.append(rf)
        try:
            root = ET.parse(rf).getroot()
        except Exception:
            continue
        for el in root:
            if el.tag == "include":
                nm = el.get("name")
                if nm:
                    tgt = os.path.join(mdir, nm)
                    if not os.path.exists(tgt):
                        tgt = os.path.join(os.path.dirname(rf), nm)
                    queue.append(tgt)
    return order


root_candidates = [
    os.path.join(base, ".repo", "manifest.xml"),
    os.path.join(mdir, "manifest.xml"),
]
root_file = next((c for c in root_candidates if os.path.exists(c)), None)
if not root_file:
    sys.exit("no root manifest found")
mfiles = resolve_includes(root_file)
print(f"merged-manifest files: {len(mfiles)}", file=sys.stderr)

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
removed, skipped = 0, 0
for name in sorted(excluded):
    if name and len(paths_by_name.get(name, [])) == 1:
        lines.append(f'  <remove-project name="{name}" />')
        removed += 1
    else:
        skipped += 1
for path, name, rev in ADD:
    lines.append(f'  <project path="{path}" name="{name}" remote="extra" revision="{rev}" />')
lines.append("</manifest>")
print(f"projects={len(projects)} excluded={len(excluded)} emitted={removed} skipped-ambiguous={skipped}", file=sys.stderr)
print("\n".join(lines))
