#!/usr/bin/env python3
"""Shared crDroid manifest logic: include-graph resolution + project data.

Used by gha_sync.py (plain git-clone syncer for the GHA runner) and
gen_local_manifest.py (local-manifest XML output).  Both consumers rely on
ONE include-graph truth: only manifest files reached by <include> merges
(default.xml -> crdroid.xml + lineage.xml for crDroid 16.0) are live; the
kernel-*.xml snippets are never merged and are naturally invisible here.
"""
import fnmatch
import os
import urllib.parse
import xml.etree.ElementTree as ET

DEFAULT_FETCH = "https://android.googlesource.com"
GITHUB = "https://github.com"
# Host repo of the manifest XML; relative fetches (".", "..") are resolved
# against its directory, mirroring repo's own semantics.
MANIFEST_URL = "https://github.com/crdroidandroid/android.git"


def resolve_fetch(fetch):
    """Manifest <remote> fetch attribute -> absolute git host URL."""
    if not fetch:
        return None
    if fetch.startswith(("https://", "http://", "git://", "ssh://")):
        return fetch
    if fetch.startswith("."):
        return urllib.parse.urljoin(MANIFEST_URL, fetch)
    return None

# Path patterns not needed for the pipa build (disk-pressure trims)
EXCLUDE = [
    "device/google*",
    "device/generic/*",
    "device/lineage/*",
    "device/sample",
    "packages/apps/Car*",
    "packages/modules/desktop*",
    "prebuilts/go/darwin*",
    "prebuilts/go/linux-x86",           # no go-based host tooling needed
    "prebuilts/clang/host/darwin*",
    "prebuilts/devtools*",
    "prebuilts/ndk*",
    "prebuilts/gcc/*mingw*",
    "prebuilts/qemu-kernel*",           # emulator-only
    "prebuilts/android-emulator*",
    "prebuilts/jdk/jdk8",
    "prebuilts/jdk/jdk25",
    "cts",                              # platform CTS: multi-GB, unused by pipa
    "pdk/*",
    "developers/*",
    "hardware/qcom-caf/sm7*",           # other SoCs' HALs (big)
    "hardware/qcom-caf/sm83*",
    "hardware/qcom-caf/sm84*",
    "hardware/qcom-caf/sm85*",
    "hardware/qcom-caf/sm86*",
    "hardware/qcom-caf/sm87*",
    "hardware/qcom-caf/sm88*",
    "hardware/qcom-caf/qcm*",
    "hardware/qcom-caf/msm*",
    "external/chromium-webview/prebuilt/arm",
    "external/chromium-webview/prebuilt/x86",
    "external/chromium-webview/prebuilt/x86_64",
    "test/*",
]

# (path, name, revision) - GitHub-hosted pipa device set, overrides manifest
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


def resolve_includes(start, mdir):
    """Traverse <include name=...> from `start` (repo resolves includes
    relative to the manifests dir, wherever the root file lives)."""
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


def parse_merged(base):
    """Collect everything a plain clone needs from the merged manifest."""
    mdir = os.path.join(base, ".repo", "manifests")
    root = next((c for c in (os.path.join(base, ".repo", "manifest.xml"),
                             os.path.join(mdir, "manifest.xml"))
                 if os.path.exists(c)), None)
    if not root:
        raise SystemExit("no root manifest found under " + base)

    remotes = {}
    d_fetch, d_rev, d_remote = DEFAULT_FETCH, None, None
    projects, pos = [], {}          # pos: path -> index in projects
    for f in resolve_includes(root, mdir):
        try:
            r = ET.parse(f).getroot()
        except Exception:
            continue
        if r.tag != "manifest":
            continue
        for el in r:
            t = el.tag
            if t == "remote":
                remotes.setdefault(el.get("name"),
                                   (resolve_fetch(el.get("fetch", "")), el.get("revision")))
            elif t == "default":
                d_rev = el.get("revision") or d_rev
                d_remote = el.get("remote") or d_remote
            elif t == "project":
                name = el.get("name")
                path = el.get("path") or name
                remote = el.get("remote") or d_remote or ""
                _, rrev = remotes.get(remote, (None, None))
                rev = el.get("revision") or rrev or d_rev
                rec = {"name": name, "path": path, "remote": remote, "revision": rev}
                if path in pos:
                    projects[pos[path]] = rec       # later merge wins
                else:
                    pos[path] = len(projects)
                    projects.append(rec)
    return {"remotes": remotes, "default_fetch": d_fetch, "default_rev": d_rev,
            "default_remote": d_remote, "projects": projects}


def repo_url(remotes, default_fetch, name, remote_name):
    fetch = remotes.get(remote_name, (default_fetch, None))[0]
    if not fetch or not fetch.startswith(("https://", "http://", "git://", "ssh://")):
        fetch = default_fetch or DEFAULT_FETCH
    return fetch.rstrip("/") + "/" + name + ".git"


def normalize_rev(rev):
    """(clone ref, kind): kind 'sha' needs an extra fetch, 'ref' takes -b."""
    r = (rev or "").strip()
    if len(r) == 40 and all(c in "0123456789abcdef" for c in r.lower()):
        return r, "sha"
    for pfx in ("refs/heads/", "refs/tags/"):
        if r.startswith(pfx):
            r = r[len(pfx):]
    return r, "ref"


def collect(base):
    """[(path, name, url, rev_for_clone, kind)] for the pipa build.

    Live merged-manifest projects minus EXCLUDE paths, plus ADD overrides
    (GitHub-hosted pipa device set with per-repo branches).  Dedupe by
    path, so no ambiguous-name problem like repo's remove-project had.
    """
    data = parse_merged(base)
    add_by_path = {path: (name, rev) for path, name, rev in ADD}
    add_names = {name for _, name, _ in ADD}

    out = {}
    for p in data["projects"]:
        name, path = p["name"], p["path"]
        if not name or path in add_by_path or name in add_names:
            continue
        if any(fnmatch.fnmatch(path, pat) for pat in EXCLUDE):
            continue
        url = repo_url(data["remotes"], data["default_fetch"], name, p["remote"])
        rev, kind = normalize_rev(p["revision"])
        out[path] = (name, url, rev, kind)

    for path, (name, rev) in add_by_path.items():
        rev, kind = normalize_rev(rev)
        out[path] = (name, f"{GITHUB}/{name}.git", rev, kind)

    return [(path,) + out[path] for path in sorted(out)]
