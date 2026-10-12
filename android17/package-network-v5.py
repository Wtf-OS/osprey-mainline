from pathlib import Path
import hashlib, io, json, subprocess, zipfile
base = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey/android17-port')
root = Path('/home/debian/osprey-port/lineage')
source = root/'out/target/product/osprey/system/apex/com.android.tethering.capex'
before = base/'first-boot/tethering-before-v5.capex'
def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
with zipfile.ZipFile(source) as new, zipfile.ZipFile(before) as old:
    assert new.read('apex_pubkey') == old.read('apex_pubkey'), 'APEX signing key changed'
    # CAPEX adds the original payload digest to its outer manifest.
    with zipfile.ZipFile(io.BytesIO(new.read('original_apex'))) as new_apex, zipfile.ZipFile(io.BytesIO(old.read('original_apex'))) as old_apex:
        assert new_apex.read('apex_manifest.pb') == old_apex.read('apex_manifest.pb'), 'APEX identity changed'
old_sha, new_sha = digest(before), digest(source)
script = '''#!/sbin/sh
set -eu
OUTFD="$2"
ZIP="$3"
ui() { echo "ui_print $*" > /proc/self/fd/$OUTFD; echo ui_print > /proc/self/fd/$OUTFD; }
[ "$(getprop ro.product.device)" = osprey ] || exit 1
mkdir -p /system_root
if ! grep -q ' /system_root ' /proc/mounts; then mount -t ext4 /dev/block/mmcblk0p41 /system_root; fi
mount -o remount,rw /system_root
grep -qx 'ro.build.version.sdk=37' /system_root/system/build.prop || exit 1
TARGET=/system_root/system/apex/com.android.tethering.capex
[ ! -L "$TARGET" ] && [ "$(sha256sum "$TARGET" | cut -d ' ' -f 1)" = OLD_SHA ] || exit 1
unzip -p "$ZIP" com.android.tethering.capex > "$TARGET.new"
[ "$(sha256sum "$TARGET.new" | cut -d ' ' -f 1)" = NEW_SHA ] || exit 1
chmod 0644 "$TARGET.new"
chown 0:0 "$TARGET.new"
chcon u:object_r:system_file:s0 "$TARGET.new"
mv -f "$TARGET.new" "$TARGET"
CACHE=/data/apex/decompressed/com.android.tethering@370399999.decompressed.apex
[ ! -L "$CACHE" ] || exit 1
rm -f "$CACHE"
sync
ui 'Osprey compat getsockopt test corrected; BPF loading and filters remain required'
'''.replace('OLD_SHA',old_sha).replace('NEW_SHA',new_sha)
script_file = base/'package/v5-update-binary'
script_file.write_text(script)
subprocess.run(['bash', '-n', str(script_file)], check=True)
package=base/'package/osprey-a17-v5-netd-compat.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    info=zipfile.ZipInfo('META-INF/com/google/android/update-binary');info.external_attr=0o100755<<16
    z.writestr(info,script);z.writestr('META-INF/com/google/android/updater-script','# Shell installer\n')
    z.write(source,'com.android.tethering.capex')
with zipfile.ZipFile(package) as z: assert z.testzip() is None
(base/'package/network-v5-manifest.json').write_text(json.dumps(dict(old_capex_sha256=old_sha,new_capex_sha256=new_sha,zip_sha256=digest(package),kernel_unchanged=True,bpf_required=True),indent=2)+'\n')
print(package.name,package.stat().st_size,new_sha)
