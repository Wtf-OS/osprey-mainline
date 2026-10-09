#!/sbin/sh
export LD_LIBRARY_PATH=/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
exec /system/bin/cmd "$@"
