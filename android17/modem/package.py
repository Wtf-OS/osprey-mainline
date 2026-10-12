from pathlib import Path
import hashlib, json, zipfile

p = Path(__file__).resolve().parent
m = json.loads((p/'v7-manifest.json').read_text())
def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
assert sha(p/'boot-a17-modem-v7.img') == m['modem_boot_sha256']
assert sha(p/'boot-before-v7.img') == m['base_boot_sha256']
for name, expected in m['assets'].items():
    assert sha(p/'assets'/name) == expected, name

header = '''#!/sbin/sh
set -eu
ui() { echo "ui_print $*" > /proc/self/fd/$2; }
[ "$(getprop ro.product.device)" = osprey ]
[ "$(cat /sys/class/block/mmcblk0p31/size)" = 32768 ]
WORK=$(mktemp -d /tmp/osprey-modem.XXXXXX)
trap 'umount "$WORK/root" 2>/dev/null || true; rm -rf "$WORK"' EXIT
unzip -o "$3" -d "$WORK" >/dev/null
(cd "$WORK" && sha256sum -c payload.sha256)
CURRENT=$(sha256sum /dev/block/mmcblk0p31 | cut -d ' ' -f1)
'''
header += f'[ "$CURRENT" = {m["base_boot_sha256"]} ] || [ "$CURRENT" = {m["modem_boot_sha256"]} ]\n'
install = header + '''
umount /system 2>/dev/null || true
umount /system_root 2>/dev/null || true
mkdir "$WORK/root"
mount -t ext4 -o rw /dev/block/mmcblk0p41 "$WORK/root"
grep -q '^ro.build.version.sdk=37$' "$WORK/root/system/build.prop"
'''
for name in m['assets']:
    mode = '0755' if '/bin/' in name else '0644'
    install += f'mkdir -p "$WORK/root/{Path(name).parent.as_posix()}"\n'
    install += f'cp "$WORK/{name}" "$WORK/root/{name}.new"\nchmod {mode} "$WORK/root/{name}.new"\nchown 0:0 "$WORK/root/{name}.new"\nchcon u:object_r:vendor_file:s0 "$WORK/root/{name}.new"\nmv "$WORK/root/{name}.new" "$WORK/root/{name}"\n'
install += '''sync
umount "$WORK/root"
dd if="$WORK/boot.img" of=/dev/block/mmcblk0p31 bs=4096
sync
'''
install += f'[ "$(sha256sum /dev/block/mmcblk0p31 | cut -d \' \' -f1)" = {m["modem_boot_sha256"]} ]\n'
rollback = header + '''
dd if="$WORK/boot.img" of=/dev/block/mmcblk0p31 bs=4096
sync
'''
rollback += f'[ "$(sha256sum /dev/block/mmcblk0p31 | cut -d \' \' -f1)" = {m["base_boot_sha256"]} ]\n'
# The old DT disables MPSS; modem service cannot access EFS or start it.
for filename, script, boot, assets in [
    ('osprey-a17-modem-v7.zip', install, 'boot-a17-modem-v7.img', True),
    ('osprey-a17-modem-v7-disable.zip', rollback, 'boot-before-v7.img', False),
]:
    entries = {'boot.img': p/boot}
    if assets:
        entries.update({name: p/'assets'/name for name in m['assets']})
    with zipfile.ZipFile(p/filename, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
        info = zipfile.ZipInfo('META-INF/com/google/android/update-binary')
        info.external_attr = 0o100755 << 16
        z.writestr(info, script)
        z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
        z.writestr('payload.sha256', ''.join(f'{sha(path)}  {name}\n' for name, path in entries.items()))
        for name, path in entries.items():
            z.write(path, name)
    print(filename, sha(p/filename))
