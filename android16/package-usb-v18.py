from pathlib import Path
import hashlib
import json
import re
import zipfile

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
tree = Path('/home/debian/osprey-port/lineage')
product = tree / 'out/target/product/osprey'
vendor = product / 'system/vendor'
original = (out / 'init-v17.rc').read_bytes()
updated = (tree / 'device/motorola/msm8916-common/mainline-boot/init.osprey.rc').read_bytes()
expected = original.replace(b'on init\n    start osprey-early-log\n', b'on init\n    start osprey-early-log\n    mkdir /dev/usb-ffs 0775 shell shell\n')
expected = expected.replace(b'on boot\n    setprop sys.usb.config adb\n', b'on boot\n    setprop sys.usb.configfs 1\n    setprop sys.usb.config adb\n')
assert updated == expected and updated != original
files = {'init.osprey.rc': updated}
before = {'init.osprey.rc': hashlib.sha256(original).hexdigest()}
checksums = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
assert all(re.fullmatch(r'[A-Za-z0-9_./@+-]+', name) and '..' not in name for name in files)
script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v18-assets
ROOT=/tmp/osprey-a16-v18-root
cleanup() { umount "$ROOT" 2>/dev/null || true; }
trap cleanup EXIT
[ ! -L "$WORK" ] && [ ! -L "$ROOT" ]
mkdir -p "$WORK" "$ROOT"
'''
for name, sha in checksums.items():
    script += f'''mkdir -p "$WORK/$(dirname {name})"
unzip -p "$ZIP" files/{name} > "$WORK/{name}"
[ "$(sha256sum "$WORK/{name}" | cut -d ' ' -f 1)" = {sha} ]
'''
script += 'mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"\n'
for name in files:
    if name in before:
        script += f'[ "$(sha256sum "$ROOT/{name}" | cut -d \' \' -f 1)" = {before[name]} ]\n'
    else:
        script += f'[ ! -e "$ROOT/{name}" ] && [ ! -L "$ROOT/{name}" ]\n'
for name, sha in checksums.items():
    label = 'rootfs'
    mode = '0750'
    group = 2000
    script += f'''mkdir -p "$ROOT/$(dirname {name})"
cat "$WORK/{name}" > "$ROOT/{name}"
chmod {mode} "$ROOT/{name}"
chown 0:{group} "$ROOT/{name}"
chcon u:object_r:{label}:s0 "$ROOT/{name}"
[ "$(sha256sum "$ROOT/{name}" | cut -d ' ' -f 1)" = {sha} ]
'''
script += '''sync
umount "$ROOT"
echo 'FunctionFS parent permissions and configfs init verified; Data and boot unchanged'
'''
package = out / 'osprey-a16-v18-usb-init.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, data in files.items():
        z.writestr('files/' + name, data)
(out / 'usb-v18-manifest.json').write_text(json.dumps(dict(package=package.name, files=checksums,
    package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, len(files), package.stat().st_size)
