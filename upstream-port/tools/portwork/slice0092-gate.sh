#!/usr/bin/env bash
# slice0092-gate.sh - gate for patch 0092 (video/mt6768/dispsys/ddp_mmp.c landed verbatim,
# plus one obj-$(CONFIG_MTK_DISP_BRINGUP) line), i.e. the MMP layer the display code has been
# calling since 0085.
#
#   bash /home/user/portwork/slice0092-gate.sh
#
# Inherited rules, each one a real bug in an earlier gate:
#   * assert the measured step HAPPENED ("LD vmlinux" present, non-empty name set, object counts) -
#     "0 undefined" also describes a build that died before the link.
#   * delete the objects whose existence is the claim and rebuild them; a warm tree lies.
#   * the ON state is measured with a WHOLE-TREE link, never a directory-scoped make.
#   * count DISTINCT names; ld truncates per object, so reference-line counts are lower bounds.
#   * sub-scripts run as `bash script.sh` with rc checked, so a mode bit lost in a restore cannot
#     silently skip the config step.
#   * every number is written under portwork/logs, not /tmp, because /tmp does not survive a reset.
#   * a file the patch calls verbatim is compared by sha256 against the vendor source, not by
#     assertion in prose.
LOG=${LOG:-/home/user/portwork/logs/slice0092-gate-$(date -u +%Y%m%dT%H%M%SZ).log}
: > "$LOG"; exec >>"$LOG" 2>&1
set -o pipefail
START=$(date +%s)
TREE=${TREE:-/home/user/portwork/series}
EXPECT_TREE=${EXPECT_TREE:-b5d70973e7f154d47f556bd7abac4aeca4d4176c}
REPO=${REPO:-/home/user/Zenium_Kernel}
VENDOR=${VENDOR:-/home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/dispsys}
D=drivers/misc/mediatek/video/mt6768/dispsys
LOGDIR=/home/user/portwork/logs
BASE=/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0091.txt
. /home/user/portwork/tools/env.sh
NM="${CROSS_COMPILE}nm"
cd "$TREE" || exit 1
echo "=== gate start $(date -Is) ==="
echo "tree: $(git rev-parse HEAD^{tree})  HEAD=$(git rev-parse --short HEAD)"
[ "$(git rev-parse HEAD^{tree})" = "$EXPECT_TREE" ] \
  && echo "tree matches the expected 0092 tip: yes" \
  || echo "WARNING: tree is NOT the expected 0092 tip ($EXPECT_TREE)"
echo "tracked modifications pending (expect 0, the slice is committed): $(git status --porcelain | grep -vc '^?? ' || true)"

echo "--- [0] the file this patch lands is the vendor's, byte for byte ---"
vs=$(sha256sum "$VENDOR/ddp_mmp.c" | cut -c1-12); ps=$(sha256sum "$D/ddp_mmp.c" | cut -c1-12)
echo "  vendor  $VENDOR/ddp_mmp.c  $vs"
echo "  port    $D/ddp_mmp.c  $ps"
[ "$vs" = "$ps" ] && echo "  VERBATIM: yes ($(wc -l < $D/ddp_mmp.c) lines on both sides)" || echo "  ERROR: NOT verbatim - this gate has not passed"
echo "  gated obj- lines in the dispsys Makefile: $(grep -c 'obj-$(CONFIG_MTK_DISP_BRINGUP)' $D/Makefile) (expect 16)"

echo "--- [1] config of record, display switch OFF ---"
bash /home/user/portwork/configs/apply.sh; rc=$?
echo "apply.sh rc=$rc"; [ $rc -eq 0 ] || { echo "FATAL: config of record not applied"; exit 1; }
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "config-sha: $(sha256sum .config | cut -c1-12)  (0089-0092 round: 099cdd6421b6)"
grep -E "^CONFIG_(MFD_MT6370_PMU|MT6370_PMU_DSV|RT_REGMAP|MTK_CMDQ|MTK_CMDQ_MBOX|MTK_DISP_M4U)=|^# CONFIG_MTK_DISP_BRINGUP|^CONFIG_MMPROFILE" .config | tr '\n' ' '; echo
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
rm -f arch/arm64/boot/Image.gz-dtb vmlinux System.map 2>/dev/null

