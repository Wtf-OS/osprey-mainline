from pathlib import Path
import gzip, struct, hashlib, sys

s = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey/mainline-probe')
scheduling = '--scheduling' in sys.argv[1:]
tethering = '--tethering' in sys.argv[1:]
assert not tethering or scheduling
boot = (s / 'boot-mainline-android-v49-camera-video.img').read_bytes()
assert boot[:8] == b'ANDROID!'
ks, rs = struct.unpack_from('<I', boot, 8)[0], struct.unpack_from('<I', boot, 16)[0]
page = struct.unpack_from('<I', boot, 36)[0]
assert page == 2048 and struct.unpack_from('<I', boot, 24)[0] == 0
align = lambda n: (n + page - 1) // page * page
kernel = boot[page:page + ks]
off = page + align(ks)
raw = gzip.decompress(boot[off:off + rs])
result = bytearray()
pos = 0
changed = set()
while pos + 110 <= len(raw):
    h = raw[pos:pos + 110]
    assert h[:6] == b'070701'
    fields = [int(h[6 + i * 8:14 + i * 8], 16) for i in range(13)]
    ns, fs = fields[11], fields[6]
    name = raw[pos + 110:pos + 110 + ns]
    start = (pos + 110 + ns + 3) & ~3
    end = start + fs
    body = raw[start:end]
    label = name.rstrip(b'\0').decode().removeprefix('./')
    if tethering and b'probe-disable-tethering' in body:
        body = body.replace(b'probe-disable-tethering', b'probe-enable-tethering')
        body = body.replace(b'package disable-user --user 0 com.android.networkstack.tethering', b'package enable --user 0 com.android.networkstack.tethering')
        changed.add('tethering ' + label)
    if scheduling and b'socket adbd stream 0660 system system' in body:
        assert body.count(b'socket adbd stream 0660 system system') == 1
        body = body.replace(b'socket adbd stream 0660 system system', b'socket adbd seqpacket 0660 system system')
        changed.add('adbd seqpacket')
    if label == 'mainline-vendor-manifest.xml':
        body = (s / 'bluetooth-vendor-manifest.xml').read_bytes()
        changed.add(label)
    if label == 'systemserver-probe.rc':
        body += b'''
service mainline-bluetooth /data/bluetooth-runtime/android.hardware.bluetooth-service.default
    class hal
    user bluetooth
    group bluetooth
    capabilities NET_ADMIN NET_RAW BLOCK_SUSPEND SYS_NICE
    seclabel u:r:hal_bluetooth_default:s0
    interface aidl android.hardware.bluetooth.IBluetoothHci/default
    setenv LD_LIBRARY_PATH /data/bluetooth-runtime:/system/lib:/system/lib/bootstrap:/data/graphics-libs:/vendor/lib
    disabled
    stdio_to_kmsg
'''
        changed.add(label)
    fields[6] = len(body)
    result += h[:6] + ''.join(f'{v:08x}' for v in fields).encode() + name
    result += b'\0' * (-len(result) % 4)
    result += body
    result += b'\0' * (-len(result) % 4)
    pos = (end + 3) & ~3
    if label == 'TRAILER!!!':
        break
expected = {'mainline-vendor-manifest.xml', 'systemserver-probe.rc'}
if scheduling:
    expected.add('adbd seqpacket')
if tethering:
    expected.update({'tethering mainline-init.rc', 'tethering systemserver-probe.rc'})
assert changed == expected, changed
result += b'\0' * (-len(result) % 512)
ramdisk = gzip.compress(bytes(result), mtime=0)
header = bytearray(boot[:page])
struct.pack_into('<I', header, 16, len(ramdisk))
header[576:608] = hashlib.sha1(kernel + struct.pack('<I', ks) + ramdisk + struct.pack('<I', len(ramdisk)) + struct.pack('<I', 0)).digest() + b'\0' * 12
new = header + kernel + b'\0' * (align(ks) - ks) + ramdisk + b'\0' * (align(len(ramdisk)) - len(ramdisk))
(s / ('boot-mainline-android-v52-tethering.img' if tethering else 'boot-mainline-android-v51-scheduling.img' if scheduling else 'boot-mainline-android-v50-bluetooth.img')).write_bytes(new)
print('Bluetooth boot:', len(new), hashlib.sha256(new).hexdigest())
