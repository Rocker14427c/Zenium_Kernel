#!/usr/bin/env bash
# slice0093-gate.sh - gate for patch 0093 (ddp_color.c + ddp_dither.c + ddp_gamma.c landed verbatim behind
# three obj-$(CONFIG_MTK_DISP_BRINGUP) lines, plus cmdqRecReadToDataRegister() added to the record adapter).
#
#   bash /home/user/portwork/slice0093-gate.sh
#
# The claim under test, in the order the gate can falsify it: the three objects exist and are what the vendor
# ships; with the switch off the tree is unchanged; with it on the whole-tree link opens exactly eight fewer
# names and nothing new; the new entry point is what closes the one name the trio needs; both switch states
# still pass the host harnesses, whose new section is the reason "the same instruction word" is a measurement.
#
# Inherited rules, each one a real bug in an earlier gate:
#   * assert the measured step HAPPENED (LD vmlinux present, non-empty name set, object counts).
#   * delete the objects whose existence is the claim and rebuild them; a warm tree lies.
#   * the ON state is a WHOLE-TREE link, never a directory-scoped make; -k so every gap is reported.
#   * count DISTINCT names, not ld reference lines.
#   * sub-scripts run as `bash script.sh` with rc checked.
#   * every number goes under portwork/logs and is mirrored into the repo, because /tmp and /home/user/portwork
#     have both been wiped mid-round twice; a log that only exists there is a log that did not happen.
#   * a file the patch calls verbatim is compared by sha256, and a function the patch calls a delegation is
#     checked in the source text, not in prose.
LOG=${LOG:-/home/user/portwork/logs/slice0093-gate-$(date -u +%Y%m%dT%H%M%SZ).log}
: > "$LOG"; exec >>"$LOG" 2>&1
set -o pipefail
START=$(date +%s)
TREE=${TREE:-/home/user/portwork/series}
REPO=${REPO:-/home/user/Zenium_Kernel}
VCOM=${VCOM:-/home/user/Zenium_Kernel/drivers/misc/mediatek/video/common}
D=drivers/misc/mediatek/video/mt6768/dispsys
R=drivers/soc/mediatek/mtk-cmdq-disp-record.c
LOGDIR=/home/user/portwork/logs
DURABLE=$REPO/upstream-port/report/logs
BASE=$REPO/upstream-port/report/l2-open-names-at-0092.txt
CLOSED="ddp_driver_ccorr ddp_driver_color ddp_driver_dither ddp_driver_gamma corr_dbg_en disp_ccorr_on_end_of_frame disp_color_dbg_log_level disp_color_ioctl"
. /home/user/portwork/tools/env.sh
NM="${CROSS_COMPILE}nm"
cd "$TREE" || exit 1
echo "=== gate start $(date -Is) ==="
echo "tree: $(git rev-parse HEAD^{tree})  HEAD=$(git rev-parse --short HEAD) $(git log -1 --format=%s | cut -c1-72)"
# self-maintaining staleness check: the working tree must be exactly HEAD, and HEAD must be this slice
echo "tracked modifications pending (expect 0, the slice is committed): $(git status --porcelain | grep -vc '^?? ' || true)"
# match on the subject's own words, not on a filename: the run this line was written for printed
# "WARNING: HEAD is not the 0093 commit" against a correct tree, because the subject reads "land the colour
# trio" and never says ddp_color. A gate check that fires on a good state is worse than no check.
git log -1 --format=%s | grep -qE "colour trio|ddp_color" && echo "HEAD is the 0093 slice: yes" || echo "WARNING: HEAD is not the 0093 commit; the numbers below describe a different tree"
echo "  (tree of record for reference: 0092 tip was b5d70973e7f154d47f556bd7abac4aeca4d4176c)"

