from pathlib import Path
import hashlib, io, json, tarfile, zipfile, sys
stage=Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey/mainline-probe')
wifi_android='--wifi-android' in sys.argv[1:]
native_audio='--native-audio' in sys.argv[1:]
camera_id='--camera-id' in sys.argv[1:]
camera='--camera' in sys.argv[1:]
charger_control='--charger-control' in sys.argv[1:]
backlight_control = '--backlight' in sys.argv[1:]
camera_30fps = '--camera-30fps' in sys.argv[1:]
camera_full = '--camera-full' in sys.argv[1:]
camera_front = '--camera-front' in sys.argv[1:]
camera_flash = '--camera-flash' in sys.argv[1:]
camera_fast_af = '--camera-fast-af' in sys.argv[1:]
camera_quality = '--camera-quality' in sys.argv[1:]
camera_cached_output = '--camera-cached-output' in sys.argv[1:]
camera_video = '--camera-video' in sys.argv[1:]
bluetooth = '--bluetooth' in sys.argv[1:]
scheduling = '--scheduling' in sys.argv[1:]
tethering = '--tethering' in sys.argv[1:]
wifi_compat = '--wifi-compat' in sys.argv[1:]
adb_cmd = '--adb-cmd' in sys.argv[1:]
assert not adb_cmd or wifi_compat
assert not wifi_compat or tethering
assert not tethering or scheduling
assert not scheduling or bluetooth
assert not bluetooth or camera_video
assert not camera_video or camera_cached_output
assert not camera_cached_output or camera_quality
assert not camera_quality or camera_fast_af
assert not camera_fast_af or camera_flash
assert not camera_flash or camera_front
assert not camera_front or '--camera-lens' in sys.argv[1:]
camera_lens = '--camera-lens' in sys.argv[1:]
assert not camera_lens or camera_full
assert not camera_full or camera_30fps
assert not camera_30fps or backlight_control
assert not backlight_control or charger_control
assert not charger_control or camera
assert not camera or camera_id
assert not camera_id or native_audio
netfilter='--netfilter' in sys.argv[1:]
assert not native_audio or netfilter
managed_graphics='--managed-graphics' in sys.argv[1:]
assert not netfilter or managed_graphics
assert not managed_graphics or wifi_android
version='v49' if camera_video else 'v48' if camera_cached_output else 'v47' if camera_quality else 'v46' if camera_fast_af else 'v45' if camera_flash else 'v44' if camera_front else 'v43' if camera_lens else 'v42' if camera_full else 'v41' if camera_30fps else 'v40' if backlight_control else 'v39' if charger_control else 'v38' if camera else 'v35' if camera_id else 'v34' if native_audio else 'v33' if netfilter else 'v32' if managed_graphics else 'v31' if wifi_android else 'v30'
out=stage/('permanent-package-'+version if wifi_android else 'permanent-package')
if bluetooth:
    version = 'v50'
    out = stage / 'permanent-package-v50'
if scheduling:
    version = 'v51'
    out = stage / 'permanent-package-v51'
if tethering:
    version = 'v54'
    out = stage / 'permanent-package-v54'
if wifi_compat:
    version = 'v55'
    out = stage / 'permanent-package-v55'
if adb_cmd:
    version = 'v56'
    out = stage / 'permanent-package-v56'
out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
lk=(stage/'lk2nd-fastboot.img').read_bytes()
android=(stage/('boot-mainline-android-v49-camera-video.img' if camera_video else 'boot-mainline-android-v45-camera-flash.img' if camera_flash else 'boot-mainline-android-v44-camera-front.img' if camera_front else 'boot-mainline-android-v43-camera-lens.img' if camera_lens else 'boot-mainline-android-v42-camera-full.img' if camera_full else 'boot-mainline-android-v41-camera-30fps.img' if camera_30fps else 'boot-mainline-android-v40-backlight-camera.img' if backlight_control else 'boot-mainline-android-v39-charger.img' if charger_control else 'boot-mainline-android-v36-camera.img' if camera else 'boot-mainline-android-v35-camera-id.img' if camera_id else 'boot-mainline-android-v34-audio.img' if native_audio else 'boot-mainline-android-v33-netfilter.img' if netfilter else 'boot-mainline-android-v32-managed.img' if managed_graphics else 'boot-mainline-android-v31-wifi-android.img' if wifi_android else 'boot-mainline-android-v30-compact.img')).read_bytes()
assert lk[:8]==android[:8]==b'ANDROID!'
if bluetooth:
    android = (stage / 'boot-mainline-android-v50-bluetooth.img').read_bytes()
    assert android[:8] == b'ANDROID!'
