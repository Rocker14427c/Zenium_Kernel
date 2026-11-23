# Zenium Kernel — Agent Handoff & Source Analysis (2026-11-23)

Successor to `AGENT_HANDOFF.md`. This document records what was **verified from the
actual repository** in this session, corrects the previous handoff where it was
wrong, and describes the tooling now in-tree so any future session can pick up
without re-deriving everything.

---

## 1. Reality check on the previous handoff

| Previous claim | Verified state (2026-11-23) |
|---|---|
| "Session branch `arena/01a0eb93-…`, last commit `6d719977060b`" | Correct, but that **tag** (`v2.0.0-ksunext-susfs-nomount-20260929`) is **not** the newest work. |
| "Newest state" | Actually newest: **`v1.7-cip137-sync-20260929` → `33144f83459b`** (BakaSU + CIP137 + SUSFS v2.4.0 + NoMount v2.3). |
| "Local checkout dirty, base `7d5fb409a`" | That sandbox no longer exists. Cloned fresh today; the old checkout is not recoverable here. |
| "`BakaSU` branch must be created; four '21Nov' commits excluded" | **Done.** No `BakaSU` branch existed upstream; it now exists (see §3). |
| "No device testing" | Still true for every shipped package. |
| "Wi-Fi suspect commit `e38c83e13e20`" | **Not supported** — see §6. |
| "Official KernelSU first, fallback KSU-Next" | KSU-Next `legacy` is the published integration; the V1.7 line returned to **BakaSU**. Two parallel backends now exist. |

## 2. Repository map (all remote refs, as of today)

```
default branch: rui4-sus   (fork of Badmaneers/zenium_realme_even, branch rui4-clean)
```

| Ref | Commit | What it is |
|---|---|---|
| `KSU-N` (was `arena/01a0eb93-zenium-kernel`) | `f69170baa` | **KernelSU-Next line.** BakaSU → KSU-Next legacy migration + V2.0.0 release + the docs/tooling commit. Renamed 2026-11-23. |
| `v2.0.0-ksunext-susfs-nomount-20260929` (tag) | `6d7199770` | Same commit as above. KSU-Next 33327, SUSFS v2.4.0, NoMount 23. |
| `v1.7-cip137-sync-20260929` (tag) | `33144f83459b` | V1.7 CIP137 build. BakaSU `5d6d1843` (35261), SUSFS v2.4.0, NoMount v2.3.0, HZ=250. **No longer on the BakaSU branch** (see §3); kept reachable through this tag. |
| `BakaSU` | `f93f264766c3` | **BakaSU line, rewritten 2026-11-23.** V1.6 + BakaSU/SUSFS/NoMount refresh; the V1.7 merge/package/docs commits were removed at the user's request. |
| `bakasu-pre-v1.7-recovery` (tag) | `33144f83459b` | Recovery anchor: the BakaSU tip **before** that rewrite. Use it if the V1.7 state is ever needed again. |
| `rui4-sus` | `55838462d` | Badmaneers' V1.6 line + torch commit; **22 commits behind / diverged**. Do not build from it. |
| `rui4-clean` | `7d5fb409a` | Mirror of upstream tracker, 0 fork-only commits. |
| `upstream (Badmaneers/zenium_realme_even:rui4-clean)` | `e6c04d542c14` (2026-11-21) | Real upstream. Fork is **2 commits behind**: `f40a406a51f1` *capability: add CAP_CHECKPOINT_RESTORE for Android 17 zygote*. Worth merging before the next release. |
| `Upstream-work` | `3fbb4de63` | Unrelated 5.15 driver-port series ("0093 …"). Do not mix. |
| `stock-rui4` | `f78ba5b1ada5` | Realme RMX3430_11_F.16 stock tree (2023-06-27). Baseline for fork-delta purposes. |

Commit graph, newest first on the maintenance line:

```
6d7199770  Add repository download link to kernel release      <- tag v2.0.0 / branch arena/01a0eb93
09ec0ac35  Publish KernelSU-Next SUSFS NoMount V2.0.0 build
3dc1a2de2  Fix KernelSU-Next SUSFS AVC SID integration
488d848eb  Replace BakaSU with KernelSU-Next legacy             <- the 4 "21 Nov" commits start here
f93f26476  kernel: refresh BakaSU, SUSFS and NoMount
64fd19e11  susfs: sync to the current upstream patchset (priority-UID filter)
a2ca2326f  ak3: fix the stale kernel.string and pin the build identity
0e30b70f1  susfs: sync with the latest upstream 4.19 patchset
d2115dcbb  nomount: update to v2.2.0
63cf74737  mt6768/even: lower tick 300 -> 250 Hz
25717d95a  NoMount v2.1.0 + ReSukiSU -> BakaSU                    <- tag bakasu-nomount-2.1
689605bd6  Integrate SUSFS v2.3.0 + NoMount v2.0.0
7d5fb409a  even: flashlights torch brightness 5 -> 7              <- upstream parent
```

