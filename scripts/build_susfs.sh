#!/usr/bin/env bash
#
# build_susfs.sh - build this kernel exactly the way run.sh does, using the
#                  toolchain provisioned by scripts/setup_build_env.sh.
#
# Produces:  out/arch/arm64/boot/Image.gz-dtb   (flashable via AnyKernel3)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TOOLS_DIR="${KERNEL_TOOLS_DIR:-$ROOT/.kernel-tools}"
ENV_FILE="$TOOLS_DIR/env.sh"

if [ ! -f "$ENV_FILE" ]; then
    bash scripts/setup_build_env.sh
fi
# shellcheck disable=SC1090
. "$ENV_FILE"

MKARGS_FILE="$TOOLS_DIR/mkargs.sh"
HOST_MAKE_ARGS=()
if [ -f "$MKARGS_FILE" ]; then
    # shellcheck disable=SC1090
    . "$MKARGS_FILE"
    HOST_MAKE_ARGS=("${KERNEL_HOST_MAKE_ARGS[@]}")
fi

DEFCONFIG="${DEFCONFIG:-even_defconfig}"
ARCH="${ARCH:-arm64}"
JOBS="${JOBS:-$(nproc)}"
OUT="${OUT:-out}"

echo "==> make $DEFCONFIG"
make O="$OUT" ARCH="$ARCH" "$DEFCONFIG"

echo "==> building with -j$JOBS"
make -j"$JOBS" O="$OUT" \
    ARCH="$ARCH" \
    LD=ld.lld \
    AR=llvm-ar \
    AS=llvm-as \
    NM=llvm-nm \
    OBJDUMP=llvm-objdump \
    STRIP=llvm-strip \
    CC=clang \
    CLANG_TRIPLE=aarch64-linux-gnu- \
    CROSS_COMPILE=aarch64-linux-gnu- \
    CROSS_COMPILE_ARM32=arm-linux-gnueabihf- \
    CONFIG_NO_ERROR_ON_MISMATCH=y \
    CONFIG_DEBUG_SECTION_MISMATCH=y \
    "${HOST_MAKE_ARGS[@]}" \
    V=0

echo
echo "==> built: $OUT/arch/arm64/boot/Image.gz-dtb"
ls -l "$OUT/arch/arm64/boot/Image.gz-dtb"
