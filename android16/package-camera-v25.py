from pathlib import Path
import hashlib, json, re, subprocess, zipfile

project = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey')
out = project / 'android16-port/package'
tree = Path('/home/debian/osprey-port/lineage')
product = tree / 'out/target/product/osprey'
vendor = product / 'system/vendor'
source = tree / 'device/motorola/msm8916-common'
readelf = tree / 'prebuilts/clang/host/linux-x86/clang-r574158/bin/llvm-readelf'
before = {}
for line in (out / 'vendor-before-camera-v25.sha256').read_text(encoding='utf-8-sig').splitlines():
    sha, path = line.split(None, 1)
    before['system/vendor/' + path.strip().split('/vendor/', 1)[1]] = sha
files = {}
seeds = ['lib/hw/libcamera-hal.so', 'lib/hw/android.hardware.camera.provider@2.4-impl.so',
         'bin/hw/android.hardware.camera.provider@2.4-service', 'lib/libcamera/ipa/ipa_softisp.so',
         'bin/libcamera/softisp_ipa_proxy']
queue = [vendor / name for name in seeds]
for name in seeds:
    files['system/vendor/' + name] = (vendor / name).read_bytes()
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
            key = 'system/vendor/lib/' + name
            data = library.read_bytes()
            if key in before and key not in files:
                assert before[key] == hashlib.sha256(data).hexdigest(), (key, 'Existing dependency changed')
            elif key not in before:
                files[key] = data
        else:
            assert (product / 'system/lib' / name).exists() or name in ['libc.so', 'libm.so', 'libdl.so'], name
for path in ['etc/libcamera/camera_hal.yaml', 'etc/vintf/manifest/camera-provider.xml']:
    files['system/vendor/' + path] = (source / 'mainline-camera' / Path(path).name).read_bytes()
for path in ['lib/libcamera/ipa/ipa_softisp.so.sign', 'share/libcamera/ipa/softisp/s5k3m2.yaml', 'share/libcamera/ipa/softisp/uncalibrated.yaml']:
    files['system/vendor/' + path] = (source / 'mainline-camera' / Path(path).name).read_bytes()
for path in ['etc/init/android.hardware.camera.provider@2.4-service.rc', 'etc/permissions/android.hardware.camera.flash-autofocus.xml', 'etc/permissions/android.hardware.camera.front.xml']:
    original = tree / 'frameworks/native/data/etc' / Path(path).name if path.startswith('etc/permissions/') else vendor / path
    files['system/vendor/' + path] = original.read_bytes()
for original, updated, target in [
    ('hardware-before-camera-v25.sh', 'osprey-hardware.sh', 'system/vendor/bin/osprey-hardware.sh'),
    ('ueventd-before-camera-v25.rc', 'ueventd.osprey.rc', 'system/vendor/etc/ueventd.rc')]:
    before[target] = hashlib.sha256((out / original).read_bytes()).hexdigest()
    files[target] = (source / 'mainline-boot' / updated).read_bytes()
appdirs = [d for d in [product / 'system/product/app/Camera2', product / 'product/app/Camera2'] if d.exists()]
assert len(appdirs) == 1, appdirs
for f in appdirs[0].rglob('*'):
    if f.is_symlink():
        target = f.readlink()
        assert str(target).startswith('/system/product/lib/'), target
        files['system/product/app/Camera2/' + str(f.relative_to(appdirs[0]))] = (product / str(target).lstrip('/')).read_bytes()
    elif f.is_file():
        files['system/product/app/Camera2/' + str(f.relative_to(appdirs[0]))] = f.read_bytes()
assert any(name.endswith('Camera2.apk') for name in files)
assert all('system/product/app/Camera2/lib/arm/' + name in files for name in ['libjni_tinyplanet.so', 'libjni_jpegutil.so'])
alias = 'system/vendor/lib/hw/camera.osprey.so'
checksums = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
assert all(re.fullmatch(r'[A-Za-z0-9_./@+-]+', name) and '..' not in name for name in files)
script = '#!/sbin/sh\nset -eu\nZIP="$3"\nWORK=/tmp/osprey-a16-v25-assets\nROOT=/tmp/osprey-a16-v25-root\ntrap \'umount "$ROOT" 2>/dev/null || true\' EXIT\n[ "$(getprop ro.product.device)" = osprey ]\n[ ! -L "$WORK" ] && [ ! -L "$ROOT" ]\nmkdir -p "$WORK" "$ROOT"\n'
for name, sha in checksums.items():
    script += f'mkdir -p "$WORK/$(dirname {name})"\nunzip -p "$ZIP" files/{name} > "$WORK/{name}"\n[ "$(sha256sum "$WORK/{name}" | cut -d " " -f 1)" = {sha} ]\n'
script += 'mount -t ext4 /dev/block/mmcblk0p41 "$ROOT"\n'
for name in files:
    if name in before:
        script += f'[ "$(sha256sum "$ROOT/{name}" | cut -d " " -f 1)" = {before[name]} ]\n'
    else:
        script += f'[ ! -e "$ROOT/{name}" ] && [ ! -L "$ROOT/{name}" ]\n'
script += f'[ ! -e "$ROOT/{alias}" ] && [ ! -L "$ROOT/{alias}" ]\n'
for name, sha in checksums.items():
    mode = '0755' if '/bin/' in name else '0644'
    group = 2000 if mode == '0755' else 0
    label = 'vendor_configs_file' if name.startswith('system/vendor/etc/') else 'vendor_file' if name.startswith('system/vendor/') else 'system_file'
    script += f'mkdir -p "$ROOT/$(dirname {name})"\ncat "$WORK/{name}" > "$ROOT/{name}.new"\nchmod {mode} "$ROOT/{name}.new"\nchown 0:{group} "$ROOT/{name}.new"\nchcon u:object_r:{label}:s0 "$ROOT/{name}.new"\nmv "$ROOT/{name}.new" "$ROOT/{name}"\n[ "$(sha256sum "$ROOT/{name}" | cut -d " " -f 1)" = {sha} ]\n'
script += f'ln -s libcamera-hal.so "$ROOT/{alias}"\n[ "$(readlink "$ROOT/{alias}")" = libcamera-hal.so ]\nsync\numount "$ROOT"\necho "Camera2, A16 provider and calibrated libcamera installed; Data and boot preserved"\n'
package = out / 'osprey-a16-v25-camera.zip'
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as z:
    info = zipfile.ZipInfo('META-INF/com/google/android/update-binary'); info.external_attr = 0o100755 << 16
    z.writestr(info, script)
    z.writestr('META-INF/com/google/android/updater-script', '# Shell installer\n')
    for name, data in files.items():
        z.writestr('files/' + name, data)
(out / 'camera-v25-manifest.json').write_text(json.dumps(dict(package=package.name, files=checksums, package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=2) + '\n')
print(package.name, len(files), package.stat().st_size)