echo "--- [2] whole-tree link with the switch OFF: must be CLEAN and unchanged by 0092 ---"
make ARCH=arm64 -j2 vmlinux Image.gz-dtb > "$LOGDIR/off0092.log" 2>&1; rc=$?
echo "OFF rc=$rc | LD-vmlinux=$(grep -c 'LD *vmlinux' "$LOGDIR/off0092.log") (must be >=1) | error:=$(grep -c 'error:' "$LOGDIR/off0092.log") | undefined:=$(grep -c 'undefined reference' "$LOGDIR/off0092.log")"
[ "$rc" = 0 ] || { echo "FATAL: the OFF build did not link; every number below would be meaningless"; exit 1; }
for f in vmlinux System.map arch/arm64/boot/Image arch/arm64/boot/Image.gz arch/arm64/boot/Image.gz-dtb; do
  [ -f "$f" ] && echo "  $f: $(stat -c%s $f)" || echo "  MISSING $f"; done
python3 -c "
import os
print('  appended DTB payload: %d bytes (expect 493517, unchanged since 0081)' % (os.path.getsize('arch/arm64/boot/Image.gz-dtb')-os.path.getsize('arch/arm64/boot/Image.gz')))"
echo "  ddp_mmp.o with the switch off (must be absent): $([ -f $D/ddp_mmp.o ] && echo PRESENT || echo absent)"
echo "  gated display objects with switch off (must be 0): $(ls $D/*.o 2>/dev/null | wc -l)"
for s in ddp_mmp_init ddp_mmp_get_events ddp_path_init cmdqRecWrite display_bias_regulator_init; do
  echo "  nm vmlinux $s: $($NM vmlinux 2>/dev/null | grep -c " $s\$")"; done
echo "  dtb sha: $(sha256sum arch/arm64/boot/dts/mediatek/mt6768.dtb 2>/dev/null | cut -c1-12) (0081 onward: 34a7e6b536a3)"

echo "--- [3] switch ON: ddp_mmp.o from scratch ---"
./scripts/config --enable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
rm -f $D/ddp_mmp.o $D/.*ddp_mmp.o.cmd
make ARCH=arm64 -j2 $D/ddp_mmp.o > "$LOGDIR/on0092-single.log" 2>&1; rc=$?
echo "  single-object make rc=$rc (0 expected)"
echo "  error:=$(grep -c 'error:' "$LOGDIR/on0092-single.log")  warning:=$(grep -c 'warning:' "$LOGDIR/on0092-single.log")"
echo "  diags naming ddp_mmp.c/ddp_mmp.h (expect 0): $(grep -E 'error:|warning:' "$LOGDIR/on0092-single.log" | grep -cE 'ddp_mmp\.(c|h):')"
echo "  warning sources, so the count is attributable:"
grep -E "warning:" "$LOGDIR/on0092-single.log" | grep -oE "[a-z_0-9./]+\.(h|c):[0-9]+" | sed 's|.*/||' | sort | uniq -c | sort -rn | head -6 | sed 's/^/    /'
ls -l $D/ddp_mmp.o 2>/dev/null | awk '{printf "  ddp_mmp.o %s bytes (expect 85592)\n",$5}'
[ -s "$D/ddp_mmp.o" ] || echo "  ERROR: the object the patch claims does not exist or is empty"
[ "$(stat -c%s $D/ddp_mmp.o 2>/dev/null)" = "85592" ] && echo "  object size matches the prediction: yes" || echo "  object size differs from the prediction"
echo "  defined by the object (expect the 5 MMP names plus init_ddp_mmp_events, all T):"
$NM $D/ddp_mmp.o 2>/dev/null | awk '$2=="T"{print "    T",$3}'
echo "  undefined by the object: $($NM -u $D/ddp_mmp.o 2>/dev/null | awk 'END{print NR}')"
$NM -u $D/ddp_mmp.o 2>/dev/null | awk '{print "    U",$2}' | sort | head -30

