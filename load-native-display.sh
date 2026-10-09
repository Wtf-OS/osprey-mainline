#!/sbin/sh
set -e
[ ! -d /sys/module/msm ]
/sbin/toybox dmesg >/data/native-display-before.log
/sbin/toybox insmod /probe-modules/native/drm_exec.ko
/sbin/toybox insmod /probe-modules/native/drm_gpuvm.ko
/sbin/toybox insmod /probe-modules/native/gpu-sched.ko
# Shared with WCNSS; Wi-Fi may already have loaded this module.
if [ ! -d /sys/module/mdt_loader ]; then
    /sbin/toybox insmod /probe-modules/native/mdt_loader.ko
fi
/sbin/toybox insmod /probe-modules/native/ubwc_config.ko
/sbin/toybox insmod /probe-modules/native/cec.ko
/sbin/toybox insmod /probe-modules/native/drm_display_helper.ko
/sbin/toybox insmod /probe-modules/native/panel-motorola-osprey-inx.ko
echo 83200000.framebuffer >/sys/bus/platform/drivers/simple-framebuffer/unbind
/sbin/toybox insmod /probe-modules/native/msm.ko separate_gpu_kms=1
/sbin/toybox sleep 3
/sbin/toybox chmod 0666 /dev/dri/*
if [ -e /sys/class/backlight/osprey-backlight/brightness ]; then
    /sbin/toybox chown 1000:1000 /sys/class/backlight/osprey-backlight/brightness
    /sbin/toybox chmod 0660 /sys/class/backlight/osprey-backlight/brightness
fi
/sbin/toybox dmesg >/data/native-display-after.log
/sbin/toybox ls /dev/dri
