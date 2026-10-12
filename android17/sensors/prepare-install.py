from pathlib import Path
import hashlib
import json
import shutil
import zipfile

p = Path(__file__).parent
tree = Path('/home/debian/osprey-port/lineage')
common = tree / 'device/motorola/msm8916-common'
product = tree / 'out/target/product/osprey'
receipt = json.loads((p/'manifest.json').read_text())
assets = p/'assets'
before = (p/'hardware-before.sh').read_text()
current = (common/'mainline-boot/osprey-hardware.sh').read_text()
assert current.split('\n# Optional during bring-up:')[0].rstrip() == before.rstrip(), 'Unrelated hardware script changes'
def sha(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()
sources = {
    'system/vendor/bin/hw/android.hardware.sensors-service.osprey': product/'system/vendor/bin/hw/android.hardware.sensors-service.osprey',
    'system/vendor/etc/init/sensors-osprey.rc': common/'mainline-sensors/sensors-osprey.rc',
    'system/vendor/etc/vintf/manifest/sensors-osprey.xml': common/'mainline-sensors/sensors-osprey.xml',
    'system/vendor/etc/permissions/android.hardware.sensor.accelerometer.xml': tree/'frameworks/native/data/etc/android.hardware.sensor.accelerometer.xml',
    'system/vendor/etc/permissions/android.hardware.sensor.light.xml': tree/'frameworks/native/data/etc/android.hardware.sensor.light.xml',
    'system/vendor/etc/permissions/android.hardware.sensor.proximity.xml': tree/'frameworks/native/data/etc/android.hardware.sensor.proximity.xml',
    'system/vendor/lib/modules/stml0xx-accel.ko': p/'stml0xx-accel.ko',
    'system/vendor/bin/osprey-hardware.sh': common/'mainline-boot/osprey-hardware.sh',
    'system/product/overlay/OspreyMainlineFrameworkOverlay.apk': product/'system/product/overlay/OspreyMainlineFrameworkOverlay.apk',
    'boot.img': p/'boot-sensors-v5.img',
}
for module in (common/'mainline-boot/modules').glob('*.ko'):
    sources.setdefault('system/vendor/lib/modules/'+module.name, module)
for target, source in sources.items():
    assert source.is_file(), source
    path = assets/target
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, path)
assert sha(assets/'boot.img') == receipt['boot_sha256']
assert sha(assets/'system/vendor/lib/modules/stml0xx-accel.ko') == receipt['module_sha256']
manifest = {name: sha(assets/name) for name in sources}
receipt['assets'] = manifest
(p/'manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
(assets/'payload.sha256').write_text(''.join(f'{digest}  {name}\n' for name, digest in manifest.items()))
def install(root):
    lines = []
    for name in sources:
        if name == 'boot.img': continue
        destination = f'{root}/{name}'
        mode = '0755' if '/bin/' in name else '0644'
        context = 'vendor_file' if '/vendor/' in name else 'system_file'
        lines += [f'mkdir -p "{Path(destination).parent}"',
            f'cp "$WORK/{name}" "{destination}.new"',
            f'chmod {mode} "{destination}.new"', f'chown 0:0 "{destination}.new"',
            f'chcon u:object_r:{context}:s0 "{destination}.new"',
            f'mv "{destination}.new" "{destination}"']
    return '\n'.join(lines) + '\n'
guard = f'''[ "$(getprop ro.product.device)" = osprey ]
CURRENT=$(sha256sum /dev/block/mmcblk0p31 | cut -d ' ' -f1)
[ "$CURRENT" = {receipt['base_boot_sha256']} ] || [ "$CURRENT" = {receipt['boot_sha256']} ]
(cd "$WORK" && sha256sum -c payload.sha256)
'''
flash = f'''sync
dd if="$WORK/boot.img" of=/dev/block/mmcblk0p31 bs=4096
sync
[ "$(sha256sum /dev/block/mmcblk0p31 | cut -d ' ' -f1)" = {receipt['boot_sha256']} ]
'''
live = '#!/system/bin/sh\nset -eu\nWORK=/data/local/tmp/osprey-sensors-assets\n' + guard
live += '[ "$(getprop ro.build.version.sdk)" = 37 ]\n' + install('') + flash
(p/'install.sh').write_text(live)
recovery = '''#!/sbin/sh
set -eu
WORK=$(mktemp -d /tmp/osprey-sensors.XXXXXX)
trap 'umount "$WORK/root" 2>/dev/null || true; rm -rf "$WORK"' EXIT
unzip -o "$3" -d "$WORK" >/dev/null
'''+guard+'''
umount /system 2>/dev/null || true
umount /system_root 2>/dev/null || true
mkdir "$WORK/root"
mount -t ext4 -o rw /dev/block/mmcblk0p41 "$WORK/root"
grep -q '^ro.build.version.sdk=37$' "$WORK/root/system/build.prop"
'''+install('$WORK/root')+'''sync
umount "$WORK/root"
'''+flash
with zipfile.ZipFile(p/'osprey-a17-navigation-sensors-v5.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    archive.writestr(info, recovery)
    archive.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    archive.write(assets/'payload.sha256', 'payload.sha256')
    for name in sources: archive.write(assets/name, name)
print('Prepared', len(sources), 'assets and recovery ZIP')
