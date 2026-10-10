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

## First boot follow-up

The v4 system reaches both init stages, then restarts with
`bootstrap-apexd-failed`. Its kernel lacks legacy cpuset support required by
the stock Android 16 cgroup configuration. Kernel v5 enables CPUSETS_V1 and
PROC_PID_CPUSET; package-kernel-fix.py also installs 56 matching modules and
an lk2nd build without forced fastboot. Successful Android boot is still
unconfirmed. The phone's apexd-bootstrap service has stdio_to_kmsg enabled
for diagnosis; this temporary change is not included in the original v4 ZIP.

build-kernel-cpuset.sh uses a separate mainline-a16-out directory. Future
full package.py runs require its kernel-fix-manifest.json and a systemimage
rebuilt with the corresponding module inputs, preventing mixed kernel/module
versions.

The v5 kernel now completes APEX bootstrap. The v7 empty base device VINTF
manifest also parses successfully, but keystore2 still aborts four times and
init restarts the phone. No keystore2 tombstone was found in Data. The v8
diagnostic starts a filtered logcat reader during init and sends its output
to the kernel log for pstore collection. It preserves the keystore critical
restart policy and existing Data. This does not yet identify or fix the abort.

The v8 log reaches createMintDevice(TRUSTED_ENVIRONMENT), then /dev/kmsg
rate limiting drops the following messages. The v9 diagnostic restricts
keystore output to warnings/errors and starts the existing persistent
logcat service at post-fs-data instead of waiting for late_start.

The v9 pstore confirms keystore2 cannot connect to KeyMint and aborts with
HARDWARE_TYPE_UNAVAILABLE. The product was missing any KeyMint service.
The bring-up configuration now selects AOSP's software-only
android.hardware.security.keymint-service. This is a reference implementation
without TEE protection and is unsuitable for protecting real secrets.
package-keymint.py checks ARM32 ELF dependencies and existing library hashes
before producing a small TWRP update. It does not modify keystore databases,
disable keystore's critical policy, or overwrite boot.

After explicit approval of software-only key protection, v10 installed
successfully through TWRP (RC=0). The 16 payload files passed checksum checks.
Boot success and resolution of the keystore abort still require verification.

The v10 log confirms Keystore 2.0 registers successfully and opens its
database. The next reboot is bpfloader-failed: NetBpfLoad defaults the missing
ro.board.first_api_level to 36, then rejects ARM32 on Linux 7. The v11 update
sets the board's original API to 22 and opts only osprey ARM32 on an ARM64
kernel into the existing kernel-upgrade path, including Linux 6.13+.
All BPF syscall, map/program load and error checks remain active. Actual
ARM32 BPF operation remains to be verified from the next boot log. The APEX
was rebuilt and installed with the original signing key; Data and boot were
not overwritten.

The v11 pstore confirms bpfloader exits with status 0 after loading BPF.
The system now reaches graphics/audio startup, where ConfigStore has no
device VINTF entry, the generic audio service no longer supports the installed
2.0 adapters, and generic minigbm was built without selecting MSM. The next
update selects the existing minigbm Soong platform=msm option, audio/effect
4.0 adapters, and VINTF declarations for installed HIDL services. Hardware
behavior and GUI startup remain unverified until the next boot.

The v12 HAL update built successfully (415 tasks), passed ARM32 dependency
and original-library checks, and installed through TWRP with RC=0. It replaces
the generic minigbm driver library, adds audio/effect 4.0 adapters and their
missing libraries, and updates the device manifest. No kernel or user data
changes were needed for this iteration. GUI and audio operation are not yet
confirmed.

The v12 boot log now confirms graphics allocation reaches MSM/FD307, but Mesa
fails because its gralloc0 metadata query receives a handle imported by mapper5
in another driver instance. v13 temporarily retains/releases the handle during
the gralloc0 query, preserving import errors. It also fixes ComposerClient
unlocking its mutex after destroying its owner, and changes audio/effect
adapters plus VINTF from 4.0 to 6.0 (the oldest version supported by A16's
audio framework). These fixes are building; runtime results remain unverified.

v13 built successfully (454 tasks) and installed through TWRP with RC=0.
All payload hash checks passed; Data and boot were unchanged. The temporary
host-only Soong GOMEMLIMIT forwarding was reverted after the build. The next
boot must verify EGL imports, composer stability and audio registration.

The v13 boot log no longer reports the previous EGL-import or composer/audio
crashes. system_server is killed by Watchdog while its main thread waits in
LightsService.setLight_native: the Light HAL repeatedly exits because it tries
the old lcd-backlight path. A16 omitted debug.mainline.light_probe=true, which
selects the existing native osprey-backlight code. v14 restores that property
in mainline.mk and the installed vendor configuration; no kernel rebuild or
Data change is needed. Full boot and physical brightness remain unverified.

