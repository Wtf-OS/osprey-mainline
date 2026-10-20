#!/bin/bash
set -euo pipefail
port=${HOME}/osprey-port
src=$port/linux-mainline-osprey
out=$port/mainline-a16-out
scripts=$(cd "$(dirname "$0")" && pwd)
export PATH="$port/lineage/prebuilts/clang/host/linux-x86/clang-r563880c/bin:$PATH"
mkdir -p "$out"
if [ ! -f "$out/.config" ]; then
    cp "$scripts/kernel.config" "$out/.config"
fi
"$src/scripts/config" --file "$out/.config" --module STML0XX_ACCEL
"$src/scripts/config" --file "$out/.config" --enable NVMEM_SYSFS
"$src/scripts/config" --file "$out/.config" --enable FS_VERITY
make -C "$src" O="$out" ARCH=arm64 LLVM=1 olddefconfig
make -C "$src" O="$out" ARCH=arm64 LLVM=1 KALLSYMS_EXTRA_PASS=1 -j8 Image.gz modules qcom/msm8916-motorola-osprey-mainline.dtb
make -C "$port/lk2nd" -j8 lk2nd-msm8916 BOOTLOADER_OUT="$port/lk2nd-a16-out" LK2ND_FORCE_FASTBOOT=0 DEBUG_FBCON=1
python3 "$scripts/prepare-kernel.py"
