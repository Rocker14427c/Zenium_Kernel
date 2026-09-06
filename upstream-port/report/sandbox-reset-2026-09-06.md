# Sandbox reset, 2026-09-06 (00:51 IST / 20:51 UTC) - second reset of this port

## What was lost
- `/home/user/portwork/` entirely: `tools/build-tools` (bison/flex/m4/bc/make from
  `LineageOS/android_prebuilts_build-tools@lineage-21.0`), `tools/gcc` (Buildroot aarch64 gcc 9.3.0 /
  ld 2.33.1), `ref/linux` (gregkh/linux @ v5.15.220 = `0996e0926`), the `series`, `buildfull` and
  `buildpub` trees, `dl/bt.tar.gz` (368 MB) and every `logs/*.log`.
- The local git object store: branch `arena/01a06d8b-zenium-kernel` was rolled back to the session base
  `011d4a1f2` with the later files left on disk *untracked*, so `git log` no longer contained any of the
  151 published/recorded commits and `git cat-file -t 11a9ffb4c` failed.

## What survived, and why
Everything that matters, because the standing rule is that durable state lives in the repo and is pushed:
`git ls-remote origin` still showed `11a9ffb4c156e7aa0d6521f8e27cf14a873745c2` (0089 + all records).

## Recovery actually used
```sh
cd /home/user/Zenium_Kernel
git fetch -q origin arena/01a06d8b-zenium-kernel
git reset --hard -q 11a9ffb4c156e7aa0d6521f8e27cf14a873745c2     # -> clean, 89 .eml, 151 decisions
mkdir -p /home/user/portwork
cp -a /home/user/Zenium_Kernel/upstream-port/tools/portwork/. /home/user/portwork/
bash /home/user/portwork/restore.sh        # tools -> gcc -> ref/linux clone -> series + git am of the .eml set
bash /home/user/portwork/build0.sh         # defconfig + configs/apply.sh + make prepare + dtc/genksyms proof
```
Disk after restore: `df -h /` showed 18 G available on a 21 G volume, 2 CPUs, 3 GB RAM - the same shape
the gates were tuned for (`-j2`).

## Bug the reset exposed in the tooling (fixed same round)
`restore.sh` sourced `portwork/tools/env.sh` for `M4` *before* installing it, and the durable copy in the
repo sits flat (`upstream-port/tools/portwork/env.sh`). The source failed silently (it is wrapped in
`2>/dev/null`), `M4` stayed unset, and the run aborted with `bison: m4 subprocess failed` on a correctly
extracted bison - i.e. a recovery script that dies with a good toolchain because of a path convention.
Fix in `upstream-port/tools/portwork/restore.sh`: install `tools/env.sh` and `configs/apply.sh` from the
durable copies at the top, and `export M4=${M4:-$ROOT/tools/build-tools/bin/m4}` before the probe. The
probe itself stays the gate: `bison ok: 1270-line parser generated` must appear in `logs/restore.log`.

## Standing consequence
The published tree's build state is stale by construction after a reset, so the next round re-runs
`upstream-port/tools/portwork/slice0089-gate.sh` (both directions) in the recreated tree and records it as a
re-verification before landing anything on top of 0089. Never conclude from a green `restore.sh` that the
build gate has passed - it only proves the tools exist.

## ADDENDUM, later the same day: a second and a third reset, and what the fix bought

Two more resets hit after that section was written - one mid-round (before the 0089 re-verification gate
finished) and one mid-turn, ~2.5 h later, while a before/after measurement was running. The third one
deleted `/home/user/portwork` *after* its own builds had completed, which is the worst time for it: the
tree hash was current, the logs were gone. Recovery was the same three commands both times:

```
git -C /home/user/Zenium_Kernel fetch -q origin arena/01a06d8b-zenium-kernel
git -C /home/user/Zenium_Kernel reset --hard -q <pushed-tip>
cp -a /home/user/Zenium_Kernel/upstream-port/tools/portwork/. /home/user/portwork/
```

What the round's tooling fixes changed, measured rather than hoped:

- The `chmod +x` fix held. All 16 files in the durable dir arrived `755` (`ls -la` after the `cp -a`), so
  `restore.sh` and `build0.sh` were runnable without touching a bit - the first reset had needed manual
  intervention for exactly this.
- The probe/census scripts committed this round (`probe-file.sh`, `probe-path-fixed.sh`,
  `before-after-0090.sh`, `on-state-check.sh`, `probes-0090.sh`, `providers0090.py`, `namecensus0090.py`)
  came across executable too, and their method rules are in their headers - the reset cost the *logs*, not
  the *method*, which is the point of writing them into the file.
- The `git status` after a reset is misleading on its own: the branch pointer rolls back to the session base
  while the working tree still holds this session's files, so `upstream-port/` shows as `??` untracked. Do
  not conclude the records are lost, and do not "clean" them away: fetch, then `reset --hard` to the pushed
  tip, and verify (`154` decisions, plan `1079` lines, tip `8c4aa0219`).
- Disk after the third restore: 16 G available of 21 G, repo 1.9 G - the series tree plus one ON build fits,
  which is why `buildfull` is no longer recreated (the memory note from the previous round still holds).

What is still unrecoverable in-sandbox, and therefore recorded instead: `/tmp` (the ON/OFF link logs) and
`portwork/logs/*`. The numbers that matter live in `report/build.json` (gate `l2_pmic_dsv_reverify48`) and
`report/l2-slice-0090-before-after.md`, which is the only reason a mid-turn reset is survivable at all.
