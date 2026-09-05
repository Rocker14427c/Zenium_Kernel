# Sandbox reset on 2026-09-05: what was lost, what survived, how to rebuild

## What happened

The sandbox was reset while L2 slice 1 was being finalised. Two effects, different in kind:

1. **The build environment is gone.** `/home/user/portwork/` (the 5.15 working tree `series/`, the
   shallow `ref/linux` clone, `tools/env.sh`, the LineageOS build-tools and the gcc-9.3 prebuilt, and the
   `amgateNN` reproduction worktrees) lived outside the repo and was not snapshotted. No compile, link,
   `nm` or `git am` gate can run until it is rebuilt.
2. **The repo's local history rolled back** to the session base commit `011d4a1f2` (shallow, one commit),
   so none of this session's commits existed locally. The working tree files, including everything under
   `upstream-port/`, survived on disk as untracked content.

## What survived, and why nothing was lost

- `origin/arena/01a06d8b-zenium-kernel` still pointed at `fe07fd938` (my last pushed commit). Recovered
  with `git fetch --depth=15 origin arena/01a06d8b-zenium-kernel && git reset --hard FETCH_HEAD`, after
  first backing the working copy up to `/tmp/keep-upstream-port` - `reset --hard` would otherwise have
  reverted the tracked cover letter, MANIFEST and the 83 renumbered `.eml` files.
- `upstream-port/` on disk held the newer, never-committed work: `0084-*.eml`, the `/84` renumbering,
  the cover and MANIFEST edits, and the `bin/` tooling changes. It was restored over the reset tree and
  committed on top, so the published series is whole: 85 `.eml` (cover + 0001-0084).
- The L2 slice *content* itself is not lost even though `portwork/series/` is, because the patch file
  carries it: 91 files, 27,994 insertions - the 14 `.c` objects, 46 dispsys/videox headers and the 7 v3
  CMDQ headers. Reconstructing means `git am` of the series onto a fresh 5.15.220 tree, not re-deriving.

## Rebuilding the environment

    cd /home/user && cp -a Zenium_Kernel/upstream-port/tools/portwork/. portwork/   # restore.sh, build0.sh, configs/, l1-gate.sh
    cd /home/user/portwork && ./restore.sh      # ref/linux (v5.15.220 = 0996e0926), build-tools, gcc-9.3 prebuilt
    git -C /home/user/portwork/series init . && git -C series ... # then:
    git am /home/user/Zenium_Kernel/upstream-port/patch-series/00{01..84}-*.eml     # -> tree 3fa1c650082e917773ac00d2190befb35d575572
    make ARCH=arm64 defconfig && TREE=$PWD ../configs/apply.sh && make prepare
    make -j2 ARCH=arm64 CROSS_COMPILE=$CROSS_COMPILE drivers/misc/mediatek/video/mt6768/dispsys/   # 14 objects

Requirements unchanged from the earlier environment notes: no `apt` (kernel.org and distro mirrors time
out here; only GitHub codeload/api and PyPI were reachable), `dtc` is the in-tree `scripts/dtc/dtc`,
`make` must source `tools/env.sh`, and `configs/apply.sh` needs an existing `.config`.

## Status of the claims, stated conservatively

The L2 slice gate results (compile rc=0, 14 non-empty objects, 0 duplicate link-visible definitions, the
`nm -u` census) were measured **before** the reset, in the fresh `git am` reproduction tree, and are
recorded in `patch-series/MANIFEST.txt`, `build.json` and the commit message of 0084. They are not
re-claimed as currently reproducible in this sandbox: re-running them is the first task after the
environment is restored. Nothing in this port has ever been run on the device, and no display output,
panel or backlight behaviour is claimed.

## Closed: the gates were re-run after the environment was rebuilt (later the same day)

The recipe above worked, with three fixes now versioned in the repo (the `env.sh` that used to exist
only here, the SDK-sysroot-`bin`-on-PATH trap, and the relocated-`bison` datadir/`M4` problem) - see
`l2-recovery-and-record-probe.md` section 1 for each cause and its measured symptom. Both reproducibility
gates and the whole slice gate then passed in a fresh `git am` tree:

    0001-0084 -> rc=0, 85 commits, dirty=0, tree 3fa1c650082e917773ac00d2190befb35d575572   (== recorded)
    0001-0083 -> rc=0, tree 1bbd779ea9182f344c9e231621bca0ae8b715dae                          (no regression)
    defconfig + configs/apply.sh + make prepare -> rc=0 (.config sha256 758ae54339bf)
    slice build in the reproduced tree -> rc=0, 0 error: lines, 14/14 objects non-empty,
                                          248 link-visible definitions, 0 duplicates

So the results that the section above declined to re-claim are re-claimed, with `portwork/l2-slice-gate.sh`
as the durable form of the check. What remains unproven is unchanged and deliberate: no `vmlinux`/`Image`
link (never rebuilt since 0082; the full-image state after 0084 is UNKNOWN here), and nothing at all
about device behaviour - no display output, panel or backlight claim is made or implied.
