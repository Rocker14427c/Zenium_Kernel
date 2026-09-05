#!/bin/bash
# fullbuild0085.sh - the gate the per-directory gates could not provide: build the WHOLE tree at the
# 0085 tip and link it.  Found necessary by the 0085 regression itself (0084 broke
# `make drivers/misc/mediatek/video/` while every gate that named .../dispsys/ stayed green), so
# "every directory the series wires" is still only a subset and a link has never been demonstrated
# since 0081. Stages are separated and each is timed; the log is the evidence, nothing here is a
# claim about the device.
#
#   build    = make -j2 (defconfig + in-repo fragments + the recorded SYMS via configs/apply.sh)
#   vmlinux  = the link the sandbox has never produced post-0082
#   image    = Image.gz-dtb (the DTB-appended boot payload)
#   modules  = the 840-.ko set
set -o pipefail
ROOT=/home/user/portwork
WT=$ROOT/buildfull
LOGD=$ROOT/logs; mkdir -p "$LOGD"
. "$ROOT/tools/env.sh" >/dev/null

stage() { # name  cmd...
  local name=$1; shift
  local t0=$(date +%s)
  echo "$(date +%H:%M:%S) >>> $name : $*"
  "$@" > "$LOGD/full-0085-$name.log" 2>&1; local rc=$?
  local t1=$(date +%s)
  printf '%s <<< %s rc=%d %ds  error:=%d  warning:=%d  objs=%s\n' \
    "$(date +%H:%M:%S)" "$name" "$rc" $((t1-t0)) \
    "$(grep -c ' error:' "$LOGD/full-0085-$name.log")" \
    "$(grep -c ' warning:' "$LOGD/full-0085-$name.log")" \
    "$(find "$WT" -name '*.o' 2>/dev/null | wc -l)" | tee -a "$LOGD/full-0085.summary"
  [ $rc -eq 0 ] || { echo "$(date +%H:%M:%S) ABORT at $name" | tee -a "$LOGD/full-0085.summary"; exit $rc; }
}

: > "$LOGD/full-0085.summary"
if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
  git -C "$ROOT/series" worktree add --detach "$WT" HEAD > "$LOGD/full-0085-worktree.log" 2>&1 \
    || { echo "worktree add failed"; tail -5 "$LOGD/full-0085-worktree.log"; exit 1; }
fi
cd "$WT" || exit 1
echo "tree=$(git rev-parse 'HEAD^{tree}') head=$(git rev-parse --short HEAD) dirty=$(git status --porcelain | grep -v '^??' | wc -l)" \
  | tee -a "$LOGD/full-0085.summary"

stage 00-identity  git rev-parse HEAD^{tree}
[ -f .config ] || make ARCH=arm64 defconfig > "$LOGD/full-0085-defconfig.log" 2>&1 || { echo defconfig failed; exit 1; }
TREE="$WT" REPO=/home/user/Zenium_Kernel "$ROOT/configs/apply.sh" >> "$LOGD/full-0085-defconfig.log" 2>&1 \
  || { echo "apply.sh failed"; tail -20 "$LOGD/full-0085-defconfig.log" | tee -a "$LOGD/full-0085.summary"; exit 1; }
echo "config sha256=$(sha256sum .config | cut -c1-12) (series tree at 0084 was 758ae54339bf - a Makefile-only patch must not move it)" \
  | tee -a "$LOGD/full-0085.summary"
make ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" prepare -j2 >> "$LOGD/full-0085-prepare.log" 2>&1 \
  || { echo "make prepare failed"; tail -20 "$LOGD/full-0085-prepare.log" | tee -a "$LOGD/full-0085.summary"; exit 1; }
echo "$(date +%H:%M:%S) make prepare ok" | tee -a "$LOGD/full-0085.summary"

stage 10-vmlinux make ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" -j2 vmlinux
stage 20-image   make ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" -j2 Image.gz-dtb
stage 30-modules make ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" -j2 modules

for f in arch/arm64/boot/Image arch/arm64/boot/Image.gz arch/arm64/boot/Image.gz-dtb arch/arm64/boot/dts/mediatek/mt6768.dtb vmlinux; do
  [ -f "$f" ] && printf '%s %10d B  %s\n' "$f" "$(stat -c%s "$f")" "$(sha256sum "$f" | cut -c1-12)" >> "$LOGD/full-0085.summary" \
             || printf '%s MISSING\n' "$f" >> "$LOGD/full-0085.summary"
done
printf 'ko=%s  objects=%s\n' "$(find . -name '*.ko' | wc -l)" "$(find . -name '*.o' | wc -l)" >> "$LOGD/full-0085.summary"
nm_out=$(${CROSS_COMPILE}nm vmlinux 2>/dev/null | grep -cE ' T disp_helper_get_option$' || true)
printf 'vmlinux disp_helper_get_option as T: %s\n' "$nm_out" >> "$LOGD/full-0085.summary"
echo "$(date +%H:%M:%S) ALL STAGES DONE" | tee -a "$LOGD/full-0085.summary"
