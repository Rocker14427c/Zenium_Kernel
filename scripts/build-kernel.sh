#!/usr/bin/env bash
#
# build-kernel.sh - one build entry point, used by the GitHub workflow and by
#                   humans. Keeps the toolchain provisioning, the driver-version
#                   sanity check and the packaging in ONE place so CI and local
#                   builds cannot drift apart.
#
# Usage:
#   scripts/build-kernel.sh [--defconfig even_defconfig] [--out out] [--jobs N]
#                           [--branch NAME] [--download-clang]
#
# Environment:
#   CLANG_DIR   toolchain root containing bin/clang (default: $ROOT/.clang)
#   JOBS        make -j value (default: nproc)
#   SB          ccache dir for ccache builds (optional)
#
# The script stops on the first problem: a missing submodule commit, a shallow
# submodule (wrong KSU version), an unexpected kernel branch, or a build error.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEFCONFIG="even_defconfig"
OUT="out"
JOBS="$(nproc)"
WANT_BRANCH=""
DOWNLOAD_CLANG=0

while [ $# -gt 0 ]; do
    case "$1" in
        --defconfig)      DEFCONFIG="$2"; shift 2 ;;
        --out)            OUT="$2"; shift 2 ;;
        --jobs)           JOBS="$2"; shift 2 ;;
        --branch)         WANT_BRANCH="$2"; shift 2 ;;
        --download-clang) DOWNLOAD_CLANG=1; shift ;;
        -h|--help)        sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m==>\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- identity --
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [ -n "$WANT_BRANCH" ] && [ "$BRANCH" != "$WANT_BRANCH" ]; then
    die "building branch '$BRANCH' but --branch '$WANT_BRANCH' was requested"
fi
ZENIUM_VERSION="$(grep -m1 -E '^export version=' run.sh 2>/dev/null | cut -d= -f2- | tr -d '"')"
ZENIUM_VERSION="${ZENIUM_VERSION:--V0.0}"
say "branch $BRANCH @ $COMMIT, run.sh version $ZENIUM_VERSION"

# --------------------------------------------------------------- submodule --
if [ ! -e KernelSU/kernel ] && [ ! -e KernelSU/Kbuild ]; then
    say "initialising the KernelSU submodule"
    git submodule sync -- KernelSU
    git submodule update --init KernelSU
fi
[ -d KernelSU/.git ] || [ -f KernelSU/.git ] || [ -e .git/modules/KernelSU ] \
    || die "KernelSU is not a git checkout - the driver version cannot be derived"

KSU_PIN_REPO="$(git config -f .gitmodules submodule.KernelSU.url || echo '?')"
KSU_PIN_COMMIT="$(git ls-tree HEAD KernelSU | awk '{print $3}')"
KSU_HAVE="$(git -C KernelSU rev-parse HEAD 2>/dev/null || echo missing)"
[ "$KSU_HAVE" = "$KSU_PIN_COMMIT" ] \
    || die "submodule is at $KSU_HAVE but the branch pins $KSU_PIN_COMMIT"

# A shallow submodule silently produces the wrong KSU version code.
if [ -f .git/modules/KernelSU/shallow ] || [ -f KernelSU/.git/shallow ]; then
    KSU_COUNT="$(git -C KernelSU rev-list --count HEAD 2>/dev/null || echo 1)"
    if [ "$KSU_COUNT" -le 1 ]; then
        say "submodule is shallow; fetching full history for a correct driver version"
        git -C KernelSU fetch --unshallow origin \
            || die "cannot unshallow KernelSU; abort rather than ship a wrong version code"
    fi
fi
KSU_COUNT="$(git -C KernelSU rev-list --count HEAD 2>/dev/null || echo 0)"
case "$KSU_PIN_REPO" in
    *KernelSU-Next*|*KernelSU_NEXT*)  KSU_VER=$((30000 + KSU_COUNT + 289)) ;;
    *Baka-SU*|*ReSukiSU*|*bakasu*)    KSU_VER=$((30000 + KSU_COUNT + 700)) ;;
    *) KSU_VER=$KSU_COUNT ; warn "unknown submodule origin; driver version is raw commit count" ;;
esac
say "submodule $KSU_PIN_REPO @ ${KSU_PIN_COMMIT:0:12}, $KSU_COUNT commits -> driver version $KSU_VER"
# Hook mode is a Kconfig *choice*: on BakaSU, KSU_SUSFS is one of the choice
# entries, so SUSFS builds use the inline-hook path and MANUAL_HOOK may be n.
# Only flag the genuinely broken case (neither selected).
HOOK_MODE="$(grep -E '^CONFIG_KSU_(SUSFS|MANUAL_HOOK|TRACEPOINT_HOOK)=y' "arch/arm64/configs/$DEFCONFIG" 2>/dev/null | head -1)"
[ -n "$HOOK_MODE" ] || warn "no KernelSU hook mode is enabled in $DEFCONFIG"