echo "--- [4] whole-tree ON link (-k so every gap is reported) ---"
make ARCH=arm64 -j2 -k vmlinux > "$LOGDIR/on0092.log" 2>&1; rc=$?
echo "ON rc=$rc (2 expected: the link fails on the known gaps)"
echo "  error:=$(grep -c 'error:' "$LOGDIR/on0092.log") (expect 0)  warning:=$(grep -c 'warning:' "$LOGDIR/on0092.log")"
echo "  diags attributed to ddp_mmp.c (expect 0): $(grep -E 'error:|warning:' "$LOGDIR/on0092.log" | grep -c 'ddp_mmp\.c:')"
echo "  undefined-reference lines: $(grep -c 'undefined reference to' "$LOGDIR/on0092.log") (0091 state: 211 lines / 62 names)"
grep -E "error:" "$LOGDIR/on0092.log" | head -4
grep -oE "undefined reference to \`[^']+'" "$LOGDIR/on0092.log" | sed "s/.*\`//;s/'//" | sort -u > "$LOGDIR/names-0092.txt"
n=$(wc -l < "$LOGDIR/names-0092.txt")
echo "distinct undefined names: $n (expect 57; 0089 78, 0090 65, 0091 62)"
[ -s "$LOGDIR/names-0092.txt" ] || echo "ERROR: empty name set - the link never ran, this gate has NOT passed"
[ "$n" = 57 ] && echo "  name-count expectation met: yes" || echo "  name-count expectation NOT met: got $n"
grep -E '^[A-Za-z_][A-Za-z0-9_]*$' "$BASE" | sort -u > /tmp/open62-92.txt
echo "--- the delta, both directions, against $BASE ---"
echo "  CLOSED ($(comm -13 "$LOGDIR/names-0092.txt" /tmp/open62-92.txt | wc -l), expect 5):"
comm -13 "$LOGDIR/names-0092.txt" /tmp/open62-92.txt | sed 's/^/    /'
echo "  OPENED ($(comm -23 "$LOGDIR/names-0092.txt" /tmp/open62-92.txt | wc -l), expect 0):"
comm -23 "$LOGDIR/names-0092.txt" /tmp/open62-92.txt | sed 's/^/    /'
echo "--- the 5 names this patch claims (open:0 in the link, defined:1 tree-wide) ---"
for s in ddp_mmp_init ddp_mmp_get_events ddp_mmp_ovl_layer ddp_mmp_rdma_layer ddp_mmp_wdma_layer; do
  defs=$(find drivers kernel lib mm fs net -name '*.o' | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | grep -cE " T $s\$")
  printf "  %-22s open:%s defined-tree-wide:%s in-object:%s\n" "$s" \
    "$(grep -cx "$s" "$LOGDIR/names-0092.txt")" "$defs" "$($NM $D/ddp_mmp.o 2>/dev/null | grep -c " $s\$")"
done
echo "--- what must stay open, and why it is not this patch's job ---"
for s in primary_display_is_video_mode rdma_dump_reg ovl_dump_reg ddp_driver_ovl disp_pwm_set_backlight; do
  printf "  %-30s open:%s (expect 1)\n" "$s" "$(grep -cx "$s" "$LOGDIR/names-0092.txt")"
done
echo "  0089's bias names must stay closed: $(grep -cE '^(disp_late_bias_enable|display_bias_regulator_init)$' "$LOGDIR/names-0092.txt") (expect 0)"
echo "  0090's 15 path names must stay closed: $(grep -cE '^(ddp_path_init|ddp_connect_path|ddp_disconnect_path|ddp_check_path|ddp_is_module_in_scenario|ddp_get_dst_module|ddp_set_dst_module|ddp_get_module_num|ddp_get_module_num_l|ddp_get_scenario_list|ddp_get_scenario_name|ddp_get_mode_name|ddp_path_top_clock_on|ddp_path_top_clock_off|module_list_scenario)$' "$LOGDIR/names-0092.txt") (expect 0)"
echo "  0091's 3 record names must stay closed: $(grep -cE '^(cmdqRecWrite|cmdqRecWaitNoClear|cmdqRecSetEventToken)$' "$LOGDIR/names-0092.txt") (expect 0)"
echo "  the open set, for the record:"
cat "$LOGDIR/names-0092.txt" | sed 's/^/    /'

