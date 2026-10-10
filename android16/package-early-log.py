from pathlib import Path
import hashlib
import zipfile

out = Path(__file__).resolve().parent / 'package'
original = (out / 'init.osprey-installed.rc').read_bytes()
assert original.count(b'on init\n') == 1
assert original.count(b'start osprey-early-log\n') == 1
assert b'keystore2:V' in original
updated = original.replace(b'keystore2:V', b'keystore2:W').replace(
    b'crash_dump32:V tombstoned:V', b'crash_dump32:W tombstoned:W')
updated += b'''
on post-fs-data
    start osprey-boot-log
'''
old_sha = hashlib.sha256(original).hexdigest()
new_sha = hashlib.sha256(updated).hexdigest()
script = f'''#!/sbin/sh
set -eu
ZIP="$3"
WORK=/tmp/osprey-a16-v9-assets
ROOT=/tmp/osprey-a16-v9-root
cleanup() {{ umount "$ROOT" 2>/dev/null || true; }}
trap cleanup EXIT
[ ! -L "$WORK" ] && [ ! -L "$ROOT" ]
mkdir -p "$WORK" "$ROOT"
unzip -p "$ZIP" init.osprey.rc > "$WORK/init.osprey.rc"
[ "$(sha256sum "$WORK/init.osprey.rc" | cut -d ' ' -f 1)" = {new_sha} ]
mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"
[ "$(sha256sum "$ROOT/init.osprey.rc" | cut -d ' ' -f 1)" = {old_sha} ]
cat "$WORK/init.osprey.rc" > "$ROOT/init.osprey.rc"
sync
[ "$(sha256sum "$ROOT/init.osprey.rc" | cut -d ' ' -f 1)" = {new_sha} ]
umount "$ROOT"
echo 'Early keystore log capture installed; Data and boot unchanged'
'''
# TWRP accepts a shell update-binary; retain the current file's label and mode.
package = out / 'osprey-a16-v9-early-log.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
    info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    z.writestr('init.osprey.rc', updated)
(out / 'init.osprey-early-log.rc').write_bytes(updated)
print(package, new_sha)
