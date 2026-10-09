#!/sbin/sh
set -eu
export LD_LIBRARY_PATH=/sbin
# WCNSS reports incompatible Google BLE filter capabilities.
setprop bluetooth.core.le.vendor_capabilities.enabled false
/sbin/toybox mkdir -p /data/misc/bluetooth/logs /data/misc/bluedroid
/sbin/toybox chown 1002:1002 /data/misc/bluetooth /data/misc/bluetooth/logs /data/misc/bluedroid
/sbin/toybox chmod 0770 /data/misc/bluetooth /data/misc/bluetooth/logs /data/misc/bluedroid
for name in btqca btqcomsmd; do
    [ -d /sys/module/$name ] || /sbin/toybox insmod /data/bluetooth-modules/$name.ko
done
if [ -e /dev/rfkill ]; then
    /sbin/toybox chown 1002:1002 /dev/rfkill
    /sbin/toybox chmod 0600 /dev/rfkill
fi
setprop ctl.start mainline-bluetooth
