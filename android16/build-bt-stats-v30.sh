#!/bin/bash
set -e
cd /home/debian/osprey-port/lineage
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache GOMEMLIMIT=18GiB
source build/envsetup.sh
lunch lineage_osprey-trunk_staging-userdebug
m -j4 services
