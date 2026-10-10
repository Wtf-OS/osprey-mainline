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
source = tree / 'device/motorola/msm8916-common/mainline-camera/media_profiles_V1_0.xml'
import xml.etree.ElementTree as ET
assert {c.get('cameraId') for c in ET.parse(source).getroot().findall('CamcorderProfiles')} == {'0', '1'}
files = {'etc/media_profiles_V1_0.xml': source.read_bytes()}
before = {}
checksums = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
assert all(re.fullmatch(r'[A-Za-z0-9_./@+-]+', name) and '..' not in name for name in files)
script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v26-assets
ROOT=/tmp/osprey-a16-v26-root
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
echo 'Camera media profiles installed and verified; Data and boot unchanged'
'''
package = out / 'osprey-a16-v26-camera-profiles.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, data in files.items():
        z.writestr('files/' + name, data)
(out / 'camera-profiles-v26-manifest.json').write_text(json.dumps(dict(package=package.name, files=checksums,
    package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, len(files), package.stat().st_size)
