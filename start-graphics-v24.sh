#!/sbin/sh
set -e
if [ -f /data/setup-mainline-scheduling.sh ]; then
    /sbin/sh /data/setup-mainline-scheduling.sh
fi
if [ -f /data/setup-bluetooth-mainline.sh ] && /sbin/toybox grep -q '^service mainline-bluetooth ' /systemserver-probe.rc; then
    /sbin/sh /data/setup-bluetooth-mainline.sh || echo 'Bluetooth setup failed; continuing graphics startup'
fi
# Do not boot the framework with an unresponsive LMKD: inherited -1000
# priorities otherwise protect cached apps while the kernel kills graphics.
if ! /data/lmkd-registration-probe; then
    setprop ctl.restart lmkd
    ready=0
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        /sbin/toybox sleep 1
        if /data/lmkd-registration-probe; then ready=1; break; fi
    done
    [ "$ready" = 1 ]
fi
/sbin/toybox mount --bind /data/graphics-libs/libcutils.so /system/lib/libcutils.so
setprop sys.use_memfd true
setprop debug.mainline.allow_memfd true
if [ -f /data/graphics-libs/libcutils-media-memfd.so ]; then
    /sbin/toybox mount --bind /data/mediaextractor-mainline.policy /apex/com.android.media/etc/seccomp_policy/mediaextractor.policy
    /sbin/toybox mount --bind /data/graphics-libs/libcutils-media-memfd.so /apex/com.android.media/lib/libcutils.so
    /sbin/toybox mount --bind /data/graphics-libs/libcutils-vendor-memfd.so /vendor/lib/libcutils.so
    /sbin/toybox mount --bind /data/graphics-libs/libcutils-swcodec-memfd.so /apex/com.android.media.swcodec/lib/libcutils.so
    setprop ctl.restart probe-media
    setprop ctl.restart probe-mediaextractor
    setprop ctl.restart mainline-swcodec
fi
setprop ro.surface_flinger.default_composition_pixel_format 5
/sbin/sh /data/setup-freedreno-egl.sh
if [ -f /probe-bin/graphics-init-managed ]; then
    /sbin/sh /data/setup-native-hw.sh
    setprop ctl.start mainline-vndservicemanager
    setprop ctl.start mainline-configstore
    /sbin/toybox sleep 1
    setprop ctl.start mainline-composer
    setprop ctl.start mainline-allocator
    if [ -f /probe-bin/audio-init-native ]; then
    /sbin/toybox cp /data/graphics-libs/audio.primary.mainline.so /data/probe-hw/audio.primary.msm8916.so
    /sbin/toybox chmod 0644 /data/probe-hw/audio.primary.msm8916.so
else
    /sbin/toybox cp /vendor/lib/hw/audio.primary.default.so /data/probe-hw/audio.primary.msm8916.so
fi
    setprop debug.mainline.audio_ready 1
    /sbin/toybox sleep 1
    setprop ctl.start mainline-surfaceflinger
    /sbin/toybox sleep 2
    setprop service.bootanim.exit 0
    setprop ctl.start mainline-bootanimation
    exit 0
fi
# Run once after a fresh RAM boot: start-drm-composer binds vendor/lib/hw.
/sbin/toybox runcon u:r:vndservicemanager:s0 /sbin/sh /data/run-vndservicemanager.sh >/data/vndservicemanager.log 2>&1 &
/sbin/toybox runcon u:r:hal_configstore_default:s0 /sbin/sh /data/run-configstore.sh >/data/configstore.log 2>&1 &
/sbin/toybox sleep 1
/sbin/toybox runcon u:r:hal_graphics_composer_default:s0 /sbin/sh /data/start-drm-composer.sh >/data/composer.log 2>&1 &
/sbin/toybox sleep 1
if [ -f /probe-bin/audio-init-native ]; then
    /sbin/toybox cp /data/graphics-libs/audio.primary.mainline.so /data/probe-hw/audio.primary.msm8916.so
    /sbin/toybox chmod 0644 /data/probe-hw/audio.primary.msm8916.so
else
    /sbin/toybox cp /vendor/lib/hw/audio.primary.default.so /data/probe-hw/audio.primary.msm8916.so
fi
setprop debug.mainline.audio_ready 1
/sbin/toybox runcon u:r:hal_graphics_allocator_default:s0 /sbin/sh /data/run-allocator.sh >/data/allocator.log 2>&1 &
/sbin/toybox sleep 1
/sbin/toybox runcon u:r:surfaceflinger:s0 /sbin/sh /data/run-surfaceflinger.sh >/data/surfaceflinger.log 2>&1 &
/sbin/toybox sleep 2
setprop service.bootanim.exit 0
/sbin/toybox runcon u:r:bootanim:s0 /sbin/sh /data/run-bootanimation.sh >/data/bootanimation.log 2>&1 &
