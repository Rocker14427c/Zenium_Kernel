#!/usr/bin/env bash
# slice0090-gate.sh - gate for patch 0090 (ddp_path.c, the display path/scenario layer).
#
#   TREE=/home/user/portwork/series EXPECT_TREE=7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed \
#     bash /home/user/portwork/slice0090-gate.sh
#
# Inherited rules, because each of these was a real bug in an earlier gate:
#   * assert the measured step HAPPENED (`LD vmlinux`, non-empty name set, object counts) - "0 undefined"
#     also describes a build that died before the link.
#   * delete the objects whose existence is the claim and rebuild them, or a warm tree lies.
#   * sub-scripts run via `bash script.sh` with their rc checked: a mode-bit lost in a restore must not
#     silently skip the config step.
#   * the ON state is measured with a WHOLE-TREE link: video/Makefile descends into videox/ on
#     CONFIG_MTK_DISP_M4U while the objects gate on CONFIG_MTK_DISP_BRINGUP.
#   * count DISTINCT names; ld truncates per object, so reference-line counts are lower bounds.
LOG=${LOG:-/home/user/portwork/logs/slice0090-gate-$(date -u +%Y%m%dT%H%M%SZ).log}
: > "$LOG"; exec >>"$LOG" 2>&1
set -o pipefail
START=$(date +%s)
TREE=${TREE:-/home/user/portwork/series}
EXPECT_TREE=${EXPECT_TREE:-7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed}
D=drivers/misc/mediatek/video/mt6768/dispsys
. /home/user/portwork/tools/env.sh
NM="${CROSS_COMPILE}nm"
cd "$TREE" || exit 1
echo "=== gate start $(date -Is) ==="
echo "tree: $(git rev-parse HEAD^{tree})  HEAD=$(git rev-parse --short HEAD)"
[ "$(git rev-parse HEAD^{tree})" = "$EXPECT_TREE" ] \
  && echo "tree matches the expected 0090 tip: yes" || echo "WARNING: tree is NOT the expected 0090 tip ($EXPECT_TREE)"
echo "tracked modifications pending (expect 0, the slice is committed): $(git status --porcelain | grep -vc '^?? ' || true)"

