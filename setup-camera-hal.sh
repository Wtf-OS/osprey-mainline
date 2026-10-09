#!/sbin/sh
set -eu
umask 022
export LD_LIBRARY_PATH=/data/camera-runtime/lib:/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
export PATH=/system/bin:/sbin
chmod -R a+rX /data/camera-runtime
chmod 755 /data/camera-runtime/bin/* /data/camera-runtime/libexec/libcamera/*
for name in camera.msm8916.so camera.vendor.msm8916.so camera.default.so; do
    [ ! -f /data/probe-hw/$name ] || [ -f /data/probe-hw/$name.before-libcamera ] || cp /data/probe-hw/$name /data/probe-hw/$name.before-libcamera
    cp /data/camera-runtime/lib/libcamera-hal.so /data/probe-hw/$name.new
    chmod 0644 /data/probe-hw/$name.new
    mv /data/probe-hw/$name.new /data/probe-hw/$name
done
cp /data/camera-runtime/lib/android.hardware.camera.provider@2.4-impl.so /data/probe-hw/android.hardware.camera.provider@2.4-impl.so.new
chmod 0644 /data/probe-hw/android.hardware.camera.provider@2.4-impl.so.new
mv /data/probe-hw/android.hardware.camera.provider@2.4-impl.so.new /data/probe-hw/android.hardware.camera.provider@2.4-impl.so
for node in /dev/media0 /dev/video* /dev/v4l-subdev* /dev/dma_heap/system; do
    [ -e "$node" ] || continue
    chown 1047:1006 "$node"
    chmod 0660 "$node"
done
for node in /sys/class/leds/osprey:flash/brightness /sys/class/leds/osprey:flash/flash_strobe; do
    [ -e "$node" ] || continue
    chown 1047:1006 "$node"
    chmod 0660 "$node"
done
# Refresh only Camera2's old capability cache after adding the lamp.
(
export LD_LIBRARY_PATH=/sbin
if [ -e /sys/class/leds/osprey:flash/brightness ]; then
for prefs in /data/data/com.android.camera2/shared_prefs/*.xml; do
    [ -f "$prefs" ] || continue
    /sbin/toybox grep -q 'name="pref_flash_supported_back_camera">0' "$prefs" || continue
    uid=$(/sbin/toybox stat -c %u "$prefs")
    [ -e "$prefs.before-flash" ] || /sbin/toybox cp -p "$prefs" "$prefs.before-flash"
    /sbin/toybox sed -i '/name="pref_flash_supported_back_camera"/d' "$prefs"
    /sbin/toybox chown "$uid:$uid" "$prefs"
    /sbin/toybox chmod 0600 "$prefs"
done
fi
)
setprop ctl.start mainline-camera-provider
setprop ctl.start mainline-cameraserver
