#!/usr/bin/env bash
# sweep-0093.sh - price every candidate the static screen left standing, against the 92-patch tree.
# Lands nothing: each row is probe-slice.sh applied and restored (apply, whole-tree ON link with -k,
# distinct open-name delta against report/l2-open-names-at-0092.txt). Run it AFTER a build so the links
# are incremental, not cold.
LOG=${LOG:-/home/user/portwork/logs/sweep-0093.log}
# DURABLE mirrors the running log into the repo after every candidate, so a sandbox reset (this workspace
# has been wiped twice during the 0092/0093 rounds) costs at most the candidate in flight, not the whole sweep.
DURABLE=${DURABLE:-/home/user/Zenium_Kernel/upstream-port/report/logs/sweep-0093.log}
: > "$LOG"
cd /home/user/portwork/series || exit 1
T=$(git rev-parse HEAD^{tree})
[ "$T" = "b5d70973e7f154d47f556bd7abac4aeca4d4176c" ] || echo "WARNING: series tree $T is not the 0092 tip" | tee -a "$LOG"
echo "== sweep on tree $T, dirty $(git status --porcelain | wc -l) ==" | tee -a "$LOG"
for c in ddp_dsi.c ddp_disp_bdg.c disp_recovery.c ddp_aal.c ddp_pwm.c disp_cust.c debug.c disp_lowpower.c mtkfb.c fbconfig_kdebug.c primary_display.c; do
  echo "#### $c" | tee -a "$LOG"
  bash /home/user/portwork/probe-slice.sh "$c" >> "$LOG" 2>&1
  echo "   probe rc=$?" | tee -a "$LOG"
  mkdir -p "$(dirname "$DURABLE")" && cp "$LOG" "$DURABLE" 2>/dev/null
  grep -E "^== probe|link rc|obj |mtk_dramc|distinct open|CLOSED|OPENED|fatal error|not found|restored" "$LOG" | sed -n "/#### $c/,\$p" | tail -9
done
# final hygiene: the tree must be back to the published state with the switch off
git checkout -- . 2>/dev/null
./scripts/config --disable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "== sweep end: tree $(git rev-parse HEAD^{tree}) dirty $(git status --porcelain | grep -v '^?? ' | wc -l) config $(sha256sum .config | cut -c1-12) ==" | tee -a "$LOG"
echo SWEEP_DONE | tee -a "$LOG"