# --------------------------------------------------------------- toolchain --
CLANG_DIR="${CLANG_DIR:-$ROOT/.clang}"
if [ ! -x "$CLANG_DIR/bin/clang" ]; then
    if [ "$DOWNLOAD_CLANG" -eq 1 ]; then
        say "downloading the Android clang r416183b toolchain (~1.7 GB, shallow clone)"
        rm -rf "$CLANG_DIR"
        git clone --depth=1 \
            https://github.com/anrui2032/android_prebuilts_clang_kernel_linux-x86_clang-r416183b \
            "$CLANG_DIR"
    else
        die "no clang at $CLANG_DIR (pass --download-clang, or set CLANG_DIR)"
    fi
fi
export PATH="$CLANG_DIR/bin:$PATH"
command -v ld.lld >/dev/null || die "ld.lld missing from $CLANG_DIR/bin"
say "toolchain: $("$CLANG_DIR/bin/clang" --version | head -1)"

# host tools the 4.19 tree needs
for t in bison flex bc perl make; do
    command -v "$t" >/dev/null || die "host tool '$t' missing (install: bison flex bc perl make)"
done
say "host tools: bison/flex/bc present"

# ------------------------------------------------------------------ build ---
export ARCH=arm64
export KBUILD_BUILD_USER="${KBUILD_BUILD_USER:-Rocker14427c}"
export KBUILD_BUILD_HOST="${KBUILD_BUILD_HOST:-Rocker14427c}"
export KBUILD_BUILD_VERSION="${KBUILD_BUILD_VERSION:-1}"
export LC_ALL=C

# LLVM=1 + LLVM_IAS=1 is what this tree was always built with: it makes clang
# use its integrated assembler AND falls back to the host `as` for *.S files,
# which is the only way this vendor tree assembles with a clang-only toolchain.
export LLVM=1
export LLVM_IAS=1
MAKE_VARS=(
    ARCH=arm64 O="$OUT" V=0
    CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu-
    CROSS_COMPILE_ARM32=arm-linux-gnueabihf-
)
if command -v ccache >/dev/null && [ -n "${SB:-}" ]; then
    MAKE_VARS+=(CC="ccache clang")
fi

say "defconfig: $DEFCONFIG"
make "${MAKE_VARS[@]}" "$DEFCONFIG"

say "building with -j$JOBS (out=$OUT)"
set +e
make -j"$JOBS" "${MAKE_VARS[@]}" 2>&1 | tee "$OUT/build.log"
makerc=${PIPESTATUS[0]}
set -e
if [ "$makerc" -ne 0 ]; then
    printf '\033[1;31m==>\033[0m make failed with rc=%s\n' "$makerc" >&2
    grep -nE "error:|Error [0-9]+|undefined symbol|No rule to make" "$OUT/build.log" | tail -20 >&2 || true
    exit "$makerc"
fi

# ---------------------------------------------------------------- outputs ---
IMG="$OUT/arch/arm64/boot/Image.gz-dtb"
[ -s "$IMG" ] || IMG="$OUT/arch/arm64/boot/Image"
[ -s "$IMG" ] || die "build finished without producing a kernel image (see $OUT/build.log)"

say "image: $IMG ($(stat -c %s "$IMG") bytes)"
say "sha256: $(sha256sum "$IMG" | cut -d' ' -f1)"

# The banner is the only place the *shipped* identity can be read back.
if command -v gzip >/dev/null; then
    BANNER="$(gzip -dc "$IMG" 2>/dev/null | strings | grep -aoE 'Linux version [^ ]+ \([^)]*\)' | head -1 || true)"
    [ -n "$BANNER" ] && say "banner: $BANNER"
fi
grep -qE "^CONFIG_KSU_SUSFS=y" "$OUT/.config"  || warn "SUSFS not enabled in the built config"
grep -qE "^CONFIG_NOMOUNT=y"  "$OUT/.config"  || warn "NoMount not enabled in the built config"
SUSFS_BUILT="$(sed -n 's/^#define SUSFS_VERSION "\(.*\)"/\1/p' include/linux/susfs.h | head -1)"
say "SUSFS $SUSFS_BUILT, NoMount base $(sed -n 's/^#define NOMOUNT_BASE_VERSION "\(.*\)"/\1/p' fs/nomount/nomount.h | head -1)"

cat > "$OUT/build-info.txt" <<EOF
branch=$BRANCH
commit=$COMMIT
zenium_version=$ZENIUM_VERSION
defconfig=$DEFCONFIG
ksu_repo=$KSU_PIN_REPO
ksu_commit=$KSU_PIN_COMMIT
ksu_commit_count=$KSU_COUNT
ksu_driver_version=$KSU_VER
susfs_version=$SUSFS_BUILT
image_sha256=$(sha256sum "$IMG" | cut -d' ' -f1)
built_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
say "wrote $OUT/build-info.txt"