echo "--- [5] symbol census ---"
$NM $D/ddp_mmp.o 2>/dev/null | awk '$2=="T"||$2=="D"||$2=="B"{print $3}' | sort -u > "$LOGDIR/newT-0092.txt"
echo "  new global text/data symbols from ddp_mmp.o: $(wc -l < "$LOGDIR/newT-0092.txt") (expect 6)"
find drivers kernel lib mm fs net -name '*.o' | grep -v "$D/ddp_mmp.o" | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | awk '$2=="T"||$2=="D"{print $3}' | sort -u > "$LOGDIR/treeT-0092.txt"
echo "  collisions with the rest of the tree: $(comm -12 "$LOGDIR/newT-0092.txt" "$LOGDIR/treeT-0092.txt" | wc -l) (expect 0)"
comm -12 "$LOGDIR/newT-0092.txt" "$LOGDIR/treeT-0092.txt" | head -8 | sed 's/^/  /'

echo "--- [6] host harnesses: untouched by this slice, so both must still pass ---"
gcc -std=gnu11 -Wall -Wextra -Wno-unused-parameter \
    -I "$REPO/upstream-port/tests/stub" -I include -I drivers/misc/mediatek/cmdq/v3 \
    -o "$LOGDIR/mtk_disp_record_host_check" \
    "$REPO/upstream-port/tests/mtk_disp_record_host_check.c" > "$LOGDIR/harness-build-rec.log" 2>&1
echo "  record harness build rc=$? (warnings: $(grep -c 'warning:' "$LOGDIR/harness-build-rec.log"))"
"$LOGDIR/mtk_disp_record_host_check" "$TREE" "$REPO" > "$LOGDIR/harness-run-rec.log" 2>&1
echo "  record harness rc=$?  $(grep -E '^[0-9]+ cases' "$LOGDIR/harness-run-rec.log")"
grep -i "mismatch" "$LOGDIR/harness-run-rec.log" | grep -v "0 mismatches" | head -5 | sed 's/^/    /'
gcc -std=gnu11 -Wall -Wextra -Wno-unused-parameter \
    -I "$REPO/upstream-port/tests/stub" -I include -I drivers/misc/mediatek/cmdq/v3 \
    -o "$LOGDIR/mtk_disp_slot_host_check" \
    "$REPO/upstream-port/tests/mtk_disp_slot_host_check.c" > "$LOGDIR/harness-build-slot.log" 2>&1
echo "  slot harness build rc=$? (warnings: $(grep -c 'warning:' "$LOGDIR/harness-build-slot.log"))"
"$LOGDIR/mtk_disp_slot_host_check" "$TREE" "$REPO" > "$LOGDIR/harness-run-slot.log" 2>&1
echo "  slot harness rc=$?  $(grep -E '^[0-9]+ cases' "$LOGDIR/harness-run-slot.log")"
echo "  files this slice changed, sha256 prefixes:"
for f in "$D/ddp_mmp.c" "$D/Makefile"; do
  echo "    $(sha256sum "$f" | cut -c1-12)  $f"; done
echo "  record adapter files, unchanged since 0091 (compare with that round's gate log):"
for f in drivers/soc/mediatek/mtk-cmdq-disp-record.c include/linux/soc/mediatek/mtk-cmdq-disp-record.h; do
  echo "    $(sha256sum "$f" | cut -c1-12)  $f"; done

echo "--- [7] restore the default config, leave the tree usable ---"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
echo "final config-sha: $(sha256sum .config | cut -c1-12)  dirty: $(git status --porcelain | grep -v '^?? ' | wc -l)"
echo "open-name set kept for the record: $LOGDIR/names-0092.txt"
echo "=== gate end $(date -Is) ($(( $(date +%s)-START ))s) ==="
