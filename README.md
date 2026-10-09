# Osprey Android 15 mainline

Curated source package through v56. Component commits are pinned in
component-revisions.json, all on lineage-22.1-mainline. This is a new clean
repository: the historical probe repository and its earlier commits are not
part of the publication.

Included: boot/package generation and its local source dependencies. Excluded:
historical build/patch helpers, benchmark probes, experiment logs, flash
execution scripts, binary artifacts and phone backups. Generated TWRP ZIPs
still contain an installer; the user chooses whether to flash them.

The scripts currently use the original workstation paths under
/home/debian/osprey-port and .../osprey/mainline-probe. That directory remains
the artifact staging area. Compiled kernels, HALs, libraries, firmware and
the original ROM are external inputs; this source package alone cannot build
a complete ROM from nothing. Do not run prepare-android.py without those
inputs: it recreates its dedicated ramdisk work directory.

Runtime compatibility fixes: upstream processgroup/RefBase error handling and
strict netd BPF/bandwidth initialization have been restored in source. The
phone still runs the earlier binaries until a rebuild and deployment.
These source changes have not been build- or boot-verified yet.

Camera, ISP, charging and kernel hardware support remain experimental.
Wi-Fi transition networks use WPA2; WPA3-only support is still absent.
