# Osprey Android 15 mainline

Curated source package through v58. Component commits are pinned in
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
strict netd BPF/bandwidth initialization have been restored in source. The rebuilt libraries and netd were deployed and survived a fresh boot on
osprey: boot_completed=1, Settings and Calculator launch, Wi-Fi has DHCP and
VALIDATED Internet. xt_policy/xt_u32/xt_quota2 modules now load before netd.
The kernel module build must match the running kernel ABI and release string.
The v58 package requires strict-runtime binaries in the external staging area;
strict-runtime/mount.sh here is their source loader.
Quota verification: the counter reached zero and emitted a Netlink alert;
bandwidthSetGlobalAlert succeeds. XFRM initializes and Android netd allocates
and deletes SPI state from 32-bit userspace. No VPN peer/tunnel was tested.
SELinux remains permissive.

Camera, ISP, charging and kernel hardware support remain experimental.
Wi-Fi transition networks use WPA2; WPA3-only support is still absent.
