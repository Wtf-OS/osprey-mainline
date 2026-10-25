from pathlib import Path
import hashlib, json, re, struct, subprocess, zipfile

port = Path.home() / 'osprey-port'
root = port / 'lineage'
out = Path(__file__).resolve().parent / 'package'
out.mkdir(exist_ok=True)
work = port / 'android17-package'
work.mkdir(exist_ok=True)
def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
product = root/'out/target/product/osprey'
props = (product/'system/build.prop').read_text()
assert 'ro.build.version.sdk=37\n' in props and 'ro.build.version.release=17\n' in props
assert 'ro.surface_flinger.default_composition_pixel_format=1\n' in props, 'OpenGL composition requires RGBA output'
assert 'media.c2.hal.selection=aidl\n' in props, 'Codec2 AIDL selection must persist in system properties'
vendor_props = (product/'system/vendor/build.prop').read_text()
assert 'ro.vendor.v4l2_codec2.encoder.supported.h264=true\n' in vendor_props
assert 'ro.vendor.v4l2_codec2.encode_concurrent_instances=1\n' in vendor_props
assert (product/'root/init.osprey.rc').is_file()
init_text = (product/'root/init.osprey.rc').read_text()
assert init_text.index('bd65b60.ko') < init_text.index('panel-motorola-osprey-inx.ko') < init_text.index('simple-framebuffer/unbind')
assert (product/'system/vendor/lib/egl/libEGL_adreno.so').is_file()
hardware = root/'device/motorola/msm8916-common/mainline-boot'
fix = json.loads((hardware/'kernel-artifacts.json').read_text())
boot_input = hardware/'boot-mainline.img'
assert digest(boot_input) == fix['boot_sha256'], 'Build matching kernel artifacts first'
release_vars = (root/'out/soong/release-config/release_config-lineage_osprey-cp2a.vars').read_text()
clang_version = re.search(r'^RELEASE_BUILD_CLANG_VERSION :=\$= (\S+)$', release_vars, re.M)
assert clang_version, 'Missing active Android clang version'
clang = root/'prebuilts/clang/host/linux-x86'/clang_version[1]/'bin'
assert (product/'system/vendor/bin/hw/android.hardware.gnss-service.osprey').is_file()
assert (product/'system/vendor/etc/permissions/android.hardware.usb.host.xml').is_file()
assert (product/'system/vendor/etc/permissions/android.hardware.bluetooth_le.xml').is_file(), 'Missing BLE API feature declaration'
assert 'functions/ffs.mtp' in (product/'system/etc/init/hw/init.usb.configfs.rc').read_text()
boot_bytes = boot_input.read_bytes()
assert len(boot_bytes) == 16*1024*1024
assert boot_bytes[512*1024:512*1024+8] == b'ANDROID!'
assert struct.unpack_from('<I', boot_bytes, 512*1024+16)[0] == 0, 'No initramfs requested'
modules = {module.name: module for module in (product/'system/vendor/lib/modules').glob('*.ko')}
assert set(modules) == set(fix['modules']), 'Kernel module list differs from validated boot'
for name, module in modules.items():
    source = root/'device/motorola/msm8916-common/mainline-boot/modules'/name
    assert digest(source) == fix['modules'][name], 'Kernel/source module mismatch: '+name
    # Android strips debug sections with its current LLVM toolchain.
    stripped = work/name
    subprocess.run([str(clang/'llvm-strip'), '-o', str(stripped), '--strip-debug', str(source)], check=True)
    assert digest(module) == digest(stripped), 'Unexpected installed module changes: '+name
    stripped.unlink()
    assert (b'vermagic='+fix['kernel_release'].encode()+b' ') in module.read_bytes(), name
bootfile = out/'boot.img'
bootfile.write_bytes(boot_bytes)
cmdline = (boot_bytes[512*1024+64:512*1024+576].split(b'\0',1)[0] +
           boot_bytes[512*1024+608:512*1024+1632].split(b'\0',1)[0]).decode()
assert 'lk2nd.pass-simplefb=1' in cmdline and 'root=/dev/mmcblk0p41' in cmdline
assert 'enforcing=1' in cmdline and 'androidboot.selinux=enforcing' in cmdline, 'Android 17 must start SELinux enforcing'
assert 'rootfstype=ext4 ro init=/init' in cmdline, 'System root must mount read-only for ART artifacts'
raw = work/'system.raw.img'
subprocess.run([str(root/'out/host/linux-x86/bin/simg2img'),str(product/'system.img'),str(raw)],check=True)
assert raw.stat().st_size == 2432696320

