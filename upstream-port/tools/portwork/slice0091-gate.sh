#!/usr/bin/env bash
# slice0091-gate.sh - gate for patch 0091 (the record adapter: cmdqRecWrite,
# cmdqRecWaitNoClear, cmdqRecSetEventToken) plus its host encoding harness.
#
#   bash /home/user/portwork/slice0091-gate.sh
#
# Inherited rules, each one a real bug in an earlier gate:
#   * assert the measured step HAPPENED ("LD vmlinux" present, non-empty name set, object
#     counts) - "0 undefined" also describes a build that died before the link.
#   * delete the objects whose existence is the claim and rebuild them; a warm tree lies.
#   * the ON state is measured with a WHOLE-TREE link, never a directory-scoped make.
#   * count DISTINCT names; ld truncates per object, so reference-line counts are lower bounds.
#   * sub-scripts run as `bash script.sh` with rc checked, so a mode bit lost in a restore cannot
#     silently skip the config step.
#   * every number is written under portwork/logs, not /tmp, because /tmp does not survive a reset.
LOG=${LOG:-/home/user/portwork/logs/slice0091-gate-$(date -u +%Y%m%dT%H%M%SZ).log}
: > "$LOG"; exec >>"$LOG" 2>&1
set -o pipefail
START=$(date +%s)
TREE=${TREE:-/home/user/portwork/series}
EXPECT_TREE=${EXPECT_TREE:-3483759c24eb022373a5290523933b61bbd7ac62}
REPO=${REPO:-/home/user/Zenium_Kernel}
D=drivers/misc/mediatek/video/mt6768/dispsys
S=drivers/soc/mediatek
LOGDIR=/home/user/portwork/logs
. /home/user/portwork/tools/env.sh
NM="${CROSS_COMPILE}nm"
cd "$TREE" || exit 1
echo "=== gate start $(date -Is) ==="
echo "tree: $(git rev-parse HEAD^{tree})  HEAD=$(git rev-parse --short HEAD)"
[ "$(git rev-parse HEAD^{tree})" = "$EXPECT_TREE" ] \
  && echo "tree matches the expected 0091 tip: yes" \
  || echo "WARNING: tree is NOT the expected 0091 tip ($EXPECT_TREE)"
echo "tracked modifications pending (expect 0, the slice is committed): $(git status --porcelain | grep -vc '^?? ' || true)"

echo "--- [1] config of record, display switch OFF ---"
bash /home/user/portwork/configs/apply.sh; rc=$?
echo "apply.sh rc=$rc"; [ $rc -eq 0 ] || { echo "FATAL: config of record not applied"; exit 1; }
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "config-sha: $(sha256sum .config | cut -c1-12)  (0089-0091 round: 099cdd6421b6)"
grep -E "^CONFIG_(MFD_MT6370_PMU|MT6370_PMU_DSV|RT_REGMAP|MTK_CMDQ|MTK_CMDQ_MBOX|MTK_DISP_M4U)=|^# CONFIG_MTK_DISP_BRINGUP" .config | tr '\n' ' '; echo
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
rm -f $S/mtk-cmdq-disp-record.o $S/.*mtk-cmdq-disp-record.o.cmd 2>/dev/null
rm -f arch/arm64/boot/Image.gz-dtb vmlinux System.map 2>/dev/null

echo "--- [2] whole-tree link with the switch OFF: must be CLEAN and unchanged by 0091 ---"
make ARCH=arm64 -j2 vmlinux Image.gz-dtb > "$LOGDIR/off0091.log" 2>&1; rc=$?
echo "OFF rc=$rc | LD-vmlinux=$(grep -c 'LD *vmlinux' "$LOGDIR/off0091.log") (must be >=1) | error:=$(grep -c 'error:' "$LOGDIR/off0091.log") | undefined:=$(grep -c 'undefined reference' "$LOGDIR/off0091.log")"
[ "$rc" = 0 ] || { echo "FATAL: the OFF build did not link; every number below would be meaningless"; exit 1; }
grep -E "error:" "$LOGDIR/off0091.log" | head -5
for f in vmlinux System.map arch/arm64/boot/Image arch/arm64/boot/Image.gz arch/arm64/boot/Image.gz-dtb; do
  [ -f "$f" ] && echo "  $f: $(stat -c%s $f)" || echo "  MISSING $f"; done
python3 -c "
import os
try: print('  appended DTB payload: %d bytes (0090 state: 493517)' % (os.path.getsize('arch/arm64/boot/Image.gz-dtb')-os.path.getsize('arch/arm64/boot/Image.gz')))
except Exception as e: print('  payload: n/a', e)"
echo "  record object with the switch off (must be absent): $([ -f $S/mtk-cmdq-disp-record.o ] && echo PRESENT || echo absent)"
echo "  gated display objects with switch off (must be 0): $(ls $D/*.o 2>/dev/null | wc -l)"
for s in cmdqRecWrite ddp_path_init module_list_scenario display_bias_regulator_init; do
  echo "  nm vmlinux $s: $($NM vmlinux 2>/dev/null | grep -c " $s\$")"; done