if scheduling:
    android = (stage / 'boot-mainline-android-v51-scheduling.img').read_bytes()
    assert android[:8] == b'ANDROID!'
if tethering:
    android = (stage / 'boot-mainline-android-v52-tethering.img').read_bytes()
    assert android[:8] == b'ANDROID!'
assert len(lk)<=512*1024
boot=lk.ljust(512*1024,b'\0')+android
assert len(boot)<=16*1024*1024
boot=boot.ljust(16*1024*1024,b'\0')
(out/('boot-mainline-permanent-'+version+'.img')).write_bytes(boot)
# Only active runtime dependencies. Exclude experiments and backup libraries.
files={}
with tarfile.open(stage/'permanent-runtime.tar') as archive:
    for m in archive:
        if not m.isfile() or '.before-' in m.name: continue
        assert '..' not in Path(m.name).parts and not m.name.startswith('/')
        files[m.name]=archive.extractfile(m).read()
assert sha(files['graphics-libs/hwcomposer.drm_minigbm.so'])=='c5998ba3978782b87614e2b76aea59b4094b927835a79d020ecddff30b5ebafb'
if wifi_android:
    files['start-native-wifi.sh']=(stage/'start-native-wifi.sh').read_bytes()
    files['load-native-display.sh']=(stage/'load-native-display.sh').read_bytes()
if native_audio:
    files['graphics-libs/audio.primary.mainline.so']=(stage/'audio.primary.mainline.so').read_bytes()
if managed_graphics:
    files['graphics-libs/libminigbm_gralloc_msm.so']=(stage/'graphics-libs/libminigbm_gralloc_msm.so').read_bytes()
    files['graphics-libs/gralloc.minigbm_msm.so']=(stage/'graphics-libs/gralloc.minigbm_msm.so').read_bytes()
    for name in ['setup-native-hw.sh','setup-freedreno-egl.sh','start-graphics-v24.sh','run-native-composer.sh']:
        files[name]=(stage/name).read_bytes()
if camera_video:
    files['mediaextractor-mainline.policy']=(stage/'mediaextractor-mainline.policy').read_bytes()
    for name in ['libcutils-media-memfd.so','libcutils-vendor-memfd.so','libcutils-swcodec-memfd.so']:
        files['graphics-libs/'+name]=(stage/name).read_bytes()
if bluetooth:
    files['setup-bluetooth-mainline.sh'] = (stage / 'setup-bluetooth-mainline.sh').read_bytes()
    files['setup-mainline-scheduling.sh'] = (stage / 'setup-mainline-scheduling.sh').read_bytes()
    for directory in ['bluetooth-runtime', 'bluetooth-modules']:
        for p in sorted((stage / directory).iterdir()):
            assert p.is_file() and not p.is_symlink(), p
            files[p.relative_to(stage).as_posix()] = p.read_bytes()
if scheduling:
    files['scheduling-modules/af_key.ko'] = (stage / 'scheduling-modules/af_key.ko').read_bytes()
if tethering:
    files['networkstack-runtime/NetworkStack.apk'] = (stage / 'networkstack-runtime/NetworkStack.apk').read_bytes()
    files['networkstack-runtime/com.android.networkstack.xml'] = (stage / 'networkstack-runtime/com.android.networkstack.xml').read_bytes()
if wifi_compat:
    files['wifi-runtime/OspreyMainlineWifiOverlay.apk'] = (stage / 'wifi-runtime/OspreyMainlineWifiOverlay.apk').read_bytes()
if adb_cmd:
    files['adb-cmd.sh'] = (stage / 'adb-cmd.sh').read_bytes()
if camera:
    for p in sorted((stage/'camera-runtime').rglob('*')):
        assert not p.is_symlink(), p
        if p.is_file():
            files[p.relative_to(stage).as_posix()]=p.read_bytes()
    files['setup-camera-hal.sh']=(stage/'setup-camera-hal.sh').read_bytes()
    files['start-native-graphics.sh']=(stage/'start-native-graphics.sh').read_bytes()
