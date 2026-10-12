#!/bin/bash
set -euo pipefail
src=/home/debian/osprey-port/linux-mainline-osprey
out=/home/debian/osprey-port/mainline-a16-out
export PATH=/home/debian/osprey-port/lineage/prebuilts/clang/host/linux-x86/clang-r563880c/bin:$PATH
"$src/scripts/config" --file "$out/.config" --module INTERCONNECT_QCOM --module INTERCONNECT_QCOM_MSM8916
make -C "$src" O="$out" ARCH=arm64 LLVM=1 olddefconfig
make -C "$src" O="$out" ARCH=arm64 LLVM=1 KALLSYMS_EXTRA_PASS=1 -j8 Image.gz modules
