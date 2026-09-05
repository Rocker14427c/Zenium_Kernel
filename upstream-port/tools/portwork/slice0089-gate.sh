#!/bin/bash
# slice0089-gate.sh - gate for patch 0089 (MT6370 sub-PMIC DSV as the provider of the panel bias rails).
#
#   TREE=/home/user/portwork/series bash /home/user/portwork/slice0089-gate.sh
#
# Any tree at the 0089 tip works; after a sandbox reset, restore.sh's `series` tree is exactly that, and
# its `git rev-parse HEAD^{tree}` must equal the published 7320325c38fdc188de726f3ba658d0f6b80e7eb6.
#
# Why this script looks like this instead of "make and grep error:": the first version of this gate
# reported "0 undefined references" in BOTH directions, which read as a pass but meant the build had died
# at the compile stage (rt-regmap/Makefile was missing an -I) and never reached the link at all. Every
# stage below therefore asserts that the thing it is measuring happened - the `LD vmlinux` marker, the
# object count, a non-empty name set - and treats an empty result as a failure rather than a clean bill.
# The second lesson it encodes is that a warm tree lies: after one ON run, `lcm_pmic.o` was still sitting
# in the directory while the switch was off, so the objects whose existence is the claim get deleted and
# rebuilt from scratch, and the stale display/lcm .o files are cleared before the off run.
LOG=${LOG:-/home/user/portwork/logs/slice0089-gate-$(date -u +%Y%m%dT%H%M%SZ).log}
: > "$LOG"; exec >>"$LOG" 2>&1
set -o pipefail
START=$(date +%s)
. /home/user/portwork/tools/env.sh
NM="${CROSS_COMPILE}nm"
cd "$TREE" || exit 1
echo "=== gate start $(date -Is) ==="
echo "tree: $(git rev-parse HEAD^{tree})  HEAD=$(git rev-parse --short HEAD)"
[ "$(git rev-parse HEAD^{tree})" = "7320325c38fdc188de726f3ba658d0f6b80e7eb6" ] \
  && echo "tree matches the published 0089 tip: yes" || echo "WARNING: tree is NOT the published 0089 tip"
d=$(git status --porcelain | grep -vc '^?? \(arch/arm64/boot\|vmlinux\|System.map\|.tmp_\|.*\.o$\|.*\.cmd$\)' || true)
echo "tracked changes outside build outputs: $d"

