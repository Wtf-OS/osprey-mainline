#!/sbin/sh
set -e
/sbin/toybox grep -qx PARTNAME=modem /sys/class/block/mmcblk0p1/uevent
/sbin/toybox mkdir -p /firmware
if ! /sbin/toybox grep -q ' /firmware ' /proc/mounts; then
    /sbin/toybox mount -t ext4 -o ro,noload /dev/mmcblk0p1 /firmware
fi
[ -r /firmware/image/wcnss.mdt ]
[ -r /vendor/firmware/wlan/prima/WCNSS_qcom_wlan_nv.bin ]
echo /vendor/firmware >/sys/module/firmware_class/parameters/path
for name in qcom_common mdt_loader qcom_pil_info wcnss_ctrl wcn36xx qcom_wcnss_pil; do
    if [ ! -d /sys/module/$name ]; then
        /sbin/toybox insmod /probe-modules/wifi/$name.ko
    fi
done
attempt=0
while [ ! -d /sys/class/net/wlan0 ] && [ "$attempt" -lt 30 ]; do
    /sbin/toybox sleep 1
    attempt=$((attempt + 1))
done
/sbin/toybox ls /sys/class/net
/sbin/toybox dmesg >/data/wifi-kernel.log
[ -d /sys/class/net/wlan0 ]
/sbin/toybox setprop debug.mainline.wifi_ready 1
