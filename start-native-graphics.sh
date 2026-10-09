#!/sbin/sh
set -e
# Run once after boot-mainline-android-v28-native-display.img, before graphics.
# ADB inherits the ramdisk library path; cmd must use Android's libraries.
if [ -f /data/adb-cmd.sh ]; then
    /sbin/toybox cp /data/adb-cmd.sh /sbin/cmd
    /sbin/toybox chmod 0755 /sbin/cmd
fi
# Preserve existing overlays while adding mainline Wi-Fi compatibility.
if [ -f /data/wifi-runtime/OspreyMainlineWifiOverlay.apk ]; then
    /sbin/toybox mkdir -p /data/wifi-runtime/product-overlay
    /sbin/toybox cp -a /product/overlay/. /data/wifi-runtime/product-overlay/
    /sbin/toybox cp /data/wifi-runtime/OspreyMainlineWifiOverlay.apk /data/wifi-runtime/product-overlay/
    /sbin/toybox chmod 0755 /data/wifi-runtime /data/wifi-runtime/product-overlay
    /sbin/toybox chmod 0644 /data/wifi-runtime/product-overlay/OspreyMainlineWifiOverlay.apk
    /sbin/toybox mount --bind /data/wifi-runtime/product-overlay /product/overlay
fi
# Existing probe systems contain the incompatible in-process NetworkStack APK.
if [ -f /data/networkstack-runtime/NetworkStack.apk ] && [ -f /system/priv-app/InProcessNetworkStack/InProcessNetworkStack.apk ]; then
    /sbin/toybox mkdir -p /data/networkstack-runtime/permissions
    /sbin/toybox cp -a /system/etc/permissions/. /data/networkstack-runtime/permissions/
    /sbin/toybox cp /data/networkstack-runtime/com.android.networkstack.xml /data/networkstack-runtime/permissions/
    /sbin/toybox chmod 0755 /data/networkstack-runtime/permissions
    /sbin/toybox chmod 0644 /data/networkstack-runtime/permissions/com.android.networkstack.xml
    /sbin/toybox mount --bind /data/networkstack-runtime/permissions /system/etc/permissions
    /sbin/toybox mkdir -p /data/networkstack-runtime/system-app
    /sbin/toybox cp /data/networkstack-runtime/NetworkStack.apk /data/networkstack-runtime/system-app/NetworkStack.apk
    /sbin/toybox chmod 0755 /data/networkstack-runtime/system-app
    /sbin/toybox chmod 0644 /data/networkstack-runtime/system-app/NetworkStack.apk
    /sbin/toybox mount --bind /data/networkstack-runtime/system-app /system/priv-app/InProcessNetworkStack
    # Boot-time clocks can run backwards, leaving the old APK path in parser cache.
    if [ -d /data/system/package_cache ]; then
        /sbin/toybox find /data/system/package_cache -maxdepth 2 -type f -name 'InProcessNetworkStack-*' -delete
    fi
fi
[ -x /probe-bin/lmkd ]
[ ! -d /sys/module/msm ]
/sbin/sh /data/load-native-display.sh
# Register the real backlight before SystemServer enumerates lights.
setprop ctl.restart probe-light
setprop vendor.hwc.drm.device /dev/dri/card1
setprop debug.mainline.gralloc msm
setprop vendor.minigbm.debug nocompression
/sbin/sh /data/start-graphics-v24.sh
if [ -f /probe-bin/camera-init-native ]; then
    /sbin/toybox mkdir -p /mnt/runtime/default /mnt/runtime/read /mnt/runtime/write /mnt/runtime/full /mnt/user/0 /mnt/pass_through/0
    setprop ctl.start mainline-swcodec
    /sbin/sh /data/setup-camera-hal.sh
fi
setprop ctl.start zygote-systemserver
