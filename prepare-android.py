from pathlib import Path
import subprocess, shutil, re, gzip, hashlib, json, sys
import xml.etree.ElementTree as ET

persistent_data = '--persistent-data' in sys.argv[1:]
psi_probe = '--psi' in sys.argv[1:]
diagnostic_log = '--diagnostic-log' in sys.argv[1:]
gpu_probe = '--gpu' in sys.argv[1:]
trace_probe = '--trace' in sys.argv[1:]
presentation_probe = '--presentation' in sys.argv[1:]
native_display = '--native-display' in sys.argv[1:]
wifi_probe = '--wifi' in sys.argv[1:]
wifi_android = '--wifi-android' in sys.argv[1:]
assert not wifi_android or wifi_probe
compact = '--compact' in sys.argv[1:]
autostart = '--autostart' in sys.argv[1:]
native_audio = '--native-audio' in sys.argv[1:]
charger_control = '--charger-control' in sys.argv[1:]
backlight_control = '--backlight' in sys.argv[1:]
camera_30fps = '--camera-30fps' in sys.argv[1:]
camera_full = '--camera-full' in sys.argv[1:]
camera_front = '--camera-front' in sys.argv[1:]
camera_flash = '--camera-flash' in sys.argv[1:]
assert not camera_flash or camera_front
assert not camera_front or '--camera-lens' in sys.argv[1:]
camera_lens = '--camera-lens' in sys.argv[1:]
assert not camera_lens or camera_full
assert not camera_full or camera_30fps
assert not camera_30fps or backlight_control
assert not backlight_control or charger_control
assert not charger_control or native_audio
camera_id = '--camera-id' in sys.argv[1:]
camera = '--camera' in sys.argv[1:]
assert not camera or camera_id
assert not camera_id or native_audio
netfilter = '--netfilter' in sys.argv[1:]
assert not native_audio or netfilter
managed_graphics = '--managed-graphics' in sys.argv[1:]
assert not netfilter or managed_graphics
assert not managed_graphics or autostart
assert not compact or (native_display and persistent_data)
assert not autostart or compact
assert not wifi_probe or native_display, 'Wi-Fi variant requires native display'
assert not native_display or gpu_probe, 'Native display requires GPU firmware'
assert not (native_display and presentation_probe), 'Select one display variant'
assert not presentation_probe or trace_probe, 'Presentation timing requires trace probe'
assert not trace_probe or gpu_probe, 'Trace probe requires GPU probe'
assert not psi_probe or persistent_data, 'PSI probe requires persistent test data'
assert not diagnostic_log or psi_probe, 'Diagnostic logging requires the PSI probe'
assert not gpu_probe or diagnostic_log, 'GPU probe requires diagnostic logging'

stage = Path('/mnt/c/Users/mrtol/AndroidStudioProjects/osprey/mainline-probe')
source = Path('/home/debian/osprey-port/lineage/out/target/product/osprey/system')
root = Path('/home/debian/osprey-port/mainline-android-ramdisk')
if root.exists():
    assert root.resolve() == Path('/home/debian/osprey-port/mainline-android-ramdisk')
    shutil.rmtree(root)
