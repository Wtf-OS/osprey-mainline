#!/bin/bash
set -euo pipefail
src=/home/debian/osprey-port/linux-mainline-osprey
out=/home/debian/osprey-port/mainline-a16-out
stage=/mnt/c/Users/mrtol/AndroidStudioProjects/osprey/android17-port/sensors
cp "$out/.config" "$stage/kernel-before-suspend.config"
export PATH=/home/debian/osprey-port/lineage/prebuilts/clang/host/linux-x86/clang-r563880c/bin:$PATH
"$src/scripts/config" --file "$out/.config" --enable SUSPEND --enable PM_DEBUG --enable PM_SLEEP_DEBUG
make -C "$src" O="$out" ARCH=arm64 LLVM=1 olddefconfig
make -C "$src" O="$out" ARCH=arm64 LLVM=1 KALLSYMS_EXTRA_PASS=1 -j8 Image.gz modules
cp "$out/.config" "$stage/kernel-suspend.config"
