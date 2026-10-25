# Bluetooth LE feature declaration

The mainline product now installs the upstream
`android.hardware.bluetooth_le.xml` permission file alongside classic Bluetooth.
The controller reports LE support, but the missing PackageManager feature made
BLE APIs unavailable to applications even when Settings showed Bluetooth ON.
The packer requires the declaration in both the staged product and system image.

Qingping (`com.cleargrass.app.air`) also needs the user-granted Nearby devices
permissions (`BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT`). Those were granted on the
development phone; the ROM does not automatically grant them to third-party apps.

The declaration is installed and visible to PackageManager on the development
phone after reboot. The previous full ZIP still lacks this change. This fix does
not enable the separately missing A2DP audio profiles.

## Legacy scan updates

Android 17 waited for SCAN_RSP before forwarding scannable advertisements to
active clients. This older controller supplies scan responses infrequently,
so CGD1 service-data updates, including binding flags, were withheld from Qingping.
The Bluetooth patch queue allows legacy scan clients to receive advertisements
without waiting for a fresh scan response. Extended scans, passive scan response
filtering, location/permission checks and application filters remain unchanged.

The rebuilt, signed APEX was installed and loaded after an ordinary reboot.
Only Bluetooth.apk changed among its 27 payload files; the native libraries,
framework jars, module version and keys remain unchanged. SELinux is Enforcing.
The API diagnostic now receives FDCD service data without SCAN_RSP. Qingping's
log repeatedly identifies the alarm clocks, and the user confirmed CGD1 appeared/
connected. The temporary diagnostic APK was removed. No long-duration regression
or Bluetooth audio check was performed. The full ROM ZIP has not been repacked.