echo "--- [1] config of record (board fragments, display switch off) ---"
/home/user/portwork/configs/apply.sh; echo "apply.sh rc=$?"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "config-sha: $(sha256sum .config | cut -c1-12)  (0089 round: 099cdd6421b6)"
grep -E "^CONFIG_(MFD_MT6370_PMU|MT6370_PMU_DSV|RT_REGMAP|MFD_CORE)=|^# CONFIG_MTK_DISP_BRINGUP" .config | tr '\n' ' '; echo
NEWDIRS="drivers/misc/mediatek/pmic/mt6370/v1 drivers/misc/mediatek/rt-regmap drivers/misc/mediatek/lcm"
NEWOBJS_P="drivers/misc/mediatek/pmic/mt6370/v1 drivers/misc/mediatek/rt-regmap/rt-regmap.o drivers/misc/mediatek/lcm/lcm_pmic.o"
for d in $NEWDIRS; do rm -f $d/*.o $d/.*.cmd $d/built-in.a 2>/dev/null; done
rm -f arch/arm64/boot/Image.gz-dtb vmlinux System.map 2>/dev/null
echo "--- [2] whole-tree link with the display switch OFF ---"
make ARCH=arm64 -j2 vmlinux Image.gz-dtb > /tmp/off0089.log 2>&1; rc=$?
echo "OFF rc=$rc | LD-vmlinux=$(grep -c 'LD *vmlinux' /tmp/off0089.log) (must be >=1) | error:=$(grep -c 'error:' /tmp/off0089.log) | undefined:=$(grep -c 'undefined reference' /tmp/off0089.log)"
grep -E "error:" /tmp/off0089.log | head -5
for f in vmlinux System.map arch/arm64/boot/Image arch/arm64/boot/Image.gz arch/arm64/boot/Image.gz-dtb; do
  [ -f "$f" ] && echo "  $f: $(stat -c%s $f)" || echo "  MISSING $f"
done
python3 -c "
import os
try: print('  appended DTB payload: %d bytes' % (os.path.getsize('arch/arm64/boot/Image.gz-dtb')-os.path.getsize('arch/arm64/boot/Image.gz')))
except Exception as e: print('  payload: n/a', e)"
echo "  board objects built (expect 8): $(ls drivers/misc/mediatek/pmic/mt6370/v1/*.o drivers/misc/mediatek/rt-regmap/*.o 2>/dev/null | wc -l)"
echo "  lcm_pmic.o with switch off (expect absent): $([ -f drivers/misc/mediatek/lcm/lcm_pmic.o ] && echo PRESENT || echo absent)"
for s in display_bias_regulator_init mt6370_pmu_regmap_register rt_regmap_device_register; do
  echo "  nm vmlinux $s: $($NM vmlinux 2>/dev/null | grep -c "$s")"
done
echo "--- [3] display switch ON, nine new objects from scratch ---"
./scripts/config --enable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
make ARCH=arm64 -j2 vmlinux > /tmp/on0089a.log 2>&1
echo "objects: $(ls drivers/misc/mediatek/pmic/mt6370/v1/*.o drivers/misc/mediatek/rt-regmap/*.o drivers/misc/mediatek/lcm/*.o 2>/dev/null | wc -l) (expect 9)"
ls -l drivers/misc/mediatek/pmic/mt6370/v1/*.o drivers/misc/mediatek/rt-regmap/*.o drivers/misc/mediatek/lcm/*.o 2>/dev/null | awk '{printf "  %9s %s\n",$5,$9}'
echo "--- [4] whole-tree link with the switch ON (-k, so the known gaps are reported in full) ---"
make ARCH=arm64 -j2 -k vmlinux > /tmp/on0089.log 2>&1; rc=$?
echo "ON rc=$rc (2 expected) | error:=$(grep -c 'error:' /tmp/on0089.log) | warning:=$(grep -c 'warning:' /tmp/on0089.log) | new-file-diags=$(grep -E 'error:|warning:' /tmp/on0089.log | grep -cE 'mt6370|rt-regmap|lcm_pmic') | undefined-lines=$(grep -c 'undefined reference' /tmp/on0089.log) (0089 expectation: 499)"
grep -E "error:" /tmp/on0089.log | head -4
grep -oE "undefined reference to \`[^']+'" /tmp/on0089.log | sed "s/.*\`//;s/'//" | sort -u > /tmp/names-0089.txt
echo "distinct undefined names: $(wc -l < /tmp/names-0089.txt) (0089 expectation: 78; 0088 was 80)"
[ -s /tmp/names-0089.txt ] || { echo "ERROR: empty name set - the link never ran, this gate has NOT passed"; }
echo "bias names still undefined (expect 0, and their provider is this patch):"
grep -cE '^(disp_late_bias_enable|display_bias_regulator_init)$' /tmp/names-0089.txt | sed 's/^/  /'
grep -E '^(disp_late_bias_enable|display_bias_regulator_init)$' /tmp/names-0089.txt | sed 's/^/  STILL-OPEN: /'
echo "cmdqRecWrite references still there (deferred record layer, expect 29): $(grep -c cmdqRecWrite /tmp/on0089.log)"
echo "--- [5] symbol census ---"
$NM drivers/misc/mediatek/lcm/lcm_pmic.o | grep -E " [TU] " | sed 's/^/  lcm_pmic: /'
$NM drivers/misc/mediatek/pmic/mt6370/v1/*.o drivers/misc/mediatek/rt-regmap/*.o drivers/misc/mediatek/lcm/*.o 2>/dev/null | awk '$2=="T"{print $3}' | sort -u > /tmp/newT.txt
echo "new unique text symbols: $(wc -l < /tmp/newT.txt) (0089 expectation: 39)"
find drivers kernel lib mm fs net -name '*.o' | grep -vE "pmic/mt6370|mediatek/lcm|rt-regmap/" | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | awk '$2=="T"{print $3}' | sort -u > /tmp/treeT.txt
echo "collisions with the rest of the tree: $(comm -12 /tmp/newT.txt /tmp/treeT.txt | wc -l) (expect 0)"
comm -12 /tmp/newT.txt /tmp/treeT.txt | head -5 | sed 's/^/  /'
echo "--- [6] restore the default config, leave the tree usable ---"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "final config-sha: $(sha256sum .config | cut -c1-12)"
echo "=== gate end $(date -Is) ($(( $(date +%s)-START ))s) ==="
