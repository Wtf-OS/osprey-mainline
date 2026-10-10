#!/bin/bash
set -e
cd /home/debian/osprey-port/lineage
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache GOMEMLIMIT=18GiB
source build/envsetup.sh
lunch lineage_osprey-trunk_staging-userdebug
m -j4 Camera2 android.hardware.camera.provider@2.4-service android.hardware.camera.provider@2.4-impl libcamera-hal ipa_softisp softisp_ipa_proxy osprey_camera_hal_alias
