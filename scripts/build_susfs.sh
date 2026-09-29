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

# --------------------------------------------------------------- KSU version --
# KernelSU/kernel/Kbuild derives the version reported to the manager as
#
#     KSU_VERSION = 30000 + $(git -C KernelSU rev-list --count HEAD) + 700
#
# There is no Kconfig override. A *shallow* submodule clone (depth 1) makes
# rev-list report 1, which yields KSU_VERSION = 30701, and every ReSukiSU
# manager refuses to work with that ("version 30701 is too low ... please
# upgrade to 35040 or higher") - no superuser UI, no feature toggles, nothing.
#
# So the submodule must carry its full history, and we verify the resulting
# number before spending 30 minutes on a build that cannot work.
KSU_MIN_VERSION="${KSU_MIN_VERSION:-35040}"
KSU_DIR="$ROOT/KernelSU"

if [ -d "$KSU_DIR/.git" ] || [ -f "$KSU_DIR/.git" ]; then
    KSU_COMMITS="$(git -C "$KSU_DIR" rev-list --count HEAD 2>/dev/null || echo 0)"
    if [ -f "$ROOT/.git/modules/KernelSU/shallow" ] || [ "${KSU_COMMITS:-0}" -le 1 ]; then
        echo "==> KernelSU submodule is shallow (rev-list --count HEAD = ${KSU_COMMITS:-0})"
        echo "==> fetching full history so KSU_VERSION is not stuck at 30701"
        git -C "$KSU_DIR" fetch --unshallow origin \
            || { echo "ERROR: could not unshallow the KernelSU submodule." >&2
                 echo "       Run: git -C KernelSU fetch --unshallow origin" >&2
                 exit 1; }
        KSU_COMMITS="$(git -C "$KSU_DIR" rev-list --count HEAD 2>/dev/null || echo 0)"
    fi
    KSU_VERSION=$((30000 + KSU_COMMITS + 700))
    echo "==> KernelSU commits: $KSU_COMMITS -> KSU_VERSION: $KSU_VERSION"
    if [ "$KSU_VERSION" -lt "$KSU_MIN_VERSION" ]; then
        echo "ERROR: KSU_VERSION $KSU_VERSION is below $KSU_MIN_VERSION; the ReSukiSU" >&2
        echo "       manager will refuse to run (no superuser UI, no features)." >&2
        echo "       Fix: git -C KernelSU fetch --unshallow origin" >&2
        exit 1
    fi
else
    echo "WARNING: no KernelSU git metadata found at $KSU_DIR;" >&2
    echo "         KSU_VERSION cannot be derived and the manager may reject the build." >&2
fi

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
