#!/sbin/sh
set -e
export PATH=/sbin
export LD_LIBRARY_PATH=/sbin
exec >/data/mainline-native-start.log 2>&1
# Bring up wlan0 before the framework requests the Wi-Fi HAL.
/sbin/sh /data/start-native-wifi.sh || echo 'Wi-Fi setup failed; see wifi-kernel.log'
/sbin/sh /data/start-native-graphics.sh
