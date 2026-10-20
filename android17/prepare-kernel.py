from pathlib import Path
import hashlib, json, shutil, struct, subprocess

port=Path.home()/'osprey-port'
tree=port/'lineage'
kernel=port/'mainline-a16-out'
common=tree/'device/motorola/msm8916-common'
output=common/'mainline-boot'
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

release=(kernel/'include/config/kernel.release').read_text().strip()
modules={}
module_names=json.loads((Path(__file__).resolve().parent/'kernel-modules.json').read_text())
assert module_names and len(module_names)==len(set(module_names))
(output/'modules').mkdir(parents=True,exist_ok=True)
assert not {p.name for p in (output/'modules').glob('*.ko')}-set(module_names), 'Unexpected stale kernel modules'
for name in sorted(module_names):
    assert Path(name).name==name and name.endswith('.ko')
    destination=output/'modules'/name
    candidates=list(kernel.rglob(destination.name))
    assert len(candidates)==1,(destination.name,candidates)
    source=candidates[0]
    assert b'vermagic='+release.encode()+b' ' in source.read_bytes(),destination.name
    shutil.copy2(source,destination)
    modules[destination.name]=sha(destination)
image=kernel/'arch/arm64/boot/Image.gz'
dtb=kernel/'arch/arm64/boot/dts/qcom/msm8916-motorola-osprey-mainline.dtb'
lk=port/'lk2nd-a16-out/build-lk2nd-msm8916/lk2nd.img'
assert lk.read_bytes()[:8]==b'ANDROID!' and lk.stat().st_size<=512*1024
assert dtb.read_bytes()[:4]==bytes.fromhex('d00dfeed')
assert subprocess.check_output(['fdtget',str(dtb),'/soc@0/remoteproc@4080000','status'],text=True).strip()=='okay'
assert subprocess.check_output(['fdtget',str(dtb),'/reserved-memory/ramoops@af000000','compatible'],text=True).strip()=='ramoops'
assert subprocess.check_output(['fdtget',str(dtb),'/soc@0/cci@1b0c000/i2c-bus@0/rear-camera@2d','compatible'],text=True).strip()=='samsung,s5k3m2'
payload=kernel/'Image.gz-dtb';payload.write_bytes(image.read_bytes()+dtb.read_bytes())
cmdline='root=/dev/mmcblk0p41 rootwait rootfstype=ext4 ro init=/init androidboot.hardware=osprey console=ttyMSM0,115200n8 console=tty0 loglevel=7 panic=0 cma=32M enforcing=1 selinux=1 androidboot.selinux=enforcing lk2nd.pass-simplefb=1 msm.separate_gpu_kms=1 clk_ignore_unused pd_ignore_unused regulator_ignore_unused'
inner=kernel/'boot-mainline.img'
subprocess.run(['python3',str(tree/'system/tools/mkbootimg/mkbootimg.py'),'--kernel',str(payload),
                '--header_version','0','--base','0x80000000','--kernel_offset','0x80000',
                '--tags_offset','0x1e00000','--pagesize','2048','--cmdline',cmdline,'-o',str(inner)],check=True)
data=lk.read_bytes();data+=bytes(512*1024-len(data));data+=inner.read_bytes()
assert len(data)<=16*1024*1024
data+=bytes(16*1024*1024-len(data))
assert data[524288:524296]==b'ANDROID!' and struct.unpack_from('<I',data,524288+16)[0]==0
boot=output/'boot-mainline.img';boot.write_bytes(data)
(output/'kernel-artifacts.json').write_text(json.dumps(dict(boot_sha256=sha(boot),kernel_sha256=sha(image),
    dtb_sha256=sha(dtb),lk2nd_sha256=sha(lk),kernel_release=release,modules=modules,cmdline=cmdline),indent=2)+'\n')
print('Matched kernel, DTB, lk2nd and modules prepared:',release)
