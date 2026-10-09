#!/sbin/sh
set -eu
export LD_LIBRARY_PATH=/sbin
if [ -f /data/scheduling-modules/af_key.ko ] && [ ! -d /sys/module/af_key ]; then
    /sbin/toybox insmod /data/scheduling-modules/af_key.ko
fi
# The probe does not run the standard init.rc hierarchy setup.
for group in foreground foreground_window background top-app rt system system-background dex2oat nnapi-hal camera-daemon; do
    path=/dev/cpuctl/$group
    /sbin/toybox mkdir -p "$path"
    /sbin/toybox chown 1000:1000 "$path" "$path/tasks" "$path/cgroup.procs"
    /sbin/toybox chmod 0664 "$path/tasks" "$path/cgroup.procs"
    case "$group" in
        background|system-background|dex2oat) shares=128 ;;
        top-app) shares=2048 ;;
        *) shares=1024 ;;
    esac
    echo "$shares" >"$path/cpu.shares"
done
for path in /dev/cpuctl /dev/blkio; do
    /sbin/toybox chown 1000:1000 "$path/tasks" "$path/cgroup.procs"
    /sbin/toybox chmod 0664 "$path/tasks" "$path/cgroup.procs"
done
/sbin/toybox mkdir -p /dev/blkio/background
/sbin/toybox chown 1000:1000 /dev/blkio/background /dev/blkio/background/tasks /dev/blkio/background/cgroup.procs
/sbin/toybox chmod 0664 /dev/blkio/background/tasks /dev/blkio/background/cgroup.procs
# Keep fast app launch without reserving five processes on a 1 GiB device.
setprop persist.device_config.runtime_native.usap_pool_size_max 2
setprop persist.device_config.runtime_native.usap_pool_size_min 1
# zRAM has no seek cost; adjacent swap-page reads only add decompression work.
echo 0 >/proc/sys/vm/page-cluster
