from pathlib import Path
import hashlib,json,shutil,struct,zlib,subprocess
p=Path(__file__).parent;r=Path('/home/debian/osprey-port');tree=r/'lineage';common=tree/'device/motorola/msm8916-common'
sha=lambda data:hashlib.sha256(data).hexdigest()
base=(p/'boot-sensors-v4.img').read_bytes();assert sha(base)=='0a6c1282a4c8d2e0ceedc6849e1751a0df916ae1943aba493b14c0c2d068692d'
offset=512*1024;size=struct.unpack_from('<I',base,offset+8)[0];page=struct.unpack_from('<I',base,offset+36)[0]
assert struct.unpack_from('<I',base,offset+16)[0]==0
old=base[offset+page:offset+page+size];gz=zlib.decompressobj(31);gz.decompress(old);dtb=gz.unused_data
assert dtb[:4]==b'\xd0\x0d\xfe\xed'
(p/'before-suspend.dtb').write_bytes(dtb)
subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',str(p/'compass.dtbo'),str(p/'compass-overlay.dts')],check=True)
subprocess.run(['fdtoverlay','-i',str(p/'before-suspend.dtb'),'-o',str(p/'compass.dtb'),str(p/'compass.dtbo')],check=True)
subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',str(p/'display-icc.dtbo'),str(p/'display-icc-overlay.dts')],check=True)
subprocess.run(['fdtoverlay','-i',str(p/'compass.dtb'),'-o',str(p/'display-icc.dtb'),str(p/'display-icc.dtbo')],check=True)
def cells(node, prop):
    return [int(x,16) for x in subprocess.check_output(['fdtget','-t','x',str(p/'display-icc.dtb'),node,prop],text=True).split()]
snoc=cells('/soc@0/interconnect@580000','phandle')[0]
bimc=cells('/soc@0/interconnect@400000','phandle')[0]
assert cells('/soc@0/display-subsystem@1a00000/display-controller@1a01000','interconnects')==[snoc,2,bimc,6]
config=(r/'mainline-a16-out/.config').read_text();assert all(option+'\n' in config for option in ('CONFIG_SUSPEND=y','CONFIG_PM_SLEEP=y','CONFIG_INTERCONNECT_QCOM=m','CONFIG_INTERCONNECT_QCOM_MSM8916=m'))
kernel=(r/'mainline-a16-out/arch/arm64/boot/Image.gz').read_bytes()+(p/'display-icc.dtb').read_bytes()
boot=bytearray(base[:offset+page]);struct.pack_into('<I',boot,offset+8,len(kernel));boot+=kernel;assert len(boot)<=len(base);boot+=bytes(len(base)-len(boot))
boot[offset+576:offset+608]=hashlib.sha1(kernel+struct.pack('<I',len(kernel))+bytes(8)).digest()+bytes(12)
(p/'boot-sensors-v5.img').write_bytes(boot)
modules=common/'mainline-boot/modules';
for name in ('interconnect_qcom','icc-smd-rpm','qnoc-msm8916'):
    shutil.copy2(r/('mainline-a16-out/drivers/interconnect/qcom/'+name+'.ko'),modules/(name+'.ko'))
shutil.copy2(r/'mainline-a16-out/drivers/iio/magnetometer/ak8975.ko',modules/'ak8975.ko')
release=(r/'mainline-a16-out/include/config/kernel.release').read_text().strip();digests={}
for module in sorted(modules.glob('*.ko')):
    if module.name=='stml0xx-accel.ko':source=p/module.name
    elif module.name=='osprey-camera-id.ko':source=r/'osprey-camera-id-a16-build'/module.name
    else:
        matches=list((r/'mainline-a16-out').rglob(module.name));assert len(matches)==1,(module.name,matches);source=matches[0]
    data=source.read_bytes();assert b'vermagic='+release.encode()+b' ' in data,module.name
    if source!=module:shutil.copy2(source,module)
    digests[module.name]=sha(data)
helper=common/'mainline-boot/osprey-hardware.sh';s=helper.read_text()
if '\nload ak8975\n' not in s:s+='\nload ak8975\n'
helper.write_text(s)
receipt={'base_boot_sha256':sha(base),'boot_sha256':sha(boot),'module_sha256':digests['stml0xx-accel.ko'],'modules':digests,'kernel_release':release,'change':'Enable display interconnect; preserve verified sensors, suspend, lk2nd and existing DT configuration'}
(p/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
f=p/'prepare-install.py';s=f.read_text().replace('boot-sensors-v4.img','boot-sensors-v5.img').replace('osprey-a17-navigation-sensors-v4.zip','osprey-a17-navigation-sensors-v5.zip')
needle='for target, source in sources.items():'
if "sources.setdefault('system/vendor/lib/modules/'" not in s:s=s.replace(needle,"for module in (common/'mainline-boot/modules').glob('*.ko'):\n    sources.setdefault('system/vendor/lib/modules/'+module.name, module)\n"+needle)
f.write_text(s)
f=p.parent/'package.py';s=f.read_text().replace("boot-sensors-v4.img","boot-sensors-v5.img")
if "fix['modules'].update(sensors_manifest" not in s:s=s.replace("fix['modules']['stml0xx-accel.ko'] = sensors_manifest['module_sha256']", "fix['modules'].update(sensors_manifest['modules'])")
f.write_text(s)
print('prepared boot and',len(digests),'matching modules')
