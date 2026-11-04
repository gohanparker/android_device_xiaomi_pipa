#!/bin/bash
# Full crDroid 17.0 ROM build for Xiaomi Pad 6 (pipa).
#
# Run this on a big machine (>= 32 GB RAM, >= 300 GB free disk):
#   - a Crave devspace shell
#   - a cloud VM (e.g. Hetzner CCX33/CPX51) - just SSH in and run it
#   - a self-hosted GitHub Actions runner (the crdroid17-rom-build workflow does this for you)
#
# Usage:   bash build_rom17.sh [workdir]
set -euo pipefail

WORK="${1:-$HOME/rom17}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORK"
cd "$WORK"

echo "=== preflight ==="
echo "RAM:  $(free -g | awk 'NR==2{print $2" GB total, "$7" GB available"}')"
echo "disk: $(df -h "$WORK" | tail -1 | awk '{print $4" free on "$6}')"
echo "cpus: $(nproc)"
[ "$(nproc)" -lt 4 ] && echo "WARNING: fewer than 4 CPUs - the build will be slow"

echo "=== 1/4 manifests (crDroid 17.0) ==="
if [ ! -f .repo/manifest.xml ]; then
    command -v repo >/dev/null || {
        sudo curl -sL -o /usr/local/bin/repo https://storage.googleapis.com/git-repo-downloads/repo
        sudo chmod a+rx /usr/local/bin/repo
    }
    repo init -u https://github.com/crdroidandroid/android.git -b 17.0 --depth=1
fi

echo "=== 2/4 tree sync (full, plain clones, resumable) ==="
ROM_BUILD=1 CRDROID_BRANCH=17.0 python3 "$SCRIPTS/gha_sync.py" --root "$WORK" -j "$(nproc)"

echo "=== 3/4 build (bacon) ==="
export ALLOW_MISSING_DEPENDENCIES=true     # tolerate test-suite modules absent upstream
export SKIP_ABI_CHECKS=true
export CCACHE_DIR="$WORK/.ccache"; mkdir -p "$CCACHE_DIR"
source build/envsetup.sh
lunch lineage_pipa-cp2a-userdebug
m -j"$(nproc)" bacon 2>&1 | tee /tmp/rom_build.log | tail -n 30

echo "=== 4/4 result ==="
ZIP="$(ls -t out/target/product/pipa/*.zip 2>/dev/null | head -n 1 || true)"
if [ -n "$ZIP" ]; then
    echo "ROM package: $WORK/$ZIP"
    ls -la "$ZIP"
else
    echo "no ROM zip produced - see /tmp/rom_build.log"
    exit 1
fi
