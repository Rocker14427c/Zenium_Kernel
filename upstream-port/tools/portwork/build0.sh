#!/bin/bash
# build0.sh - environment proof + build-38 baseline: configure the restored series tree and get
# `make prepare` green, which is the precondition every later layer's gate assumes. Nothing here
# ports display code; it only proves that the recreated toolchain can configure and prepare this
# tree, and that scripts/dtc builds (the DTB gates depend on it).
set -o pipefail
ROOT=/home/user/portwork
REPO=/home/user/Zenium_Kernel
LOG=$ROOT/logs/build-38.log
exec > >(tee -a "$LOG") 2>&1
say(){ printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }
. $ROOT/tools/env.sh
cd $ROOT/series || exit 1
say "tree: $(git rev-parse --short HEAD) ($(git describe --tags))  prefix=$CROSS_COMPILE  cc=$(${CROSS_COMPILE}gcc -dumpversion)"
say "== [1/4] defconfig =="
make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" defconfig 2>&1 | tail -3
say "== [2/4] configs/apply.sh (recorded recipe, never ./build.sh configure) =="
bash $ROOT/configs/apply.sh 2>&1 | tail -14
say "== [3/4] make prepare (host progs, scripts/dtc, genksyms) =="
time make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" prepare 2>&1 | tail -25
say "  prepare rc=${PIPESTATUS[0]}"
say "== [4/4] the toolchain/DTB artefacts the later gates need =="
for b in scripts/dtc/dtc scripts/kconfig/conf scripts/mod/modpost; do
  [ -x "$b" ] && say "  ok $b ($(sha256sum $b | cut -c1-10))" || say "  MISSING $b"
done
printf '#include <linux/soc/mediatek/mtk-cmdq.h>\nint probe(void);\n' > /tmp/cmdq-probe.c
say "  header compile probe (expects a normal C-compile, no cmdq engine):"
# The include set below is the kernel's own, not a shortcut: with only -I./include this probe died on
# `asm/rwonce.h: No such file or directory` and then on `linux/time_types.h`, which is an artefact of the
# probe and says nothing about the tree. Measured on the 2026-09-06 restored tree: rc=0 with all six -I
# paths plus -include linux/kconfig.h, rc=1 with the shortcut. A recovery script that reports a failure
# the build does not have is how a real defect gets explained away later.
KINCLUDES="-I./include -I./include/generated -I./include/uapi -I./arch/arm64/include -I./arch/arm64/include/generated -I./arch/arm64/include/uapi"
${CROSS_COMPILE}gcc -D__KERNEL__ -Wall $KINCLUDES -include linux/kconfig.h -fsyntax-only -x c /tmp/cmdq-probe.c \
  && say "    ok: vendor header path resolves standalone (rc=0)" \
  || say "    FATAL: header probe failed - check KINCLUDES, not the tree"
say "BUILD0_DONE"
