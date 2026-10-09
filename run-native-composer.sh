#!/sbin/sh
export LD_LIBRARY_PATH=/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
exec /vendor/bin/hw/android.hardware.graphics.composer@2.1-service