echo "--- [0] the three landed files are the vendor's, byte for byte ---"
for pair in color20/ddp_color.c corr10/ddp_dither.c corr10/ddp_gamma.c; do
  b=${pair##*/}
  vs=$(sha256sum "$VCOM/$pair" | cut -c1-12); ps=$(sha256sum "$D/$b" 2>/dev/null | cut -c1-12)
  echo "  $b  vendor $vs  port $ps  $(wc -l < "$D/$b" 2>/dev/null) lines"
  [ "$vs" = "$ps" ] && echo "    VERBATIM: yes" || echo "    ERROR: NOT verbatim - this gate has not passed"
done
echo "  gated obj- lines in the dispsys Makefile: $(grep -c 'obj-$(CONFIG_MTK_DISP_BRINGUP)' $D/Makefile) (expect 19)"
echo "  the record adapter: $(wc -l < $R) lines (expect 491), cmdqRecReadToDataRegister mentioned $(grep -c cmdqRecReadToDataRegister $R) times"
echo "  no new Kconfig symbol anywhere: $(git diff HEAD~1 --name-only | grep -c Kconfig) (expect 0)"
echo "  no Device Tree change: $(git diff HEAD~1 --name-only | grep -cE '\.dts|\.dtsi|\.dtsi\.overlay') (expect 0)"

echo "--- [1] config of record, display switch OFF ---"
bash /home/user/portwork/configs/apply.sh; rc=$?
echo "apply.sh rc=$rc"; [ $rc -eq 0 ] || { echo "FATAL: config of record not applied"; exit 1; }
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "config-sha: $(sha256sum .config | cut -c1-12)  (0089-0093 rounds: 099cdd6421b6)"
grep -E "^CONFIG_(MFD_MT6370_PMU|MT6370_PMU_DSV|RT_REGMAP|MTK_CMDQ_MTK_DISP|MTK_CMDQ_MBOX|MTK_DISP_M4U)=|^# CONFIG_MTK_DISP_BRINGUP|^CONFIG_MMPROFILE" .config | tr '\n' ' '; echo
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
rm -f drivers/soc/mediatek/mtk-cmdq-disp-record.o drivers/soc/mediatek/.*mtk-cmdq-disp-record.o.cmd 2>/dev/null
rm -f arch/arm64/boot/Image.gz-dtb vmlinux System.map 2>/dev/null

echo "--- [2] whole-tree link with the switch OFF: must be CLEAN and the same size as 0092's ---"
make ARCH=arm64 -j2 vmlinux Image.gz-dtb > "$LOGDIR/off0093.log" 2>&1; rc=$?
echo "OFF rc=$rc | LD-vmlinux=$(grep -c 'LD *vmlinux' "$LOGDIR/off0093.log") (must be >=1) | error:=$(grep -c 'error:' "$LOGDIR/off0093.log") | undefined:=$(grep -c 'undefined reference' "$LOGDIR/off0093.log")"
[ "$rc" = 0 ] || { echo "FATAL: the OFF build did not link; every number below would be meaningless"; exit 1; }
for f in vmlinux System.map arch/arm64/boot/Image arch/arm64/boot/Image.gz arch/arm64/boot/Image.gz-dtb; do
  [ -f "$f" ] && echo "  $f: $(stat -c%s $f)" || echo "  MISSING $f"; done
python3 -c "
import os
print('  appended DTB payload: %d bytes (expect 493517, unchanged since 0081)' % (os.path.getsize('arch/arm64/boot/Image.gz-dtb')-os.path.getsize('arch/arm64/boot/Image.gz')))"
echo "  sizes to compare with 0092's OFF gate: vmlinux 168340520 System.map 6911826 Image.gz-dtb 12228269; a difference here would mean this slice changed the OFF build, which it must not"
echo "  the trio with the switch off (all three must be absent): $(ls $D/ddp_color.o $D/ddp_dither.o $D/ddp_gamma.o 2>/dev/null | wc -l) (expect 0)"
echo "  the record object with the switch off (must be absent): $([ -f drivers/soc/mediatek/mtk-cmdq-disp-record.o ] && echo PRESENT || echo absent)"
echo "  gated display objects with switch off (must be 0): $(ls $D/*.o 2>/dev/null | wc -l)"
for s in $CLOSED cmdqRecReadToDataRegister ddp_mmp_init disp_late_bias_enable; do
  echo "  nm vmlinux $s: $($NM vmlinux 2>/dev/null | grep -c " $s\$")"; done
echo "  dtb sha: $(sha256sum arch/arm64/boot/dts/mediatek/mt6768.dtb 2>/dev/null | cut -c1-12) (0081 onward: 34a7e6b536a3)"

echo "--- [3] switch ON: the three objects and the adapter from scratch ---"
./scripts/config --enable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
rm -f $D/ddp_color.o $D/.*ddp_color.o.cmd $D/ddp_dither.o $D/.*ddp_dither.o.cmd \
      $D/ddp_gamma.o $D/.*ddp_gamma.o.cmd drivers/soc/mediatek/mtk-cmdq-disp-record.o \
      drivers/soc/mediatek/.*mtk-cmdq-disp-record.o.cmd 2>/dev/null
make ARCH=arm64 -j2 $D/ddp_color.o $D/ddp_dither.o $D/ddp_gamma.o drivers/soc/mediatek/mtk-cmdq-disp-record.o \
  > "$LOGDIR/on0093-single.log" 2>&1; rc=$?
echo "  single-object make rc=$rc (0 expected)"
echo "  error:=$(grep -c 'error:' "$LOGDIR/on0093-single.log")  warning:=$(grep -c 'warning:' "$LOGDIR/on0093-single.log")"
echo "  diags naming the landed files themselves (expect 0): $(grep -E 'error:|warning:' "$LOGDIR/on0093-single.log" | grep -cE 'ddp_(color|dither|gamma)\.(c|h):|mtk-cmdq-disp-record\.c:')"
echo "  warning sources, so the count is attributable:"
grep -E "warning:" "$LOGDIR/on0093-single.log" | grep -oE "[a-z_0-9./]+\.(h|c):[0-9]+" | sed 's|.*/||' | sort | uniq -c | sort -rn | head -8 | sed 's/^/    /'
for b in ddp_color ddp_dither ddp_gamma; do
  ls -l $D/$b.o 2>/dev/null | awk -v n=$b '{printf "  %s.o %s bytes\n",n,$5}'
  [ -s "$D/$b.o" ] || echo "  ERROR: $b.o, which the patch claims, does not exist or is empty"
done
echo "  object sizes vs the pricing probe (expect 272968 / 104728 / 139560): $(stat -c%s $D/ddp_color.o $D/ddp_dither.o $D/ddp_gamma.o 2>/dev/null | tr '\n' ' ')"
echo "  adapter object: $(stat -c%s drivers/soc/mediatek/mtk-cmdq-disp-record.o 2>/dev/null) bytes (0091/0092 built it too; the delta is this slice's function)"
echo "  defined by the adapter (T, expect cmdqRecReadToDataRegister among 4 entry points + 3 more):"
$NM drivers/soc/mediatek/mtk-cmdq-disp-record.o 2>/dev/null | awk '$2=="T"{print "    T",$3}' | sort
echo "  cmdqRecReadToDataRegister in the adapter object: $($NM drivers/soc/mediatek/mtk-cmdq-disp-record.o 2>/dev/null | grep -c ' T cmdqRecReadToDataRegister$') (expect 1)"
echo "  still undefined in the adapter object: $($NM -u drivers/soc/mediatek/mtk-cmdq-disp-record.o 2>/dev/null | wc -l)"
$NM -u drivers/soc/mediatek/mtk-cmdq-disp-record.o 2>/dev/null | awk '{print "    U",$2}' | sort | head -20

echo "--- [4] whole-tree ON link (-k so every gap is reported) ---"
make ARCH=arm64 -j2 -k vmlinux > "$LOGDIR/on0093.log" 2>&1; rc=$?
echo "ON rc=$rc (2 expected: the link fails on the known gaps)"
echo "  error:=$(grep -c 'error:' "$LOGDIR/on0093.log") (expect 0)  warning:=$(grep -c 'warning:' "$LOGDIR/on0093.log")"
echo "  undefined-reference lines: $(grep -c 'undefined reference to' "$LOGDIR/on0093.log") (0092 state: 160 lines / 57 names)"
grep -E "error:" "$LOGDIR/on0093.log" | head -4
grep -oE "undefined reference to \`[^']+'" "$LOGDIR/on0093.log" | sed "s/.*\`//;s/'//" | sort -u > "$LOGDIR/names-0093.txt"
n=$(wc -l < "$LOGDIR/names-0093.txt")
echo "distinct undefined names: $n (expect 49; 0089 78, 0090 65, 0091 62, 0092 57)"
[ -s "$LOGDIR/names-0093.txt" ] || echo "ERROR: empty name set - the link never ran, this gate has NOT passed"
[ "$n" = 49 ] && echo "  name-count expectation met: yes" || echo "  name-count expectation NOT met: got $n"
grep -E '^[A-Za-z_][A-Za-z0-9_]*$' "$BASE" | sort -u > "$LOGDIR/open57.txt"
echo "--- the delta, both directions, against $BASE ---"
echo "  CLOSED ($(comm -13 "$LOGDIR/names-0093.txt" "$LOGDIR/open57.txt" | wc -l), expect 8):"
comm -13 "$LOGDIR/names-0093.txt" "$LOGDIR/open57.txt" | sed 's/^/    /'
# compare as sets: comm's order is the sort order of the name files, mine is prose order, and a
# gate check that fires on a correct state is worse than no check
c=$(comm -13 "$LOGDIR/names-0093.txt" "$LOGDIR/open57.txt" | sort | tr '\n' ' ')
e=$(echo $CLOSED | tr ' ' '\n' | sort | tr '\n' ' ')
[ "$c" = "$e" ] && echo "  the closed set is exactly the eight predicted names: yes" || echo "  WARNING: closed set differs from the prediction"
echo "  OPENED ($(comm -23 "$LOGDIR/names-0093.txt" "$LOGDIR/open57.txt" | wc -l), expect 0):"
comm -23 "$LOGDIR/names-0093.txt" "$LOGDIR/open57.txt" | sed 's/^/    /'
echo "--- the 8 names this patch claims (open:0 in the link, defined:1 tree-wide) ---"
for s in $CLOSED; do
  defs=$(find drivers kernel lib mm fs net -name '*.o' | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | grep -cE " [TDB] $s\$")
  printf "  %-30s open:%s defined-tree-wide:%s in-trio:%s\n" "$s" \
    "$(grep -cx "$s" "$LOGDIR/names-0093.txt")" "$defs" \
    "$($NM --defined-only -g $D/ddp_color.o $D/ddp_dither.o $D/ddp_gamma.o 2>/dev/null | grep -c " $s\$")"
done
echo "--- and the name that made this slice necessary ---"
echo "  cmdqRecReadToDataRegister  open:$(grep -cx cmdqRecReadToDataRegister "$LOGDIR/names-0093.txt") (expect 0)  defined:$($NM --defined-only -g drivers/soc/mediatek/mtk-cmdq-disp-record.o 2>/dev/null | grep -c ' T cmdqRecReadToDataRegister$') (expect 1)"
echo "  callsites that were open at 0092 and are now answered:"
grep -n "cmdqRecReadToDataRegister" $D/ddp_color.c | sed 's/^/    /'
echo "--- what must stay open, and why it is not this patch's job ---"
for s in primary_display_idlemgr_kick primary_display_is_video_mode rdma_dump_reg ovl_dump_reg ddp_driver_ovl disp_pwm_set_backlight aal_dbg_en; do
  printf "  %-30s open:%s (expect 1)\n" "$s" "$(grep -cx "$s" "$LOGDIR/names-0093.txt")"
done
echo "  0092's 5 mmp names must stay closed: $(grep -cE '^(ddp_mmp_init|ddp_mmp_get_events|ddp_mmp_ovl_layer|ddp_mmp_rdma_layer|ddp_mmp_wdma_layer)$' "$LOGDIR/names-0093.txt") (expect 0)"
echo "  0089's bias names must stay closed: $(grep -cE '^(disp_late_bias_enable|display_bias_regulator_init)$' "$LOGDIR/names-0093.txt") (expect 0)"
echo "  0091's 3 record names must stay closed: $(grep -cE '^(cmdqRecWrite|cmdqRecWaitNoClear|cmdqRecSetEventToken)$' "$LOGDIR/names-0093.txt") (expect 0)"
echo "  the open set, for the record:"
cat "$LOGDIR/names-0093.txt" | sed 's/^/    /'

echo "--- [5] symbol census ---"
# nm reads an object from a pipe as nothing at all (measured: `cat x.o | nm -g --defined-only` prints
# 0 symbols, `nm x.o` prints 4), so every census line in this gate passes the files as arguments
$NM --defined-only -g $D/ddp_color.o $D/ddp_dither.o $D/ddp_gamma.o 2>/dev/null | \
  awk '$2!="u"{print $3}' | sort -u > "$LOGDIR/newT-0093.txt"
echo "  new global symbols from the three objects: $(wc -l < "$LOGDIR/newT-0093.txt") (the trio's whole defined set; 8 of them are names this tree had open)"
echo "  the 8 predicted names inside that census: $(for s in $CLOSED; do grep -cx "$s" "$LOGDIR/newT-0093.txt"; done | awk '{t+=$1} END{print t}') (expect 8)"
find drivers kernel lib mm fs net -name '*.o' | grep -vE "dispsys/(ddp_color|ddp_dither|ddp_gamma)\.o$" | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | awk '$2=="T"||$2=="D"{print $3}' | sort -u > "$LOGDIR/treeT-0093.txt"
echo "  collisions with the rest of the tree: $(comm -12 "$LOGDIR/newT-0093.txt" "$LOGDIR/treeT-0093.txt" | wc -l) (expect 0)"
comm -12 "$LOGDIR/newT-0093.txt" "$LOGDIR/treeT-0093.txt" | head -8 | sed 's/^/  /'

echo "--- [6] host harnesses: the record one grew a section, so its case count is the prediction ---"
gcc -std=gnu11 -Wall -Wextra -Wno-unused-parameter \
    -I "$REPO/upstream-port/tests/stub" -I include -I drivers/misc/mediatek/cmdq/v3 \
    -o "$LOGDIR/mtk_disp_record_host_check" \
    "$REPO/upstream-port/tests/mtk_disp_record_host_check.c" > "$LOGDIR/harness-build-rec.log" 2>&1
echo "  record harness build rc=$? (warnings: $(grep -c 'warning:' "$LOGDIR/harness-build-rec.log"))"
"$LOGDIR/mtk_disp_record_host_check" "$TREE" "$REPO" > "$LOGDIR/harness-run-rec.log" 2>&1
echo "  record harness rc=$?  $(grep -E '^[0-9]+ cases' "$LOGDIR/harness-run-rec.log")  (expect: 85 cases, 0 mismatches)"
grep -i "mismatch" "$LOGDIR/harness-run-rec.log" | grep -v "0 mismatches" | head -5 | sed 's/^/    /'
echo "  read_s words compared: $(grep -c 'read_s word identical.*ok' "$LOGDIR/harness-run-rec.log") (expect 12 = 4 resolvable addresses x 3 registers below JPEG_DST)"
echo "  refusal cases: $(grep -c 'refused, not encoded.*ok' "$LOGDIR/harness-run-rec.log") (expect 9 = 3 unresolvable addresses x 3 registers)"
gcc -std=gnu11 -Wall -Wextra -Wno-unused-parameter \
    -I "$REPO/upstream-port/tests/stub" -I include -I drivers/misc/mediatek/cmdq/v3 \
    -o "$LOGDIR/mtk_disp_slot_host_check" \
    "$REPO/upstream-port/tests/mtk_disp_slot_host_check.c" > "$LOGDIR/harness-build-slot.log" 2>&1
echo "  slot harness build rc=$? (warnings: $(grep -c 'warning:' "$LOGDIR/harness-build-slot.log"))"
"$LOGDIR/mtk_disp_slot_host_check" "$TREE" "$REPO" > "$LOGDIR/harness-run-slot.log" 2>&1
echo "  slot harness rc=$?  $(grep -E '^[0-9]+ cases' "$LOGDIR/harness-run-slot.log")"
echo "  files this slice changed, sha256 prefixes:"
for f in $D/ddp_color.c $D/ddp_dither.c $D/ddp_gamma.c $D/Makefile $R; do
  echo "    $(sha256sum "$f" | cut -c1-12)  $f"; done

echo "--- [7] restore the default config, leave the tree usable, mirror the evidence ---"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig >/dev/null 2>&1
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
echo "final config-sha: $(sha256sum .config | cut -c1-12)  dirty: $(git status --porcelain | grep -v '^?? ' | wc -l)"
mkdir -p "$DURABLE"
for f in slice0093-gate-$(basename "$LOG" | sed 's/.*-//;s/\.log//').log names-0093.txt harness-run-rec.log; do
  cp "$LOGDIR/$f" "$DURABLE/$f" 2>/dev/null && echo "  mirrored $f"; done
cp "$LOGDIR/names-0093.txt" "$REPO/upstream-port/report/l2-open-names-at-0093.txt" 2>/dev/null && \
  echo "  the 49-name open set written to report/l2-open-names-at-0093.txt ($(wc -l < $REPO/upstream-port/report/l2-open-names-at-0093.txt) lines)"
echo "=== gate end $(date -Is) ($(( $(date +%s)-START ))s) ==="