for name in list(files):
    if name.endswith('.sh'):
        files[name]=files[name].decode('utf-8-sig').replace('\r\n','\n').encode()
with tarfile.open(out/'runtime.tar','w') as archive:
    for name,data in sorted(files.items()):
        m=tarfile.TarInfo(name); m.size=len(data); m.mode=0o755; m.uid=m.gid=0
        archive.addfile(m,io.BytesIO(data))
boot_sha=sha(boot)
runtime_sha=sha((out/'runtime.tar').read_bytes())
old=(stage/'mainline-preinstall-boot.img').read_bytes()
assert len(old)==len(boot)
old_sha=sha(old)
previous_sha=json.loads((stage/('permanent-package-v48/manifest.json' if camera_video else 'permanent-package-v44/manifest.json' if camera_flash else 'permanent-package-v43/manifest.json' if camera_front else 'permanent-package-v42/manifest.json' if camera_lens else 'permanent-package-v41/manifest.json' if camera_full else 'permanent-package-v40/manifest.json' if camera_30fps else 'permanent-package-v39/manifest.json' if backlight_control else 'permanent-package-v38/manifest.json' if charger_control else 'permanent-package-v34/manifest.json' if camera_id else 'permanent-package-v33/manifest.json' if native_audio else 'permanent-package-v31/manifest.json')).read_text())['boot_sha256'] if managed_graphics else boot_sha
base_sha='9e9c47615d42c2563da9fd564921352c59570d7248fa288d596cdcb853584920'
if bluetooth:
    previous_sha = json.loads((stage / 'permanent-package-v49/manifest.json').read_text())['boot_sha256']
if scheduling:
    previous_sha = json.loads((stage / 'permanent-package-v50/manifest.json').read_text())['boot_sha256']
if tethering:
    previous_sha = json.loads((stage / 'permanent-package-v51/manifest.json').read_text())['boot_sha256']
