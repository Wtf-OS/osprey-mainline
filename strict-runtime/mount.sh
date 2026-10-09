#!/sbin/sh
set -e
export LD_LIBRARY_PATH=/sbin
[ -f /data/strict-runtime/enabled ] || exit 0
for name in xt_policy xt_u32 xt_quota2; do
    if ! /sbin/toybox grep -q "^$name " /proc/modules; then
        /sbin/toybox insmod /data/strict-runtime/$name.ko
    fi
done
for name in libprocessgroup.so libutils.so; do
    [ -s /data/strict-runtime/$name ]
    /sbin/toybox mount --bind /data/strict-runtime/$name /system/lib/$name
done
/sbin/toybox mount --bind /data/strict-runtime/netd /system/bin/netd
/sbin/toybox mount --bind /data/strict-runtime/netd.rc /system/etc/init/netd.rc