echo "  dtb sha: $(sha256sum arch/arm64/boot/dts/mediatek/mt6768.dtb 2>/dev/null | cut -c1-12) (0081 onward: 34a7e6b536a3)"

echo "--- [3] switch ON: mtk-cmdq-disp-record.o from scratch ---"
./scripts/config --enable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
rm -f $S/mtk-cmdq-disp-record.o $S/.*mtk-cmdq-disp-record.o.cmd
make ARCH=arm64 -j2 $S/mtk-cmdq-disp-record.o > "$LOGDIR/on0091-single.log" 2>&1; rc=$?
echo "  single-object make rc=$rc (0 expected; a non-zero rc here means the file does not compile)"
echo "  error:=$(grep -c 'error:' "$LOGDIR/on0091-single.log")  warning:=$(grep -c 'warning:' "$LOGDIR/on0091-single.log")"
echo "  warnings naming the two new files (expect 0): $(grep -E 'error:|warning:' "$LOGDIR/on0091-single.log" | grep -cE 'mtk-cmdq-disp-record\.(c|h):')"
echo "  warning sources, so the count is attributable:"
grep -E "warning:" "$LOGDIR/on0091-single.log" | grep -oE "[a-z_0-9./]+\.(h|c):[0-9]+" | sort | uniq -c | sort -rn | head -8 | sed 's/^/    /'
ls -l $S/mtk-cmdq-disp-record.o 2>/dev/null | awk '{printf "  mtk-cmdq-disp-record.o %s bytes\n",$5}'
[ -s $S/mtk-cmdq-disp-record.o ] || echo "  ERROR: the object the patch claims does not exist or is empty"
echo "  defined by the object (expect exactly the 3 record names as T):"
$NM $S/mtk-cmdq-disp-record.o 2>/dev/null | awk '$2=="T"{print "    T",$3}'
echo "  undefined by the object, and the provider of each in this tree:"
for s in $($NM -u $S/mtk-cmdq-disp-record.o 2>/dev/null | awk '{print $2}'); do
  prov=$(grep -rl "^[a-z_ ]*\b$s\b *(" --include=*.c drivers | head -3 | tr '\n' ' ')
  printf "    %-32s %s\n" "$s" "${prov:-<no C definition found by this heuristic>}"
done

echo "--- [4] whole-tree ON link (-k so every gap is reported) ---"
make ARCH=arm64 -j2 -k vmlinux > "$LOGDIR/on0091.log" 2>&1; rc=$?
echo "ON rc=$rc (2 expected: the link fails on the known gaps)"
echo "  error:=$(grep -c 'error:' "$LOGDIR/on0091.log") (expect 0)  warning:=$(grep -c 'warning:' "$LOGDIR/on0091.log")"
echo "  diags attributed to the record file (expect 0): $(grep -E 'error:|warning:' "$LOGDIR/on0091.log" | grep -c 'mtk-cmdq-disp-record\.c:')"
echo "  undefined-lines=$(grep -c 'undefined reference to' "$LOGDIR/on0091.log") (0090 state: 281 in the same measurement)"
grep -E "error:" "$LOGDIR/on0091.log" | head -4
grep -oE "undefined reference to \`[^']+'" "$LOGDIR/on0091.log" | sed "s/.*\`//;s/'//" | sort -u > "$LOGDIR/names-0091.txt"
n=$(wc -l < "$LOGDIR/names-0091.txt")
echo "distinct undefined names: $n (expectation: 62; 0089 was 78, 0090 was 65)"
[ -s "$LOGDIR/names-0091.txt" ] || echo "ERROR: empty name set - the link never ran, this gate has NOT passed"
[ "$n" = 62 ] && echo "  name-count expectation met: yes" || echo "  name-count expectation NOT met: got $n"
echo "--- the 3 names this patch claims to close (open:0 in the link, defined:1 tree-wide) ---"
for s in cmdqRecWrite cmdqRecWaitNoClear cmdqRecSetEventToken; do
  defs=$(find drivers kernel lib mm fs net -name '*.o' | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | grep -cE " T $s\$")
  printf "  %-24s open:%s defined-tree-wide:%s in-object:%s\n" "$s" \
    "$(grep -cx "$s" "$LOGDIR/names-0091.txt")" "$defs" \
    "$([ -f $S/mtk-cmdq-disp-record.o ] && $NM $S/mtk-cmdq-disp-record.o | grep -c " $s\$" || echo NA)"
