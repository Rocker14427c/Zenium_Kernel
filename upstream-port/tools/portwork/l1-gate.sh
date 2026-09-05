#!/bin/bash
# l1-gate.sh - the L1 gate from report/display-bringup-plan.md section 6, run against a real
# v5.15.220 tree. L1 = "CMDQ: port only the delta mainline lacks", and the delta cannot be sized
# without these checks, so L2 (dispsys) stays blocked until this prints a short list.
#
# The 14 symbols / 48 callsites below are the measured demand of video/mt6768/dispsys/*.c
# (report/panel-path-analysis.md section 5). Three of them are the known vendor-only extensions
# named when the plan was written: cmdq_pkt_sleep_by_poll, cmdq_pkt_wait_no_clear,
# cmdq_dev_get_event.
set -o pipefail
TREE=${TREE:-/home/user/portwork/series}
H=include/linux/soc/mediatek/mtk-cmdq.h
cd "$TREE" || exit 1
echo "TREE=$TREE  base=$(git describe --tags 2>/dev/null)  HEAD=$(git rev-parse --short HEAD)"
echo
echo "=== 1. mainline header presence and size ==="
if [ -f "$H" ]; then echo "  $H: $(wc -l < $H) lines, $(grep -c 'cmdq_pkt_' $H) cmdq_pkt_ mentions"; else echo "  MISSING: $H"; fi
for f in drivers/soc/mediatek/cmdq.c drivers/mailbox/mtk-cmdq-mailbox.c include/linux/mailbox/mtk-cmdq-mailbox.h; do
  [ -f "$f" ] && echo "  present: $f ($(wc -l < $f) lines)" || echo "  absent:  $f"
done
echo
echo "=== 2. per-symbol availability (what dispsys needs vs what 5.15 declares) ==="
printf '%-34s %-8s %-8s %s\n' SYMBOL in-mainline-h in-mainline-c vendor-callsites
for s in cmdq_pkt_write cmdq_pkt_write_masked cmdq_pkt_read cmdq_pkt_sleep cmdq_pkt_sleep_by_poll \
         cmdq_pkt_wait cmdq_pkt_wait_no_clear cmdq_pkt_clear_event cmdq_pkt_event_clear \
         cmdq_dev_get_event cmdq_pkt_create cmdq_pkt_destroy cmdq_pkt_flush cmdq_pkt_flush_async \
         cmdq_pkt_flush_threaded cmdq_pkt_poll cmdq_mbox_create cmdq_register_device \
         cmdq_pkt_write_s; do
  h=$(grep -c "\b$s\b" $H 2>/dev/null || echo 0)
  c=$(grep -rl "\b$s\b" drivers/soc/mediatek drivers/mailbox 2>/dev/null | wc -l)
  printf '%-34s %-8s %-8s\n' "$s" "$h" "$c"
done
echo
echo "=== 3. struct/enum contract the vendor passes through ==="
for t in cmdq_pkt cmdq_client cmdq_msg_data cmdq_reg cmdq_pkt_size cmdq_data_type; do
  printf '  struct/enum %-16s mainline:%s vendor:%s\n' "$t" \
    "$(grep -c "struct $t\b\|enum $t\b" $H 2>/dev/null)" \
    "$(grep -c "struct $t\b\|enum $t\b" /home/user/Zenium_Kernel/$H 2>/dev/null)"
done
echo
echo "=== 4. the missing-delta verdict ==="
miss=""
for s in cmdq_pkt_sleep_by_poll cmdq_pkt_wait_no_clear cmdq_dev_get_event cmdq_pkt_poll cmdq_register_device; do
  grep -q "\b$s\b" $H 2>/dev/null || miss="$miss $s"
done
if [ -n "$miss" ]; then
  echo "  L1 delta required for:$miss"
  echo "  -> port these (plus their engine-side definitions) before L2; L2 stays gated."
else
  echo "  header already declares the vendor set -> L1 reduces to the engine objects;"
  echo "     re-measure the callsite semantics before opening L2."
fi
echo
echo "=== 5. real build probe: one object that uses the header ==="
. /home/user/portwork/tools/env.sh 2>/dev/null
if [ -f .config ]; then
  echo "  make drivers/mailbox/mtk-cmdq-mailbox.o (mainline side of the L1 boundary)"
  ./scripts/config --enable MAILBOX --enable MTK_CMDQ_MBOX >/dev/null 2>&1
  make olddefconfig >/dev/null 2>&1
  echo "  MTK_CMDQ_MAILBOX state: $(./scripts/config --state CONFIG_MTK_CMDQ_MAILBOX)"
  make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" \
       drivers/mailbox/mtk-cmdq-mailbox.o 2>&1 | tail -4
  echo "  rc=${PIPESTATUS[0]}"
  echo "  scripts/dtc/dtc: $([ -x scripts/dtc/dtc ] && echo present || echo absent)"
else
  echo "  no .config - run configs/apply.sh first"
fi
