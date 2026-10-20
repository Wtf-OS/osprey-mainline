# Android 17 mainline build

Run `bash /path/to/osprey-mainline/android17/build.sh` from WSL after syncing
the pinned manifest and applying all seven patch queues. Keep the kernel checkout at
`~/osprey-port/linux-mainline-osprey`, Android at `~/osprey-port/lineage`, and
lk2nd at `~/osprey-port/lk2nd`.

The script incrementally builds the mainline kernel and modules, the complete
camera/audio/display DT include chain with MPSS enabled, and lk2nd. Kernel output
continues to use `mainline-a16-out` to preserve the existing incremental cache.
The name of that directory does not select Android 16.

`prepare-kernel.py` verifies the DTB's modem, camera and ramoops nodes and every
selected module's vermagic. It produces `mainline-boot/boot-mainline.img` and
`kernel-artifacts.json` in the device tree. There is no initramfs: the existing
first-stage init is installed in the system root by the packer.

The ROM packer consumes those artifacts instead of the Android 16 checkpoint and
the modem/sensor probe images. It validates the product's installed modules,
GNSS service and USB configuration. LLVM stripping uses the active Android release
configuration, rather than a hardcoded toolchain version.

The final TWRP ZIP preserves Data and uses 16 MiB system chunks, partition-size
checks and full-image hashes. A fresh kernel build does not flash the phone.
Keep compiler caches and current build outputs when freeing WSL space; at least
one additional 2.4 GB raw system image must fit during packaging.

The explicit module list works without generated files from older probes. Boot
uses a read-only system root and SELinux Enforcing. The packer verifies TimeKeep,
the real init module order, policy hashes, camera workers and Codec2 dependencies
against the image before writing the ZIP. It creates no automatic device backups.

The current ZIP was rebuilt incrementally from the staged Android product after
refreshing its image inputs. The installed kernel and recent hardware fixes were
checked on the development phone; this full ZIP has not been flashed again and
the published build entry point has not had a clean-checkout build.