v14 installed through TWRP with RC=0 and matching payload hashes. The phone
was restarted for runtime verification. Data and boot were not modified.

v14 removes the LightsService watchdog block. The next boot repeatedly kills
system_server in batterystats-handler because synchronizeKernelRCU cannot
create AF_KEY sockets (EAFNOSUPPORT, -97). CONFIG_NET_KEY=m is already built,
but af_key.ko was omitted from the A16 module assets and early load list.
v15 adds the matching module and loads it before framework startup. Linux 7's
pfkey_release still calls synchronize_rcu, so no BPF/statistics bypass is used.
The package verifies the exact installed boot hash and payload hashes; TWRP
installation completed with RC=0 without changing boot or Data. Runtime
socket operation and full GUI startup require the next boot log.

The v15 log reaches LOCKED_BOOT_COMPLETED without the prior system_server
RCU crash. The remaining native launcher/SystemUI EGL crashes are preceded
by EACCES opening /dev/dri/renderD128. The existing wildcard rule only grants
system/graphics access, unlike AOSP Goldfish's application-accessible render
node. A proposal to separate render and card permissions is pending explicit
approval after automatic review rejection; no GPU permission change was made.
Separately, the internal-error dialog reports SEPolicy version 0 in VINTF.
v16 declares the actually installed policy version 202604; installation
completed through TWRP with RC=0. Compatibility must be rechecked next boot.

After explicit approval, v17 separates DRM node permissions: card* stays
0660 system graphics; renderD* is 0666 system graphics, as in AOSP Goldfish.
The source rule and installed vendor/etc/ueventd.rc match. TWRP installation
completed with RC=0 and checksum verification. No data or boot changes were
made. Launcher/SystemUI GPU access requires verification after restart.

v17 reaches the desktop. v18 fixes USB by creating /dev/usb-ffs as 0775
shell:shell before the hardware service (whose umask 077 previously made the
parent inaccessible to dropped-privilege adbd), and resetting configfs=1 on
boot after the generic on-init fallback set it to 0. Installation completed
with RC=0. Live USB ADB now reports ZY2223C9DZ device, kernel 7.0 and SDK36;
sys.usb.configfs=1 and sys.usb.state=adb. ADB authentication was not disabled.
Wi-Fi kernel wlan0 exists, but BOARD_WLAN_DEVICE=wlan0 selected the unsupported
fallback function table. Source now selects qcwcn with hardware/qcom/wlan in
PRODUCT_SOONG_NAMESPACES. The replacement libwifi-hal is building; association
and connectivity remain unverified.

v19 builds the qcwcn Wi-Fi backend (550 tasks, successful) and installs it
with matching ARM32 libcld80211. Both payload and original HAL checksums
were checked before live replacement; the old HAL is retained locally.
Source exports the legacy namespace and includes libcld80211 in the product.
The HAL initializes successfully and wificond creates wlan0. Framework
then blocks on the missing supplicant init service: v20 includes the standard
A16 AIDL supplicant init.rc via PRODUCT_COPY_FILES. Both patches are installed;
association and connectivity still need checking after reboot. USB adb root
reconnected successfully before this reboot. MTP/UsbService is not verified.
The temporary host-only Soong GOMEMLIMIT forwarding edit was removed.

After v20 reboot: USB ADB returns, sys.boot_completed=1, wpa_supplicant
running. Wi-Fi automatically associates to the saved WPA2 network and obtains
IPv4 via DHCP. Two pings each to 1.1.1.1 and example.com succeed with 0% loss;
ConnectivityService marks the Wi-Fi network VALIDATED. Live evidence is saved
in android16-port/package/live-wifi-v20.log and wifi-connectivity-v20.txt.
Qualcomm vendor-only feature commands remain unsupported on wcn36xx; this
did not block connection. Long-term Wi-Fi stability and MTP remain unchecked.

v21 fixes shared storage and screenshot saving: CONFIG_FUSE_FS=m and fuse.ko
were already packaged, but the early hardware script omitted loading FUSE.
Vold could not open /dev/fuse; emulated;0 was UNMOUNTABLE and ImageExporter
crashed with Volume external_primary not found. Loading the existing matching
module and remounting via StorageManager makes emulated;0 mounted. The normal
SystemUI screenshot path saves Screenshot_20261010-020042_Trebuchet.png and
returns a MediaStore URI, confirmed in screenshot-fixed-v21.log. Added load
fuse before hardware initialization in source and on-device script; original
and payload hashes checked before replacement. No Data was erased. Persistence
after a future reboot remains unverified; no reboot was needed for live repair.

