#!/bin/sh
# env.sh - the environment every gate in this port sources before it runs `make`.
#
# This file used to live only in /home/user/portwork/tools/, outside the repo, and that is exactly
# why a sandbox reset broke the recipe: restore.sh step [4/5] sources it, so without it the restore
# itself failed. It is now versioned here (upstream-port/tools/portwork/env.sh) and `cp -a` into
# $ROOT/tools/ is part of the restore. Do not delete it from either place.
#
# Nothing in the kernel tree is patched to fit this sandbox: everything below is PATH + variables.
#
# Why these three path entries, each from a measurement (see report/display-bringup-plan.md s9):
#  * $ROOT/tools/build-tools/bin - bison 3.8.2 / flex 2.6.4 / m4 1.4.19 / gavinhoward-bc 6.5.0 /
#    make 4.3 from LineageOS/android_prebuilts_build-tools. apt is dead here (no sources.list, all
#    distro mirrors time out), and this set has NO dtc and NO ld, so it cannot shadow the cross
#    linker or the in-tree dtc.
#  * $ROOT/tools/gcc/bin - the aarch64 gcc 9.3 driver symlinks (Buildroot-relocated; the drivers are
#    a toolchain-wrapper in front of *.br_real). This is what `scripts/Kconfig.include:39
#    *** compiler not found` fails on when it is missing.
#  * $ROOT/tools/gcc/bin - the aarch64 gcc 9.3 drivers (Buildroot-relocated: the drivers are a
#    toolchain-wrapper in front of *.br_real, and that wrapper is what finds the sysroot). The two
#    gcc candidates are probed rather than assumed, because the tarball has been unpacked both with
#    and without an extra directory level. Nothing else from that SDK goes on PATH - see the
#    `as: unrecognized option` note below.
ROOT=${PORTWORK:-/home/user/portwork}
REPO=${ZENIUM_REPO:-/home/user/Zenium_Kernel}

# Locate the cross bin directories once; fall back to the recorded layout if discovery finds nothing.
GTARGET=""
for c in "$ROOT/tools/gcc/bin"; do
  ls "$c"/*-gcc >/dev/null 2>&1 && GTARGET="$c" && break
done
[ -n "$GTARGET" ] || for c in "$ROOT"/tools/gcc/*/bin; do
  ls "$c"/*-gcc >/dev/null 2>&1 && GTARGET="$c" && break
done
GTARGET=${GTARGET:-$ROOT/tools/gcc/bin}

PATH="$ROOT/tools/build-tools/bin:$GTARGET"
PATH="$PATH:/usr/local/bin:/usr/bin:/bin"
export PATH

# The triple-prefixed binutils that also exist at $ROOT/tools/gcc/aarch64-buildroot-linux-gnu/bin are
# deliberately NOT added to PATH, even though they are there under *unprefixed* names (as, ld, ar,
# objcopy, nm, objdump). Measured 2026-09-05, after a sandbox reset: an env.sh that did add that
# directory made the kernel's own host-tool build die, because the AArch64 `as` then shadowed the
# host x86_64 one -
#   as: unrecognized option '--64'
#   *** [scripts/Makefile.host:95: scripts/basic/fixdep] Error 1
#   *** Makefile:563: scripts_basic] Error 2  (so `make defconfig` produced no .config at all)
# The kernel reaches binutils only as ${CROSS_COMPILE}ld / ${CROSS_COMPILE}objcopy, and every such
# prefixed name resolves through $GTARGET, so the sysroot bin/ dir is never needed on PATH.
# Same trap on the other side: a gate that inspects the produced aarch64 objects must call
# ${CROSS_COMPILE}nm explicitly, because /usr/bin/nm here is built for x86 targets.

# The prefix this series was built with since build-38: gcc 9.3.0 (Buildroot 2020.08), ld 2.33.1.
# Derived from the driver that discovery actually found, so an SDK spelling either
# `aarch64-buildroot-linux-gnu-` or plain `aarch64-linux-gnu-` configures without editing this file.
# Deliberately NOT hardcoded: a wrong prefix is the `*** compiler not found` failure mode again.
# No KCFLAGS/HOSTCC overrides are exported here on purpose - the recorded gates ran on the defaults,
# and a -Wno-error injected from the environment would make a later gate incomparable with them.
GCC_DRIVER=$(ls "$GTARGET"/*-gcc 2>/dev/null | head -1)
if [ -n "$GCC_DRIVER" ]; then
  CROSS_COMPILE=$(basename "$GCC_DRIVER"); CROSS_COMPILE=${CROSS_COMPILE%-gcc}-
else
  CROSS_COMPILE=aarch64-buildroot-linux-gnu-
fi
export CROSS_COMPILE

export ARCH=arm64
# The build-tools lib64 ships the shared objects some of its binaries were linked against.
[ -d "$ROOT/tools/build-tools/lib64" ] && LD_LIBRARY_PATH="$ROOT/tools/build-tools/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" && export LD_LIBRARY_PATH
# m4 for the build-tools bison, and the bison datadir - both measured 2026-09-05 after a reset, both
# Bazel-relocation artifacts of the LineageOS prebuilt, both silent-failure-shaped:
#  * that bison has /usr/bin/m4 compiled in and this image ships no /usr/bin/m4, so every run died with
#    `bison: m4 subprocess failed` (exit 1), which inside a build shows up as
#    *** [scripts/Makefile.host:17: scripts/kconfig/parser.tab.h] Error 1 -> no .config at all.
#    bison honors $M4, so point it at the m4 that sits next to bison. No root, tree untouched.
#  * its pkgdatadir is baked as /nonexistent/common/bison, where m4sugar/m4sugar.m4 and the skeletons
#    live; the tarball keeps those under common/bison at the REPO ROOT (not linux-x86/common), and
#    restore.sh symlinks $ROOT/tools/build-tools to /nonexistent so the baked path resolves. If that
#    link is missing, bison says `/nonexistent/common/bison/m4sugar/m4sugar.m4: cannot open`.
if [ -x "$ROOT/tools/build-tools/bin/m4" ]; then
  M4="$ROOT/tools/build-tools/bin/m4"; export M4
fi
[ -f /nonexistent/common/bison/m4sugar/m4sugar.m4 ] || \
  echo "env.sh: WARNING bison datadir missing; run: sudo ln -sfn $ROOT/tools/build-tools /nonexistent" >&2

# `bc` is a make prerequisite for the kernel's math and the sandbox has none; build-tools ships
# gavinhoward-bc, which the kernel accepts via a `bc` symlink made by restore.sh.
[ -x "$ROOT/tools/build-tools/bin/bc" ] || ln -sf gavinhoward-bc "$ROOT/tools/build-tools/bin/bc" 2>/dev/null

# PORT_ENV_QUIET=1 keeps the report lines out of gates that parse make output.
if [ -z "$PORT_ENV_QUIET" ]; then
  echo "env.sh: PATH head = $(echo "$PATH" | cut -d: -f1-2)"
  echo "env.sh: CROSS_COMPILE=$CROSS_COMPILE -> $(command -v ${CROSS_COMPILE}gcc || echo MISSING)"
  ${CROSS_COMPILE}gcc --version 2>&1 | head -1 | sed 's/^/env.sh: cc  /'
  for t in bison flex m4 bc; do
    printf 'env.sh: %-6s %s\n' "$t" "$(command -v $t >/dev/null 2>&1 && $t --version 2>&1 | head -1 || echo MISSING)"
  done
fi
