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
original = (out / 'hardware-v14.sh').read_bytes()
updated = (tree / 'device/motorola/msm8916-common/mainline-boot/osprey-hardware.sh').read_bytes()
assert original.count(b'for name in btqca btqcomsmd xt_policy') == 1
assert updated == original.replace(b'for name in btqca btqcomsmd xt_policy', b'for name in af_key btqca btqcomsmd xt_policy')
module = (tree / 'device/motorola/msm8916-common/mainline-boot/modules/af_key.ko').read_bytes()
release = Path('/home/debian/osprey-port/mainline-a16-out/include/config/kernel.release').read_text().strip()
assert module[:5] == b'\x7fELF\x02' and (b'vermagic=' + release.encode() + b' ') in module
files = {'bin/osprey-hardware.sh': updated, 'lib/modules/af_key.ko': module}
before = {'bin/osprey-hardware.sh': hashlib.sha256(original).hexdigest()}
checksums = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
assert all(re.fullmatch(r'[A-Za-z0-9_./@+-]+', name) and '..' not in name for name in files)
script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v15-assets
ROOT=/tmp/osprey-a16-v15-root
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
boot_sha = json.loads((out / 'kernel-fix-manifest.json').read_text())['boot_sha256']
script += f'[ "$(sha256sum /dev/block/mmcblk0p31 | cut -d \' \' -f 1)" = {boot_sha} ]\n'
script += 'mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"\n'
for name in files:
    if name in before:
        script += f'[ "$(sha256sum "$ROOT/system/vendor/{name}" | cut -d \' \' -f 1)" = {before[name]} ]\n'
    else:
        script += f'[ ! -e "$ROOT/system/vendor/{name}" ] && [ ! -L "$ROOT/system/vendor/{name}" ]\n'
for name, sha in checksums.items():
    label = 'vendor_file' if name.startswith(('lib/', 'bin/')) or name == 'build.prop' else 'vendor_configs_file'
    mode = '0755' if name.startswith('bin/') else '0644'
    group = 2000 if name.startswith('bin/') else 0
    script += f'''mkdir -p "$ROOT/system/vendor/$(dirname {name})"
cat "$WORK/{name}" > "$ROOT/system/vendor/{name}"
chmod {mode} "$ROOT/system/vendor/{name}"
chown 0:{group} "$ROOT/system/vendor/{name}"
chcon u:object_r:{label}:s0 "$ROOT/system/vendor/{name}"
[ "$(sha256sum "$ROOT/system/vendor/{name}" | cut -d ' ' -f 1)" = {sha} ]
'''
script += '''sync
umount "$ROOT"
echo 'PF_KEY module and early loading verified; Data and boot unchanged'
'''
package = out / 'osprey-a16-v15-pfkey.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, data in files.items():
        z.writestr('files/' + name, data)
(out / 'pfkey-v15-manifest.json').write_text(json.dumps(dict(package=package.name, files=checksums,
    package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, len(files), package.stat().st_size)