v22 caches only WIFI_ERROR_NOT_SUPPORTED feature/logger query results for
the lifetime of a HAL instance; other failures remain retryable. HAL rebuild
completed 25/25 tasks, original library backed up, hashes checked before/after
live replacement. Wi-Fi reconnects after a foreground scan. Screen-off PNO
scans are unsupported by wcn36xx and remain a separate limitation.
v23 kernel cgroup-v1 migration permits cross-UID scheduling only when the
file-opening credential is UID1000 with CAP_SYS_NICE in the initial user
namespace. Explicit user authorization followed an automatic review rejection.
It preserves root/same-UID access and inherited-FD protection. Kernel built
with KALLSYMS_EXTRA_PASS=1 after the linker requested an extra symbol pass.
Normal TWRP ZIP contains kernel and all 57 matching modules, no initramfs;
previous boot partition is backed up locally. Installation is awaiting TWRP;
cgroup migration improvement is not yet verified on device.

v23 installed through TWRP3.6.2_9-0 successfully. ZIP SHA256 matches its
manifest and written boot SHA256 is
9d930d7a7e420982ba9036b0e4f65ee72dc9e91ff8ae6a3888a4f1f5b035f57b.
All 57 module hashes were verified by the installer. Data and recovery were
preserved; runtime migration checks await system startup. Recovery receipt:
android16-port/package/recovery-v23.log.

v23 runtime: sys.boot_completed=1, USB ADB available, shared storage mounted
automatically after boot (v21 FUSE persistence confirmed), Wi-Fi associated
to saved network. Launching Settings no longer emits cross-UID cgroup write
errors from system_server (PID688, UID1000). Remaining migration failures
are exclusively lmkd (PID205, UID1069, CAP_SYS_NICE), which is outside the
authorized UID1000 exception. Asked for explicit authorization to extend
the same file-credential capability check to LMKD UID1069; not applied yet.
Evidence: android16-port/package/runtime-v23.log, runtime-v23-status.txt.

v24 extends the explicitly approved migration exception to LMKD UID1069,
while still requiring file-opening CAP_SYS_NICE in the initial user namespace
for both allowed UIDs1000/1069. Other access checks remain unchanged. User
approved this extension directly. Incremental kernel/modules build succeeds.
TWRP ZIP and matching module source assets are ready; normal recovery reboot
did not switch the device, so installation awaits manual entry to TWRP.

v24 installed through TWRP successfully. ZIP checksum matches manifest;
written boot checksum is
256b89e6569c1037c921e85c5f46ce84d0dd04944b02dfe0374633d6b31e9ae2.
Installer verified all 57 matching modules; Data and recovery preserved.
Receipts: twrp-install-v24.log and recovery-v24.log. Runtime check pending.

v24 runtime confirmed: sys.boot_completed=1, shared volume emulated;0 mounted,
Wi-Fi connected, Settings launched. Collected runtime-v24.log contains LMKD
killinfo activity but no AddTidToCgroup/Failed to add task errors from LMKD
or system_server and no Java/native crash matches in the captured window.
This confirms the scoped migration fix during actual memory reclamation.
Source and installed kernel now include both approved UIDs. Performance
improvement and long-term stability have not been benchmarked.

## Android 16 camera integration (v25)

Uses the existing osprey libcamera simple pipeline and calibrated software ISP from the Android 15 mainline port, rebuilt for the Android 16 vendor libraries. Camera2 and the standard HIDL 2.4 provider replace the missing camera stack. Both sensors, AK7375 lens and SKY81296 flash use the existing kernel modules; boot and Data are preserved.

Sources: `mainline-camera/`, `camera-a16-integration.diff`, `camera-a16-board.diff`. Build with `build-libcamera-a16.py`, then `build-camera-a16.sh`; `package-camera-v25.py` creates the incremental TWRP ZIP after checking ELF dependencies and the installed vendor hashes. v25 was installed successfully in TWRP. Android reports two cameras; Camera2 preview works on the rear and front sensors. Rear capture produced a valid 3120x4152 JPEG (3.9 MB); front capture produced a valid 1920x2552 JPEG (0.77 MB). Existing A15 media profiles were missing and are restored in v26; v26 was installed successfully in TWRP and Camera2 preview works after a full reboot with an empty media.settings.xml property (the standard vendor profile search). The migrated camera private Pictures directory retained its old app UID: ownership was corrected to the current UID without deleting images. Video and calibrated image quality have not been revalidated on A16.

## Camera quality configuration (v27)

Restores the existing A15 `configuration.yaml` omitted from the A16 camera integration. Enables chroma denoise, neutral-preserving colour boost and optional high-quality luma denoise already implemented in libcamera. FAST preview filters chroma only; HIGH_QUALITY requests may also filter low-contrast luminance. Tested live via a reversible bind mount visible in the provider namespace; v27 was installed successfully in TWRP and the configuration checksum was verified after reboot. No new measured colour calibration is claimed, and no change to the previously measured rear black level is made.

