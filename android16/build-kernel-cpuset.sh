#!/bin/bash
set -euo pipefail
src=/home/debian/osprey-port/linux-mainline-osprey
out=/home/debian/osprey-port/mainline-a16-out
clang=/home/debian/osprey-port/lineage/prebuilts/clang/host/linux-x86/clang-r530567/bin
if [ ! -x "$clang/clang" ]; then
    clang=/home/debian/osprey-port/lineage/prebuilts/clang/host/linux-x86/clang-r574158/bin
fi
export PATH="$clang:$PATH"
if [ ! -d "$out" ]; then
    cp -a /home/debian/osprey-port/mainline-probe-out "$out"
fi
"$src/scripts/config" --file "$out/.config" --enable CPUSETS_V1 --enable PROC_PID_CPUSET
make -C "$src" O="$out" ARCH=arm64 LLVM=1 olddefconfig
make -C "$src" O="$out" ARCH=arm64 LLVM=1 -j8 Image.gz modules
external=/home/debian/osprey-port/osprey-camera-id-a16-build
mkdir -p "$external"
cp /home/debian/osprey-port/osprey-camera-id-build/Makefile /home/debian/osprey-port/osprey-camera-id-build/osprey-camera-id.c "$external/"
make -C "$src" O="$out" M="$external" ARCH=arm64 LLVM=1 -j8 modules
cp "$out/.config" /mnt/c/Users/mrtol/AndroidStudioProjects/osprey/android16-port/package/kernel-a16.config
make -C /home/debian/osprey-port/lk2nd -j8 lk2nd-msm8916 BOOTLOADER_OUT=/home/debian/osprey-port/lk2nd-a16-out LK2ND_FORCE_FASTBOOT=0 DEBUG_FBCON=1