**The four "21 Nov" commits** (author-date 2026-11-21, one linear chain) are exactly:

```
488d848ebd79  Replace BakaSU with KernelSU-Next legacy
3dc1a2de2964  Fix KernelSU-Next SUSFS AVC SID integration
09ec0ac35a7b  Publish KernelSU-Next SUSFS NoMount V2.0.0 build
6d719977060b  Add repository download link to kernel release
```

All four belong to the **KSU-Next experiment**, which is why the user does not want
them on the BakaSU branch. Verified: `f93f264766c3` is the direct parent of
`488d848e`; the branch point is clean.

## 3. `BakaSU` branch — created 2026-11-23, then rewritten on the user's request

History, so nobody repeats it:

1. Created at `33144f83459b` (= tag `v1.7-cip137-sync-20260929`). It contained none of
   the four 2026-11-21 KSU-Next commits (verified by ancestry).
2. **The user then asked for three commits to be removed from it:**
   `aa782965ee59` (merge of `Badmaneers:rui4-clean`), `d41e643aa6d8` (publish V1.7 CIP137
   package), `33144f83459b` (docs: V1.7 download link). This is a **confirm-gated
   force-push**, recorded here because it is a deliberate history rewrite.
3. Result: **`BakaSU` = `f93f264766c3`** ("kernel: refresh BakaSU, SUSFS and NoMount"),
   i.e. the merge's first parent and the tree before any of the three commits.
   Pushed with `--force-with-lease refs/heads/BakaSU:33144f83459b`.

Consequences to keep in mind:

- `BakaSU` no longer contains the **CIP137 bump** or the V1.7 package. Those live in the
  tag `v1.7-cip137-sync-20260929` and in `KSU-N`. Its kernel banner is the cip136 state.
- Recovery anchor: tag **`bakasu-pre-v1.7-recovery` → `33144f83459b`** (pushed).
  `git switch -c restore BakaSU && git cherry-pick aa782965...` is **not** the way back —
  reset to the tag instead.
- Do **not** repeat this removal; it is done. Do not force-push `BakaSU` again without a
  new explicit instruction naming the hashes.
- The `v1.7-cip137-sync-20260929` tag was deliberately **kept** (it is a release anchor).
- To continue BakaSU work: `git switch BakaSU`, build with `scripts/build_susfs.sh`,
  package with `scripts/zenium-package.sh`.
- If a later session wants upstream fixes, merge `Badmaneers/zenium_realme_even`
  `rui4-clean` deliberately (2 commits, a clean capability-table addition) — but note the
  user removed exactly such an upstream merge before, so **ask first**.

## 4. Component matrix (verified against the actual trees)

| Line | Submodule (.gitmodules) | Pin | Driver version | SUSFS | NoMount | HZ |
|---|---|---|---|---|---|---|
| `arena/01a0eb93` (V2.0.0) | `KernelSU-Next/KernelSU-Next` `legacy` | `e5f5ec998de8…` | **33327** = 30000+3038+289 (verified: legacy HEAD is still that commit) | v2.4.0 | 23 (upstream v2.3.0 + 4.19 adaptation) | 250 |
| `BakaSU` / `v1.7-cip137` | `Baka-SU/BakaSU` `main` | `5d6d1843c893…` (2026-11-15) | **35261** (verified: 5261 commits) | v2.4.0 | 23 (same file set) | 250 |

Notes that matter:

- **BakaSU moved** since the V1.7 tag: `main` is now `63ad1ea3a9` (21 commits ahead of
  the pin), tags up to v3.1.8. **BakaSU `main` implements
  `CMD_SUSFS_SET_PRIORITY_UID_FILTER` (0x60030); the pinned `5d6d1843` does not.**
  So the kernel's priority-UID filter code (present in `fs/susfs.c` since `64fd19e11`)
  is inert on the V1.7 pin and would become live after a BakaSU bump + Kconfig enable.
  Do not enable the Kconfig until the kernel side and manager are bumped **together**.