shutil.copytree('/home/debian/osprey-port/mainline-probe-ramdisk', root, symlinks=True, dirs_exist_ok=True)
subprocess.run(['arm-none-eabi-gcc', '-Os', '-marm', '-march=armv7-a', '-nostdlib', '-static', '-fno-pie', '-fno-stack-protector', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-Wl,-e,_start', '-Wl,-z,noexecstack', '-o', str(root/'init'), str(stage/'init-wrapper.c')], check=True)
(root/'init').chmod(0o755)
if (root/'system/lib').is_symlink():
    (root/'system/lib').unlink()
(root/'etc').symlink_to('/system/etc')
recovery = Path('/home/debian/osprey-port/mainline-recovery-extract/sbin')
shutil.copyfile(stage/'adb-cmd.sh', root/'sbin/cmd')
(root/'sbin/cmd').chmod(0o755)
queue = ['toolbox']; copied = set()
while queue:
    name = queue.pop()
    if name in copied or name == 'ld-android.so': continue
    copied.add(name)
    binary = recovery/name
    assert binary.is_file(), name
    shutil.copyfile(binary, root/'sbin'/name)
    (root/'sbin'/name).chmod(0o755)
    dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
    queue.extend(re.findall(r'Shared library: \[([^]]+)\]', dynamic))
for name, applet in [('getprop', 'toolbox'), ('setprop', 'toybox')]:
    target = root/'sbin'/name
    if target.is_symlink(): target.unlink()
    target.symlink_to(applet)
for folder in ['system/lib/bootstrap', 'system/bin/bootstrap', 'android-lib', 'apex', 'bootstrap-apex', 'linkerconfig', 'vendor/etc/selinux', 'system/etc/selinux', 'dev', 'mnt/user']:
    (root/folder).mkdir(parents=True, exist_ok=True)
android_bins = ['init', 'servicemanager', 'service']
for name in android_bins:
    shutil.copyfile(source/'bin'/name, root/'system/bin'/name)
    (root/'system/bin'/name).chmod(0o755)
shutil.copyfile(source/'bin/bootstrap/linker', root/'system/bin/bootstrap/linker')
(root/'system/bin/linker').symlink_to('/system/bin/bootstrap/linker')
for name in ['libc.so', 'libm.so', 'libdl.so', 'libdl_android.so']:
    shutil.copyfile(source/'lib/bootstrap'/name, root/'system/lib/bootstrap'/name)
queue = [source/'bin'/name for name in android_bins]; seen = set()
while queue:
    binary = queue.pop()
    dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
    for name in re.findall(r'Shared library: \[([^]]+)\]', dynamic):
        if name in seen or name == 'ld-android.so': continue
        seen.add(name)
        candidates = [source/'lib/bootstrap'/name, source/'lib'/name]
        dependency = next((p for p in candidates if p.is_file()), None)
        assert dependency is not None, name
        shutil.copyfile(dependency, root/'system/lib'/name)
        queue.append(dependency)
for binary in ['system/bin/init', 'system/bin/bootstrap/linker']:
    (root/binary).chmod(0o755)
for part, src in [('system', source), ('vendor', source/'vendor'), ('system_ext', source/'system_ext'), ('product', source/'product')]:
    contexts = src/'etc/selinux'
    if contexts.is_dir():
        shutil.copytree(contexts, root/part/'etc/selinux', dirs_exist_ok=True)
shutil.copyfile(source/'vendor/etc/selinux/precompiled_sepolicy', root/'policy')
for name in ['cgroups.json', 'task_profiles.json']:
    shutil.copyfile(source/'etc'/name, root/'system/etc'/name)
groups = json.loads((root/'system/etc/cgroups.json').read_text())
groups['Cgroups'] = [g for g in groups['Cgroups'] if g['Controller'] not in ['memory', 'cpuset']]
groups['Cgroups2'] = {'Path': '/sys/fs/cgroup', 'Mode': '0755', 'UID': 'system', 'GID': 'system', 'Controllers': [
    {'Controller': name, 'Path': '.', 'Mode': '0755', 'UID': 'system', 'GID': 'system', 'NeedsActivation': True}
    for name in ['memory', 'cpuset', 'pids']]}
(root/'system/etc/cgroups.json').write_text(json.dumps(groups, indent=2)+'\n')
profiles = json.loads((root/'system/etc/task_profiles.json').read_text())
for attr in profiles['Attributes']:
    if attr['Controller'] == 'cpuset' and attr['File'].endswith('/cpus'):
        attr['FileV2'] = attr['File'][:-4]+'cpuset.cpus'
    if attr['Name'] == 'MemUsage': attr['FileV2'] = 'memory.current'
(root/'system/etc/task_profiles.json').write_text(json.dumps(profiles, indent=2)+'\n')
shutil.copyfile(root/'system/etc/cgroups.json', root/'mainline-cgroups.json')
shutil.copyfile(root/'system/etc/task_profiles.json', root/'mainline-task-profiles.json')
(root/'system/build.prop').write_text('ro.secure=0\nro.debuggable=1\nro.adb.secure=1\nro.product.cpu.abi=armeabi-v7a\nro.product.cpu.abilist=armeabi-v7a,armeabi\nro.product.cpu.abilist32=armeabi-v7a,armeabi\nro.build.version.sdk=35\nro.build.version.release=15\nro.product.first_api_level=23\n')
(root/'vendor/etc/selinux/plat_sepolicy_vers.txt').write_text('202404\n')
bootstrap = (stage/'init').read_text(encoding='utf-8-sig').split('ADB_TRACE=')[0]
bootstrap += '''
mkdir -p /sys/fs/selinux /dev/socket /dev/__properties__
ln -s /dev/kmsg /dev/kmsg_debug
/sbin/toybox ifconfig lo up
mkdir -p /mnt/installed-system /dev/mapper
/sbin/toybox grep -qx PARTNAME=system /sys/class/block/mmcblk0p41/uevent || { echo 'OSPREY: wrong system partition'; while true; do sleep 5; done; }
mount -t ext4 -o ro,noload /dev/mmcblk0p41 /mnt/installed-system || { echo 'OSPREY: read-only system mount failed'; while true; do sleep 5; done; }
mount --bind /mnt/installed-system/system /system
mount --bind /mainline-cgroups.json /system/etc/cgroups.json
mount --bind /mainline-task-profiles.json /system/etc/task_profiles.json
mount --bind /sbin/sh /system/bin/sh
mount --bind /system/vendor /vendor
mkdir -p /product /system_ext
mount --bind /system/product /product
mount --bind /system/system_ext /system_ext
ln -s /dev/device-mapper /dev/mapper/control
mount -t selinuxfs selinuxfs /sys/fs/selinux
echo 0 >/sys/fs/selinux/enforce
/sbin/toybox load_policy /policy || { echo 'OSPREY ANDROID: policy load failed'; while true; do sleep 5; done; }
echo u:r:init:s0 >/proc/self/attr/current
echo 'OSPREY ANDROID: entering Android 15 second-stage init'
export LD_LIBRARY_PATH=/system/lib:/system/lib/bootstrap
exec /system/bin/init second_stage
'''
# vold sees only RAM data, no eMMC partitions or removable disk sources.
(root/'mainline-fstab').write_text('tmpfs /data tmpfs defaults defaults\n')
bootstrap = bootstrap.replace('mount --bind /system/vendor /vendor', 'mount --bind /system/vendor /vendor\nmount --bind /mainline-fstab /vendor/etc/fstab.qcom')
if persistent_data:
    # Use only the explicitly prepared test directory, never installed user data.
    bootstrap = bootstrap.replace("echo u:r:init:s0 >/proc/self/attr/current", '''
/sbin/toybox grep -qx PARTNAME=userdata /sys/class/block/mmcblk0p42/uevent || { echo 'OSPREY: wrong userdata partition'; while true; do sleep 5; done; }
mkdir -p /mnt/probe-userdata
mount -t ext4 -o rw,noatime /dev/mmcblk0p42 /mnt/probe-userdata || { echo 'OSPREY: userdata mount failed'; while true; do sleep 5; done; }
P=/mnt/probe-userdata/mainline-probe-data
[ -d "$P" ] && [ ! -L "$P" ] && /sbin/toybox grep -qx osprey-mainline-test-data-v1 "$P/.mainline-probe" || { echo 'OSPREY: missing test data marker'; while true; do sleep 5; done; }
mount --bind "$P" /data || { echo 'OSPREY: test data bind failed'; while true; do sleep 5; done; }
echo u:r:init:s0 >/proc/self/attr/current''')
(root/'probe-init').write_text(bootstrap)
if psi_probe:
    manifest = ET.parse(source/'vendor/etc/vintf/manifest.xml')
    for hal in list(manifest.getroot()):
        if hal.tag == 'hal' and hal.findtext('name') == 'vendor.lineage.livedisplay':
            # The simpledrm probe has none of the legacy fb0 color sysfs nodes.
            manifest.getroot().remove(hal)
    if camera:
        for hal in manifest.getroot().findall('hal'):
            if hal.findtext('name') == 'android.hardware.camera.provider':
                camera_transport = hal.find('transport')
                camera_transport.text = 'hwbinder'
                camera_transport.attrib.clear()
    manifest.write(root/'mainline-vendor-manifest.xml', encoding='utf-8', xml_declaration=True)
    bootstrap = bootstrap.replace('mount --bind /mainline-fstab /vendor/etc/fstab.qcom', 'mount --bind /mainline-fstab /vendor/etc/fstab.qcom\nmount --bind /mainline-vendor-manifest.xml /vendor/etc/vintf/manifest.xml')
    bootstrap = bootstrap.replace('mount --bind /mainline-task-profiles.json /system/etc/task_profiles.json', '''mount --bind /mainline-task-profiles.json /system/etc/task_profiles.json
# Override only diagnostic properties in RAM; installed build.prop stays read-only.
/sbin/toybox grep -v -E '^(ro.lmk.use_psi|ro.cp_system_other_odex)=' /system/build.prop >/mainline-build.prop
echo ro.lmk.use_psi=true >>/mainline-build.prop
# This probe has no system_other copy service or partition.
echo ro.cp_system_other_odex=0 >>/mainline-build.prop
mount --bind /mainline-build.prop /system/build.prop''')
    (root/'probe-init').write_text(bootstrap)
shutil.copyfile(stage/'systemserver-probe.rc', root/'systemserver-probe.rc')
shutil.copyfile(stage/'netbpfload_mainline_probe', root/'netbpfload_mainline_probe')
(root/'netbpfload_mainline_probe').chmod(0o755)
shutil.copyfile(stage/'light-service-probe', root/'light-service-probe')
(root/'light-service-probe').chmod(0o755)
(root/'mainline-init.rc').write_text(r'''import /mnt/installed-system/init.environ.rc
import /systemserver-probe.rc

on early-init
    loglevel 7
    setprop service.adb.root 1
    chmod 0666 /dev/kmsg
    mkdir /dev/socket 0755 root root
    mkdir /linkerconfig/bootstrap 0755 root root
    mkdir /linkerconfig/default 0755 root root
    write /linkerconfig/bootstrap/ld.config.txt \#
    write /linkerconfig/default/ld.config.txt \#
    mount none /linkerconfig/bootstrap /linkerconfig bind rec
    start ueventd
    exec_start apexd-bootstrap
    perform_apex_config --bootstrap
    start adbd
    chmod 0666 /dev/binder
    chmod 0666 /dev/hwbinder
    chmod 0666 /dev/vndbinder
    start servicemanager
    start logd

on init
    mkdir /metadata 0755 root root
    mkdir /metadata/apex 0755 root system
    mkdir /metadata/apex/sessions 0700 root system
    mkdir /data/apex 0755 root system
    mkdir /data/apex/active 0755 root system
    mkdir /data/apex/decompressed 0755 root system
    mkdir /data/apex/hashtree 0700 root system
    mkdir /data/apex/backup 0700 root system
    mkdir /data/misc 01771 system misc
    mkdir /data/misc/net 0750 root radio
    mkdir /data/misc_de 01771 system misc
    mkdir /data/misc_ce 01771 system misc
    mkdir /data/vendor_de 01771 root misc
    mkdir /data/vendor_ce 01771 root misc
    mkdir /data/media 0770 media_rw media_rw
    mkdir /data/misc/user 0775 root root
    mkdir /data/misc/apexdata 0755 root system
    mkdir /data/system 0775 system system
    mkdir /data/system/environ 0700 system system
    mkdir /data/dalvik-cache 0771 root root
    mkdir /data/dalvik-cache/arm 0771 root root
    setprop pm.dexopt.first-boot.concurrency 1
    setprop dalvik.vm.dex2oat-Xmx 128m
    setprop dalvik.vm.heapstartsize 16m
    setprop dalvik.vm.heapgrowthlimit 96m
    setprop dalvik.vm.heapsize 256m
    setprop dalvik.vm.heaptargetutilization 0.75
    setprop dalvik.vm.heapminfree 2m
    setprop dalvik.vm.heapmaxfree 8m
    mkdir /mnt/user 0755 root root
    mkdir /mnt/user/0 0755 root root
    mkdir /storage 0755 root root
    chown system system /sys/power/state
    chown system system /sys/power/wakeup_count
    chmod 0660 /sys/power/state
    mkdir /data/app 0771 system system
    mkdir /data/app-private 0771 system system
    mkdir /mnt/expand 0711 system system
    mkdir /data/user 0711 system system
    mkdir /data/user/0 0711 system system
    mkdir /data/data 0771 system system
    mount none /data/data /data/user/0 bind rec
    mkdir /data/user_de 0711 system system
    mkdir /data/user_de/0 0711 system system
    mkdir /data/system_de 0770 system system
    mkdir /data/system_de/0 0770 system system
    mkdir /data/system_ce 0770 system system
    mkdir /data/system_ce/0 0770 system system
    mkdir /data/local 0751 root root
    mkdir /data/local/tmp 0771 shell shell
    mkdir /data/tombstones 0771 system system
    mkdir /data/misc/profiles 0771 root root
    mkdir /data/misc/profiles/cur 0771 root root
    mkdir /data/misc/profiles/cur/0 0771 root root
    mkdir /data/misc/profiles/ref 0771 root root
    mkdir /data/misc/installd 0700 root root
    mkdir /data/misc/vold 0700 root root
    mkdir /data/misc/vold/user_keys 0700 root root
    mkdir /data/misc/vold/user_keys/ce 0700 root root
    mkdir /data/misc/vold/user_keys/de 0700 root root
    start apexd

on property:apexd.status=activated
    perform_apex_config
    exec_start derive_classpath
    load_exports /data/system/environ/classpath
    exec_start apexd-snapshotde
    setprop osprey.probe.art_ready 1
    start probe-hwservicemanager
    wait_for_prop hwservicemanager.ready true
    start probe-powerstats
    start probe-memtrack
    start probe-system-suspend
    start probe-installd
    start probe-health
    start probe-vibrator
    setprop debug.mainline.light_probe true
    start probe-light
    mkdir /data/misc/gatekeeper 0700 system system
    mkdir /data/misc/keystore 0700 keystore keystore
    mkdir /data/anr 0775 system system
    mkdir /data_mirror 0700 root system
    mount tmpfs tmpfs /data_mirror nodev noexec nosuid mode=0700,uid=0,gid=1000
    mkdir /data_mirror/data_ce 0700 root root
    mkdir /data_mirror/data_de 0700 root root
    mkdir /data_mirror/misc_ce 0700 root root
    mkdir /data_mirror/misc_de 0700 root root
    mkdir /data_mirror/data_ce/null 0700 root root
    mkdir /data_mirror/data_de/null 0700 root root
    mkdir /data_mirror/misc_ce/null 0700 root root
    mkdir /data_mirror/misc_de/null 0700 root root
    mkdir /data/storage_area 0700 root root
    mkdir /data_mirror/storage_area 0700 root root
    mount none /data/user /data_mirror/data_ce/null bind rec
    mount none /data/user_de /data_mirror/data_de/null bind rec
    mount none /data/misc_ce /data_mirror/misc_ce/null bind rec
    mount none /data/misc_de /data_mirror/misc_de/null bind rec
    mount none /data/storage_area /data_mirror/storage_area bind rec
    mkdir /data_mirror/cur_profiles 0700 root root
    mount none /data/misc/profiles/cur /data_mirror/cur_profiles bind rec
    mkdir /data_mirror/ref_profiles 0700 root root
    mount none /data/misc/profiles/ref /data_mirror/ref_profiles bind rec
    start tombstoned
    start probe-gatekeeper-hal
    start probe-gatekeeperd
    start probe-keymaster
    start probe-keystore
    start probe-gnss
    start probe-artd
    start probe-vold
    start probe-storaged
    mkdir /data/resource-cache 0771 system system
    start idmap2d
    mount bpf bpf /sys/fs/bpf nodev noexec nosuid
    start probe-bpfloader
    # Start Zygote explicitly after the RAM graphics stack has registered.


on property:sys.usb.ffs.ready=1
    write /sys/kernel/config/usb_gadget/osprey/UDC ${sys.usb.controller}

service adbd /sbin/adbd
    class core
    user root
    group root shell
    seclabel u:r:adbd:s0
    socket adbd seqpacket 0660 system system
    setenv LD_LIBRARY_PATH /sbin
    setenv PATH /sbin
    setenv ADB_TRACE usb,transport
    stdio_to_kmsg

service servicemanager /system/bin/servicemanager
    class core
    user system
    group system readproc
    seclabel u:r:servicemanager:s0
    setenv LD_LIBRARY_PATH /system/lib:/system/lib/bootstrap
    stdio_to_kmsg

service ueventd /system/bin/ueventd
    class core
    seclabel u:r:ueventd:s0
    stdio_to_kmsg

service apexd-bootstrap /system/bin/apexd --bootstrap
    user root
    group system
    seclabel u:r:apexd:s0
    oneshot
    disabled
    stdio_to_kmsg

service apexd /system/bin/apexd
    interface aidl apexservice
    user root
    group system
    seclabel u:r:apexd:s0
    oneshot
    disabled
    stdio_to_kmsg

service apexd-snapshotde /system/bin/apexd --snapshotde
    user root
    group system
    seclabel u:r:apexd:s0
    oneshot
    disabled
    stdio_to_kmsg

service derive_classpath /apex/com.android.sdkext/bin/derive_classpath
    user system
    group system
    seclabel u:r:derive_classpath:s0
    oneshot
    disabled
    stdio_to_kmsg

service logd /system/bin/logd
    socket logd stream 0666 logd logd
    socket logdr seqpacket 0666 logd logd
    socket logdw dgram+passcred 0222 logd logd
    file /proc/kmsg r
    file /dev/kmsg w
    user logd
    group logd system package_info readproc
    capabilities SYSLOG AUDIT_CONTROL
    seclabel u:r:logd:s0
    stdio_to_kmsg

''')
if psi_probe:
    with (root/'systemserver-probe.rc').open('a') as rc:
        rc.write('''
service lmkd /system/bin/lmkd
    user lmkd
    group lmkd system readproc
    capabilities DAC_OVERRIDE KILL IPC_LOCK SYS_NICE SYS_RESOURCE
    socket lmkd seqpacket+passcred 0660 system system
    seclabel u:r:lmkd:s0
    setenv LD_LIBRARY_PATH /system/lib:/system/lib/bootstrap
    disabled

service probe-mediaextractor /system/bin/mediaextractor
    user mediaex
    group drmrpc mediadrm
    seclabel u:r:mediaextractor:s0
    setenv LD_LIBRARY_PATH /system/lib:/system/lib/bootstrap
    disabled

service probe-media /system/bin/mediaserver
    user media
    group audio camera inet net_bt net_bt_admin net_bw_acct drmrpc mediadrm
    seclabel u:r:mediaserver:s0
    setenv LD_LIBRARY_PATH /data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
    disabled

service probe-omx /vendor/bin/hw/android.hardware.media.omx@1.0-service
    user mediacodec
    group camera drmrpc mediadrm audio
    seclabel u:r:mediacodec:s0
    setenv LD_LIBRARY_PATH /vendor/lib:/system/lib:/system/lib/bootstrap
    disabled
''')
    init_rc = root/'mainline-init.rc'
    with init_rc.open('a') as rc:
        rc.write('\non property:bpf.progs_loaded=1\n    start lmkd\n')
    init_rc.write_text(init_rc.read_text().replace('    start tombstoned', '    start tombstoned\n    start probe-omx\n    start probe-mediaextractor\n    start probe-media'))

if diagnostic_log:
    modules = root/'probe-modules'
    modules.mkdir()
    for name in ['rmi_core.ko', 'rmi_i2c.ko', 'max17042_battery.ko']:
        shutil.copyfile(stage/name, modules/name)
    if native_display:
        native = modules/'native'
        native.mkdir()
        for name in json.loads((stage/'native-modules.json').read_text()):
            shutil.copyfile(stage/'native-modules'/name, native/name)
    if wifi_probe:
        wifi = modules/'wifi'
        wifi.mkdir()
        for name in json.loads((stage/'wifi-modules.json').read_text()):
            shutil.copyfile(stage/'wifi-modules'/name, wifi/name)
    if native_audio:
        audio = modules/'audio'
        audio.mkdir()
        names = json.loads((stage/'audio-modules.json').read_text())
        for name in names:
            shutil.copyfile(stage/'audio-modules'/name, audio/name)
        init_rc = root/'mainline-init.rc'
        init_rc.write_text(init_rc.read_text().replace('    start ueventd',
            ''.join('    insmod /probe-modules/audio/'+name+(' control_charging=1' if charger_control and name == 'fan54046-monitor.ko' else '')+'\n' for name in names)+'    start ueventd'))
        (root/'probe-bin').mkdir(exist_ok=True)
        (root/'probe-bin/audio-init-native').touch()
    if camera_id:
        camera_id_dir = modules/'camera-id'
        camera_id_dir.mkdir()
        names = json.loads((stage/'camera-id-modules.json').read_text())
        for name in names:
            shutil.copyfile(stage/'camera-id-modules'/name, camera_id_dir/name)
        init_rc = root/'mainline-init.rc'
        init_rc.write_text(init_rc.read_text().replace('    start ueventd',
            ''.join('    insmod /probe-modules/camera-id/'+name+'\n' for name in names)+'    start ueventd'))
    if camera:
        shutil.copyfile(stage/'fuse.ko', modules/'fuse.ko')
        (root/'probe-bin/camera-init-native').touch()
        with (root/'systemserver-probe.rc').open('a') as rc:
            rc.write((stage/'camera-services.rc').read_text())
        cam = modules/'camera'
        cam.mkdir()
        names = json.loads((stage/'camera-modules.json').read_text())
        if camera_lens: names.insert(names.index('s5k3m2.ko'), 'ak7375.ko')
        if camera_front: names.append('s5k5e2.ko')
        if camera_flash: names += ['led-class-flash.ko', 'leds-sky81296.ko']
        for name in names:
            shutil.copyfile(stage/'camera-modules'/name, cam/name)
        init_rc = root/'mainline-init.rc'
        init_rc.write_text(init_rc.read_text().replace('    start ueventd',
            '    insmod /probe-modules/fuse.ko\n'+''.join('    insmod /probe-modules/camera/'+name+'\n' for name in names)+'    start ueventd'))
    with (root/'systemserver-probe.rc').open('a') as rc:
        rc.write('''
service probe-logcat /system/bin/logcat -b all -v threadtime -f /data/mainline-boot.log -r 4096 -n 3
    user root
    group log root readproc
    seclabel u:r:shell:s0
    setenv LD_LIBRARY_PATH /system/lib:/system/lib/bootstrap
    disabled

# Restore the service Settings queries synchronously, including existing test data.
service probe-enable-tethering /system/bin/cmd -w package enable --user 0 com.android.networkstack.tethering
    user root
    group root
    seclabel u:r:shell:s0
    setenv LD_LIBRARY_PATH /system/lib:/system/lib/bootstrap
    disabled
    oneshot
''')
    init_rc = root/'mainline-init.rc'
    init_rc.write_text(init_rc.read_text()
        .replace('    start ueventd', '    insmod /probe-modules/rmi_core.ko\n    insmod /probe-modules/rmi_i2c.ko\n    insmod /probe-modules/max17042_battery.ko\n    start ueventd')
        .replace('    start logd', '    start logd\n    start probe-logcat\n    start probe-enable-tethering'))

if gpu_probe:
    firmware = root/'lib/firmware/qcom'
    firmware.mkdir(parents=True, exist_ok=True)
    donor = Path('/home/debian/osprey-port/lineage/vendor/motorola/msm8916-common/proprietary/vendor/firmware')
    for name in ['a300_pfp.fw', 'a300_pm4.fw']:
        shutil.copyfile(donor/name, firmware/name)

# Keep the LMKD fix confined to the native-display RAM boot variant.
if native_display:
    probe_bin = root/'probe-bin'
    probe_bin.mkdir(exist_ok=True)
    shutil.copyfile(stage/'lmkd-epoll-fixed', probe_bin/'lmkd')
    (probe_bin/'lmkd').chmod(0o755)
    rc = root/'systemserver-probe.rc'
    rc.write_text(rc.read_text().replace('service lmkd /system/bin/lmkd',
                                        'service lmkd /probe-bin/lmkd'))

if wifi_android:
    shutil.copyfile(stage/'libwifi-hal.mainline.so', root/'probe-bin/libwifi-hal.so')
    with (root/'systemserver-probe.rc').open('a') as rc:
        rc.write((stage/'native-wifi-services.rc').read_text())

if managed_graphics:
    (root/'probe-bin/graphics-init-managed').touch()
    with (root/'systemserver-probe.rc').open('a') as rc:
        rc.write((stage/'native-graphics-services.rc').read_text())

if autostart:
    shutil.copyfile(stage/'boot-native.sh', root/'probe-bin/boot-native.sh')
    (root/'probe-bin/boot-native.sh').chmod(0o755)
    with (root/'mainline-init.rc').open('a') as rc:
        rc.write("\non property:bpf.progs_loaded=1\n    start mainline-native-start\n")
    with (root/'systemserver-probe.rc').open('a') as rc:
        rc.write("\nservice mainline-native-start /sbin/sh /probe-bin/boot-native.sh\n    user root\n    group root\n    seclabel u:r:init:s0\n    setenv LD_LIBRARY_PATH /sbin\n    setenv PATH /sbin\n    disabled\n    oneshot\n")

if compact:
    # probe-init mounts installed system/vendor/product before modern init.
    # Keep policy and mainline-* overrides; these copies are hidden by mounts.
    for name in ['system', 'vendor', 'product', 'system_ext']:
        folder = root/name
        if folder.is_symlink():
            folder.unlink()
        elif folder.exists():
            shutil.rmtree(folder)
        folder.mkdir()

if camera_full:
    memory = root/'probe-modules/memory'
    memory.mkdir(parents=True, exist_ok=True)
    for name in ['lzo_compress.ko', 'zsmalloc.ko', 'zram.ko']:
        shutil.copyfile(stage/'memory-modules'/name, memory/name)
    shutil.copyfile(stage/'start-zram.sh', root/'probe-bin/start-zram.sh')
    (root/'probe-bin/start-zram.sh').chmod(0o755)
    rc = root/'mainline-init.rc'
    text = rc.read_text().replace('    start ueventd',
        '    insmod /probe-modules/memory/lzo_compress.ko\n'
        '    insmod /probe-modules/memory/zsmalloc.ko\n'
        '    insmod /probe-modules/memory/zram.ko\n    start ueventd', 1)
    text += '\non init\n    exec_start mainline-zram\n\nservice mainline-zram /sbin/sh /probe-bin/start-zram.sh\n    user root\n    group root\n    disabled\n    oneshot\n    setenv LD_LIBRARY_PATH /sbin\n    seclabel u:r:init:s0\n'
    rc.write_text(text)


paths = subprocess.check_output(['find', '.', '-print0'], cwd=root)
cpio = subprocess.run(['cpio', '--null', '-o', '-H', 'newc', '--owner=0:0'], input=paths, cwd=root, stdout=subprocess.PIPE, check=True).stdout
(stage/'android-ramdisk.cpio.gz').write_bytes(gzip.compress(cpio, mtime=0))
out = Path('/home/debian/osprey-port/mainline-probe-out')
kernel = (stage/'Image-native-audio.gz' if native_audio else stage/'Image-native-netfilter.gz' if netfilter else stage/'Image-native-display.gz' if native_display else stage/'Image-gpu-presentation.gz' if presentation_probe else stage/'Image-gpu-trace.gz' if trace_probe else stage/'Image-gpu.gz' if gpu_probe else stage/'Image-psi.gz' if psi_probe else stage/'Image-v17-before-psi.gz' if (stage/'Image-v17-before-psi.gz').exists() else out/'arch/arm64/boot/Image.gz').read_bytes()

dtb = (stage/'msm8916-motorola-osprey-camera-flash.dtb' if camera_flash else 'msm8916-motorola-osprey-camera-front.dtb' if camera_front else stage/'msm8916-motorola-osprey-camera-lens.dtb' if camera_lens else stage/'msm8916-motorola-osprey-camera-probe.dtb' if camera else stage/'msm8916-motorola-osprey-camera-id-probe.dtb' if camera_id else stage/'msm8916-motorola-osprey-native-audio-probe.dtb' if native_audio else stage/'msm8916-motorola-osprey-native-wifi-probe.dtb' if wifi_probe else stage/'msm8916-motorola-osprey-native-probe.dtb' if native_display else stage/'msm8916-motorola-osprey-gpu-probe.dtb' if gpu_probe else out/'arch/arm64/boot/dts/qcom/msm8916-motorola-osprey-probe.dtb').read_bytes()
assert dtb[:4] == b'\xd0\x0d\xfe\xed'
# lk2nd's boot memory arena is 50 MiB; keep this diagnostic below it.
raw_kernel = len(gzip.decompress(kernel))
assert raw_kernel + len(cpio) + len(dtb) < 48*1024*1024, (raw_kernel, len(cpio))
(stage/'android-Image.gz-dtb').write_bytes(kernel+dtb)
image = stage/('boot-mainline-android-v45-camera-flash.img' if camera_flash else 'boot-mainline-android-v44-camera-front.img' if camera_front else 'boot-mainline-android-v43-camera-lens.img' if camera_lens else 'boot-mainline-android-v42-camera-full.img' if camera_full else 'boot-mainline-android-v41-camera-30fps.img' if camera_30fps else 'boot-mainline-android-v40-backlight-camera.img' if backlight_control else 'boot-mainline-android-v39-charger.img' if charger_control else 'boot-mainline-android-v36-camera.img' if camera else 'boot-mainline-android-v35-camera-id.img' if camera_id else 'boot-mainline-android-v34-audio.img' if native_audio else 'boot-mainline-android-v33-netfilter.img' if netfilter else 'boot-mainline-android-v32-managed.img' if managed_graphics else 'boot-mainline-android-v31-wifi-android.img' if wifi_android else 'boot-mainline-android-v30-compact.img' if compact else 'boot-mainline-android-v29-native-wifi.img' if wifi_probe else 'boot-mainline-android-v28-native-display.img' if native_display else 'boot-mainline-android-v27-presentation.img' if presentation_probe else 'boot-mainline-android-v26-gpu-trace.img' if trace_probe else 'boot-mainline-android-v25-gpu.img' if gpu_probe else 'boot-mainline-android-v22-persistent-psi.img' if diagnostic_log else 'boot-mainline-android-v18-persistent-psi.img' if psi_probe else 'boot-mainline-android-v17-persistent.img' if persistent_data else 'boot-mainline-android-v16.img')
subprocess.run(['python3', '/home/debian/osprey-port/lineage/system/tools/mkbootimg/mkbootimg.py', '--kernel', str(stage/'android-Image.gz-dtb'), '--ramdisk', str(stage/'android-ramdisk.cpio.gz'), '--header_version', '0', '--base', '0x80000000', '--kernel_offset', '0x00080000', '--ramdisk_offset', '0x02000000', '--tags_offset', '0x01e00000', '--pagesize', '2048', '--cmdline', 'rdinit=/init androidboot.init_rc=/mainline-init.rc console=ttyMSM0,115200n8 console=tty0 loglevel=8 ignore_loglevel panic=0 cma=32M enforcing=0 selinux=1 lk2nd.pass-simplefb=1 clk_ignore_unused pd_ignore_unused regulator_ignore_unused' + (' msm.separate_gpu_kms=1' if gpu_probe else ''), '--output', str(image)], check=True)
print('Libraries:', sorted(seen))
print('Raw kernel/ramdisk bytes:', raw_kernel, len(cpio))
print('Image:', image.stat().st_size, hashlib.sha256(image.read_bytes()).hexdigest())
