from pathlib import Path
import hashlib
import json
import zipfile

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
product = Path('/home/debian/osprey-port/lineage/out/target/product/osprey')
old_apex = out / 'tethering-v10.capex'
new_apex = product / 'system/apex/com.android.tethering.capex'
with zipfile.ZipFile(old_apex) as old, zipfile.ZipFile(new_apex) as new:
    assert old.read('apex_pubkey') == new.read('apex_pubkey'), 'APEX signing key changed'
original_props = (out / 'vendor-v10.build.prop').read_bytes()
assert b'ro.board.first_api_level=' not in original_props
assert b'ro.vendor.osprey.mainline_bpf_compat=' not in original_props
props = original_props + b'\n# Experimental osprey mainline ARM32 kernel upgrade.\nro.board.first_api_level=22\nro.vendor.osprey.mainline_bpf_compat=1\n'
assets = {
    'system/apex/com.android.tethering.capex': (old_apex.read_bytes(), new_apex.read_bytes()),
    'system/vendor/build.prop': (original_props, props),
}
assert assets['system/apex/com.android.tethering.capex'][0] != assets['system/apex/com.android.tethering.capex'][1], 'APEX not rebuilt'
checksums = {name: {'before': hashlib.sha256(old).hexdigest(), 'after': hashlib.sha256(new).hexdigest()} for name, (old, new) in assets.items()}
script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v11-assets
ROOT=/tmp/osprey-a16-v11-root
cleanup() { umount "$ROOT" 2>/dev/null || true; }
trap cleanup EXIT
[ ! -L "$WORK" ] && [ ! -L "$ROOT" ]
mkdir -p "$WORK" "$ROOT"
'''
for name, hashes in checksums.items():
    script += f'''mkdir -p "$WORK/$(dirname {name})"
unzip -p "$ZIP" files/{name} > "$WORK/{name}"
[ "$(sha256sum "$WORK/{name}" | cut -d ' ' -f 1)" = {hashes['after']} ]
'''
script += 'mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"\n'
for name, hashes in checksums.items():
    script += f'[ "$(sha256sum "$ROOT/{name}" | cut -d \' \' -f 1)" = {hashes["before"]} ]\n'
for name, hashes in checksums.items():
    script += f'''cat "$WORK/{name}" > "$ROOT/{name}"
[ "$(sha256sum "$ROOT/{name}" | cut -d ' ' -f 1)" = {hashes['after']} ]
'''
script += '''sync
umount "$ROOT"
echo 'Osprey ARM32 NetBpfLoad compatibility installed; BPF loading and error checks preserved; Data and boot unchanged'
'''
package = out / 'osprey-a16-v11-bpf-loader.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, (_, data) in assets.items():
        z.writestr('files/' + name, data)
(out / 'bpf-loader-manifest.json').write_text(json.dumps(dict(package=package.name, files=checksums,
    package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, package.stat().st_size)
