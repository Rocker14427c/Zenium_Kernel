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

# --------------------------------------------------------- build identity --
# scripts/mkcompile_h falls back to `whoami`@`uname -n` when KBUILD_BUILD_USER
# and KBUILD_BUILD_HOST are unset, which bakes the build machine's identity into
# the kernel banner ("Linux version ... (someuser@somehost)"). Pin them so the
# banner credits the kernel author instead of whatever host ran the build.
# Overridable from the environment for reproducible/CI builds.
export KBUILD_BUILD_USER="${KBUILD_BUILD_USER:-Rocker14427c}"
export KBUILD_BUILD_HOST="${KBUILD_BUILD_HOST:-Rocker14427c}"

# ---------------------------------------------------------- KSU-Next version --
# The pinned legacy branch computes its driver version as 30000 + the full
# submodule commit count + 289. The commit count must be complete; a depth-1
# checkout would otherwise report the fallback-era version 30290.
KSU_DIR="$ROOT/KernelSU"

if [ -d "$KSU_DIR/.git" ] || [ -f "$KSU_DIR/.git" ]; then
    KSU_COMMITS="$(git -C "$KSU_DIR" rev-list --count HEAD 2>/dev/null || echo 0)"
    if [ -f "$ROOT/.git/modules/KernelSU/shallow" ] || [ "${KSU_COMMITS:-0}" -le 1 ]; then
        echo "==> KernelSU-Next submodule is shallow (commit count = ${KSU_COMMITS:-0})"
        echo "==> fetching full legacy-branch history for the correct driver version"
        git -C "$KSU_DIR" fetch --unshallow origin legacy \
            || { echo "ERROR: could not unshallow the KernelSU-Next submodule." >&2
                 echo "       Run: git -C KernelSU fetch --unshallow origin legacy" >&2
                 exit 1; }
        KSU_COMMITS="$(git -C "$KSU_DIR" rev-list --count HEAD 2>/dev/null || echo 0)"
    fi
    if [ "${KSU_COMMITS:-0}" -le 1 ]; then
        echo "ERROR: KernelSU-Next history is incomplete; refusing a fallback-version build." >&2
        exit 1
    fi
    KSU_VERSION=$((30000 + KSU_COMMITS + 289))
    echo "==> KernelSU-Next commits: $KSU_COMMITS -> KSU_VERSION: $KSU_VERSION"
    echo "==> install a matching KernelSU-Next manager and SUSFS userspace helper"
else
    echo "ERROR: KernelSU-Next submodule metadata is missing; cannot derive its driver version." >&2
    exit 1
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
