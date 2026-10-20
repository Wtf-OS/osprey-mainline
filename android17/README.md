# Osprey Android 17 mainline checkpoint

LineageOS 24.0 / Android 17 / SDK 37, `cp2a`, ARM32 userspace and Linux 7
ARM64. Sources use `lineage-24.0-mainline`; A15 legacy and A16 mainline remain
on their existing branches.

## Published inputs

- `component-revisions.json`: verified Wtf-OS repository commits, including
  the device trees, graphics, Wi-Fi, BPF integration, kernel and libcamera.
- `patch-components.json` and `patches/`: Soong, XMP Toolkit, Highway, Skia and
  SwiftShader, Camera2 and TimeKeep changes. No repositories were created for
  these dependencies.
- `pinned-manifest.xml`: exact Android source revisions. The seven patch-only
  projects are pinned to their upstream base, not to unpublished commits.
- `kernel.config` and `kernel-modules.json`: kernel configuration and the exact
  module selection, including the external backlight driver.
- `modem/` and `sensors/`: integration/packaging references and hash records.

After syncing the pinned manifest, apply each patch in the listed order:

```sh
git -C build/soong am /path/to/osprey-mainline/android17/patches/build_soong/*.patch
```

Repeat for all seven paths from `patch-components.json`. Check the local HEAD
against the recorded base before applying. The kernel and libcamera are
separate checkouts at the commits in `component-revisions.json`.

## Current hardware state

The port boots to Android. USB ADB, Wi-Fi Internet, GPU display, audio,
Bluetooth, cameras, accelerometer, light, proximity and magnetometer have
had hardware checks during development; a full regression suite has not run.
Power suspend/resume uses s2idle. Brightness changes and Power wake no longer
flicker in the latest physical check after removing live DSI PLL retuning.
Charging resumed after the checked wake cycles.

Radio exposes modem/baseband and SIM state without an inserted SIM. Calls,
SMS and mobile data are not validated. RMTFS uses a RAM shadow for EFS writes.
SELinux is Enforcing; KeyMint remains software-only. Camera capture, recording
with microphone/modem, autofocus and zoom have had hardware checks. ARM64 RAW/JPEG
workers serve the ARM32 camera HAL; the validated Codec2 runtime is isolated under
`/vendor/lib/venus-codec2`. Camera quality and long-term stability remain experimental.

The external BD65B60 LEDs now turn off with the panel and return without display
corruption in the completed hardware checks. TimeKeep restores wall time from the
read-only RTC plus a persisted offset. Active host USB holds autosuspend off while
the bus is active; unplugging releases the hold. Screen-off connection and unplug/
reconnect without pressing Power passed. Long-duration battery drain is unmeasured.

## Build/package limits

This is a source checkpoint, not a ROM download or an unattended flash recipe.
See [BUILDING.md](BUILDING.md) for the incremental build/package entry point.
Scripts retain the development workspace paths and require the pinned external
kernel/libcamera sources, lk2nd and firmware. The kernel script generates matched
boot and modules from the explicit module selection. Built images/modules, private
device logs and captures are not published.
The module manifests record the actual installed build, whose release suffix
predates committing its formerly dirty sources. Rebuild all kernel modules
with the same configuration/release before creating a new boot/system pair.
`replay-results.json` records changes already provided or removed by A17.
The A16 sources and artifacts are not overwritten by this checkpoint.

`package-receipt.json` records the rebuilt development ZIP and its checksums.
The installer preserves Data and recovery, checks partition sizes and hashes,
and creates no automatic backups. The separately generated rollback helper only
works with a valid backup left by an earlier installer; it does not create one.