done
echo "--- what must stay open, and why it is not this patch's job ---"
for s in primary_display_is_video_mode ddp_path_init cmdqRecCreate cmdqRecFinalize; do
  printf "  %-28s open:%s\n" "$s" "$(grep -cx "$s" "$LOGDIR/names-0091.txt")"
done
echo "  0089's bias names must stay closed: $(grep -cE '^(disp_late_bias_enable|display_bias_regulator_init)$' "$LOGDIR/names-0091.txt") (expect 0)"
echo "  0090's 15 path names must stay closed: $(grep -cE '^(ddp_path_init|ddp_connect_path|ddp_disconnect_path|ddp_check_path|ddp_is_module_in_scenario|ddp_get_dst_module|ddp_set_dst_module|ddp_get_module_num|ddp_get_module_num_l|ddp_get_scenario_list|ddp_get_scenario_name|ddp_get_mode_name|ddp_path_top_clock_on|ddp_path_top_clock_off|module_list_scenario)$' "$LOGDIR/names-0091.txt") (expect 0)"
echo "  the open set, for the record:"
cat "$LOGDIR/names-0091.txt" | sed 's/^/    /' | head -70
echo "--- [5] symbol census ---"
$NM $S/mtk-cmdq-disp-record.o 2>/dev/null | awk '$2=="T"||$2=="D"||$2=="B"{print $3}' | sort -u > "$LOGDIR/newT-0091.txt"
echo "  new global text/data symbols from the record object: $(wc -l < "$LOGDIR/newT-0091.txt") (expect 3)"
find drivers kernel lib mm fs net -name '*.o' | grep -v "$S/mtk-cmdq-disp-record.o" | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | awk '$2=="T"||$2=="D"{print $3}' | sort -u > "$LOGDIR/treeT-0091.txt"
echo "  collisions with the rest of the tree: $(comm -12 "$LOGDIR/newT-0091.txt" "$LOGDIR/treeT-0091.txt" | wc -l) (expect 0)"
comm -12 "$LOGDIR/newT-0091.txt" "$LOGDIR/treeT-0091.txt" | head -5 | sed 's/^/  /'

echo "--- [6] host harness: encoding and address rules against the vendor source ---"
gcc -std=gnu11 -Wall -Wextra -Wno-unused-parameter \
    -I "$REPO/upstream-port/tests/stub" -I include -I drivers/misc/mediatek/cmdq/v3 \
    -o "$LOGDIR/mtk_disp_record_host_check" \
    "$REPO/upstream-port/tests/mtk_disp_record_host_check.c" > "$LOGDIR/harness-build.log" 2>&1
echo "  harness build rc=$? (warnings: $(grep -c 'warning:' "$LOGDIR/harness-build.log"))"
grep -E "error:|warning:" "$LOGDIR/harness-build.log" | head -4 | sed 's/^/    /'
"$LOGDIR/mtk_disp_record_host_check" "$TREE" "$REPO" > "$LOGDIR/harness-run.log" 2>&1
echo "  harness rc=$?  $(grep -E '^[0-9]+ cases' "$LOGDIR/harness-run.log")"
grep -i "mismatch" "$LOGDIR/harness-run.log" | grep -v "^0 mismatches" | grep -v "cases," | head -8 | sed 's/^/    /'
echo "  the transcription this harness rests on, pinned so an edit to it is visible:"
python3 - "$S/mtk-cmdq-helper.c" <<'PY'
import hashlib, sys
src = open(sys.argv[1]).read()
probes = (("cmdq_pkt_write_s_value", "int cmdq_pkt_write_s_value("),
          ("cmdq_pkt_write_s_mask_value", "int cmdq_pkt_write_s_mask_value("),
          ("struct cmdq_instruction", "struct cmdq_instruction {"))
for n, needle in probes:
    i = src.find(needle)
    if i < 0:
        print("    MISSING", n); continue
    # take the body up to the closing brace at column 0
    j = src.find("\n}\n", i)
    body = src[i:j+3] if j > 0 else src[i:i+400]
    print("    %-32s %d B  sha256 %s" % (n, len(body), hashlib.sha256(body.encode()).hexdigest()[:12]))
PY
echo "  files under test, sha256 prefixes:"
for f in "$S/mtk-cmdq-disp-record.c" include/linux/soc/mediatek/mtk-cmdq-disp-record.h \
         "$REPO/upstream-port/tests/mtk_disp_record_host_check.c"; do
  [ -f "$f" ] && echo "    $(sha256sum "$f" | cut -c1-12)  $f" || echo "    MISSING $f"
done

echo "--- [7] restore the default config, leave the tree usable ---"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "final config-sha: $(sha256sum .config | cut -c1-12)"
echo "open-name set kept for the record: $LOGDIR/names-0091.txt"
echo "=== gate end $(date -Is) ($(( $(date +%s)-START ))s) ==="
