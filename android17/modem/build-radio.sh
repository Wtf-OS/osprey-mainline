#!/bin/bash
set -euo pipefail
cd /home/debian/osprey-port/lineage
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache
export GOMAXPROCS=8 GOMEMLIMIT=12GiB
export SOONG_BUILD_MEMORY_LIMIT_BYTES=12884901888
source build/envsetup.sh
lunch lineage_osprey cp2a userdebug
m -j8 android.hardware.radio-service.osprey > /home/debian/osprey-port/modem-tools/build-radio.log 2>&1