- **SUSFS**: `gitlab.com/simonpunk/susfs4ksu` `kernel-4.19` branch is stale (v1.5.5,
  2025-02-23). The live 4.19 source used by this project is
  `JackA1ltman/NonGKI_Kernel_Build_2nd` (as recorded in commit `64fd19e11`).
  **Do not sync from the simonpunk 4.19 branch** — it would be a large regression.
- **NoMount**: in-tree is upstream `maxsteeel/nomount` **v2.3.0** (`kernel/src/…`) with a
  small 4.19 back-port: five hunks replacing `rcu_guard()` (≥5.9 API) with explicit
  `rcu_read_lock()` sections, plus comment changes. Verified by diff (102 lines).
  Upstream now has **v2.3.1**; not adopted yet (`Kconfig` + `nomount.c`/`.h` differ;
  re-apply the `rcu_guard` adaptation when bumping — the check in `zenium-verify.sh`
  will catch a missed one).
- **KernelSU-Next**: submodule already at its `legacy` HEAD, i.e. no update available.

## 5. SUSFS / NoMount integration points (4.19, non-GKI, manual hook)

- Kernel side: `fs/susfs.c` (≈4.5 kLOC), `include/linux/susfs.h`, `include/linux/susfs_def.h`.
- Hooks live in: `fs/{namei,namespace,open,stat,statfs,super,exec,readdir}.c`,
  `fs/proc/{base,cmdline,fd,task_mmu,proc_namespace,fdinfo}.c`, `block/ioprio.c`,
  `kernel/{kallsyms,reboot,sys}.c`, `mm/memory.c`, `security/selinux/avc.c`, `fs/internal.h`,
  `include/linux/seccomp.h`.
- SELinux AVC spoofing: `susfs_ksu_sid` / `susfs_priv_app_sid` are **SUSFS-owned globals**
  resolved at runtime by `security_secctx_to_secid("u:r:su:s0")` and
  `("u:r:priv_app:s0:c512,c768")` when userspace enables the feature (`3dc1a2de2`).
  Works with any backend that names those contexts. Do not reintroduce externs into the
  KSU tree.
- KSU-Next also carries its own optional AVC/KPROBE spoofing in `kernel/extras.c` —
  **do not enable both** paths at once.
- NoMount is backend-independent (own `nomount` key type, userspace via `add_key`).
- `CONFIG_MODULE_SIG_FORCE=y` + `CONFIG_MODVERSIONS=y`: any out-of-tree module must be
  rebuilt and signed for **this exact image**; "module works on another Zenium build"
  means nothing.

## 6. The Wi-Fi regression: what the evidence actually says

User reports: **V1.6 Wi-Fi works; V1.7 toggles on but scans return no networks.**

Verified today:

1. **The device's real Wi-Fi stack did not change between V1.6 and V1.7.**
   `drivers/misc/mediatek/connectivity/**` (built-in gen4m/connac, `CONFIG_WLAN_DRV_BUILD_IN=y`)
   and `arch/arm64/boot/dts/**`: **zero diff** between `v1.6-sus-20260928` (a7842fea) and
   `v1.7-cip137-sync-20260929` (33144f8). The merge `aa782965ee59` matched upstream exactly
   in `net/` (no manual conflict resolution there).
2. **`e38c83e13e20` (CIP137) touched no MediaTek Wi-Fi code.** Its wireless changes are
   `net/wireless/{scan,util,nl80211}.c`, `net/mac80211/*`, and unrelated
   `drivers/net/wireless/*` (mwifiex, rsi, rtlwifi, …). `scan.c` gained upstream commit
   *"only group with an entry that has beacon data"*, `util.c` hardened DSCP parsing —
   both are plausible only if the driver used `cfg80211_inform_bss()` without beacon IEs.
   **Unproven for gen4m.**
3. **Extracted the built-in config out of the shipped images** (`IKCONFIG=y` →
   `scripts/zenium-verify.sh` / `scripts/zenium-wifi-diff.sh`). V1.6 vs V1.7 differ in
   13 option lines; the only runtime-behavioural ones are the **CIP137 ARM64 TLBI errata
   workarounds** (`ARM64_ERRATUM_1286807`, `ARM64_ERRATUM_4118414`,
   `ARM64_WORKAROUND_REPEAT_TLBI`). The V1.7 handoff notes themselves say
   "CONFIG_HZ=250" is a V1.8 change, yet V1.7 ships HZ=250 — the config/perf deltas
   and the release notes do **not** line up.

**Conclusion:** the regression is **not explained by a kernel-side diff of the Wi-Fi
driver or its DT**. Next step is device-side evidence, not more reverts:

```bash
# on the phone (root shell) right after a failed scan
dmesg | grep -iE 'wlan|conn|scan|cfg80211|wpa_supp|gen4m' | tail -80
logcat -d | grep -iE 'wpa_supplicant|WifiScan|scan' | tail -60
# compare firmware/calibration and MAC behaviour between a V1.6 and a V1.7 flash
```
Possibilities to test, in order: (a) userspace `wpa_supplicant`/`libwifi` mismatch with
the flashed kernel (vendor modules are signed *and* the wlan stack is built-in, but
RUI4 also loads `wlan_drv_gen4m.ko` on some builds — check `lsmod`); (b) scanning blocked
by a MAC/regulatory change in the flashed vendor partition, not `boot`; (c) CIP137
`scan.c` interaction. A one-variable rebuild to isolate (c):
`e38c83e13e20`'s `net/wireless/scan.c` hunk is a 7-line block — reverting only that hunk
on top of V1.7 is a safe, scoped experiment. **Never claim a Wi-Fi fix without the user's
device report.**

## 7. Tooling added to the repo

| Script | Purpose |
|---|---|
| `scripts/zenium-verify.sh` | Pre/post-flight checks: submodule pin + shallow-history + derived driver version, SUSFS/NoMount constants, `rcu_guard` regression, defconfig invariants (AAL off, priority-UID off, KSU/hook mode, HZ), and full package verification (zip integrity, image sha256 vs fresh build, device names, `BLOCK`, `IS_SLOT_DEVICE`, `kernel.string`). Exit 1 on failure. |
| `scripts/zenium-package.sh` | Wraps a fresh `Image.gz-dtb` in the **validated** AnyKernel3 scaffold taken from the newest in-repo release ZIP (never a fresh osm0sis clone), rewrites `kernel.string`, enforces `BLOCK=/dev/block/by-name/boot`, `IS_SLOT_DEVICE=0`, `do.modules=0`, the six device names, compares packaged image sha256 to the build output, writes `SHA256SUMS`/`System.map`/`even_defconfig.config`/`RELEASE_NOTES.md` into `release/<tag>/`. Publishes nothing without `y`. |
| `scripts/zenium-publish.sh` | GitHub **release-asset** upload with retries (the previous session's EOF failure was never actually retried). Falls back to the repo-committed ZIP convention. |
| `scripts/zenium-wifi-diff.sh` | One-shot Wi-Fi regression analysis (commits + built-in config diff + driver-diff of two refs; default `v1.6-sus-20260928` → `v1.7-cip137-sync-20260929`). |

All four were executed against this tree today; `zenium-package.sh` produced a verified
package from a shipped image (round-trip: 18 pass / 3 warn / 0 fail).

## 8. Release state and the audit findings that still matter

Package inventory (`release/…`, all compile/link verified, **none device tested**):

| Tag | ZIP | Image sha256 | Notes |
|---|---|---|---|
| `susfs-4` | V1.6-susfs-4-nomount | `46c0c676…c3` | BakaSU-era V1.6 |
| `susfs-sync-v1.6` | V1.6-susfs-sync | `e8111833…fb` | SUSFS synced, HZ 250 |
| `bakasu-nomount-2.1` | V1.7 BakaSU+NoMount 2.1 | `c7a1e2d1…02` | SUSFS v2.3.0 |
| `hz250-v1.8` | V1.8 hz250 | `c1ed99e4…1d` | one-symbol change |
| `nomount-2.2.0` | V1.9 nomount 2.2.0 | `eadc66c3…06` | **`kernel.string` still says V1.8** (packaging bug) |
| `v1.7-cip137-sync-20260929` | V1.7 CIP137 | `91933583…10` (ZIP `89152503…34`, sha256 file verified) | BakaSU 35261 |
| `ksunext-susfs-nomount-v2.0.0` | V2.0.0 KSU-Next | `05dd412f…d8` | KSU-Next 33327 |

Findings to fix in the next build (not blockers):

1. **`run.sh` still says `export version=-V1.6`** while shipping V1.7/V1.8/V1.9/V2.0.0.
   `zenium-package.sh` no longer reads it; `run.sh` itself should be updated or retired.
2. **`kernel.string` drift**: `nomount-2.2.0` package advertises V1.8; `bakasu-nomount-2.1`
   advertises "by DumbDragon" although `run.sh` sets `BUILDER=Rocker14427c`.
   **Build identity inconsistency:** the BakaSU-line images (V1.7–V1.9) contain
   `Linux version … (user@e2b.local)` in their banner — the `KBUILD_BUILD_USER/HOST`
   pinning added in `a2ca2326f` only exists in `scripts/build_susfs.sh`, and those images
   were built with `run.sh`. The KSU-Next V2.0.0 image correctly shows
   `(Rocker14427c@Rocker14427c)`.
3. **`scripts/mod/modpost.c` was weakened** in the KSU-Next migration
   (`488d848eb` removed the `vsnprintf` truncation `fatal()`): a silently truncated
   `vermagic`/dependency string would no longer fail the build. Restore it or document why.
4. **Release notes vs shipped config disagree** on when HZ became 250 (V1.7 already
   ships 250; notes say V1.8).
5. **GitHub release assets are still empty** for every release; artifacts live only
   as blobs in the repo (~20 MB each). `zenium-publish.sh` exists to fix this.
6. Local dev files in-tree: `scripts/bc_shim.py`, `scripts/package/`, `scripts/basic|bvt|drvgen|mod|tracing`
   directories are project scaffolding — leave them.

## 9. Operating procedure (use this from now on)

```bash
# --- one-time per sandbox ---
git config credential.helper store      # token already in ~/.git-credentials (snapshot-excluded)
cd /home/user/zenium/src

# --- before touching anything ---
git fetch origin --prune
git --no-pager log --graph --decorate --oneline -20 --all
scripts/zenium-verify.sh

# --- build (needs bison/flex/bc/clang/dtcpio; scripts/setup_build_env.sh provisions them) ---
KERNEL_TOOLS_DIR=/tmp/zenium-tools JOBS=2 bash scripts/build_susfs.sh
#   JOBS=2 because the sandbox has 2 vCPU / ~1.9 GiB; -j4 will OOM the linker.

# --- package (never a fresh AnyKernel3 clone) ---
scripts/zenium-package.sh --version V2.1.0 --name "KSU-Next+SUSFS+NoMount" --notes notes.md
scripts/zenium-verify.sh release/v2.1.0-*/Zenium-*.zip

# --- publish (only after explicit user approval) ---
git push origin <branch>
git tag -a <tag> -m '<message>' && git push origin <tag>
GITHUB_TOKEN=$(~/.zenium/ghtok) scripts/zenium-publish.sh --tag <tag> --dir release/<tag>
```

Branch discipline:

- **`KSU-N`** (formerly `arena/01a0eb93-zenium-kernel`) — KernelSU-Next line, `f69170baa`.
  Keep as published; the old branch name no longer exists on the remote.
- **`BakaSU`** — BakaSU line, currently at `f93f264766c3`. Future BakaSU work goes here.
- Never rebase/force-push either line without the user's explicit confirmation of the
  exact branch and hashes. Do not recreate the three-commit removal that was already done.
- Keep `AAL` disabled and the priority-UID filter disabled.
- Any KSU manager must match the kernel driver version of the **flashed image**
  (BakaSU 35261 for V1.7; KSU-Next 33327 for V2.0.0). Never spoof the version constant.

## 10. Security housekeeping (read this)

- A GitHub PAT (`repo` scope, expires **2026-12-03**) is in `~/.git-credentials` and
  `~/.zenium/ghtok`. Both are excluded from workspace snapshots, but the token is
  **valid until 2026-12-03** — revoke it in GitHub settings when finished, and never
  commit it or paste it into a tracked file. Prefer `gh auth login` or an SSH key.
- `git push --dry-run origin` was used to verify write access; no branch was created.

## 11. Source index (verified today)

- Kernel repo: <https://github.com/Rocker14427c/Zenium_Kernel>
- Upstream tracker: <https://github.com/Badmaneers/zenium_realme_even> (`rui4-clean`)
- KernelSU-Next: <https://github.com/KernelSU-Next/KernelSU-Next> `legacy` @ `e5f5ec99`
- BakaSU: <https://github.com/Baka-SU/BakaSU> (pin `5d6d1843`, `main` `63ad1ea3`)
- SUSFS live 4.19 source: <https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd>
  (simonpunk `kernel-4.19` is stale — v1.5.5)
- NoMount: <https://github.com/maxsteeel/nomount> `kernel/src/` (upstream v2.3.1 exists)
- AnyKernel3: <https://github.com/osm0sis/AnyKernel3> (scaffold already vendored in releases)
- Historical: `SUSFS_INTEGRATION.md`, `KERNELSU_MIGRATION.md` in-tree.
