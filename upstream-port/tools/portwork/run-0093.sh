#!/usr/bin/env bash
# run-0093.sh - resumable driver for the pricing round.
#
# Why this exists: the sandbox has wiped /home/user/portwork twice inside the 0092/0093 rounds (build tree,
# toolchain, gate logs). Every step below first checks for the artefact it would produce, so a reset mid-run
# costs a re-run of the step in flight rather than the round, and the durable copies of both the scripts and
# their logs live in the repo (upstream-port/tools/portwork, upstream-port/report/logs).
#
#   bash /home/user/Zenium_Kernel/upstream-port/tools/portwork/run-0093.sh
TOOLS=/home/user/Zenium_Kernel/upstream-port/tools/portwork
RLOG=/home/user/Zenium_Kernel/upstream-port/report/logs
RT=/home/user/portwork
TIP=b5d70973e7f154d47f556bd7abac4aeca4d4176c
mkdir -p "$RT" "$RLOG"
# printf | tee, not printf ; tee: this runs as a background process with stdin closed, and a bare `tee -a` reading
# a closed stdin writes an empty file, which is how the driver log for the whole pricing round came out 0 bytes.
say(){ printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$RT/logs/run-0093.log"; }
mkdir -p "$RT/logs"
say "== run-0093 start; installing the durable tools into $RT =="
cp -a "$TOOLS"/. "$RT"/ && chmod 755 "$RT"/*.sh "$RT"/*.py 2>/dev/null
for f in configs/apply.sh tools/env.sh; do [ -f "$RT/$f" ] || say "  NOTE $f missing after install"; done

say "== [1] build workspace =="
tree=$(git -C "$RT/series" rev-parse HEAD^{tree} 2>/dev/null || echo none)
if [ "$tree" != "$TIP" ]; then
  say "  series tree is $tree (want $TIP) -> restore.sh + build0.sh"
  bash "$RT/restore.sh" && bash "$RT/build0.sh" || { say "FATAL: restore did not finish"; exit 1; }
  tree=$(git -C "$RT/series" rev-parse HEAD^{tree})
  say "  restored tree: $tree  dirty=$(git -C "$RT/series" status --porcelain | wc -l)"
else
  say "  series tree already at the 0092 tip: yes (dirty $(git -C "$RT/series" status --porcelain | grep -vc '^?? '))"
fi

say "== [2] re-verify gate 0092 on the recovered tree =="
g=$(ls -t "$RT"/logs/slice0092-gate-*.log 2>/dev/null | head -1)
if [ -z "$g" ] || ! grep -q "=== gate end" "$g"; then
  say "  no completed gate log present -> running slice0092-gate.sh (cold: ~20 min)"
  bash "$RT/slice0092-gate.sh"; rc=$?
  g=$(ls -t "$RT"/logs/slice0092-gate-*.log | head -1)
  say "  gate rc=$rc, log $(basename "$g")"
else
  say "  reusing $(basename "$g")"
fi
cp "$g" "$RLOG/$(basename "$g")" 2>/dev/null && say "  log mirrored into the repo"
grep -E "VERBATIM|object size|name-count expectation|CLOSED \(|OPENED \(|collisions|harness rc|final config-sha|gate end" "$g" | tail -14 | sed 's/^/    /'

say "== [3] price the remaining queue =="
s=$(ls -t "$RT"/logs/sweep-0093.log 2>/dev/null | head -1)
if [ -n "$s" ] && grep -q "SWEEP_DONE" "$s"; then
  say "  sweep already complete: $(basename "$s")"
else
  bash "$RT/sweep-0093.sh"; say "  sweep rc=$?"
fi
cp "$RT"/logs/sweep-0093.log "$RLOG/sweep-0093.log" 2>/dev/null && say "  sweep log mirrored into the repo"
grep -E "^####|^== probe|link rc|distinct open|CLOSED|OPENED|not found|fatal error" "$RT"/logs/sweep-0093.log | tail -40
say "== run-0093 done =="
echo ALL_DONE