policy_sha='04b55673274a5c68e0d84a15d7dd04d21596567efb9c0902a619c97c8beb15a2'
preamble='''#!/sbin/sh
set -eu
OUTFD="$2"
ZIP="$3"
ui() { echo "ui_print $*" > /proc/self/fd/$OUTFD; echo ui_print > /proc/self/fd/$OUTFD; }
fail() { ui "ERROR: $*"; exit 1; }
check() { [ "$(sha256sum "$1" | cut -d ' ' -f 1)" = "$2" ] || fail "Checksum mismatch: $1"; }
BOOT=/dev/block/platform/msm_sdcc.1/by-name/boot
[ -b "$BOOT" ] || BOOT=/dev/block/bootdevice/by-name/boot
[ -b "$BOOT" ] || fail 'Boot block device not found'
BOOT_NAME=$(basename "$(readlink -f "$BOOT")")
[ "$BOOT_NAME" = mmcblk0p31 ] || fail 'Unexpected boot partition'
[ "$(cat /sys/class/block/$BOOT_NAME/size)" = 32768 ] || fail 'Unexpected boot partition size'
[ "$(getprop ro.product.device)" = osprey ] || fail 'This ZIP is only for osprey'
WORK=$(mktemp -d /tmp/osprey-mainline.XXXXXX)
trap 'umount "$WORK/system" 2>/dev/null || true; rm -rf "$WORK"' EXIT
'''
install=preamble+f'''
ui 'Mainline {version}: preparing existing osprey installation'
unzip -o "$ZIP" boot.img runtime.tar -d "$WORK" >/dev/null
check "$WORK/boot.img" {boot_sha}
check "$WORK/runtime.tar" {runtime_sha}
mount /data 2>/dev/null || true
DATA=/data/mainline-probe-data
[ -d "$DATA" ] && [ ! -L "$DATA" ] || fail 'Existing mainline test data missing; mount/decrypt Data first'
grep -qx osprey-mainline-test-data-v1 "$DATA/.mainline-probe" || fail 'Mainline data marker missing'
mkdir "$WORK/system"
SYSTEM=/dev/block/platform/msm_sdcc.1/by-name/system
[ -b "$SYSTEM" ] || SYSTEM=/dev/block/bootdevice/by-name/system
[ "$(basename "$(readlink -f "$SYSTEM")")" = mmcblk0p41 ] || fail 'Unexpected system partition'
mount -t ext4 -o ro,noload "$SYSTEM" "$WORK/system" || fail 'Cannot read installed system'
check "$WORK/system/system/build.prop" {base_sha}
check "$WORK/system/system/vendor/etc/selinux/precompiled_sepolicy" {policy_sha}
umount "$WORK/system"
CURRENT=$(sha256sum "$BOOT" | cut -d ' ' -f 1)
[ "$CURRENT" = {old_sha} ] || [ "$CURRENT" = {boot_sha} ] || [ "$CURRENT" = {previous_sha} ] || fail 'Boot changed since package preparation; refusing to overwrite'
BACKUP=/data/media/0/mainline-backup
mkdir -p "$BACKUP"
if [ ! -f "$BACKUP/pre-mainline-boot.img" ]; then
    [ "$CURRENT" = {old_sha} ] || fail 'Original boot backup missing'
    dd if="$BOOT" of="$BACKUP/pre-mainline-boot.img" bs=4096 || fail 'Boot backup failed'
fi
check "$BACKUP/pre-mainline-boot.img" {old_sha}
ui 'Original boot backup saved; installing mainline runtime'
mkdir "$WORK/runtime"
tar -xf "$WORK/runtime.tar" -C "$WORK/runtime"
# Reject symlink destinations before copying into the separate test directory.
for name in graphics-libs graphics-bin mesa-libs networkstack-runtime wifi-runtime wifi-runtime/product-overlay camera-runtime camera-runtime/lib camera-runtime/lib/libcamera camera-runtime/lib/libcamera/ipa camera-runtime/libexec camera-runtime/libexec/libcamera camera-runtime/share camera-runtime/share/libcamera camera-runtime/share/libcamera/ipa camera-runtime/share/libcamera/ipa/soft camera-runtime/bin; do
    [ ! -L "$DATA/$name" ] || fail "Symlink destination: $name"
done
find "$WORK/runtime" -type f | while read file; do
    relative=${{file#"$WORK/runtime/"}}
    target="$DATA/$relative"
    [ ! -L "$target" ] || exit 1
    mkdir -p "$(dirname "$target")"
    cp "$file" "$target.mainline-new"
    chmod 0755 "$target.mainline-new"
    mv -f "$target.mainline-new" "$target"
done || fail 'Runtime copy failed'
sync
ui 'Writing boot (lk2nd + compact Android image)'
dd if="$WORK/boot.img" of="$BOOT" bs=4096 || fail 'Boot write failed; restore with rollback ZIP'
sync
check "$BOOT" {boot_sha}
ui 'Installed. Recovery and system were preserved. Reboot System to start mainline.'
'''
restore=preamble+f'''
ui 'Restoring original boot for this phone'
unzip -o "$ZIP" boot.img -d "$WORK" >/dev/null
check "$WORK/boot.img" {old_sha}
dd if="$WORK/boot.img" of="$BOOT" bs=4096 || fail 'Boot restore failed'
sync
check "$BOOT" {old_sha}
ui 'Original boot restored. Mainline test data remains available.'
'''
def package(name,script,image,runtime=False):
    with zipfile.ZipFile(out/name,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        info=zipfile.ZipInfo('META-INF/com/google/android/update-binary')
        info.external_attr=(0o100755<<16); info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,script)
        z.writestr('META-INF/com/google/android/updater-script','# shell installer\n')
        z.writestr('boot.img',image)
        if runtime: z.write(out/'runtime.tar','runtime.tar')
package('osprey-mainline-'+version+'-permanent-EXPERIMENTAL.zip',install,boot,True)
package('osprey-restore-pre-mainline-boot.zip',restore,old)
(out/'install.sh').write_text(install)
(out/'restore.sh').write_text(restore)
metadata={'android_image_bytes':len(android),'lk2nd_bytes':len(lk),'boot_bytes':len(boot),'boot_sha256':boot_sha,'original_boot_sha256':old_sha,'base_build_prop_sha256':base_sha,'status':'prepared, compact boot and automatic startup not yet verified on hardware','runtime':{n:sha(d) for n,d in sorted(files.items())}}
(out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
for p in out.glob('*.zip'): print(p.name,p.stat().st_size,sha(p.read_bytes()))
