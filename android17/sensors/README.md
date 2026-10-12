# Osprey mainline navigation and sensors

Android 17, ARM32 userspace, Linux 7.0, permanent system partition.

## Root causes

The mainline product did not inherit the old framework overlay, leaving
`config_showNavigationBar=false`. SystemUI therefore never attached its edge
Back gesture handler. `OspreyMainlineFrameworkOverlay` enables the navigation
bar without changing the user's navigation mode.

Osprey's accelerometer sits behind Motorola's STML0xx SPI sensorhub. The
mainline DT had SPI3 disabled and no sensorhub node, and the product had no
sensors HAL. Enabling an unrelated I2C accelerometer cannot fix this device.

## Implementation

* Kernel: `drivers/misc/stml0xx-accel.c`, `CONFIG_STML0XX_ACCEL=m` and an Osprey
  SPI3 node. GPIOs, supplies, framing, CRC, orientation (5,5) and accelerometer
  swap come from Motorola's existing 3.10 driver and Osprey DTS.
* Readout: `/sys/bus/spi/devices/spi0.0/accel_xyz`, signed X/Y/Z in mg.
  Invalid SPI transfers and CRCs return errors instead of synthetic samples.
* Android: `device/motorola/msm8916-common/mainline-sensors`, AIDL sensors V3.
  Reuses AOSP's FMQ and sensor scheduling source via a filegroup. The local
  header registers only the physical accelerometer. Values convert to m/s².
  Failed reads produce no events.
* Boot: `boot-sensors-v1.img` changes only the DTB of the verified modem v7
  boot image. Its compressed kernel, lk2nd, partition layout and root settings
  remain byte-identical. Sensorhub flash is never programmed.

## Build and installation

`fix-navigation.py` prepares the framework overlay. `integrate.py` prepares
the HAL and source filegroup. `build-probe.sh` compiles the small kernel
module against the existing kernel output. `integrate-kernel.py` records the
driver, Kconfig, DT, module and early boot loading in their source trees.
`build-hal.sh` builds the HAL and overlay. `prepare-boot.py` and
`prepare-install.py` create the checked payload and recovery ZIP.

`probe-overlay.dts` and `overlay-loader.c` are diagnostic helpers only. Their
numeric phandles match the pinned v7 DTB; do not apply them to another boot.
The permanent boot has the node built into its DTB and needs no overlay loader.

The installer checks osprey, Android SDK 37, the known boot hash and every
payload checksum, then replaces files atomically and writes the checked boot
image. It does not format data or modify EFS or modem firmware.

## Limits

The sensorhub uses a fixed 25 Hz rate and register polling. IRQ/FIFO handling,
runtime sensor power management and the other sensors still need porting.
Sensor power is an estimate, not a measured value. Factory calibration has
not been independently checked.

## v2: light and proximity

The installed HAL exposes three real sensors after a full reboot. The hub driver
uses the donor CT406 calibration, acknowledges hub initialization and retries
SPI errors. ALS and proximity are read from the donor IRQ packet formats;
unchanged values are cached, and transport failures do not generate fake events.
Physical cover/uncover returned proximity states 2 (saturated) and 0 (far).

Proximity currently uses awake polling and deliberately is not advertised as a
wake-up sensor. IRQ handling during suspend, sensor power management, automatic
brightness configuration and AK09912 compass integration remain outstanding.
The sensorhub firmware is unchanged. v2 recovery ZIP preserves data and retains
the same boot image as v1; the updated kernel module and HAL are persistent.

## v3: default Android proximity sensor

Android SensorManager.getDefaultSensor(TYPE_PROXIMITY) requires a wake-up sensor.
v2 exposed a non-wake-up sensor, so apps using that API got null despite the
entry being present in sensorservice. v3 adds GPIO52 threaded IRQ handling and
kernel wake-IRQ registration, caches validated proximity IRQ events and marks
the AIDL sensor as wake-up. AOSP FMQ implements acknowledgement/wakelocks.
This supersedes v2's awake-only limitation. Suspend/resume behavior still needs
physical validation; GPIO52 interrupt delivery was observed on the running phone.

