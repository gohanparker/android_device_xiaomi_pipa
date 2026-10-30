#!/usr/bin/env python3
"""Generate a local_manifest for building crDroid pipa with `repo sync`.

Uses the shared manifest logic in manifest_data.py (single source of truth
for the include-graph, EXCLUDE patterns, and the pipa ADD set).  No longer
used by the GHA workflow (gha_sync.py replaced repo sync there); kept for
manual repo-based syncs.
"""
import fnmatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifest_data as MD

base = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

data = MD.parse_merged(base)

paths_by_name = {}
excluded = set()
for p in data["projects"]:
    name, path = p["name"], p["path"]
    if not name:
        continue
    paths_by_name.setdefault(name, []).append(path)
    if any(fnmatch.fnmatch(path, pat) for pat in MD.EXCLUDE):
        excluded.add(name)

lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<manifest>"]
lines.append('  <remote name="extra" fetch="https://github.com/" />')
removed, skipped = 0, 0
for name in sorted(excluded):
    if len(paths_by_name.get(name, [])) == 1:
        lines.append(f'  <remove-project name="{name}" />')
        removed += 1
    else:
        skipped += 1
for path, name, rev in MD.ADD:
    lines.append(f'  <project path="{path}" name="{name}" remote="extra" revision="{rev}" />')
lines.append("</manifest>")
print(f"projects={len(data['projects'])} excluded={len(excluded)} emitted={removed} skipped-ambiguous={skipped}", file=sys.stderr)
print("\n".join(lines))
