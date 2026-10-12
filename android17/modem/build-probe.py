from pathlib import Path
import hashlib, json, struct, subprocess, zlib
p = Path(__file__).resolve().parent
b = (p.parent / 'package/boot.img').read_bytes()
off = 512*1024
size = struct.unpack_from('<I', b, off+8)[0]
page = struct.unpack_from('<I', b, off+36)[0]
assert b[off:off+8] == b'ANDROID!' and len(b) == 16*1024*1024
assert struct.unpack_from('<I', b, off+16)[0] == 0 and struct.unpack_from('<I', b, off+24)[0] == 0
k = b[off+page:off+page+size]
gz = zlib.decompressobj(31)
gz.decompress(k)
old = gz.unused_data
assert old[:4] == bytes.fromhex('d00dfeed')
s = (p/'current.dts').read_text()
start = s.index('remoteproc@4080000 {')
end = s.index('mba {', start)
block = s[start:end]
assert block.count('status = "disabled";') == 1
s = s[:start] + block.replace('status = "disabled";', 'status = "okay";') + s[end:]
(p/'modem-enabled.dts').write_text(s)
dtc = '/home/debian/osprey-port/mainline-a16-out/scripts/dtc/dtc'
subprocess.run([dtc,'-I','dts','-O','dtb','-o',str(p/'modem-enabled.dtb'),str(p/'modem-enabled.dts')],check=True,stderr=subprocess.DEVNULL)
newdt = (p/'modem-enabled.dtb').read_bytes()
newk = k[:-len(old)] + newdt
assert newk[:-len(newdt)] == k[:-len(old)]
out = bytearray(b[:off+page])
struct.pack_into('<I', out, off+8, len(newk))
out += newk
assert len(out) <= len(b)
out += bytes(len(b)-len(out))
h = hashlib.sha1(newk + struct.pack('<I',len(newk)) + struct.pack('<I',0)*2).digest()
out[off+576:off+608] = h + bytes(12)
(p/'boot-a17-modem-v7.img').write_bytes(out)
for n in ['qcom_q6v5','qcom_q6v5_mss']:
    src = Path('/home/debian/osprey-port/mainline-a16-out/drivers/remoteproc')/(n+'.ko')
    data = src.read_bytes()
    assert b'vermagic=7.0.0-osprey-mainline-probe-gbf7b3b6c6694-dirty ' in data
    (p/(n+'.ko')).write_bytes(data)
m = {'base_boot_sha256':hashlib.sha256(b).hexdigest(),'modem_boot_sha256':hashlib.sha256(out).hexdigest(),'change':'MPSS status disabled -> okay; identical compressed kernel and lk2nd','storage':'rmtfs read-only shadow mode; no EFS writes'}
(p/'v7-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps(m,indent=2))
