#!/sbin/sh
set -eu
[ -e /sys/block/zram0/disksize ]
if /sbin/toybox grep -q '^/dev/zram0 ' /proc/swaps; then exit 0; fi
echo 536870912 >/sys/block/zram0/disksize
# ueventd may not have created the block node yet.
if [ ! -b /dev/zram0 ]; then
    IFS=: read major minor </sys/block/zram0/dev
    /sbin/toybox mknod /dev/zram0 b "$major" "$minor"
fi
/sbin/toybox mkswap /dev/zram0
/sbin/toybox swapon /dev/zram0
