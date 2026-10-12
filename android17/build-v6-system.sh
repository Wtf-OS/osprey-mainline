#!/bin/bash
set -eo pipefail
cd /home/debian/osprey-port/lineage
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/debian/.cache/ccache
export SOONG_NINJA=ninja SOONG_BUILD_MEMORY_LIMIT_BYTES=17179869184
source build/envsetup.sh
lunch lineage_osprey cp2a userdebug
m -j8 systemimage init_first_stage 2>&1 | tee /home/debian/osprey-port/android17-v6-build.log