# Refreshing prebuilts does not update an already built system.img.
image_inputs = {
    '/system/apex/com.android.bt.capex': product/'system/apex/com.android.bt.capex',
    '/system/vendor/etc/permissions/android.hardware.bluetooth_le.xml': product/'system/vendor/etc/permissions/android.hardware.bluetooth_le.xml',
    '/system/vendor/lib/pixel-power-ext-V1-ndk.so': product/'system/vendor/lib/pixel-power-ext-V1-ndk.so',
    '/system/vendor/lib/pixelatoms-cpp.so': product/'system/vendor/lib/pixelatoms-cpp.so',
    '/init.osprey.rc': product/'root/init.osprey.rc',
    '/system/build.prop': product/'system/build.prop',
    '/system/vendor/build.prop': product/'system/vendor/build.prop',
    '/system/product/app/Camera2/Camera2.apk': product/'system/product/app/Camera2/Camera2.apk',
    '/system/vendor/bin/osprey-hardware.sh': product/'system/vendor/bin/osprey-hardware.sh',
    '/system/vendor/etc/init/osprey-modem.rc': product/'system/vendor/etc/init/osprey-modem.rc',
    '/system/vendor/lib/hw/audio.primary.mainline.so': product/'system/vendor/lib/hw/audio.primary.mainline.so',
    '/system/vendor/lib/libcamera.so': product/'system/vendor/lib/libcamera.so',
    '/system/vendor/lib/libcamera-base.so': product/'system/vendor/lib/libcamera-base.so',
    '/system/vendor/lib/libminigbm_gralloc.so': product/'system/vendor/lib/libminigbm_gralloc.so',
    '/system/vendor/lib/libminigbm_gralloc_msm.so': product/'system/vendor/lib/libminigbm_gralloc_msm.so',
    '/system/vendor/lib/hw/libcamera-hal.so': product/'system/vendor/lib/hw/libcamera-hal.so',
    '/system/vendor/lib/libcamera/ipa/ipa_softisp.so': product/'system/vendor/lib/libcamera/ipa/ipa_softisp.so',
    '/system/vendor/lib/libcamera/ipa/ipa_softisp.so.sign': product/'system/vendor/lib/libcamera/ipa/ipa_softisp.so.sign',
    '/system/vendor/bin/libcamera/softisp_ipa_proxy': product/'system/vendor/bin/libcamera/softisp_ipa_proxy',
    '/system/vendor/bin/libcamera/raw64_worker': product/'system/vendor/bin/libcamera/raw64_worker',
    '/system/vendor/bin/libcamera/jpeg64_worker': product/'system/vendor/bin/libcamera/jpeg64_worker',
    '/system/vendor/etc/selinux/precompiled_sepolicy': product/'system/vendor/etc/selinux/precompiled_sepolicy',
    '/system/vendor/etc/selinux/vendor_sepolicy.cil': product/'system/vendor/etc/selinux/vendor_sepolicy.cil',
    '/system/vendor/etc/selinux/vendor_file_contexts': product/'system/vendor/etc/selinux/vendor_file_contexts',
}
for relative in ('bin/timekeep', 'app/TimeKeep/TimeKeep.apk', 'etc/init/timekeep.rc',
                 'etc/selinux/vendor_seapp_contexts', 'etc/selinux/vendor_property_contexts',
                 'etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256',
                 'etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256',
                 'etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256'):
    image_inputs['/system/vendor/'+relative] = product/'system/vendor'/relative
assert 'user=_app seinfo=platform name=com.sony.timekeep' in (product/'system/vendor/etc/selinux/vendor_seapp_contexts').read_text()
codec2 = root/'device/motorola/msm8916-common/mainline-camera'
for label, manifest_name in (('RAW64', 'raw64-runtime-manifest.json'),
                             ('JPEG64', 'jpeg64-runtime-manifest.json')):
    manifest = json.loads((codec2/manifest_name).read_text())
    for relative, expected_hash in manifest['files'].items():
        relative = Path(relative)
        assert not relative.is_absolute() and '..' not in relative.parts
        source = codec2/'prebuilt'/relative.name
        installed = product/'system/vendor'/relative
        assert digest(source) == expected_hash, label+' source checkpoint mismatch: '+str(relative)
        assert digest(installed) == expected_hash, 'Stale product '+label+' runtime: '+str(relative)
