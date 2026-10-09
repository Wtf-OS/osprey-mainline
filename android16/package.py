from pathlib import Path
import hashlib, json, struct, subprocess, zipfile

root = Path('/home/debian/osprey-port/lineage')
project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
out.mkdir(exist_ok=True)
work = Path('/home/debian/osprey-port/android16-package')
work.mkdir(exist_ok=True)
def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
product = root/'out/target/product/osprey'
props = (product/'system/build.prop').read_text()
assert 'ro.build.version.sdk=36\n' in props and 'ro.build.version.release=16\n' in props
assert (product/'root/init.osprey.rc').is_file()
assert (product/'system/vendor/lib/egl/libEGL_adreno.so').is_file()
old = (project/'mainline-probe/boot-mainline-android-v58-quota-ipsec.img').read_bytes()
assert old[:8] == b'ANDROID!'
ks = struct.unpack_from('<I',old,8)[0]
page = struct.unpack_from('<I',old,36)[0]
kernel = work/'Image.gz-dtb'
kernel.write_bytes(old[page:page+ks])
cmdline = ('root=/dev/mmcblk0p41 rootwait rootfstype=ext4 rw init=/init '
           'androidboot.hardware=osprey androidboot.serialno=ZY2223C9DZ '
           'console=ttyMSM0,115200n8 console=tty0 loglevel=7 panic=0 cma=32M '
           'enforcing=0 selinux=1 androidboot.selinux=permissive lk2nd.pass-simplefb=1 msm.separate_gpu_kms=1 '
           'clk_ignore_unused pd_ignore_unused regulator_ignore_unused')
inner = work/'boot-android.img'
subprocess.run(['python3',str(root/'system/tools/mkbootimg/mkbootimg.py'),
                '--kernel',str(kernel),'--header_version','0','--base','0x80000000',
                '--kernel_offset','0x00080000','--ramdisk_offset','0x02000000',
                '--tags_offset','0x01e00000','--pagesize','2048','--cmdline',cmdline,
                '--output',str(inner)],check=True)
assert struct.unpack_from('<I',inner.read_bytes(),16)[0] == 0, 'No initramfs requested'
lk = (project/'mainline-probe/lk2nd-fastboot.img').read_bytes()
assert lk[:8] == b'ANDROID!' and len(lk) <= 512*1024
boot = lk.ljust(512*1024,b'\0') + inner.read_bytes()
assert len(boot) <= 16*1024*1024
bootfile = out/'boot.img'
bootfile.write_bytes(boot.ljust(16*1024*1024,b'\0'))
raw = work/'system.raw.img'
subprocess.run([str(root/'out/host/linux-x86/bin/simg2img'),str(product/'system.img'),str(raw)],check=True)
assert raw.stat().st_size == 2432696320
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
BACKUP=/data/media/0/osprey-a16-backup
[ ! -L "$BACKUP" ] || fail 'Unsafe backup directory'
for name in system.img.gz boot.img complete system.sha256 boot.sha256; do
    [ ! -L "$BACKUP/$name" ] || fail 'Unsafe backup file'
done
WORK=$(mktemp -d /tmp/osprey-a16.XXXXXX)
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
ui 'Checking Android 16 images before writing'
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
    echo osprey-a16-backup-v1 > "$BACKUP/complete"
    sync
fi
grep -qx osprey-a16-backup-v1 "$BACKUP/complete" || fail 'Unexpected backup marker'
ui 'Installing Android 16 system; Data is not formatted'
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
ui 'Installed experimental Android 16. Recovery and user data were preserved.'
'''
rollback = preamble + '''
grep -qx osprey-a16-backup-v1 "$BACKUP/complete" || fail 'Verified backup not found'
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
receipts=[create('osprey-lineage-23.2-mainline-a16-v4-EXPERIMENTAL.zip',installer,True),create('osprey-a16-rollback.zip',rollback)]
(out/'manifest.json').write_text(json.dumps(dict(android=16,sdk=36,initramfs=False,boot_sha256=bootsha,system_sha256=systemsha,kernel_sha256=digest(kernel),cmdline=cmdline,packages=receipts),indent=2)+'\n')
print(json.dumps(receipts,indent=2))
