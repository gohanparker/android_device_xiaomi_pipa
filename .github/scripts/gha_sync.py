#!/usr/bin/env python3
"""Plain-clone syncer for the GHA runner (crDroid pipa).

Enumerates the merged manifest via manifest_data.collect() and clones every
project as a plain working tree (depth=1, single-branch), deleting .git after
each clone so the runner's 106 GB disk never has to hold objects AND trees.
"""
import argparse
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifest_data as MD  # noqa: E402


def run(cmd, cwd=None, env=None, timeout=1800):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(cmd, 124, e.stdout or "", e.stderr or "")


def clone_one(entry, root, attempts=2):
    path, _name, url, rev_b, kind = entry
    dst = os.path.join(root, path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out = []
    for attempt in range(1, attempts + 1):
        if os.path.exists(os.path.join(dst, ".git")) or os.path.exists(os.path.join(dst, "Android.bp")):
            return (path, "cached-ok", out)
        cmd = ["git", "clone", "--depth=1", "--single-branch", "--no-checkout"]
        if rev_b and kind == "ref":
            cmd += ["-b", rev_b]
        cmd += [url, dst]
        r = run(cmd)
        if r.returncode != 0:
            out.append(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "clone rc!=0")
            run(["rm", "-rf", dst])
            continue
        if kind == "sha":
            # fetch the exact commit needed; blobless depth fetch won't do
            r2 = run(["git", "-C", dst, "fetch", "--depth=1", url, rev_b])
            if r2.returncode != 0:
                out.append("sha-fetch: " + (r2.stderr.strip().splitlines()[-1] if r2.stderr.strip() else "?"))
                run(["rm", "-rf", dst])
                continue
            r2b = run(["git", "-C", dst, "checkout", "-f", "--detach", rev_b],
                      env={**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"})
            if r2b.returncode != 0:
                out.append("sha-checkout: " + r2b.stderr.strip().splitlines()[-1])
                run(["rm", "-rf", dst])
                continue
        r3 = run(["git", "-C", dst, "checkout", "-f", "--force"],
                 env={**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"})
        if r3.returncode != 0 and kind == "ref":
            out.append("checkout: " + r3.stderr.strip().splitlines()[-1])
            run(["rm", "-rf", dst])
            continue
        if shutil.which("git-lfs"):
            # LFS-tracked files (e.g. chromium webview apk): skip-smudge above
            # left pointer files; pull real objects now, before .git is gone
            r4 = run(["git", "-C", dst, "lfs", "pull"])
            if r4.returncode != 0:
                out.append("lfs-pull: " + (r4.stderr.strip().splitlines()[-1] if r4.stderr.strip() else "rc!=0"))
                run(["rm", "-rf", dst])
                continue
        run(["rm", "-rf", os.path.join(dst, ".git")])   # drop pack: tree-only
        return (path, "ok", out)
    return (path, "FAIL", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("-j", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entries = MD.collect(args.root)
    print(f"projects to clone: {len(entries)}", file=sys.stderr)
    if args.dry_run:
        for e in entries[:12]:
            print(" ", e, file=sys.stderr)
        return 0

    ok, failed = 0, []
    with cf.ThreadPoolExecutor(max_workers=args.j) as ex:
        futs = {ex.submit(clone_one, e, args.root): e for e in entries}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            path, status, out = fut.result()
            if status in ("ok", "cached-ok"):
                ok += 1
            else:
                failed.append((path, out))
            if i % 50 == 0 or status == "FAIL":
                print(f"{i}/{len(entries)} synced ({ok} ok, {len(failed)} failed)"
                      + (f" -- {path}: {out}" if failed else ""), flush=True)

    if failed:
        print(f"FAILED ({len(failed)}):", file=sys.stderr)
        for path, out in failed[:40]:
            print(f"  {path}: {out}", file=sys.stderr)
        return 1
    print(f"ALL-OK {ok} projects", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
