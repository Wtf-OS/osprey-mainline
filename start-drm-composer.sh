#!/sbin/sh
set -e
# init uses umask 077; these overlays must be readable by apps/system_server.
umask 022
export LD_LIBRARY_PATH=/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
export PATH=/system/bin:/sbin
mkdir -p /data/probe-hw
chmod 0755 /data/probe-hw
cp -a /vendor/lib/hw/. /data/probe-hw/
gralloc=/data/graphics-libs/gralloc.minigbm.so
if [ "$(getprop debug.mainline.gralloc)" = msm ]; then
    setprop vendor.minigbm.debug nocompression
    gralloc=/data/graphics-libs/gralloc.minigbm_msm.so
fi
cp "$gralloc" /data/probe-hw/gralloc.msm8916.so
cp "$gralloc" /data/probe-hw/gralloc.default.so
cp /data/graphics-libs/hwcomposer.drm_minigbm.so /data/probe-hw/hwcomposer.msm8916.so
mount --bind /data/probe-hw /vendor/lib/hw
export LD_LIBRARY_PATH=/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
exec /vendor/bin/hw/android.hardware.graphics.composer@2.1-service
