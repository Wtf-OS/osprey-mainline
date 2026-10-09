#!/sbin/sh
export LD_LIBRARY_PATH=/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
export ANGLE_DEFAULT_PLATFORM=swiftshader
exec /data/graphics-bin/surfaceflinger
