# Osprey Android 17 mainline checkpoint

LineageOS 24.0 / Android 17 / SDK 37, `cp2a`, ARM32 userspace and Linux 7
ARM64. Sources use `lineage-24.0-mainline`; A15 legacy and A16 mainline remain
on their existing branches.

## Published inputs

- `component-revisions.json`: 15 verified Wtf-OS repository commits, including
  the device trees, graphics, Wi-Fi, BPF integration, kernel and libcamera.
- `patch-components.json` and `patches/`: Soong, XMP Toolkit, Highway, Skia and
  SwiftShader changes. No repositories were created for these dependencies.
- `pinned-manifest.xml`: exact Android source revisions. The five patch-only
  projects are pinned to their upstream base, not to unpublished commits.
- `kernel.config`: the configuration used for the current module build.
- `modem/` and `sensors/`: integration/packaging references and hash records.

After syncing the pinned manifest, apply each patch in the listed order:

```sh
git -C build/soong am /path/to/osprey-mainline/android17/patches/build_soong/*.patch
```

Repeat for all five paths from `patch-components.json`. Check the local HEAD
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
The port remains experimental and uses permissive SELinux/software KeyMint.
Camera quality, video and standby power still need further validation.

## Build/package limits

This is a source checkpoint, not a ROM download or an unattended flash recipe.
Packaging scripts retain the development workspace paths and expect external
boot images, lk2nd, firmware, matched modules and previous package manifests.
Those images, built modules, private device logs and captures are not included.
The module manifests record the actual installed build, whose release suffix
predates committing its formerly dirty sources. Rebuild all kernel modules
with the same configuration/release before creating a new boot/system pair.
`replay-results.json` records changes already provided or removed by A17.
The A16 sources and artifacts are not overwritten by this checkpoint.