The v3 kernel configuration had CONFIG_SUSPEND disabled. Thus
hardware deep suspend cannot be validated on this build, and the PM wake-IRQ
helpers are stubs. GPIO52 event delivery and Android wake-up FMQ semantics work
while the system is awake; enabling kernel suspend requires separate validation.

## v4: compass, automatic brightness and suspend bring-up

AK09912 is enabled on I2C6 using the donor reset/IRQ wiring and PAT5 mounting.
The HAL identifies its OF compatible even when IIO names it after the I2C bus,
applies each axis factory scale, and reports real magnetic-field samples.
After installation Android lists four physical sensors and an AOSP virtual
geomagnetic rotation vector. No physical gyroscope or barometer was found in
the donor Osprey sensor list. Hard/soft-iron calibration is still missing;
magnetic-field accuracy is explicitly UNRELIABLE.

The framework overlay enables automatic brightness with the donor lux/backlight
tables. Manual brightness and navigation remain available.

The device kernel fragment enables CONFIG_SUSPEND and PM diagnostics. All
packaged modules were rebuilt against that configuration. The available sleep
mode is s2idle, not firmware deep standby. The first devices-only suspend test
found an AK7375 resume error: an inactive lens was powered up on system resume.
Its system PM callbacks now use runtime-PM force suspend/resume, and a failed
lens initialization releases its regulator votes. The repeat test initially panicked in the charger monitor (see below); its
PM fix then passed the devices test and restored USB and Charging status.

Use prepare-v4.py and prepare-install.py for this payload. The recovery ZIP and
normal-ROM packager include the matching module set, HAL, overlay and boot.
The older prepare-boot.py generates the historical v3 payload instead.
Sensorhub runtime power management and Motorola custom gestures remain unported.
### Suspend failure captured in pstore

The repeat v4 devices test panicked in fan_poll -> fan5404x_masked_write ->
qup_i2c_xfer_v2 while the I2C controller was suspended. FAN5404x polling used
an ordinary workqueue and had no system-sleep callbacks. The monitor now
cancels polling synchronously before suspend, serializes property reads with
PM, and refuses I2C property reads while suspended. Resume restarts polling.

Charging control retains its existing wake lock while external power is
present, so ordinary screen-off does not suspend the temperature monitor.
A forced diagnostic suspend disables charging until resume because no thermal
wake-up monitoring has been ported. Charging during actual suspend remains an
explicit limitation; do not remove the wake lock without a thermal wake source.

After the FAN5404x fix, pm_test=devices completed on hardware with suspend
entry at 78.800 s and exit at 89.575 s. ADB reconnected, boot_completed stayed 1,
and charger status returned Charging. Actual RTC-woken s2idle remains under test.

### MDP5 state restoration

After a devices-test resume, the next suspend failed in mdp5_pipe_release:
saved plane state retained a hardware-pipe pointer whose global allocation
had been released during suspend. The restored display also became purple;
a normal reboot restored its colors. Plane atomic checking now reallocates
that pipe when the old plane has no pipe and its saved global slot is empty.
Existing allocations are retained on repeated atomic checks. The empty-slot
check applies to both enabling and disabling a saved plane; checking only an
old disabled plane missed other restored layers. The corrected driver passed
a real RTC-woken s2idle cycle with success=1, fail=0, no pipe warnings and
Charging restored after resume.
A second RTC test aborted safely in alarmtimer with -EBUSY (an imminent Android
alarm), without MDP5 warnings or panic. The display capture after resume shows
a normal lock screen and the charge icon. No SoC firmware deep state is exposed;
this verifies s2idle bring-up, not measured standby battery life.

The third RTC cycle passed too: /proc/uptime advanced from 231.91 to 252.91 s,
ADB returned, success=2 and fail=1 (the expected alarmtimer abort). Charging
was restored. The user confirmed normal physical colors, Power and touch after
resume. Logs are retained in suspend-fixed-log.txt and the earlier pstore folder.

## v5: display interconnect and first-frame ordering

The hardware log reports 0x04000000 = INTF1_UNDER_RUN, including at panel startup
and after screen-off/on. The product lacked both the MSM8916 ICC driver and the
MDP0-to-EBI DT path. v5 enables the existing Qualcomm modules, loads their three
dependencies before DRM, and adds mdp0-mem via SNOC MASTER_MDP_PORT0 to BIMC
SLAVE_EBI_CH0. Overlay references are checked against actual DTB phandles.

