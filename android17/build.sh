#!/bin/bash
set -eo pipefail
scripts=$(cd "$(dirname "$0")" && pwd)
port=${HOME}/osprey-port
cd "$port/lineage"
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR="$HOME/.cache/ccache"
export SOONG_NINJA=ninja
export GOMAXPROCS=8 GOMEMLIMIT=12GiB SOONG_BUILD_MEMORY_LIMIT_BYTES=12884901888
export NINJA_STATUS='[%f/%t %p] '
/usr/bin/ccache -M 40G
bash "$scripts/build-kernel.sh" 2>&1 | tee "$port/android17-kernel.log"
source build/envsetup.sh
lunch lineage_osprey cp2a userdebug
m -j8 systemimage init_first_stage 2>&1 | tee "$port/android17-build.log"
python3 "$scripts/package.py"
