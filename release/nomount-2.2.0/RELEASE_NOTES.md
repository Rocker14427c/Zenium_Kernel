# Zenium Kernel RUI4 — V1.9 (NoMount v2.2.0)

Build date: 2026-10-28
Target: Realme Narzo 50A / RMX3430 family (MT6768 Helio G85, 4 GB, 4.19 non-GKI "rui4-clean")
Branch head: tag `nomount-2.2.0` (parent `63cf7473766a3ed8d089f49abe913d0998d3f9cd`)

## What changed in this release

**NoMount v2.1.0 → v2.2.0** (`bf1847f98f`, 2026-10-22)

`fs/nomount/{Kconfig,Makefile,nomount.h,nomount.c}` were replaced with the upstream
v2.2.0 sources. The four in-tree files were verified sha256-identical to upstream
v2.1.0 immediately before the swap, so this is a clean file replacement with **no
in-kernel patching** and no change to the integration points:

| Integration point | Status |
|---|---|
| `fs/Kconfig:331` — `source "fs/nomount/Kconfig"` | unchanged |
| `fs/Makefile:19` — `obj-$(CONFIG_NOMOUNT) += nomount/` | unchanged |
| `even_defconfig` — `CONFIG_NOMOUNT=y` | unchanged |

`fs/nomount/Kconfig` is byte-identical between v2.1.0 and v2.2.0 (the tristate
prompt did not change), so it does not appear in the commit diff.

Going from v2.1.0 to v2.2.0 skips v2.1.1, so this update also carries **every**
fix and improvement from v2.1.1 (55 commits) plus v2.2.0 (50 commits).

### Kernel stability fixes (landed in v2.1.1, carried forward in v2.2.0)
- `5f13384f` — **UAF in `nm_dir_lookup()` / `nm_dir_iterate_dir()`** fixed by
  pinning `dir_node` with RCU and taking references.
- `7f227863` — **UAF in `d_revalidate`** fixed by holding RCU while reading
  `dir_node` / `iop`.
- `dbd7f4a5` — **OOB read in `NM_CMD_GET_UIDS`** fixed.
- `fb1fb9a8` — `pinned_dentry` cleanup in `nm_dir_rcu_free` corrected (leaked
  dentries on rule churn).
- `7a24793f` — `fake_fop.owner = THIS_MODULE` set, so the module refcount is held
  correctly while files are open (prevents unload under open handles).
- `7e7342cd` — `->evict_inode()` no longer called for virtual inodes.
- `9ea42b0b` — lookup rule resolution split into RCU and sleeping phases.
- `1f35f829` — rule arrays and leaves retired with `call_rcu`, mutex taken once
  per add batch.
- `89127601` / `a362f608` / `51516006` — child bloom filter widened to 256 bits
  and scaled with child count, rebuilt on growth.

### New in v2.2.0 specifically
- `5f70a17b` — **opaque-directory support**: a path can be reported as an empty
  directory (`3f5e5205` binds opaque state to directory views, `87603f4c` bypasses
  readdir merging for native replacements, `c8f57be9` invalidates only injected
  names).
- `2f7379c2` — **UID ranges with deny sub-ranges** for rule matching.
- `1197eb12` — **driver protocol bumped to v22 and the installer gates on it.**
  ⚠️ You must install the **v2.2.0 userspace module**; an older module will be
  refused by the installer.
- `0ea66af5` — internal naming unified to the `nm_` prefix (this is why the
  `nomount_*` symbol count drops; see the verification section).
- `f0478cad` — `xattr_handler->__get` probed by grepping `include/linux/xattr.h`
  instead of by kernel version. This is the mechanism that lets v2.2.0 build
  cleanly on 4.19 without patching.
- `211856e2` — batch lock held on add failures (partial rule set cannot be
  published).
- `aea50734` — rules and leaves reclaimed in process context.
- `2ef0b153` — on unload, `i_dentry` is walked to clear `d_op` before module
  memory is freed.
- `e5fe8a7f` — `d_op` hijack skipped for dentries in pseudo filesystems (procfs,
  sysfs, …), which removes a whole class of unintended interactions.
- `26c5c065` — `d_op` hijack skipped for dentries with no rule for their name.
- `3900fe30` — `inode_state_read_once` used for `I_NEW` checks.
- `6564660d` — `d_op` publication ordered before `d_flags`.
- `09573470` — dentry validation preserved for excluded UIDs.
- `8f9ede54` — repeated superblock hijack checks skipped.

### What is unchanged
| Component | Version | Note |
|---|---|---|
| SUSFS | v2.3.0 | untouched, as instructed |
| BakaSU | 35222 (`5b76b884`) | deliberately pinned — see below |
| NoMount integration | `fs/Kconfig:331`, `fs/Makefile:19`, `even_defconfig` `CONFIG_NOMOUNT=y` | unchanged |
| CPU scheduler | `CONFIG_HZ=250` | unchanged from V1.8 |
| cpufreq / DVFS | stock vendor tables | untouched |

## BakaSU — why it was NOT moved forward

`Baka-SU/BakaSU` `main` is 30 commits ahead of our pin. It was deliberately **not**
adopted, for two reasons:

