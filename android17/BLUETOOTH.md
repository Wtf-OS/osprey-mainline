# Bluetooth LE feature declaration

The mainline product now installs the upstream
`android.hardware.bluetooth_le.xml` permission file alongside classic Bluetooth.
The controller reports LE support, but the missing PackageManager feature made
BLE APIs unavailable to applications even when Settings showed Bluetooth ON.
The packer requires the declaration in both the staged product and system image.

Qingping (`com.cleargrass.app.air`) also needs the user-granted Nearby devices
permissions (`BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT`). Those were granted on the
development phone; the ROM does not automatically grant them to third-party apps.

This change requires an updated system image and reboot. The previous full ZIP
and currently booted system still lack the feature declaration. The source fix
does not enable the separately missing A2DP audio profiles. BLE connection to a
Qingping sensor has not yet been verified with the corrected system image.
