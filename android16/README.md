# Android 16 osprey mainline migration

Base: LineageOS lineage-23.2, Android 16. Target: lineage_osprey,
trunk_staging, userdebug, ARM 32-bit userspace. Source components with changes
use the separate local lineage-23.2-mainline branch.

The userspace product does not build kernel 3.10 or its CAF HALs. Linux 7 and
lk2nd remain separate boot-package inputs. The installable package uses the
physical system partition as root, the standard Android 16 init, and no
initramfs. This boot mode has not yet been validated on the phone.

replay-results.json records carried patches and upstream replacements.
Android Common ashmem/memfd ioctl detection has a guarded POSIX fallback for
mainline, keeping the existing region size seals and protections.
The old processgroup/RefBase/netd/DNS failure bypasses are not used.
The IME patch for mismatched Android 15 framework flags is not carried.

Local Meson subprojects and the unused legacy system/qcom tree have .find-ignore
markers so the Android module finder does not scan their obsolete Android.mk.

The first build also required vendor variants of libhwy, libskia_skcms,
xmp_toolkit_sdk and its zuid_md5 dependency. These are source configuration
changes committed locally on lineage-23.2-mainline. Wi-Fi uses the existing
wpa_supplicant and hostapd modules, which provide the AIDL services.

Android 15 publication reconciliation is recorded separately in
../mainline-probe/reconciled-published.json. It does not publish these new
Android 16 commits.

## Installable experimental package

package.py produces a normal TWRP ZIP with boot.img and system.img. The kernel
mounts mmcblk0p41 directly; init mounts the normal userdata partition, not the
old mainline-probe-data directory. Kernel modules and firmware are installed
under vendor. The five Freedreno libraries are NDK API 35 inputs and passed
Android 16 ELF dependency checks. No old Android 15 framework, libcutils,
libprocessgroup, libutils, netd or APK overlays are included.

The installer checks device, partition sizes and image hashes before writing.
It first saves and verifies the previous system and boot under internal
storage/osprey-a16-backup. Insufficient space aborts before flashing. The
rollback ZIP uses this backup. Do not delete it or format internal storage
until the new system is confirmed usable. Recovery is not overwritten.

The installer does not format Data. Existing installed Android data may need
manual migration or a wipe for Android 16. A data wipe is not reversed by the
system/boot rollback. Back up personal data separately.

The existing libcamera HAL is not integrated into this first Android 16
package. Camera operation and all other hardware still require on-device
verification. SELinux remains permissive during bring-up.
