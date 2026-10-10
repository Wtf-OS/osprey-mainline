from pathlib import Path
import hashlib, json, struct, subprocess, zipfile, zlib

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
workspace = Path('/home/debian/osprey-port')
out = project / 'android16-port/package'
manifest = json.loads((out / 'manifest.json').read_text())
release = (workspace / 'mainline-a16-out/include/config/kernel.release').read_text().strip()
assert release.startswith('7.0.0-osprey-mainline-probe-')
config = (workspace / 'mainline-a16-out/.config').read_text()
assert 'CONFIG_CPUSETS_V1=y\n' in config and 'CONFIG_PROC_PID_CPUSET=y\n' in config
donor = (project / 'mainline-probe/boot-mainline-android-v58-quota-ipsec.img').read_bytes()
size = struct.unpack_from('<I', donor, 8)[0]
page = struct.unpack_from('<I', donor, 36)[0]
gz = zlib.decompressobj(31)
gz.decompress(donor[page:page + size])
dtb = gz.unused_data
assert dtb[:4] == b'\xd0\x0d\xfe\xed'
assert struct.unpack_from('>I', dtb, 4)[0] == len(dtb)
kernel = out / 'Image-a16-cpuset.gz-dtb'
kernel.write_bytes((workspace / 'mainline-a16-out/arch/arm64/boot/Image.gz').read_bytes() + dtb)
inner = out / 'boot-a16-cpuset-android.img'
subprocess.run(['python3', str(workspace / 'lineage/system/tools/mkbootimg/mkbootimg.py'),
    '--kernel', str(kernel), '--header_version', '0', '--base', '0x80000000',
    '--kernel_offset', '0x00080000', '--ramdisk_offset', '0x02000000',
    '--tags_offset', '0x01e00000', '--pagesize', '2048', '--cmdline', manifest['cmdline'],
    '--output', str(inner)], check=True)
assert struct.unpack_from('<I', inner.read_bytes(), 16)[0] == 0
lk = (workspace / 'lk2nd-a16-out/build-lk2nd-msm8916/lk2nd.img').read_bytes()
assert lk[:8] == b'ANDROID!' and len(lk) <= 512 * 1024
boot = lk.ljust(512 * 1024, b'\0') + inner.read_bytes()
assert len(boot) <= 16 * 1024 * 1024
boot = boot.ljust(16 * 1024 * 1024, b'\0')
sha = hashlib.sha256(boot).hexdigest()
module_root = workspace / 'mainline-a16-out'
assets = workspace / 'lineage/device/motorola/msm8916-common/mainline-boot/modules'
modules = {}
for asset in sorted(assets.glob('*.ko')):
    matches = list(module_root.rglob(asset.name))
    if asset.name == 'osprey-camera-id.ko':
        matches = [workspace / 'osprey-camera-id-a16-build/osprey-camera-id.ko']
    assert len(matches) == 1, (asset.name, matches)
    data = matches[0].read_bytes()
    assert (b'vermagic=' + release.encode() + b' ') in data, asset.name
    modules[asset.name] = data
assert len(modules) == 57 and 'af_key.ko' in modules
module_checksums = ''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name, data in modules.items())
script = f'''#!/sbin/sh
set -eu
OUTFD="$2"
ZIP="$3"
ui() {{ echo "ui_print $*" > /proc/self/fd/$OUTFD; echo ui_print > /proc/self/fd/$OUTFD; }}
fail() {{ ui "ERROR: $*"; exit 1; }}
[ "$(getprop ro.product.device)" = osprey ] || fail 'Wrong device'
[ "$(cat /sys/class/block/mmcblk0p31/size)" = 32768 ] || fail 'Wrong boot partition size'
WORK=$(mktemp -d /tmp/a16-kernel.XXXXXX)
ROOT=/tmp/a16-kernel-root
trap 'umount /tmp/a16-kernel-root 2>/dev/null || true; rm -rf "$WORK"' EXIT
unzip -p "$ZIP" boot.img > "$WORK/boot.img"
[ "$(sha256sum "$WORK/boot.img" | cut -d ' ' -f 1)" = {sha} ] || fail 'Image checksum failed'
unzip -p "$ZIP" modules.sha256 > "$WORK/modules.sha256"
for name in {' '.join(modules)}; do
    unzip -p "$ZIP" "modules/$name" > "$WORK/$name"
done
(cd "$WORK" && sha256sum -c modules.sha256) || fail 'Module checksum failed'
[ ! -L "$ROOT" ] || fail 'Unsafe mount directory'
mkdir -p "$ROOT"
mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"
for name in {' '.join(modules)}; do
    [ -f "$ROOT/system/vendor/lib/modules/$name" ] || fail 'Expected installed module missing'
done
for name in {' '.join(modules)}; do
    cat "$WORK/$name" > "$ROOT/system/vendor/lib/modules/$name"
done
sync
(cd "$ROOT/system/vendor/lib/modules" && sha256sum -c "$WORK/modules.sha256") || fail 'Written module checksum failed'
umount "$ROOT"
ui 'Installing A16 kernel with cpuset v1 and automatic lk2nd boot'
dd if="$WORK/boot.img" of=/dev/block/mmcblk0p31 bs=4096
sync
[ "$(sha256sum /dev/block/mmcblk0p31 | cut -d ' ' -f 1)" = {sha} ] || fail 'Written boot checksum failed'
ui 'Boot and matching modules verified; recovery and Data preserved'
'''
package = out / 'osprey-a16-v5-cpuset-boot.zip'
with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    z.writestr('boot.img', boot)
    z.writestr('modules.sha256', module_checksums)
    for name, data in modules.items():
        z.writestr('modules/'+name, data)
(out / 'boot-a16-v5.img').write_bytes(boot)
(out / 'kernel-fix-manifest.json').write_text(json.dumps(dict(kernel_release=release, boot_sha256=sha,
    kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(), lk2nd_sha256=hashlib.sha256(lk).hexdigest(),
    initramfs=False, modules={name:hashlib.sha256(data).hexdigest() for name,data in modules.items()},
    package=package.name, package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2)+'\n')
print(package.name, sha)
