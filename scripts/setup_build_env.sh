#!/usr/bin/env bash
#
# setup_build_env.sh - provision a *reproducible* build environment for this
#                     Linux 4.19 non-GKI kernel (arch/arm64, clang/LLVM).
#
# The kernel itself needs, on the *build host*:
#   clang (with ld.lld, llvm-ar, llvm-nm, llvm-strip, llvm-as, llvm-objcopy)
#   bison + flex          -> scripts/kconfig/{zconf.tab.c,zconf.lex.c}
#   m4                    -> bison's skeleton post-processor
#   bc                    -> include/generated/timeconst.h (kernel/time/timeconst.bc)
#   openssl headers+lib   -> host tools scripts/sign-file, scripts/extract-cert
#                            (only needed because CONFIG_MODULE_SIG=y)
#
# Everything except openssl is fetched from sources that work from a plain
# sandbox/CI box with no apt access.  Run this script once, then source the
# generated env file (or just call scripts/build_susfs.sh, which does it for you).
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${KERNEL_TOOLS_DIR:-$ROOT/.kernel-tools}"
mkdir -p "$TOOLS_DIR/bin"

say() { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[-]\033[0m %s\n' "$*" >&2; exit 1; }

PY=${PYTHON:-python3}

# ---------------------------------------------------------------- clang ------
# Android clang r416183b (clang 12.0.5).  Same LLVM major as the one the
# original CI (Google prebuilts) used for 4.19 trees, and it is a plain
# `git clone` (no release assets involved).
CLANG_DIR="$TOOLS_DIR/clang"
if [ ! -x "$CLANG_DIR/bin/clang" ]; then
    say "cloning Android clang r416183b (this is ~1.7 GB) ..."
    rm -rf "$CLANG_DIR"
    git clone --depth=1 \
        https://github.com/anrui2032/android_prebuilts_clang_kernel_linux-x86_clang-r416183b \
        "$CLANG_DIR"
fi
"$CLANG_DIR/bin/clang" --version | head -1

# ------------------------------------------------- bison / flex / m4 via pip --
# manylinux wheels on PyPI vendor the real GNU binaries (and their data files).
# Each wheel is unpacked under $TOOLS_DIR/wheels/<dist>/ and the directory that
# holds the binary is prepended to PATH -- bison resolves its m4sugar skeletons
# relative to the executable, so the payload dir must stay next to the binary.
WHEEL_DIR="$TOOLS_DIR/wheels"
EXTRA_PATH=""

fetch_pypi() { # $1 = dist name, $2 = path suffix of the binary inside the wheel
    local name="$1" rel="$2"
    local dl dest
    dest="$WHEEL_DIR/$name"
    if [ -n "$(find "$dest" -type f -path "*$rel" 2>/dev/null | head -1)" ]; then
        _register_pypi_bin "$name" "$rel"
        return 0
    fi
    dl="$(mktemp -d)"
    say "downloading $name from PyPI ..."
    ( cd "$dl" && "$PY" -m pip download "$name" --no-deps -q )
    local whl; whl="$(ls "$dl"/*.whl | head -1)"
    [ -n "$whl" ] || die "no wheel for $name"
    mkdir -p "$dest"
    ( cd "$dl" && "$PY" -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$whl" "$dest" )
    rm -rf "$dl"
    local found; found="$(find "$dest" -type f -path "*$rel" | head -1)"
    [ -n "$found" ] || die "binary $rel not found inside $name"
    _register_pypi_bin "$name" "$rel"
}

_register_pypi_bin() {
    local name="$1" rel="$2" bin
    bin="$(find "$WHEEL_DIR/$name" -type f -path "*$rel" | head -1)"
    [ -n "$bin" ] || die "binary $rel not found inside $name"
    chmod -R a+rX "$WHEEL_DIR/$name"
    chmod a+x "$bin"
    case ":$EXTRA_PATH:" in
        *":$(dirname "$bin"):"*) ;;
        *) EXTRA_PATH="$(dirname "$bin")${EXTRA_PATH:+:$EXTRA_PATH}" ;;
    esac
}

fetch_pypi bison_bin "_payload/bin/bison"
fetch_pypi flex_bin  "scripts/flex"
fetch_pypi cmeel-m4  "cmeel.prefix/bin/m4"

# bison/flex resolve their data files relative to argv[0], so they must be run
# from inside their wheel payload (EXTRA_PATH above).  m4 has no data files, so a
# plain symlink is enough and keeps the hard-coded /usr/bin/m4 override simple.
M4_BIN="$(find "$WHEEL_DIR/cmeel-m4" -type f -path '*cmeel.prefix/bin/m4' | head -1)"
[ -n "$M4_BIN" ] || die "m4 binary not found"
ln -sf "$M4_BIN" "$TOOLS_DIR/bin/m4"

# bison built on a machine that had /usr/bin/m4 hard-codes that path; override.
export M4="$TOOLS_DIR/bin/m4"

# --------------------------------------------------------------- bc shim -----
# GNU bc is not available on most minimal hosts.  kernel/time/timeconst.bc only
# needs a handful of features, so a tiny python stand-in is enough and produces
# byte-identical output for the algorithm it implements.
if [ ! -x "$TOOLS_DIR/bin/bc" ]; then
    say "installing python bc shim (kernel/time/timeconst.bc) ..."
    install -m755 "$ROOT/scripts/bc_shim.py" "$TOOLS_DIR/bin/bc"
fi

# ------------------------------------------------------------- openssl -------
# scripts/sign-file + scripts/extract-cert need <openssl/*.h> and -lcrypto.
# Node.js ships a complete openssl header tree; most distros ship libcrypto.so.3.
OPENSSL_INC=""
for c in /usr/local/include/node /usr/include /usr/include/x86_64-linux-gnu; do
    [ -f "$c/openssl/opensslv.h" ] && { OPENSSL_INC="$c"; break; }
done
CRYPTO_LIB=""
for c in /usr/lib/x86_64-linux-gnu/libcrypto.so.3 \
         /usr/lib/x86_64-linux-gnu/libcrypto.so \
         /usr/lib64/libcrypto.so /usr/lib/libcrypto.so; do
    [ -e "$c" ] && { CRYPTO_LIB="$c"; break; }
done
if [ -z "$OPENSSL_INC" ] || [ -z "$CRYPTO_LIB" ]; then
    warn "openssl headers/libcrypto not auto-detected;"
    warn "install libssl-dev (or edit $TOOLS_DIR/mkargs.sh) if you need"
    warn "scripts/sign-file and scripts/extract-cert."
    OPENSSL_INC="${OPENSSL_INC:-/usr/include}"
    CRYPTO_LIB="${CRYPTO_LIB:--lcrypto}"
fi

# ------------------------------------------------------------- env file ------
# NOTE: the HOSTCFLAGS_*/HOSTLDLIBS_* entries are *make* variables and cannot be
# exported from a shell (they contain '-'), so they live in mkargs.sh and are
# passed on the make command line by scripts/build_susfs.sh.
cat > "$TOOLS_DIR/env.sh" <<EOF
# Generated by scripts/setup_build_env.sh -- source this before building.
export PATH="$TOOLS_DIR/bin:$EXTRA_PATH:$CLANG_DIR/bin:\$PATH"
export M4="$TOOLS_DIR/bin/m4"
export ARCH=arm64
export LLVM=1
export LLVM_IAS=1
export CLANG_TRIPLE=aarch64-linux-gnu-
export CROSS_COMPILE=aarch64-linux-gnu-
export CROSS_COMPILE_ARM32=arm-linux-gnueabihf-
export LD=ld.lld
export AR=llvm-ar
export AS=llvm-as
export NM=llvm-nm
export OBJDUMP=llvm-objdump
export STRIP=llvm-strip
export OBJCOPY=llvm-objcopy
export READELF=llvm-readelf
export OBJSIZE=llvm-size
EOF

cat > "$TOOLS_DIR/mkargs.sh" <<EOF
# Generated by scripts/setup_build_env.sh -- host openssl overrides for make.
# (make variable names are not valid shell identifiers, so no 'export' here)
KERNEL_HOST_MAKE_ARGS=(
  "HOSTCFLAGS_sign-file.o=-I${OPENSSL_INC}"
  "HOSTCFLAGS_extract-cert.o=-I${OPENSSL_INC}"
  "HOSTLDLIBS_sign-file=${CRYPTO_LIB}"
  "HOSTLDLIBS_extract-cert=${CRYPTO_LIB}"
)
EOF

say "build environment ready -> $TOOLS_DIR/env.sh"
say "build with:  bash scripts/build_susfs.sh"
