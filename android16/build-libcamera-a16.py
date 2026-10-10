from pathlib import Path
import os,subprocess
r=Path('/home/debian/osprey-port');s=Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey/android16-port/package')
a=r/'lineage';ndk=r/'android-ndk-r27d/toolchains/llvm/prebuilt/linux-x86_64/bin';prefix=r/'libcamera-install-arm';pc=prefix/'lib/pkgconfig';pc.mkdir(parents=True,exist_ok=True)
libs=a/'out/target/product/osprey/system/lib'
for name,lib,inc,version in [('libexif','exif',a/'external/libexif','0.6.24'),('libjpeg','jpeg',a/'external/libjpeg-turbo','3.0.0'),('libyuv','yuv',a/'external/libyuv/files/include','1.0'),('libhardware','hardware',a/'hardware/libhardware/include_all','1.0')]:
 if name=='libyuv' and not inc.exists(): inc=a/'external/libyuv/include'
 (pc/(name+'.pc')).write_text(f'Name: {name}\nDescription: Android platform {name}\nVersion: {version}\nLibs: -L{libs} -l{lib}\nCflags: -I{inc} -I{a}/external/minigbm/cros_gralloc\n')
cross=r/'libcamera-arm32.cross';cross.write_text(f'''[binaries]
c = '{ndk}/armv7a-linux-androideabi35-clang'
cpp = '{ndk}/armv7a-linux-androideabi35-clang++'
ar = '{ndk}/llvm-ar'
strip = '{ndk}/llvm-strip'
pkg-config = '/usr/bin/pkg-config'
[host_machine]
system = 'android'
cpu_family = 'arm'
cpu = 'armv7'
endian = 'little'
[built-in options]
cpp_link_args = ['-static-libstdc++']
[properties]
needs_exe_wrapper = true
pkg_config_libdir = '{pc}'
''')
env=dict(os.environ,PATH=str(r/'mesa-tools/bin')+':'+str(a/'prebuilts/build-tools/linux-x86/bin')+':'+os.environ['PATH'],PKG_CONFIG_LIBDIR=str(pc))
b=r/'libcamera-a16-build-arm'
with (s/'build-libcamera-a16.log').open('w') as log:
 def run(args):
  print('Running:', ' '.join(map(str,args)),flush=True)
  subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 if not (b/'build.ninja').exists():
  run(['meson','setup',str(b),str(r/'libcamera-osprey'),'--cross-file',str(cross),'--prefix','/vendor','--libexecdir','bin','--libdir','lib','-Dbuildtype=release','-Dauto_features=disabled','-Dandroid=enabled','-Dandroid_platform=generic','-Dpipelines=simple','-Dipas=softisp','-Dcam=disabled','-Dsoftisp-gpu=disabled','-Dtest=false'])
 run(['meson','configure',str(b),'--prefix','/vendor','--libexecdir','bin','-Dcpp_args=-I'+str(a/'external/minigbm/cros_gralloc')])
 run(['meson','compile','-C',str(b),'-j','8'])
 run(['meson','install','-C',str(b),'--destdir',str(r/'libcamera-a16-stage')])
print('libcamera Android HAL built into',prefix)

# Keep the product prebuilts in sync with the source build and IPA signature.
import shutil
camera = a / 'device/motorola/msm8916-common/mainline-camera'
for rel in ['lib/libcamera.so', 'lib/libcamera-base.so', 'lib/libcamera-hal.so', 'lib/libcamera/ipa/ipa_softisp.so', 'bin/libcamera/softisp_ipa_proxy']:
    source = r / 'libcamera-a16-stage/vendor' / rel
    assert source.read_bytes()[:5] == b'\x7fELF\x01'
    shutil.copy2(source, camera / 'prebuilt' / source.name)
for rel in ['lib/libcamera/ipa/ipa_softisp.so.sign', 'share/libcamera/ipa/softisp/s5k3m2.yaml', 'share/libcamera/ipa/softisp/uncalibrated.yaml']:
    source = r / 'libcamera-a16-stage/vendor' / rel
    shutil.copy2(source, camera / source.name)