echo "--- [1] config of record, display switch OFF ---"
bash /home/user/portwork/configs/apply.sh; rc=$?
echo "apply.sh rc=$rc"; [ $rc -eq 0 ] || { echo "FATAL: config of record not applied"; exit 1; }
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "config-sha: $(sha256sum .config | cut -c1-12)  (0089/0090 round: 099cdd6421b6)"
grep -E "^CONFIG_(MFD_MT6370_PMU|MT6370_PMU_DSV|RT_REGMAP|MTK_CMDQ|MTK_DISP_M4U)=|^# CONFIG_MTK_DISP_BRINGUP" .config | tr '\n' ' '; echo
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
rm -f drivers/misc/mediatek/video/mt6768/videox/*.o 2>/dev/null
rm -f arch/arm64/boot/Image.gz-dtb vmlinux System.map 2>/dev/null
echo "--- [2] whole-tree link with the switch OFF: must be CLEAN ---"
make ARCH=arm64 -j2 vmlinux Image.gz-dtb > /tmp/off0090.log 2>&1; rc=$?
echo "OFF rc=$rc | LD-vmlinux=$(grep -c 'LD *vmlinux' /tmp/off0090.log) (must be >=1) | error:=$(grep -c 'error:' /tmp/off0090.log) | undefined:=$(grep -c 'undefined reference' /tmp/off0090.log)"
[ "$rc" = 0 ] || { echo "FATAL: the OFF build did not link; every number below would be meaningless"; exit 1; }
grep -E "error:" /tmp/off0090.log | head -5
for f in vmlinux System.map arch/arm64/boot/Image arch/arm64/boot/Image.gz arch/arm64/boot/Image.gz-dtb; do
  [ -f "$f" ] && echo "  $f: $(stat -c%s $f)" || echo "  MISSING $f"; done
python3 -c "
import os
try: print('  appended DTB payload: %d bytes (0089 state: 493517)' % (os.path.getsize('arch/arm64/boot/Image.gz-dtb')-os.path.getsize('arch/arm64/boot/Image.gz')))
except Exception as e: print('  payload: n/a', e)"
echo "  ddp_path.o with the switch off (must be absent): $([ -f $D/ddp_path.o ] && echo PRESENT || echo absent)"
echo "  gated display objects with switch off (must be 0): $(ls $D/*.o 2>/dev/null | wc -l)"
for s in ddp_path_init ddp_connect_path module_list_scenario display_bias_regulator_init; do
  echo "  nm vmlinux $s: $($NM vmlinux 2>/dev/null | grep -c " $s\$")"; done

echo "--- [3] switch ON: ddp_path.o built from scratch ---"
./scripts/config --enable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
make ARCH=arm64 -j2 vmlinux > /tmp/on0090a.log 2>&1
echo "  display objects now: $(ls $D/*.o 2>/dev/null | wc -l) (expect 15: the 14 landed ones + ddp_path.o)"
ls -l $D/ddp_path.o 2>/dev/null | awk '{printf "  ddp_path.o %s bytes\n",$5}'
echo "  videox objects (disp_helper must be built here, not by a dir-scoped make): $(ls drivers/misc/mediatek/video/mt6768/videox/*.o 2>/dev/null | wc -l)"
echo "--- [4] whole-tree ON link (-k so every gap is reported) ---"
make ARCH=arm64 -j2 -k vmlinux > /tmp/on0090.log 2>&1; rc=$?
echo "ON rc=$rc (2 expected: the link fails on the known gaps)"
echo "  error:=$(grep -c 'error:' /tmp/on0090.log) (expect 0)  warning:=$(grep -c 'warning:' /tmp/on0090.log)"
echo "  diags attributed to ddp_path.c (expect 0): $(grep -E 'error:|warning:' /tmp/on0090.log | grep -c ' ddp_path\.c:')"
echo "  undefined-lines=$(grep -c 'undefined reference to' /tmp/on0090.log) (0089 state: 486 in the same measurement)"
grep -E "error:" /tmp/on0090.log | head -4
grep -oE "undefined reference to \`[^']+'" /tmp/on0090.log | sed "s/.*\`//;s/'//" | sort -u > /tmp/names-0090.txt
n=$(wc -l < /tmp/names-0090.txt)
echo "distinct undefined names: $n (expectation: 65; 0089 was 78)"
[ -s /tmp/names-0090.txt ] || echo "ERROR: empty name set - the link never ran, this gate has NOT passed"
[ "$n" = 65 ] && echo "  name-count expectation met: yes" || echo "  name-count expectation NOT met: got $n"
echo "--- the 15 names this patch claims to close (must be absent from the open set, present as T) ---"
for s in ddp_check_path ddp_connect_path ddp_disconnect_path ddp_get_dst_module ddp_get_mode_name \
         ddp_get_module_num ddp_get_module_num_l ddp_get_scenario_list ddp_get_scenario_name \
         ddp_is_module_in_scenario ddp_path_init ddp_path_top_clock_off ddp_path_top_clock_on \
         ddp_set_dst_module module_list_scenario; do
  printf "  %-26s open:%s defined:%s\n" "$s" "$(grep -cx "$s" /tmp/names-0090.txt)" "$([ -f $D/ddp_path.o ] && $NM $D/ddp_path.o | grep -c " $s\$" || echo NA)"
done
echo "--- the 2 names it opens (deferred record family, must be present and documented) ---"
for s in cmdqRecWaitNoClear cmdqRecSetEventToken cmdqRecWrite primary_display_is_video_mode; do
  printf "  %-26s open:%s\n" "$s" "$(grep -cx "$s" /tmp/names-0090.txt)"; done
echo "  0089's bias names must stay closed: $(grep -cE '^(disp_late_bias_enable|display_bias_regulator_init)$' /tmp/names-0090.txt) (expect 0)"
echo "--- [5] symbol census ---"
$NM $D/ddp_path.o | awk '$2=="T"||$2=="D"||$2=="B"{print $3}' | sort -u > /tmp/newT.txt
echo "  new global data+text symbols from ddp_path.o: $(wc -l < /tmp/newT.txt)"
find drivers kernel lib mm fs net -name '*.o' | grep -v "$D/ddp_path.o" | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | awk '$2=="T"||$2=="D"{print $3}' | sort -u > /tmp/treeT.txt
echo "  collisions with the rest of the tree: $(comm -12 /tmp/newT.txt /tmp/treeT.txt | wc -l) (expect 0)"
comm -12 /tmp/newT.txt /tmp/treeT.txt | head -5 | sed 's/^/  /'
echo "--- [6] restore the default config, leave the tree usable ---"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "final config-sha: $(sha256sum .config | cut -c1-12)"
echo "open-name set kept for the record: /tmp/names-0090.txt"
echo "=== gate end $(date -Is) ($(( $(date +%s)-START ))s) ==="