Post-reboot rear capture saved IMG_20261010_190953.jpg at 3120x4152; the JPEG was verified and the crash buffer was empty, but Camera2 had exited by the later check. An earlier capture attempt was killed by LMKD (foreground Camera2); peak camera memory remains a stability limitation on the 1 GB model. The successful retry took about 20 seconds from capture request through processing and MediaStore publication. Evidence: camera-v27-postboot-capture.log and camera-v27-rear.jpg. No resolution reduction or memory-killer exemption was applied.

## Camera memory pressure (v28)

The soft ISP now uses two internal RAW buffers instead of four. Software-ISP output streams larger than 8 MP advertise at most two buffers. RGB, NV12 and denoise scratch vectors release excess capacity on reconfiguration, including leaving NV12. Resolution, calibration and denoise settings are unchanged; hardware converter queues retain their original depth.

Built with build-libcamera-a16.py. Runtime used a reversible bind mount of the rebuilt libcamera.so. Two successive rear captures with the final library saved full 3120x4152 JPEGs; Camera2 retained PID 2959 throughout. No Camera2 LMKD kill or crash was recorded during these captures (background apps could still be reclaimed). The frame processing still takes seconds; video throughput and prolonged stability have not been measured. Patch: camera-memory-v28.diff. Evidence: camera-v28-final-capture.log, camera-v28-repeat-capture.log, camera-v28-rear.jpg. v28 installed successfully through TWRP (updater RC=0); package-camera-memory-v28.py checked the original vendor library checksum before replacement. Data and boot were unchanged. Receipts: twrp-install-v28.log and recovery-v28.log. Post-reboot library SHA256 matches dedbe2894bbb16c0ea9b629c33e9fac6462e5f5e62eafdd6f2f3d89d28c89791; provider is running. Evidence: camera-v28-postboot.log.

## Wi-Fi power save (v29)

Stub-backed supplicant uses the existing nl80211 legacy power-save operation for AIDL setSuspendModeEnabled rather than unsupported vendor SETSUSPENDMODE. Driver errors still propagate; non-stub private command backends are unchanged. Built vendor wpa_supplicant successfully. A reversible bind mount was validated: Wi-Fi reconnected with VALIDATED internet, screen sleep requested legacy_ps=1 and wake requested legacy_ps=0; iw confirmed on/off. No new setSuspendModeEnabled failure was observed in the collected window. TWRP package preserves Data/boot and the original executable SELinux label, checking the old binary hash before replacement. v29 installed successfully in TWRP (updater RC=0), preserving Data and boot. Receipts: twrp-install-v29.log and recovery-v29.log. Post-reboot confirmed: sys.boot_completed=1, supplicant running, Wi-Fi reconnected, standard nl80211 power-save call logged and crash buffer empty. Installed binary hash matches the v29 manifest. Evidence: wifi-powersave-v29-postboot.log.

Evidence: build-supplicant-v29.log, wifi-powersave-v29-live.log, wifi-powersave-v29-screen.log, wifi-powersave-v29-kernel.log. Source: wifi-powersave-v29.diff. GPU inspection found two MDP5 INTF1 underruns in the collected boot log; InputEventReceiver timing discrepancies affect latency reporting, with no GPU fault/hang observed. Graphical timing and Bluetooth energy stats were not patched without a confirmed cause. Long-term Wi-Fi battery impact has not been measured.

## Bluetooth stats while powered off (v30)

BatteryStatsImpl and the legacy BatteryExternalStatsWorker now request controller activity energy only when BluetoothAdapter.isLeEnabled() reports an active radio. This preserves BLE-only collection; a fully off radio no longer invokes an unbound service (error 9). Async errors and collector timeout handling remain intact. Built services successfully. The installer replaces services.jar, its profile and matching ART/ODEX/VDEX together, verifies every previous file checksum before writing, and preserves Data and boot. Matching rollback package restores the saved five original files. v30 installed successfully through TWRP (updater RC=0); five framework files verified, Data and boot preserved. Receipts: twrp-install-v30.log and recovery-v30.log. Post-reboot validated: sys.boot_completed=1, services.jar hash matches the manifest. With Bluetooth OFF, batterystats --sample returned without the prior unbound-service/error-9 stack trace; crash buffer was empty. Evidence: bt-stats-v30-postboot.log. Bluetooth-on and BLE-only runtime collection remain untested.

Sources: bt-stats-v30.diff, build-bt-stats-v30.sh, package-bt-stats-v30.py. Evidence: bt-stats-v30-before.log, build-bt-stats-v30.log. Graphics clocks use simple_ondemand with GPU max 400 MHz; no frequency or fence settings were changed. Extended Bluetooth-on/BLE-only behavior and battery impact have not been measured.
