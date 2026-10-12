# Osprey Android 17 mainline modem checkpoint

The phone boots MPSS automatically through `osprey-modem` after a normal reboot.
`sys.boot_completed=1`, `init.svc.osprey-modem=running`, and remoteproc1 is running.
An AT probe on `/dev/wwan0at0` returns:

```
AT: OK
AT+CGMR: MPSS.DPM.2.0.2.c1.8-00044-M8936FAAAANUZM-1
AT+CPIN?: +CME ERROR: SIM not inserted
```

The QMI control endpoint is `/dev/wwan0qmi0` (SMD DATA5_CNTL).
The AT endpoints are DATA1 and DATA4. This firmware does not expose its
telephony DMS service through QRTR.

## Reproduction

Run `build-probe.py` under WSL to enable MPSS in the validated DTB while
preserving the compressed kernel and lk2nd. Run `integrate.py` to copy the
locally extracted original firmware into the device tree. `package.py`
creates the incremental TWRP ZIP and a ZIP restoring the pre-modem boot.
The disable ZIP leaves inert modem assets on System.

The incremental ZIP targets the existing Android 17 mainline installation
and accepts only the recorded base boot or v7 boot. It verifies payload
checksums before writes. Firmware, calibration, and user-data partitions
are not flashed. RMTFS always uses its RAM shadow (`-r`): calibration writes
do not persist across modem restarts.

Source integration lives in WSL at
`lineage/device/motorola/msm8916-common/mainline-modem`; the four modules are
in `mainline-boot/modules`. The full A17 packer now selects v7 and validates
the added assets/modules. A full System rebuild was not run for this checkpoint.

## Android Radio integration

The radio/ device source implements a basic AIDL V4 HAL. Seven interfaces are
published for slot1/default. Actual AT replies provide modem revision and RF state;
QMI UIM provides SIM-absent state. CGMR has no trailing OK; parse the complete
MPSS version line. Revision is read before Android changes RF power during init.
Selecting backend 0 is a valid no-op because only one backend is exposed.

NAS QMI over /dev/wwan0qmi0 provides signal strength and the modem's actual
unregistered/searching/denied/unknown state. The initial no-SIM probe measured
WCDMA RSSI around -66 dBm. AT network commands returned ERROR. QMI message layouts
follow linux-mobile-broadband/libqmi data/qmi-service-ctl.json and qmi-service-nas.json.
Missing measurements remain unavailable. Registered-SIM/cell/PLMN translation
is not implemented. Graceful service stop releases the allocated NAS client.
Signal refresh currently follows voice-registration queries, not continuous NAS
indications. A live framework refresh confirmed WCDMA RSSI -67 dBm in Android's
telephony registry. The parser probe also checks malformed/truncated TLVs.

UIM Get Card Status (service 11, message 0x2f) confirms one empty slot and no
applications. IRadioSim and IRadioConfig share the parsed result. The probe
verified close/reopen and malformed/truncated/duplicate-TLV rejection. Cached
clients are discarded after transport failure or QMI INVALID_CLIENT_ID so the
next query reconnects. Real modem-restart recovery has not been checked.
Layout: linux-mobile-broadband/libqmi data/qmi-service-uim.json.
v10 was checked after a full normal reboot: boot_completed=1, modem/HAL running,
SIM and slot state absent. A settled framework refresh recorded WCDMA -69 dBm.
The earliest signal query failed while the modem was starting; it works after
startup. No crash-buffer entries were captured.

The shortened gsm.version.baseband property is intentional Android behavior:
GsmCdmaPhone keeps the last PROP_VALUE_MAX/2 (45) characters. The HAL returns the
complete version. There is no property ABI/readout bug or baseband spoof.

Other operations return REQUEST_NOT_SUPPORTED. SIM insertion, mobile data, SMS,
calling and emergency calling are not implemented. The service still uses root
and the existing permissive SELinux setup. A production radio domain and narrower
device-node permissions remain necessary.

`generate-radio.py`, `build-radio.sh` and `prepare-radio.py` reproduce the source,
binary and incremental `osprey-a17-radio-v10.zip`. Use the explicit per-file ADB
destination when updating an existing payload directory: pushing a directory
again nests it beneath the existing directory.

The full System image was not rebuilt. Source integration adds the HAL and
radio-access feature to the next build. Firmware is proprietary and must not
be published as open-source code. Logs and CPU samples are kept in this folder.
