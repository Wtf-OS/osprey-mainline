from pathlib import Path
import hashlib
import json
import zipfile

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
product = Path('/home/debian/osprey-port/lineage/out/target/product/osprey/system')
paths = ['framework/services.jar', 'framework/services.jar.prof'] + [f'framework/oat/arm/services.{ext}' for ext in ['art', 'odex', 'vdex']]
old = {name: (out / 'services-before-v30' / Path(name).name).read_bytes() for name in paths}
new = {name: (product / name).read_bytes() for name in paths}

def digest(data):
    return hashlib.sha256(data).hexdigest()

assert digest(old[paths[0]]) == '1a68a44294f5f8f0dc126948321957eade1a4e375cec6e26ca0d77192f794a04'
assert new[paths[0]] != old[paths[0]]
assert all(new.values())
with zipfile.ZipFile(product / paths[0]) as jar:
    assert 'classes.dex' in jar.namelist()

def package(name, files, before):
    script = '''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-v30-assets
ROOT=/tmp/osprey-v30-root
trap 'umount "$ROOT" 2>/dev/null || true' EXIT
[ "$(getprop ro.product.device)" = osprey ]
[ ! -L "$WORK" ] && [ ! -L "$ROOT" ]
mkdir -p "$WORK" "$ROOT"
'''
    for path, data in files.items():
        script += f'''mkdir -p "$WORK/$(dirname {path})"
unzip -p "$ZIP" files/{path} > "$WORK/{path}"
[ "$(sha256sum "$WORK/{path}" | cut -d ' ' -f 1)" = {digest(data)} ]
'''
    script += 'mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"\n'
    for path in files:
        script += f'''[ ! -L "$ROOT/system/{path}" ]
[ "$(sha256sum "$ROOT/system/{path}" | cut -d ' ' -f 1)" = {digest(before[path])} ]
'''
    for path, data in files.items():
        script += f'''cat "$WORK/{path}" > "$ROOT/system/{path}.new"
chmod 0644 "$ROOT/system/{path}.new"
chown 0:0 "$ROOT/system/{path}.new"
chcon u:object_r:system_file:s0 "$ROOT/system/{path}.new"
mv "$ROOT/system/{path}.new" "$ROOT/system/{path}"
[ "$(sha256sum "$ROOT/system/{path}" | cut -d ' ' -f 1)" = {digest(data)} ]
'''
    script += 'sync\numount "$ROOT"\necho "Services and preoptimization verified; Data and boot unchanged"\n'
    target = out / name
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
        info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
        info.external_attr = 0o100755 << 16
        archive.writestr(info, script)
        archive.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
        for path, data in files.items():
            archive.writestr('files/' + path, data)
    manifest = dict(package=name, package_sha256=digest(target.read_bytes()),
                    files={path: digest(data) for path, data in files.items()})
    target.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(name, target.stat().st_size)

package('osprey-a16-v30-bt-stats.zip', new, old)
package('osprey-a16-v30-bt-stats-rollback.zip', old, new)