for worker in ('raw64_worker', 'jpeg64_worker'):
    worker_headers = subprocess.check_output([
        str(clang/'llvm-readelf'), '-h', '-l', '-d', str(product/'system/vendor/bin/libcamera'/worker)
    ], text=True)
    assert 'ELF64' in worker_headers and 'AArch64' in worker_headers, worker+' must be AArch64'
    assert 'INTERP' not in worker_headers and '(NEEDED)' not in worker_headers, worker+' must be static'
    context = worker+' u:object_r:vendor_osprey_raw64_exec:s0'
    assert context in (product/'system/vendor/etc/selinux/vendor_file_contexts').read_text()
codec2_manifest = json.loads((codec2/'codec2-runtime-manifest.json').read_text())
assert len(codec2_manifest['files']) == 71, 'Incomplete validated Codec2 runtime'
assert len({entry['path'] for entry in codec2_manifest['files']}) == 71, 'Duplicate Codec2 paths'
for entry in codec2_manifest['files']:
    relative = Path(entry['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    source = codec2/'codec2-runtime'/relative
    expected = product/'system/vendor'/relative
    assert digest(source) == entry['sha256'], 'Codec2 checkpoint hash mismatch: '+str(relative)
    assert digest(expected) == entry['sha256'], 'Stale product Codec2 runtime: '+str(relative)
    image_inputs['/system/vendor/'+relative.as_posix()] = expected
image_inputs.update({f'/system/vendor/lib/modules/{name}': module for name, module in modules.items()})
image_check = work/'kernel-audio-image.check'
for image_path, expected in image_inputs.items():
    image_check.unlink(missing_ok=True)
    subprocess.run(['/usr/sbin/debugfs', '-R', f'dump {image_path} {image_check}', str(raw)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert image_check.is_file() and digest(image_check) == digest(expected), (
        f'Stale system.img at {image_path}; rebuild systemimage before packaging')
image_check.unlink()

# A17's system/bin/init is second-stage only; kernel PID1 needs the static first stage.
first_stage = product/'ramdisk/init'
headers = subprocess.check_output([str(clang/'llvm-readelf'), '-l', str(first_stage)], text=True)
assert 'INTERP' not in headers and 'LOAD' in headers, 'First-stage init must be static'
context = work/'init.selinux'
context.write_bytes(b'u:object_r:init_exec:s0\0')
network_capex = product/'system/apex/com.android.tethering.capex'
system_context = work/'system.selinux'
system_context.write_bytes(b'u:object_r:system_file:s0\0')
commands = work/'install-first-stage.debugfs'
commands.write_text(f'rm /init\nwrite {first_stage} /init\nset_inode_field /init mode 0100750\nea_set -f {context} /init security.selinux\n')
with commands.open('a') as f:
    f.write(f'rm /system/apex/com.android.tethering.capex\nwrite {network_capex} /system/apex/com.android.tethering.capex\nset_inode_field /system/apex/com.android.tethering.capex mode 0100644\nea_set -f {system_context} /system/apex/com.android.tethering.capex security.selinux\n')
subprocess.run(['/usr/sbin/debugfs', '-w', '-f', str(commands), str(raw)], check=True)
check_init = work/'init.check'
subprocess.run(['/usr/sbin/debugfs', '-R', f'dump /init {check_init}', str(raw)], check=True)
assert digest(check_init) == digest(first_stage), 'Static first-stage init missing from image'
check_init.unlink()
check_capex = work/'tethering.check'
subprocess.run(['/usr/sbin/debugfs', '-R', f'dump /system/apex/com.android.tethering.capex {check_capex}', str(raw)], check=True)
assert digest(check_capex) == digest(network_capex), 'Updated networking APEX missing from image'
check_capex.unlink()

bootsha, systemsha = digest(bootfile), digest(raw)
preamble = '''#!/sbin/sh
set -eu
OUTFD="$2"
ZIP="$3"
ui() { echo "ui_print $*" > /proc/self/fd/$OUTFD; echo ui_print > /proc/self/fd/$OUTFD; }
fail() { ui "ERROR: $*"; exit 1; }
[ "$(getprop ro.product.device)" = osprey ] || fail 'Only Motorola osprey is supported'
BOOT=/dev/block/mmcblk0p31
SYSTEM=/dev/block/mmcblk0p41
[ -b "$BOOT" ] && [ -b "$SYSTEM" ] || fail 'Required partitions missing'
[ "$(cat /sys/class/block/mmcblk0p31/size)" = 32768 ] || fail 'Unexpected boot size'
[ "$(cat /sys/class/block/mmcblk0p41/size)" = 4751360 ] || fail 'Unexpected system size'
mount /data 2>/dev/null || true
[ -d /data/media/0 ] && [ ! -L /data/media/0 ] || fail 'Mount/decrypt Data first'
BACKUP=/data/media/0/osprey-a17-backup
[ ! -L "$BACKUP" ] || fail 'Unsafe backup directory'
for name in system.img.gz boot.img complete system.sha256 boot.sha256; do
    [ ! -L "$BACKUP/$name" ] || fail 'Unsafe backup file'
done
WORK=$(mktemp -d /tmp/osprey-a17.XXXXXX)
trap 'rm -rf "$WORK"' EXIT
check() { [ "$(sha256sum "$1" | cut -d " " -f 1)" = "$2" ] || fail "Checksum: $1"; }
'''
installer = preamble + f'''
system_image() {{
    index=0
    while [ "$index" -lt 145 ]; do
        unzip -p "$ZIP" "$(printf 'system.%03d.img' "$index")" || return 1
        index=$((index+1))
    done
}}
ui 'Checking Android 17 images before writing'
unzip -p "$ZIP" boot.img > "$WORK/boot.img"
check "$WORK/boot.img" {bootsha}
[ "$(system_image | sha256sum | cut -d ' ' -f 1)" = {systemsha} ] || fail 'System image checksum failed'
ui 'Installing Android 17 system; Data is not formatted'
umount /system 2>/dev/null || true
umount /system_root 2>/dev/null || true
grep -Eq ' /system(_root)? ' /proc/mounts && fail 'Unmount System in TWRP first'
system_image | dd of="$SYSTEM" bs=1048576 || fail 'System write failed'
sync
check "$SYSTEM" {systemsha}
ui 'Installing mainline boot without initramfs'
dd if="$WORK/boot.img" of="$BOOT" bs=4096 || fail 'Boot write failed'
sync
check "$BOOT" {bootsha}
ui 'Installed experimental Android 17. Recovery and user data were preserved.'
'''
rollback = preamble + '''
grep -qx osprey-a17-backup-v1 "$BACKUP/complete" || fail 'Verified backup not found'
[ "$(gzip -dc "$BACKUP/system.img.gz" | sha256sum | cut -d ' ' -f 1)" = "$(cat "$BACKUP/system.sha256")" ] || fail 'System backup checksum failed'
check "$BACKUP/boot.img" "$(cat "$BACKUP/boot.sha256")"
ui 'Restoring previous system and boot'
umount /system 2>/dev/null || true
umount /system_root 2>/dev/null || true
grep -Eq ' /system(_root)? ' /proc/mounts && fail 'Unmount System in TWRP first'
gzip -dc "$BACKUP/system.img.gz" | dd of="$SYSTEM" bs=1048576 || fail 'System restore failed'
dd if="$BACKUP/boot.img" of="$BOOT" bs=4096 || fail 'Boot restore failed'
sync
check "$SYSTEM" "$(cat "$BACKUP/system.sha256")"
check "$BOOT" "$(cat "$BACKUP/boot.sha256")"
ui 'Previous system and boot restored. User data was preserved.'
'''
def create(name,script,images=False):
    with zipfile.ZipFile(out/name,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=False) as z:
        info=zipfile.ZipInfo('META-INF/com/google/android/update-binary')
        info.external_attr=0o100755 << 16
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,script)
        z.writestr('META-INF/com/google/android/updater-script','# Shell installer\n')
        if images:
            z.write(bootfile,'boot.img')
            # TWRP unzip buffers each entry and rejects ZIP64; keep parts at 16 MiB.
            with raw.open('rb') as source:
                part_size = 16 * 1024 * 1024
                for index, offset in enumerate(range(0, raw.stat().st_size, part_size)):
                    size = min(part_size, raw.stat().st_size - offset)
                    info = zipfile.ZipInfo(f'system.{index:03d}.img')
                    info.file_size = size
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with z.open(info, 'w') as target:
                        remaining = size
                        while remaining:
                            chunk = source.read(min(1024*1024, remaining))
                            assert chunk, 'Truncated system image'
                            target.write(chunk)
                            remaining -= len(chunk)
    return dict(file=name,sha256=digest(out/name),bytes=(out/name).stat().st_size)
receipts=[create('osprey-lineage-24.0-mainline-a17-EXPERIMENTAL.zip',installer,True),create('osprey-a17-rollback.zip',rollback)]
(out/'manifest.json').write_text(json.dumps(dict(android=17,sdk=37,initramfs=False,first_stage_sha256=digest(first_stage),network_capex_sha256=digest(network_capex),boot_sha256=bootsha,system_sha256=systemsha,kernel_sha256=fix['kernel_sha256'],cmdline=cmdline,packages=receipts),indent=2)+'\n')
print(json.dumps(receipts,indent=2))