The qnoc-msm8916 driver now uses the standard icc_sync_state callback, as the
MSM8939 driver does. Hardware debugfs confirms the display bandwidth vote and
release of initial INT_MAX reservations. MDP5's existing 6400 MB/s peak vote
is unchanged; this is bring-up configuration, not power tuning.

ICC alone did not remove the underrun on each panel enable. Video encoder
startup now flushes the first scanout before enabling the timing engine,
with a write barrier. This leaves command-mode paths unchanged. Hardware
validation found fewer startup errors, but an underrun remained at GUI startup and one during three screen-off/on cycles. The user still observed wake flicker.

build-display-icc.sh and prepare-v5.py build and package this version; the normal
ROM packager uses boot-sensors-v5.img with the matching 66 modules. The v5 ZIP
retains the sensor, lens-PM, charger-PM and saved-plane resume fixes.
The INX panel previously forced brightness 207/255 and DISPLAY_ON during
prepare, before the video host was enabled. Its prepare sequence now leaves
brightness at zero; DISPLAY_ON runs in the standard panel enable callback,
then the backlight core restores the requested brightness. With this panel change, Android boot_completed=1 at uptime 81.93 s with no
MDP underrun. Three screen-off/on cycles also produced no underrun or DSI
timeout; requested brightness was restored. One RTC-woken s2idle cycle passed
with success=1, fail=0 and Charging restored. Despite those results, the user
still observed physical wake flicker. Logs are retained in
display-panel-phase-dmesg.txt and display-panel-phase-suspend.txt.

The INX-only continuous-HS-clock probe failed: the user saw backlight only,
and one startup underrun returned. MIPI_DSI_CLOCK_NON_CONTINUOUS was restored
in source, modules, the recovery ZIP and on the phone. The failed probe's
log is retained in display-continuous-clock-fail-dmesg.txt. Do not describe
this clock change as a fix. Physical wake flicker is still unresolved.

After clock rollback, boot_completed returned to 1, Charging was restored,
and the panel module hash matched the rebuilt non-continuous-clock version.
A startup underrun occurred again at 79.516575 s, so the earlier error-free
cycle is not proof of a deterministic underrun fix. Physical image recovery
and a video distinguishing brightness flicker from frame displacement are pending.

### Panel shutdown timing probe

Forced GPU composition did not change the user-visible wake flicker; normal
hardware composition was restored. Osprey's Motorola reset-off sequence
keeps reset deasserted for 101 ms after sleep-in before asserting reset.
The INX unprepare now preserves this delay before disabling regulators.
Backlight commands remain LP, as in the donor; no PHY timing or clock rate
was changed. This module-only update is present in the v5 ZIP and the
canonical module manifest. Physical wake validation remains pending.

### DSI command PLL retuning fix

The HS brightness probe did not improve physical flicker and was reverted to
normal LP DCS writes. Private clock tracing showed that brightness commands
reprogrammed the 28nm VCO to 421728000 Hz and its pixel/byte descendants while
video was running. The actual recalculated VCO is 421708593 Hz, so rounding
made repeated clock requests execute real set_rate callbacks.

msm_dsi_host_xfer_prepare no longer repeats link_clk_set_rate. Host power-on
still sets link rates and enables clocks; dsi_host_transfer rejects an
unpowered host. Command clock enable/disable references are unchanged.
Both the canonical modules and v5 recovery ZIP include the fix; msm.ko SHA256
is 4be938d9493c90ad2a61acee3ac7c0226bd5ba8e6c15f2c2148d818f3942c4a0.
The installed module hash matches. Android reached boot_completed=1 and
Charging, with no DSI error or MDP underrun in the captured log.

Five isolated brightness changes after reboot produced no DSI/MDSS rate
changes (brightness-clock-fixed-trace.txt). A second trace overlaps the user's
screen-off/on test: clock programming is still visible from the Android
hardware service on screen enable, not from the shell brightness commands.
The user confirmed brightness changes and Power wake no longer flicker or
shift the image. This is a short hardware check, not long-term stress testing.
