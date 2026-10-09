#!/sbin/sh
export LD_LIBRARY_PATH=/vendor/lib:/system/lib:/system/lib/bootstrap
exec /vendor/bin/vndservicemanager /dev/vndbinder
