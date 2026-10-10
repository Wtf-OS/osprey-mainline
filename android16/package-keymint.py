from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
tree = Path('/home/debian/osprey-port/lineage')
product = tree / 'out/target/product/osprey'
vendor = product / 'system/vendor'
readelf = tree / 'prebuilts/clang/host/linux-x86/clang-r574158/bin/llvm-readelf'
before = {}
for line in (out / 'vendor-before-keymint.sha256').read_text(encoding='utf-8-sig').splitlines():
    sha, path = line.split(None, 1)
    before[Path(path.strip()).name] = sha

service = 'android.hardware.security.keymint-service'
files = {
    'bin/hw/' + service: vendor / 'bin/hw' / service,
    'etc/init/' + service + '.rc': vendor / 'etc/init' / (service + '.rc'),
}
for fragment in ['keymint', 'sharedsecret', 'secureclock']:
    name = 'android.hardware.security.' + fragment + '-service.xml'
    files['etc/vintf/manifest/' + name] = vendor / 'etc/vintf/manifest' / name

queue = [files['bin/hw/' + service]]
seen = set()
while queue:
    elf = queue.pop()
    if elf in seen:
        continue
    seen.add(elf)
    header = elf.read_bytes()[:5]
    assert header == b'\x7fELF\x01', (elf, 'Expected ARM32 ELF')
    result = subprocess.run([str(readelf), '-d', str(elf)], check=True, text=True, capture_output=True)
    for name in re.findall(r'\(NEEDED\).*?\[(.*?)\]', result.stdout):
        library = vendor / 'lib' / name
        if library.exists():
            queue.append(library)
            sha = hashlib.sha256(library.read_bytes()).hexdigest()
            if name in before:
                assert before[name] == sha, (name, 'Existing library differs; review before replacing')
            else:
                files['lib/' + name] = library
        else:
            # LLNDK libraries are provided by system or the runtime APEX.
            assert (product / 'system/lib' / name).exists() or name in ['libc.so', 'libm.so', 'libdl.so'], name

assets = {name: path.read_bytes() for name, path in files.items()}
checksums = {name: hashlib.sha256(data).hexdigest() for name, data in assets.items()}
assert all(re.fullmatch(r'[A-Za-z0-9_./@+-]+', name) and '..' not in name for name in assets)
script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v10-assets
ROOT=/tmp/osprey-a16-v10-root
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
for name in assets:
    script += f'[ ! -e "$ROOT/system/vendor/{name}" ] && [ ! -L "$ROOT/system/vendor/{name}" ]\n'
for name, sha in checksums.items():
    mode = '0755' if name.startswith('bin/') else '0644'
    label = 'hal_keymint_default_exec' if name.startswith('bin/') else ('vendor_file' if name.startswith('lib/') else 'vendor_configs_file')
    script += f'''mkdir -p "$ROOT/system/vendor/$(dirname {name})"
cat "$WORK/{name}" > "$ROOT/system/vendor/{name}"
chmod {mode} "$ROOT/system/vendor/{name}"
chown 0:0 "$ROOT/system/vendor/{name}"
chcon u:object_r:{label}:s0 "$ROOT/system/vendor/{name}"
[ "$(sha256sum "$ROOT/system/vendor/{name}" | cut -d ' ' -f 1)" = {sha} ]
'''
script += '''sync
umount "$ROOT"
echo 'Software-only AOSP KeyMint installed and verified; no TEE protection; Data and boot unchanged'
'''
package = out / 'osprey-a16-v10-keymint.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, data in assets.items():
        z.writestr('files/' + name, data)
(out / 'keymint-manifest.json').write_text(json.dumps(dict(package=package.name,
    software_only=True, tee_protection=False, files=checksums,
    package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, len(assets), package.stat().st_size)
