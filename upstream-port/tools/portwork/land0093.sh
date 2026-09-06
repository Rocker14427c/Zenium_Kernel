#!/usr/bin/env bash
# land0093.sh - assemble patch 0093: the colour trio plus the one record entry point they need.
#
#   bash /home/user/portwork/land0093.sh
#
# Three vendor files, copied flat into the port's dispsys directory exactly as 0092 copied ddp_mmp.c, each
# obj- line gated on CONFIG_MTK_DISP_BRINGUP; one new function in drivers/soc/mediatek/mtk-cmdq-disp-record.c
# that delegates cmdqRecReadToDataRegister() to mainline's cmdq_pkt_read_s(); and the host-harness section
# that makes "the same 64-bit word" a measurement instead of a claim. Nothing else: no header lands (the three
# ddp_{color,dither,gamma}.h the files include are already in video/include from 0085 - measured, not assumed),
# no Device Tree change, no new Kconfig symbol.
#
# Idempotent, so a re-run after a reset cannot double-apply: every step checks for its own result first.
set -e
TOOLS=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
TREE=${TREE:-/home/user/portwork/series}
REPO=${REPO:-/home/user/Zenium_Kernel}
VC=$REPO/drivers/misc/mediatek/video/common
D=drivers/misc/mediatek/video/mt6768/dispsys
cd "$TREE"

echo "--- vendor files, verbatim ---"
for pair in color20/ddp_color.c corr10/ddp_dither.c corr10/ddp_gamma.c; do
  b=${pair##*/}
  if [ -f "$D/$b" ]; then
    echo "  present  $b  $(wc -l < "$D/$b") lines"
  else
    cp "$VC/$pair" "$D/$b"
    echo "  copied   $b  $(wc -l < "$D/$b") lines"
  fi
  v=$(sha256sum "$VC/$pair" | cut -c1-12); p=$(sha256sum "$D/$b" | cut -c1-12)
  [ "$v" = "$p" ] || { echo "  ERROR: $b is not verbatim ($v vs $p)"; exit 1; }
  echo "  sha256 $p both sides: verbatim"
done

echo "--- the three gated obj- lines ---"
for b in ddp_color ddp_dither ddp_gamma; do
  if grep -q "obj-\$(CONFIG_MTK_DISP_BRINGUP) += $b.o" "$D/Makefile"; then
    echo "  already in the Makefile: $b.o"
  else
    printf 'obj-$(CONFIG_MTK_DISP_BRINGUP) += %s\n' "$b.o" >> "$D/Makefile"
    echo "  appended: $b.o"
  fi
done
echo "  gated obj- lines now: $(grep -c 'obj-\$(CONFIG_MTK_DISP_BRINGUP)' "$D/Makefile") (expect 19)"

echo "--- the record entry point ---"
R=drivers/soc/mediatek/mtk-cmdq-disp-record.c
if grep -q "cmdqRecReadToDataRegister" "$R"; then
  echo "  already present: $(grep -c "cmdqRecReadToDataRegister" "$R") mentions, file $(wc -l < "$R") lines"
else
  cat "$TOOLS/record-read-entry.c" >> "$R"
  echo "  appended: file now $(wc -l < "$R") lines (was 440 + $(wc -l < "$TOOLS/record-read-entry.c"))"
fi
# the precedence on the offset argument, so a re-run of a hand-edited file cannot lose it
sed -i 's|(u16)dst_data_reg + CMDQ_GPR_V3_OFFSET|(u16)(dst_data_reg + CMDQ_GPR_V3_OFFSET)|' "$R"
grep -c "(u16)(dst_data_reg + CMDQ_GPR_V3_OFFSET)" "$R" | sed 's/^/  offset argument, parenthesised: /'

echo "--- the host harness section (lives in the port repo, not in the series) ---"
if grep -q "cmdqRecReadToDataRegister: one instruction" "$REPO/upstream-port/tests/mtk_disp_record_host_check.c"; then
  echo "  already extended"
else
  python3 "$TOOLS/patch-harness-0093.py"
fi

echo "--- what this leaves pending in the series tree ---"
git status --porcelain | grep -v '^?? '
git diff --stat | tail -3