1. The tip of `main`, `48fa4bb7`, appends to `kernel/tools/susfs_compat.mk`:
   ```
   $(error Please wait susfs update.)
   ```
   `kernel/Kbuild:189` includes that file whenever `CONFIG_KSU_SUSFS=y`, so a
   `CONFIG_KSU_SUSFS=y` build against `main` HEAD **hard-fails**. The newest safe
   pin is its parent `9097b1a1c6`.

2. The author's own rationale (AlexLiuDev233, 2026-10-10): *"SUSFS haven't sync
   latest KernelSU. It will cause a lot of detections from selinux_hide."* Since
   SUSFS v2.3.0 is the version in this kernel, moving BakaSU forward trades a
   stealth risk for no benefit you asked for.

The latest tag `v4.2.0-rc3` (`239e1e8871`) is **older** than our pin — it is the
merge-base of the tag and our pin, i.e. our pin is 51 commits *ahead* of it. It is
not an upgrade path.

The 29 commits between our pin and `9097b1a1c6` are mostly ksud/manager userspace;
the kernel-relevant ones are `fa12ffde` (time side-channel in selinux_hide),
`d7260ca1` (`context_add_hash` before sidtab ops), `a90ac6f0` (dead code removal),
`522081c5` (32-bit userspace on 64-bit kernel), `478906f3` (`shell_su_adb_only`),
`fc80da5e` (force feature values via ksu_config), `48f0f2a5` (module preinit),
`33d49c91` (migrate to `module_blacklist` param), `64814408` (skip execve when
ksud absent), `201884b4` (`ksu_close_fd` in susfs backport), `f9b305b2`
(`ksys_unshare` to ksyscall), `d5e9e025` (limit code generators on CONFIG_KSU).
If you want these later, the correct sequence is: wait for SUSFS to sync upstream,
then move the pin and re-verify the `susfs_inline` hook set.

## SUSFS

Left at v2.3.0 per your instruction. The upstream source repository is not
reachable from this environment (`simonpunk/susfs`, `susfs/susfs`,
`JackA1ltman/susfs` all 404; GitLab TLS-blocked), so there was nothing newer to
compare against. The only known source is the patchset vendored inside
`JackA1ltman/NonGKI_Kernel_Build_2nd`.

## Build verification

- Build exit code **0**, **0** `error:` lines, **0** warnings from
  nomount / susfs / cpufreq / KernelSU code (74 warnings, all pre-existing vendor).
- `CC fs/nomount/nomount.o` + `AR fs/nomount/built-in.a` clean — **v2.2.0 compiles
  against 4.19 without any patching**. The Makefile's `NM_HAS_XATTR__GET`
  auto-detect engages because `include/linux/xattr.h:36` defines `__get`.
- **14 / 14** `susfs_inline` hooks present.
- All 10 SUSFS hook symbols present **exactly once** each in `System.map`:
  `ksu_handle_setresuid`, `ksu_handle_execveat`, `ksu_handle_execveat_sucompat`,
  `ksu_handle_post_execveat_sucompat`, `ksu_handle_faccessat`,
  `ksu_handle_sys_read`, `ksu_handle_stat`, `ksu_handle_sys_reboot`,
  `ksu_handle_input_handle_event`, `ksu_handle_vfs_fstat`.
- Config: `CONFIG_NOMOUNT=y`, `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y`, 9/9
  `CONFIG_KSU_SUSFS_*` sub-features, `CONFIG_HZ=250`.
- Symbols: 65 `susfs_*`, 226 `ksu_*`, 59 `nm_*`, 2 `nomount_*`
  (`nomount_init`, `nomount_exit`).

  The drop from 13 `nomount_*` to 2 is **intentional and expected** — v2.2.0 commit
  `0ea66af5` unifies the internal naming onto the `nm_` prefix (139 unique `nm_*`
  symbols in the source vs. the old `nomount_*` set). The externally visible entry
  points (`nomount_init`, `nomount_exit`, `nm_key_preparse`) and all 12
  `NM_CMD_*` ioctls are intact: `ADD_RULE`, `ADD_UID`, `BLOCK_ISOLATED_UIDS`,
  `CLEAR_ALL`, `CLEAR_RULES`, `CLEAR_UIDS`, `DEL_RULE`, `DEL_UID`,
  `GET_ISOLATED_STATE`, `GET_LIST`, `GET_UIDS`, `GET_VERSION`.
- In-image strings: `v4.2.0-rc3-5b76b884@BakaSU`,
  `susfs is initialized! version: v2.3.0`, `NoMount: Loaded successfully`,
  `NOMOUNT_BASE_VERSION "22"`.
- 0 TAGLMK, 0 ReSukiSU strings.
- No `.rej` / `.orig` files anywhere in the tree.
- Only `fs/nomount/*` and `release/nomount-2.2.0/*` differ from the previous
  release — the rest of the 77-entry kernel tree is untouched.

## Files

- `Image.gz-dtb` — 18,081,308 bytes, sha512 `96337724a2b921723d4f7ed4eae7f929…`
- `System.map`, `even_defconfig.config` — full symbol map and defconfig output

## Flashing

Flash `Zenium-Kernel-RUI4-V1.9-susfs-4-bakasu-nomount-2.2.0-hz250.zip` from
AnyKernel3 recovery. `BLOCK=/dev/block/by-name/boot`, `IS_SLOT_DEVICE=0`.

**After flashing, install the NoMount v2.2.0 userspace module.** The driver
protocol is now v22 and the installer refuses an older module.
