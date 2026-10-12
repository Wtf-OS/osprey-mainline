#!/system/bin/sh
set -eu
base=/sys/kernel/tracing/instances/osprey-display-clock
[ ! -e "$base" ] || exit 1
old=$(cat /sys/class/backlight/osprey-backlight/brightness)
mkdir "$base"
cleanup() {
 echo 0 > "$base/tracing_on"
 echo 0 > "$base/events/clk/enable"
 echo "$old" > /sys/class/backlight/osprey-backlight/brightness
}
trap cleanup EXIT
 echo 0 > "$base/tracing_on"
 echo > "$base/trace"
 echo 1 > "$base/events/clk/clk_set_rate/enable"
 echo 1 > "$base/events/clk/clk_set_parent/enable"
 echo 1 > "$base/tracing_on"
 for n in 32 128 224 128 32; do
 echo "brightness-$n" > "$base/trace_marker"
 echo "$n" > /sys/class/backlight/osprey-backlight/brightness
 sleep 1
 done
 cleanup
 trap - EXIT
 cat "$base/trace"
 rmdir "$base"