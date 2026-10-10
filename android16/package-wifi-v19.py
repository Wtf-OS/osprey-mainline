from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
tree = Path('/home/debian/osprey-port/lineage')
product = tree / 'out/target/product/osprey'
vendor = product / 'system/vendor'
readelf = tree / 'prebuilts/clang/host/linux-x86/clang-r574158/bin/llvm-readelf'
before = {}
for line in (out / 'vendor-before-v19.sha256').read_text(encoding='utf-8-sig').splitlines():
    sha, path = line.split(None, 1)
    before[path.strip().split('/vendor/', 1)[1]] = sha
seeds = ['lib/libwifi-hal.so']
files = {name: (vendor / name).read_bytes() for name in seeds}
queue = [vendor / name for name in seeds]
seen = set()
while queue:
    elf = queue.pop()
    if elf in seen:
        continue
    seen.add(elf)
    assert elf.read_bytes()[:5] == b'\x7fELF\x01', elf
    result = subprocess.run([str(readelf), '-d', str(elf)], check=True, text=True, capture_output=True)
    for name in re.findall(r'\(NEEDED\).*?\[(.*?)\]', result.stdout):
        library = vendor / 'lib' / name
        if library.exists():
            queue.append(library)
            path = 'lib/' + name
            data = library.read_bytes()
            if path in before and path not in seeds:
                assert before[path] == hashlib.sha256(data).hexdigest(), (path, 'Unrelated dependency changed')
            elif path not in before:
                files[path] = data
        else:
            assert (product / 'system/lib' / name).exists() or name in ['libc.so', 'libm.so', 'libdl.so'], name
checksums = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
assert all(re.fullmatch(r'[A-Za-z0-9_./@+-]+', name) and '..' not in name for name in files)
script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v19-assets
ROOT=/tmp/osprey-a16-v19-root
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
    label = 'vendor_file' if name.startswith(('lib/', 'bin/')) else 'vendor_configs_file'
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
echo 'qcwcn Wi-Fi backend and dependencies verified; Data and boot unchanged'
'''
package = out / 'osprey-a16-v19-wifi.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, data in files.items():
        z.writestr('files/' + name, data)
(out / 'wifi-v19-manifest.json').write_text(json.dumps(dict(package=package.name, files=checksums,
    package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, len(files), package.stat().st_size)
