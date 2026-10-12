from pathlib import Path
import hashlib, json, struct, subprocess, zipfile

root = Path('/home/debian/osprey-port/lineage')
project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android17-port/package'
out.mkdir(exist_ok=True)
work = Path('/home/debian/osprey-port/android17-package')
work.mkdir(exist_ok=True)
def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
product = root/'out/target/product/osprey'
props = (product/'system/build.prop').read_text()
assert 'ro.build.version.sdk=37\n' in props and 'ro.build.version.release=17\n' in props
assert 'ro.surface_flinger.default_composition_pixel_format=1\n' in props, 'OpenGL composition requires RGBA output'
assert (product/'root/init.osprey.rc').is_file()
assert (product/'system/vendor/lib/egl/libEGL_adreno.so').is_file()
baseline = project / 'android16-port/package'
fix = json.loads((baseline/'kernel-cgroup-v24-manifest.json').read_text())
modem = project/'android17-port/modem'
modem_manifest = json.loads((modem/'v7-manifest.json').read_text())
boot_input = modem/'boot-a17-modem-v7.img'
assert digest(boot_input) == modem_manifest['modem_boot_sha256']
fix['modules'].update(json.loads((root/'device/motorola/msm8916-common/mainline-modem/modules.json').read_text()))
sensors = project/'android17-port/sensors'
sensors_manifest = json.loads((sensors/'manifest.json').read_text())
boot_input = sensors/'boot-sensors-v5.img'
assert digest(boot_input) == sensors_manifest['boot_sha256']
fix['modules'].update(sensors_manifest['modules'])
for name, expected in modem_manifest['assets'].items():
    if '/lib/modules/' in name:
        continue
    installed = product/name
    assert installed.is_file(), 'Modem asset missing from rebuilt product: '+name
    assert digest(installed) == expected, 'Unexpected modem asset: '+name
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
    subprocess.run([str(root/'prebuilts/clang/host/linux-x86/clang-r596125/bin/llvm-strip'), '-o', str(stripped), '--strip-debug', str(source)], check=True)
    assert digest(module) == digest(stripped), 'Unexpected installed module changes: '+name
    stripped.unlink()
    assert (b'vermagic='+fix['kernel_release'].encode()+b' ') in module.read_bytes(), name
bootfile = out/'boot.img'
bootfile.write_bytes(boot_bytes)
cmdline = (boot_bytes[512*1024+64:512*1024+576].split(b'\0',1)[0] +
           boot_bytes[512*1024+608:512*1024+1632].split(b'\0',1)[0]).decode()
assert 'lk2nd.pass-simplefb=1' in cmdline and 'root=/dev/mmcblk0p41' in cmdline
raw = work/'system.raw.img'
subprocess.run([str(root/'out/host/linux-x86/bin/simg2img'),str(product/'system.img'),str(raw)],check=True)
assert raw.stat().st_size == 2432696320

# A17's system/bin/init is second-stage only; kernel PID1 needs the static first stage.
first_stage = product/'ramdisk/init'
headers = subprocess.check_output([str(root/'prebuilts/clang/host/linux-x86/clang-r596125/bin/llvm-readelf'), '-l', str(first_stage)], text=True)
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
mkdir -p "$BACKUP"
if [ ! -f "$BACKUP/complete" ]; then
    ui 'Backing up installed system and boot to internal storage'
    BEFORE_SYSTEM=$(sha256sum "$SYSTEM" | cut -d ' ' -f 1)
    BEFORE_BOOT=$(sha256sum "$BOOT" | cut -d ' ' -f 1)
    gzip -c < "$SYSTEM" > "$BACKUP/system.img.gz" || fail 'System backup failed; nothing flashed'
    dd if="$BOOT" of="$BACKUP/boot.img" bs=4096 || fail 'Boot backup failed; nothing flashed'
    [ "$(gzip -dc "$BACKUP/system.img.gz" | sha256sum | cut -d ' ' -f 1)" = "$BEFORE_SYSTEM" ] || fail 'System backup verification failed'
    check "$BACKUP/boot.img" "$BEFORE_BOOT"
    printf '%s\n' "$BEFORE_SYSTEM" > "$BACKUP/system.sha256"
    printf '%s\n' "$BEFORE_BOOT" > "$BACKUP/boot.sha256"
    echo osprey-a17-backup-v1 > "$BACKUP/complete"
    sync
fi
grep -qx osprey-a17-backup-v1 "$BACKUP/complete" || fail 'Unexpected backup marker'
ui 'Installing Android 17 system; Data is not formatted'
umount /system 2>/dev/null || true
umount /system_root 2>/dev/null || true
grep -Eq ' /system(_root)? ' /proc/mounts && fail 'Unmount System in TWRP first'
system_image | dd of="$SYSTEM" bs=1048576 || fail 'System write failed; use rollback ZIP'
sync
check "$SYSTEM" {systemsha}
ui 'Installing mainline boot without initramfs'
dd if="$WORK/boot.img" of="$BOOT" bs=4096 || fail 'Boot write failed; use rollback ZIP'
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
receipts=[create('osprey-lineage-24.0-mainline-a17-v7-EXPERIMENTAL.zip',installer,True),create('osprey-a17-rollback.zip',rollback)]
(out/'manifest.json').write_text(json.dumps(dict(android=17,sdk=37,initramfs=False,first_stage_sha256=digest(first_stage),network_capex_sha256=digest(network_capex),boot_sha256=bootsha,system_sha256=systemsha,kernel_sha256=fix['kernel_sha256'],cmdline=cmdline,packages=receipts),indent=2)+'\n')
print(json.dumps(receipts,indent=2))
