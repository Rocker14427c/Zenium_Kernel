# SUSFS integration into this 4.19 non-GKI "rui4-clean" kernel

This document records **exactly** what was changed to integrate
[SUSFS](https://gitlab.com/simonpunk/susfs4ksu) (v2.3.0, `NON-GKI` variant) into
this Linux 4.19 MediaTek/Oplus tree, following the integration method of
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/)
(ReSukiSU + SUSFS **inline** hooks).

Nothing else in the tree was touched: all Oplus/Realme/vendor code, drivers,
KernelSU/ReSukiSU code, configs and kernel behaviour are unchanged apart from
the SUSFS additions and the manual-hook → inline-hook conversion that SUSFS
mode requires.

---

## 1. Method (as per the reference repository)

The reference repo does, in order:

1. `Patches/Patch/susfs_patch_to_4.19.patch` — the core SUSFS patch.
2. `Patches/susfs_inline_hook_patches.sh` — converts the KernelSU *manual* hooks
   into *SUSFS inline* hooks (`CONFIG_KSU_SUSFS` guarded).
3. `.github/workflows/patch-susfs/action.yml` — writes the `CONFIG_KSU*` /
   `CONFIG_KSU_SUSFS*` defconfig entries (and `CONFIG_THREAD_INFO_IN_TASK=y`
   when the KernelSU Kconfig needs it).
4. `.github/workflows/patch-no-kprobe/action.yml` — additionally strips
   `static` from a few SELinux symbols **only when `CONFIG_KALLSYMS_ALL` is not
   set**.

All four steps were replicated. Step 2's `sed` anchors do **not** match this
Oplus tree (it assumes upstream `SYSCALL_DEFINE3(faccessat …)` /
`do_faccessat()` shapes), so every injection point was hand-adapted instead —
see §3.

### Verification against the reference patch

The reference patch was applied to a pristine checkout of the base commit in a
throw-away worktree and compared hunk-by-hunk against this branch:

* **101 / 101 hunks present** (verified programmatically: every `+` line of
  every hunk of `susfs_patch_to_4.19.patch` is present verbatim in this tree).
* Two deliberate deviations, both required by the 4.19 API (see §4).
* No `.rej` / `.orig` files anywhere in the tree.
* `fs/susfs.c`, `include/linux/susfs.h` and `include/linux/susfs_def.h` are
  **byte-identical** to the reference, except for one typo fix (see §4).

---

## 2. Files added

| File | Lines | Purpose |
|---|---:|---|
| `fs/susfs.c` | 1558 | SUSFS core: sus_path / sus_mount / sus_kstat / open_redirect / sus_map tables, uname + cmdline spoofing, AVC log spoofing, `susfs_init()` |
| `include/linux/susfs.h` | 243 | Public SUSFS API + ioctl command numbers + `SUSFS_VERSION "v2.3.0"` |
| `include/linux/susfs_def.h` | 219 | SUSFS constants: magic `0xFAFAFAFA`, `DEFAULT_KSU_MNT_ID`, `TIF_*`, `AS_FLAGS_*`, `ND_STATE_*`, `STATX_SUS_KSTAT*`, `susfs_starts_with()`, inode/TIF test helpers |

`fs/susfs.c` is built via `obj-$(CONFIG_KSU_SUSFS) += susfs.o` added to
`fs/Makefile`.

---

## 3. Files modified

### 3.1 Core SUSFS patch (`susfs_patch_to_4.19.patch`)

| File | Change |
|---|---|
| `fs/Makefile` | `obj-$(CONFIG_KSU_SUSFS) += susfs.o` |
| `fs/namei.c` | SUS_PATH hooks in `lookup_dcache()`, `__lookup_hash()`, `lookup_fast()`, `__lookup_slow()`, `walk_component()`, `link_path_walk()`, `lookup_last()`, `lookup_open()`, `do_last()`; OPEN_REDIRECT hooks in `do_tmpfile()` / `do_o_path()` |
| `fs/namespace.c` | SUS_MOUNT: `mnt_free_id()`, `mnt_alloc_group_id()`, `__lookup_mnt()`, `vfs_create_mount()`, `clone_mnt()`, `copy_mnt_ns()` + new `susfs_alloc_unshare_ksu_vfsmnt()` / `susfs_alloc_non_unshare_ksu_vfsmnt()` / `susfs_get_non_sus_mnt_id_from_mnt()` / `susfs_get_non_sus_vfsmnt_from_vfsmnt()` |
| `fs/proc_namespace.c` | SUS_MOUNT: `susfs_show_vfsmnt()`, `susfs_show_mountinfo()`, `susfs_show_vfsstat()` and their dispatch in `mounts_open_common()` wrappers |
| `fs/readdir.c` | SUS_PATH: hide sus-path entries in `fillonedir()` / `filldir()` / `filldir64()`, FUSE `/data` fallback in `old_readdir` / `getdents` / `getdents64` |
| `fs/stat.c` | SUS_KSTAT spoofing in `vfs_getattr_nosec()`; SUS_PATH+inline stat hook in `vfs_statx()`; `ksu_handle_vfs_fstat()` in `vfs_statx_fd()` |
| `fs/statfs.c` | SUS_KSTAT (`susfs_statfs_by_dentry()`) and SUS_MOUNT (`susfs_get_non_sus_vfsmnt_from_vfsmnt()`) in `vfs_statfs()` |
| `fs/super.c` | SUS_MOUNT: fake anon bdev for the KSU domain in `get_anon_bdev()` |
| `fs/notify/fdinfo.c` | SUS_KSTAT + SUS_MOUNT spoofing of inotify fdinfo (`show_fdinfo()` gains the `struct file *` argument) |
| `fs/proc/base.c` | OPEN_REDIRECT in `do_proc_readlink()`; SUS_MAP in `proc_map_files_readdir()` |
| `fs/proc/cmdline.c` | SPOOF_CMDLINE_OR_BOOTCONFIG in `cmdline_proc_show()` |
| `fs/proc/fd.c` | SUS_KSTAT + SUS_MOUNT spoofing of `/proc/<pid>/fd/<n>` |
| `fs/proc/task_mmu.c` | SUS_KSTAT in `show_map_vma()`; SUS_MAP in `show_smap()`, `show_smaps_rollup()`, `pagemap_read()`; OPEN_REDIRECT in `show_map_vma()` |
| `mm/memory.c` | SUS_MAP guard in `__access_remote_vm()` |
| `kernel/kallsyms.c` | HIDE_KSU_SUSFS_SYMBOLS: filter `ksu_*`, `susfs_*`, … from `/proc/kallsyms` |
| `kernel/sys.c` | SPOOF_UNAME in `newuname()` |
| `security/selinux/avc.c` | AVC log spoofing in `avc_dump_query()` |

### 3.2 Manual-hook → SUSFS inline-hook conversion

The tree shipped KernelSU **manual hooks** (`CONFIG_KSU_MANUAL_HOOK` +
`CONFIG_KSU_MANUAL_HOOK_AUTO_{SETUID,INITRC,INPUT}_HOOK`). SUSFS mode is a
mutually exclusive `choice` in `KernelSU/kernel/Kconfig`, and ReSukiSU's
`tools/inline_hook_check.mk` hard-fails the build if any hook is missing or if a
`CONFIG_KSU_MANUAL_HOOK` guard is left behind. Every site was therefore
converted **in place** (no duplicated/shadowed hooks):

| File | Was (manual hook) | Now (SUSFS inline hook) |
|---|---|---|
| `kernel/sys.c` | `#ifdef CONFIG_KSU_MANUAL_HOOK` + `(void)ksu_handle_setresuid(...)` in `__sys_setresuid()` | `#ifdef CONFIG_KSU_SUSFS` + same call, guard tightened |
| `fs/exec.c` | `ksu_handle_execveat()` in `do_execve()` / `compat_do_execve()` | `ksu_handle_execveat()` / `ksu_handle_execveat_sucompat()` in `__do_execve_file()` (after the `IS_ERR(filename)` check, so `call_usermodehelper()` is not hooked) + `ksu_handle_post_execveat_sucompat()` at `out_unmark:` |
| `fs/open.c` | `ksu_handle_faccessat()` in `SYSCALL_DEFINE3(faccessat)` | `getname_flags()` + `ksu_handle_faccessat()` inside `do_faccessat()` at `retry:` |
| `fs/stat.c` | `ksu_handle_stat()` in `newfstatat`/`fstatat64`, `ksu_handle_newfstat_ret()` in `newfstat`, `ksu_handle_fstat64_ret()` in `fstat64` | `ksu_handle_stat()` in `vfs_statx()`; `ksu_handle_vfs_fstat()` in `vfs_statx_fd()` (the two `*_ret` hooks do not exist in SUSFS mode and were removed) |
| `fs/read_write.c` | `if (unlikely(ksu_init_rc_hook))` | `if (static_branch_unlikely(&ksu_is_init_rc_hook_enabled))` |
| `kernel/reboot.c` | unconditional `ksu_handle_sys_reboot()` | same, wrapped in `if (system_state == SYSTEM_RUNNING)` (as in the reference script) |
| `drivers/input/input.c` | `if (unlikely(ksu_input_hook))` | `if (static_branch_unlikely(&ksu_is_input_hook_enabled))` |

The declarations were moved to the top of each file (the manual-hook versions
declared them *after* use, which is what the old `__attribute__((hot))` block
was for) so the SUSFS code compiles.

### 3.3 defconfig — `arch/arm64/configs/even_defconfig`

```
 # CONFIG_KSU_MANUAL_HOOK is not set      <-- was CONFIG_KSU_MANUAL_HOOK=y
 CONFIG_KSU_SUSFS=y                       <-- was # CONFIG_KSU_SUSFS is not set
 CONFIG_KSU_SUSFS_SUS_PATH=y
 CONFIG_KSU_SUSFS_SUS_MOUNT=y
 CONFIG_KSU_SUSFS_SUS_KSTAT=y
 CONFIG_KSU_SUSFS_SPOOF_UNAME=y
 CONFIG_KSU_SUSFS_ENABLE_LOG=y
 CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y
 CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y
 CONFIG_KSU_SUSFS_OPEN_REDIRECT=y
 CONFIG_KSU_SUSFS_SUS_MAP=y
```

(the three dead `CONFIG_KSU_MANUAL_HOOK_AUTO_*` lines were replaced by the nine
`CONFIG_KSU_SUSFS_*` feature symbols; the surrounding comment banner was
updated to point at the SUSFS repo.)

`CONFIG_THREAD_INFO_IN_TASK=y` (needed by `KSU_SUSFS`) was already set at line 15
of the defconfig, so nothing was added there.

---

## 4. The two deliberate deviations from the reference patch

1. **`fs/namespace.c` — `vfs_kern_mount()` hook relocated to
   `vfs_create_mount()`.** 4.19 refactored `vfs_kern_mount()` onto the
   `fs_context` API, so the `alloc_vfsmnt()` call the patch wants to intercept
   no longer exists there — it moved into `vfs_create_mount()`. The hook was
   therefore placed there, with `fc->source ?: "none"` instead of the patch's
   `name ?:"none"`, and a comment explaining why. Semantics are identical (and
   strictly better: `fc_mount()` paths are covered too).

2. **`fs/susfs.c` — removed a stray backslash.** The reference patch's last line
   of the `fs/susfs.c` new-file hunk is literally
   `+void susfs_init(void) {\` (trailing `\`). Left as-is that becomes a line
   continuation, which is why the upstream patch happens to still compile. It is
   removed here.

Everything else is verbatim from `susfs_patch_to_4.19.patch`.

---

## 5. Why no `security/*` changes were needed

`susfs_inline_hook_patches.sh` also patches `security/security.c`,
`security/selinux/hooks.c` and `security/selinux/ss/services.c`. For this tree
those steps are **no-ops**, and adding them would have been wrong:

* `security/security.c`: guarded by `FIRST_VERSION < 4 && SECOND_VERSION < 19`
  → **skipped for 4.19** ("Kernel needn't setuid, Skipped.").
* `security/selinux/ss/services.c`: `selinux_state` exists in
  `security/selinux/include/security.h` → **skipped** ("Kernel needn't
  selinux_state fix, Skipped.").
* `security/selinux/hooks.c`: `security_secid_to_secctx` is not present, so the
  script *would* add a `selinux_bprm_committing_creds` su-domain hook, and it
  would add a `ksu_hide_setprocattr()` hook if that symbol existed. **ReSukiSU
  implements both at runtime instead**: `KernelSU/kernel/hook/lsm_hooks.c`
  resolves `selinux_ops` and patches `ops->inode_rename`,
  `ops->setprocattr`, `ops->key_permission` (plus `task_fix_setuid` /
  `file_permission` in manual-hook mode) via `stop_machine()`. Adding static
  hooks on top would duplicate/shadow that machinery. ReSukiSU also registers
  `bprm_committed_creds` through the normal
  `security_add_hooks(...,"ksu")` path (`KSU_COMPAT_NO_POST_EXECVE_HOOK` is
  defined for this tree), which is what makes `ksu_handle_post_execveat_sucompat`
  fire.

Similarly, `patch-no-kprobe/action.yml`'s "remove `static` from SELinux symbols"
step is skipped because `CONFIG_KALLSYMS_ALL` is not set **and**
ReSukiSU's own `tools/static_export_check.mk` (which *is* included for exactly
that reason) confirms `write_op` and `sel_handle_status_ops` are already
non-static in this tree. The build log shows both checks passing.

---

## 6. SUSFS features and their status

All nine selectable features are enabled and compile/link clean:

| Feature | What it does here | Status |
|---|---|---|
| `SUS_PATH` | hides SUS-mapped paths from `open`/`stat`/`readdir` lookups (fake qstr dentry + `-ENOENT` on sub-path walks) | ✅ enabled |
| `SUS_MOUNT` | hides KSU mounts from `/proc/mounts`, `/proc/<pid>/mountinfo`, `/proc/<pid>/mountstats`, `/proc/<pid>/fd/*`, inotify fdinfo, `statfs`, and gives KSU-domain mounts a `mnt_id >= DEFAULT_KSU_MNT_ID` | ✅ enabled |
| `SUS_KSTAT` | spoofs `stat`/`statx`/`statfs`/`/proc/<pid>/maps`/`smaps`/`fd`/inotify output for SUS-mapped inodes | ✅ enabled |
| `SPOOF_UNAME` | `uname -a` returns the SUSFS-configured release string | ✅ enabled |
| `ENABLE_LOG` | `SUSFS_LOGI`/`SUSFS_LOGE` logging | ✅ enabled |
| `HIDE_KSU_SUSFS_SYMBOLS` | filters `ksu_*`, `__ksu_*`, `susfs_*`, `ksud*`, `is_ksu_*`, `is_manager_*`, `escape_to_*`, `setup_selinux`, `track_throne`, `on_post_fs_data`, `try_umount`, `kernelsu*`, `__initcall__kmod_kernelsu*`, `apply_kernelsu*`, `handle_sepolicy`, `getenforce`, `setenforce`, `is_zygote` out of `/proc/kallsyms` | ✅ enabled |
| `SPOOF_CMDLINE_OR_BOOTCONFIG` | `/proc/cmdline` returns the SUSFS-configured string | ✅ enabled |
| `OPEN_REDIRECT` | redirects `open()`/`readlink()` on redirected paths | ✅ enabled |
| `SUS_MAP` | hides SUS-mapped VMAs from `/proc/<pid>/maps`, `smaps`, `smaps_rollup`, `pagemap` and `__access_remote_vm()` (i.e. from other processes' `ptrace`/`process_vm_readv`) | ✅ enabled |

Note: these features are **dormant until userspace configures them** — SUSFS is
driven through the `ksu_susfs` ioctl interface (`CMD_SUSFS_*`, magic
`0xFAFAFAFA`) which the KernelSU manager / `ksud` issues at boot. The kernel
side is complete and correct; nothing further is required from the kernel.

Runtime sanity checks that were verified on the built image:

* `out/include/generated/autoconf.h` contains `CONFIG_KSU_SUSFS` and all nine
  sub-features.
* `out/vmlinux` contains 66 `susfs_*` symbols and 331 `ksu_*` symbols
  (`ksu_handle_susfs_cmd`, `susfs_add_sus_path`, `susfs_add_sus_mount`,
  `susfs_add_sus_kstat`, `susfs_add_open_redirect`, `susfs_add_sus_map`,
  `susfs_enable_log`, `susfs_spoof_uname`, `susfs_spoof_cmdline_or_bootconfig`, …).
* `susfs_init()` is called from `KernelSU/kernel/core/init.c:121` in the
  `CONFIG_KSU_SUSFS` branch of `ksu_hook_init()`.
* All seven required inline hooks are found by ReSukiSU's
  `tools/inline_hook_check.mk`:
  `ksu_handle_setresuid`, `ksu_handle_execveat`, `ksu_handle_faccessat`,
  `ksu_handle_sys_read`, `ksu_handle_stat`, `ksu_handle_sys_reboot`,
  `ksu_handle_input_handle_event`.
* No `CONFIG_KSU_MANUAL_HOOK` guard remains anywhere outside the untouched
  `KernelSU/` submodule.

---

## 7. Building

`run.sh` (Origami/Zenium build script) is unchanged and works as before:
`bash run.sh --choose=1`.

For a from-scratch, dependency-free build on a bare Linux box, two helper
scripts are provided:

```sh
bash scripts/setup_build_env.sh     # fetches clang r416183b + bison/flex/m4/bc shim
bash scripts/build_susfs.sh         # make even_defconfig && make (same flags as run.sh)
```

`scripts/setup_build_env.sh` provisions everything the build host needs:

* **Android clang r416183b** (clang 12.0.5, `ld.lld`, `llvm-*`) — plain
  `git clone`, no release-asset downloads.
* **bison 3.8.2 / flex 2.6.4 / GNU m4 1.4.20** — vendored inside manylinux
  wheels from PyPI (`bison_bin`, `flex_bin`, `cmeel-m4`), because
  `scripts/kconfig/zconf.{tab,lex}.c` cannot be generated without them and most
  minimal images have none of the three. `M4` is exported because the wheel's
  bison has `/usr/bin/m4` hard-coded from its build machine.
* **a `bc` stand-in** (`scripts/bc_shim.py`) — `include/generated/timeconst.h`
  is produced by piping `CONFIG_HZ` through `bc`; the shim reproduces
  `kernel/time/timeconst.bc`'s semantics exactly and emits byte-identical
  output.
* **openssl headers/libcrypto overrides** for the `scripts/sign-file` and
  `scripts/extract-cert` host tools (needed only because this defconfig has
  `CONFIG_MODULE_SIG=y` / `CONFIG_SYSTEM_TRUSTED_KEYRING=y`).

Output: `out/arch/arm64/boot/Image.gz-dtb`.

---

## 8. Verification performed

* **Full build**: `make even_defconfig` + `make -j2` (clang r416183b,
  `LLVM=1 LLVM_IAS=1`) → `out/arch/arm64/boot/Image.gz-dtb` (18 MB) produced,
  exit status 0, **no errors**.
* **Zero new warnings**: all 21 modified/new `.c` files were force-recompiled and
  produced no compiler diagnostics. The only warnings seen in a full build are
  pre-existing ones in untouched files (`lib/lz4/lz4hc.c`,
  `drivers/usb/gadget/function/rndis.c`).
* **Reproducibility**: a second, fully independent clean build in a separate
  output directory (driven by `scripts/build_susfs.sh`) produced an
  `Image.gz-dtb` of the same size, differing only in the embedded build
  timestamp.
* **Config robustness**: the tree was compiled once for each of the ten
  `CONFIG_KSU_SUSFS_*` sub-features **in isolation**, plus once with *all*
  sub-features disabled. All eleven configurations compile clean, which proves
  every `#ifdef` guard (and every `goto` label / `extern` declaration /
  `#include`) in the touched files is correctly balanced.
* **Symbols**: `out/vmlinux` contains 66 `susfs_*` and 331 `ksu_*` symbols,
  including `ksu_handle_susfs_cmd`, `susfs_add_sus_path`, `susfs_add_sus_mount`,
  `susfs_add_sus_kstat`, `susfs_add_open_redirect`, `susfs_add_sus_map`,
  `susfs_enable_log`, `susfs_spoof_uname`,
  `susfs_spoof_cmdline_or_bootconfig`.
* **ReSukiSU build-time checks all pass** (visible in the build log):
  `susfs_inline: ksu_handle_{setresuid,execveat,faccessat,sys_read,stat,
  sys_reboot,input_handle_event} found`, all `ReSukiSU/compat:` probes, and
  `symbol_export: write_op found` / `sel_handle_status_ops found`.
* **No `.rej` / `.orig` files** anywhere in the tree; no leftover
  `CONFIG_KSU_MANUAL_HOOK` guard outside the untouched `KernelSU/` submodule
  (which is still pinned at `6ec8d9a8a8be30878c388504cacf8ae7849c757b`).
* **Hunk-by-hunk comparison** with `susfs_patch_to_4.19.patch`: 101/101 hunks
  present verbatim; the only two differences are the deliberate, documented
  adaptations in §4.

### Not verified

There is no device in this environment, so the SUSFS runtime behaviour
(actual hiding of paths/mounts/stats, `ksu_susfs` ioctl round-trip, su
handling) has **not** been exercised on hardware. What is verified is that the
kernel side is complete, correctly wired into ReSukiSU, and that it builds and
links. Userspace (`ksud` / the KernelSU manager) drives SUSFS at boot through
the `CMD_SUSFS_*` ioctls.

---

## 9. Cross-branch review (`01a0eb93` vs `01a0eb9a` vs `susfs-3`)

A full independent review of three branches was performed. All three share the
same base commit `7d5fb409a`:

| | branch | head | builds? |
|---|---|---|---|
| **mine** | `arena/01a0eb93-zenium-kernel` | `554fe5946` | yes (0 errors) |
| **B** | `arena/01a0eb9a-zenium-kernel` | `f4b01b17b` | yes (0 errors, 22 files probed) |
| **C** | `susfs-3` | `f8a7a8d29` | **NO — hard compile error** |

All three carry byte-identical `fs/susfs.c`, `include/linux/susfs.h`,
`include/linux/susfs_def.h`, and identical `fs/Makefile`, `fs/proc/{base,cmdline,fd}.c`,
`fs/proc_namespace.c`, `fs/readdir.c`, `kernel/kallsyms.c`, `mm/memory.c`,
`security/selinux/avc.c`. (B and C keep the reference patch's stray trailing
backslash on `void susfs_init(void) {\` — cosmetic, still valid C.)

### 9.1 Empirical build probes

`fs/read_write.o` compiled from `susfs-3`:

```
../fs/read_write.c:619:1: error: too few arguments provided to function-like macro invocation
SYSCALL_DEFINE3(read, unsigned int fd, char __user *, buf, size_t, count)
make[2]: *** [../scripts/Makefile.build:339: fs/read_write.o] Error 1
```

`susfs-3` dropped the comma in `SYSCALL_DEFINE3(read, unsigned int, fd, ...)`
(the base/mine/B form), so `__MAP(3, __SC_DECL, …)` receives 5 arguments
instead of 6. `susfs-3` therefore cannot build at all.

### 9.2 `fs/exec.c` — the two critical runtime differences

`kernel/umh.c:109` calls `do_execve_file()`, which is
`fs/exec.c:2003-2008`:

```c
int do_execve_file(struct file *file, void *__argv, void *__envp)
{
        ...
        return __do_execve_file(AT_FDCWD, NULL, argv, envp, 0, file);
}
```

i.e. **`filename` is NULL** on the `call_usermodehelper()` path.

* **C** guards only `if (likely(susfs_is_current_proc_no_su())) goto orig_flow;`.
  `ksu_handle_execveat()` in `KernelSU/kernel/feature/sucompat.c:483` only tests
  `IS_ERR(filename)` (false for `NULL`) and then dereferences `filename->name`
  → **NULL-pointer dereference / Oops on every `call_usermodehelper()`** once
  `ksu_su_compat_enabled` is on. The reference script has the same latent bug.
* **B** does guard with `if (unlikely(!filename)) goto ksu_orig_flow;`, but calls
  `ksu_handle_execveat{,_sucompat}(…)` discarding the return value and
  **never calls `ksu_handle_post_execveat_sucompat()`** (`grep -c` = 0 in its
  `fs/exec.c`). The whole sucompat post-execve path is dead code there, so
  `ksu_handle_post_execve()` (and `ksu_install_su_fd()`) never runs.
* **mine** has both: the `!filename` guard *and* the `is_su_session`
  post-hook at `out_unmark:`.

### 9.3 `fs/notify/fdinfo.c` — latent build break, fixed on this branch

`show_fdinfo()`'s callback type is guarded by
`#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_SUS_KSTAT)`,
but on this branch (and on `susfs-3`) `inotify_fdinfo()`'s signature was guarded
by `#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT` and `fanotify_fdinfo()` was left
completely unguarded (2-arg). Both call sites
(`inotify_show_fdinfo()` / `fanotify_show_fdinfo()`) therefore passed a
2-argument function where a 3-argument pointer was required.

Reproduced before the fix, and gone after:

| configuration | before | after |
|---|---|---|
| `SUS_MOUNT=n, SUS_KSTAT=y` | `fs/notify/fdinfo.c:174: error: incompatible function pointer types` | clean |
| all features on + `CONFIG_FANOTIFY=y` | `fs/notify/fdinfo.c:236: error: incompatible function pointer types` | clean |

The shipped `even_defconfig` (all features on, `CONFIG_FANOTIFY` off) was never
affected, which is why the earlier build passed — this was a latent
config-permutation defect, not a build blocker for the default config.
Both callbacks are now guarded with the same predicate as `show_fdinfo()`.
**B** already did this correctly.

### 9.4 `fs/stat.c` — SUSFS-private `statx()` bits leaking to userspace

`cp_statx()` does `tmp.stx_mask = stat->result_mask;` (`fs/stat.c:613`), and
`STATX_SUS_KSTAT` / `STATX_SUS_KSTAT_FUSE` are private bits
(`0x10000000U` / `0x20000000U`, far outside `STATX_ALL = 0x00000fffU`).
`vfs_getattr_nosec()` sets them as an internal "please spoof this" signal. If
they are returned unchanged, `statx()` hands userspace a mask containing bits
no stock kernel ever sets — a one-instruction detector for SUSFS.

> **Correction (see §9.9):** the first version of this section had the diff
> direction backwards. It was **this branch** that leaked the bits; B and
> `susfs-3` both mask them (5 masking sites each). The masking was adopted here
> in §9.9. The section is kept because the analysis of *why* the leak matters
> is correct and is what drove the fix.

### 9.5 Cosmetic / housekeeping differences found and fixed

* `fs/namei.c` — stray trailing tab left by the `CONFIG_KSU_SUSFS_SUS_PATH`
  wrapping of `__lookup_hash()` (`return dentry;\t`). Removed.
* `fs/namespace.c` — `goto  out_free_id;` (double space) in
  `susfs_alloc_non_unshare_ksu_vfsmnt()`. Corrected.
* `kernel/sys.c` — this branch uses `(void)ksu_handle_setresuid(...)` (matches
  the base tree's existing style); B/C use the reference's
  `if (ksu_handle_setresuid(...)) pr_info("Something wrong ...")`.
  Both are functionally identical; kept as is.
* `drivers/input/input.c` — see §9.6.

### 9.6 `drivers/input/input.c` — deliberate placement difference

The reference script injects the hook into `input_handle_event()` right after
`input_get_disposition()`; B and C do that. This branch instead converted the
**pre-existing** `#ifdef CONFIG_KSU_MANUAL_HOOK` block in `input_event()`
in place (`base:459-462`) into `#ifdef CONFIG_KSU_SUSFS` +
`static_branch_unlikely(&ksu_is_input_hook_enabled)`.

Decided from the actual code, not by copying: `ksu_handle_input_handle_event()`
(`KernelSU/kernel/runtime/ksud_integration.c:789`) only reads
`*type == EV_KEY && *code == KEY_VOLUMEDOWN && *value` and bumps a counter; it
never modifies the event and always returns 0. `input_handle_event()` is
`static` and called only from `input_event()`, so both placements observe the
same event stream, and `input_get_disposition()` does not alter `value` for
`EV_KEY`. The chosen site additionally runs outside `dev->event_lock`
(irqsave), which is the safer atomic context, and it keeps the hook at the
tree's existing hook site. All three branches removed the now-dead
`CONFIG_KSU_MANUAL_HOOK` block, since ReSukiSU's Kconfig makes the three hook
methods a mutually exclusive `choice`.

### 9.7 Verification after the fixes

* Full build: **exit 0**, 0 errors. `out/System.map` is byte-identical
  (md5 `183466f34e486732e12ae41e2bceed16`) to the susfs-1 System.map, which
  confirms the three fixes are codegen-neutral for the shipped configuration.
* All **11** `CONFIG_KSU_SUSFS_*` permutations (each feature alone, all
  features, SUSFS off) compile clean — including the two that failed before.
* No `.rej` / `.orig` / stray `.bak` files were produced by this work (the five
  `.bak` files in `drivers/**/mali*/` are pre-existing and tracked in
  `7d5fb409a`).
* `git status` shows only the intended files modified.
* Flashable AnyKernel3 zip: `release/susfs-2/Zenium-Kernel-RUI4-V1.6-susfs-2.zip`
  (20,621,529 B, `Image.gz-dtb` 18,061,377 B,
  sha512 `40a0099e29405a5f9172b3bb49cf2186807e198a9e82f0269b5b0ae4e10ee93529e075a0e412830980f88d7b026e56677f9ce05d748149c75d3e32fb8c692908`).
The final release is `release/susfs-3-final/Zenium-Kernel-RUI4-V1.6-susfs-3-final.zip`
(20,619,024 B, `Image.gz-dtb` 18,060,571 B, sha512
`dc5c94b6bd2b124db24264e2fd1014043c867b1fde7fadae78167c15244bcaca81bc76b236ff091234e6b485e31c00638af1ab9e8a7803af247309920b3cd2b8`).

Still **not** verified: on-device runtime behaviour (see "Not verified" above).

### 9.8 Addendum — the other two branches moved during the review

Both other branches were force-updated by a parallel effort while this review
was running. The findings in §9.1–§9.7 are against the revisions that were
reviewed (`arena/01a0eb9a` @ `f4b01b17b`, `susfs-3` @ `f8a7a8d29`). Their current
heads and current state:

| | revision reviewed | current head | current state |
|---|---|---|---|
| mine | `554fe5946` | `58cc98b0dc8a` | builds clean, 11/11 permutations, zip released |
| `arena/01a0eb9a` | `f4b01b17b` | `2f26a2ad` | both defects fixed; 5 key files compile clean |
| `susfs-3` | `f8a7a8d29` | `449552946c` | 2 of 3 defects fixed; **still does not build** |

Current-head spot checks:

* `arena/01a0eb9a` @ `2f26a2ad` — `fs/exec.c` now has the `!filename` guard,
  captures `is_su_session` and calls `ksu_handle_post_execveat_sucompat()`
  (2 occurrences); `fs/stat.c` masks `STATX_SUS_KSTAT | STATX_SUS_KSTAT_FUSE`;
  `fs/read_write.c:619` is back to the correct `SYSCALL_DEFINE3(read,
  unsigned int, fd, …)`; `fs/notify/fdinfo.c` guards both callbacks with
  `MOUNT || KSTAT`; the `fs/namei.c` trailing tab and the
  `goto  out_free_id;` double space are gone. `fs/{exec,stat,susfs}.o`,
  `fs/notify/fdinfo.o` and `fs/read_write.o` all compile with exit 0.
* `susfs-3` @ `449552946c` — the `fs/exec.c` NULL guard and the
  `fs/notify/fdinfo.c` guards are fixed, but `fs/read_write.c:619` is **still**
  `SYSCALL_DEFINE3(read, unsigned int fd, char __user *, buf, size_t, count)`.
  Compiling it reproduces:
  ```
  ../fs/read_write.c:619:1: error: too few arguments provided to function-like macro invocation
  make[2]: *** [../scripts/Makefile.build:339: fs/read_write.o] Error 1
  ```
  so `susfs-3` still cannot produce a kernel. Its `fs/namei.c` trailing tab and
  `fs/namespace.c` `goto  out_free_id;` double space also remain.

ThinLTO (`CONFIG_LTO_CLANG=y` / `CONFIG_THINLTO=y`) is set in the **base**
tree's `even_defconfig` (lines 633-635), so all three branches — including this
one — build with ThinLTO. It is not a differentiator.

---

## 9.9 Second review round — cross-checking the other branches' fixes

After the other two agents published their own cross-branch audits, every
remaining difference between this branch and `susfs-3` @ `449552946c` was
re-diffed file by file (29 changed files), and their reports were re-checked
against the actual 4.19 code. **Their audits found a real defect in this branch
that the first review round had missed, because the first round read a diff in
the wrong direction.**

### 9.9.1 Defect in this branch — `fs/stat.c` leaked SUSFS-private `statx()` bits

`grep -c 'result_mask &= ~' fs/stat.c` returned **1** on this branch (only the
pre-existing `~STATX_ATIME`), versus **5** on both `susfs-3` and
`arena/01a0eb9a`. `cp_statx()` copies `stat->result_mask` verbatim into
`stx_mask` (`fs/stat.c:613`), so `statx()` returned
`STATX_SUS_KSTAT` (`0x10000000U`) / `STATX_SUS_KSTAT_FUSE` (`0x20000000U`) to
userspace — bits far outside `STATX_ALL` (`0x00000fffU`). That is a trivial
fingerprint for "SUSFS is present".

**Fixed:** added `stat->result_mask &= ~(STATX_SUS_KSTAT | STATX_SUS_KSTAT_FUSE);`
at all five SUS_KSTAT return paths of `vfs_getattr_nosec()` (two after
`inode->i_op->getattr()`, two on the no-getattr path), plus the mis-indented
`return err;` in the second branch. §9.4 above has been corrected.

### 9.9.2 Defect in this branch — `ksu_handle_vfs_fstat()` ran even on getattr failure

`vfs_statx_fd()` called `ksu_handle_vfs_fstat(fd, &stat->size)` whenever
`ksu_is_init_rc_hook_enabled` was set, with no `!error` check, so it could
write into a `struct kstat` that `vfs_getattr()` had failed to populate.
`susfs-3` and `arena/01a0eb9a` both guard it. **Fixed:** the condition is now
`if (!error && static_branch_unlikely(&ksu_is_init_rc_hook_enabled))`.

### 9.9.3 Input hook relocated to the reference site

`susfs-3`'s audit called the placement in `input_event()` a critical bug. It is
not a functional bug — verified from the code: `input_get_disposition()`
never writes `*pval` for `EV_KEY` (only `EV_ABS` goes through
`input_handle_abs_event()`), `input_handle_event()` is `static` and is called
only from `input_event()`, and `ksu_handle_input_handle_event()`
(`KernelSU/kernel/runtime/ksud_integration.c:789`) only reads
`*type == EV_KEY && *code == KEY_VOLUMEDOWN && *value`, never mutates the
event and always returns 0. So both sites observe identical data.

Nevertheless the reference script (`susfs_inline_hook_patches.sh:210-211`)
injects into `input_handle_event()` after `input_get_disposition()`, and both
other agents converged there. **The hook has been moved to
`input_handle_event()`** to match the reference exactly and to remove the one
remaining point of divergence. The extern block now also uses the
`__attribute__((cold))` prototype that ReSukiSU actually defines.

### 9.9.4 Cosmetic cleanups adopted

* `fs/statfs.c` — the closing `}` of `if (path->mnt == no_sus_vfsmnt) {` was
  indented one tab too shallow (the reference patch has the same typo, and
  `susfs-3` over-indents it by one). Now correctly indented at two tabs.
  **Braces were always balanced** — the claim that this branch was "missing a
  closing brace" in the `susfs-3` report is wrong; the control flow was and is
  exactly as intended.
* `fs/namespace.c` — `vfs_create_mount()` now hoists
  `const char *name = fc->source ?: "none";` to function scope instead of
  repeating the expression, matching `susfs-3`.

### 9.9.5 Claims in the other branches' reports that do not hold up

| claim | reality |
|---|---|
| `susfs-3` report: this branch is "missing its closing `}`" in `fs/statfs.c` and the "control flow is wrong … returns twice" | False. Brace depth verified 0→1→…→0 across `vfs_statfs()`; the `if (path->mnt == no_sus_vfsmnt)` block returns inside the `if` and the following block is its else-leg. Only the indentation was off. |
| `susfs-3` report: the `input_event()` placement "breaks the input-hook semantics ReSukiSU expects" | Not supported by the code — see §9.9.3. The hook has been moved anyway for reference fidelity. |
| `susfs-3` report: this branch ships binaries that "cannot have been produced by a clean build" | The susfs-1 build **did** succeed (exit 0, 0 errors). The two latent `fdinfo` defects only fire with `SUS_MOUNT=n` or `CONFIG_FANOTIFY=y`, neither of which is in the shipped `even_defconfig`. |
| `susfs-3` report: `arena/01a0eb9a` "has the `fs/statfs.c` brace bug + `susfs.c` stray backslash + missing `filename_lookup` extern" | The brace and the `filename_lookup` extern claims are both wrong (`fs/internal.h:64` declares `filename_lookup`, and both `fs/open.c` and `fs/stat.c` include it). The `fs/susfs.c` stray-backslash claim is correct — that branch does still carry it. |

### 9.9.6 State after this round

This branch and `susfs-3` @ `449552946c` are now **functionally identical**;
the only remaining differences are comment text, `#endif` trailing comments,
and where an `extern` declaration sits. This branch additionally has:

* a **building** `fs/read_write.c` (`susfs-3:619` is still
  `SYSCALL_DEFINE3(read, unsigned int fd, …)` → 20 compile errors);
* no trailing tab in `fs/namei.c`;
* no `goto  out_free_id;` double space;
* `fs/proc/task_mmu.c` matching the reference patch's unscoped form rather than
  adding a redundant `if (vma->vm_file)` / block scope.

`susfs-3` @ `449552946c` was recompiled to confirm it still fails:
```
../fs/read_write.c:619:1: error: too few arguments provided to function-like macro invocation
make[2]: *** [../scripts/Makefile.build:339: fs/read_write.o] Error 2
```

---

## 10. Round 3 — deep audit of this branch, and the `KSU_VERSION` runtime bug

Two things were done in this round: (a) a deep audit of **this branch only**
against the current mainline reference patch, and (b) a root-cause analysis and
fix for a runtime defect the user hit on the `susfs-3-final` zip.

### 10.1 The reference target was re-verified as current

`JackA1ltman/NonGKI_Kernel_Build_2nd` was re-fetched: HEAD is still `19c0215`
and `Patches/Patch/susfs_patch_to_4.19.patch` still has md5
`a47b31a4249e2f9f8b74b74f3fc397d3`. So the audit below is against the patch
that is actually current upstream, not a stale copy.

### 10.2 Runtime defect: manager refused to run on the `susfs-3-final` zip

The user flashed `Zenium-Kernel-RUI4-V1.6-susfs-3-final.zip`. The kernel
booted, susfs v2.3.0 loaded, but ReSukiSU reported:

> The current KernelSU version 30701 is too low for the manager to work
> properly, please upgrade to 35040 or higher!

…and showed no superuser or feature UI.

**Root cause — a build-environment bug, not a SUSFS bug.** `KernelSU/kernel/Kbuild`
derives the version with no Kconfig override:

```make
KSU_LOCAL_VERSION := $(shell cd $(KSU_SRC); git rev-list --count HEAD)
KSU_VERSION       := $(shell expr 30000 + $(KSU_LOCAL_VERSION) + 700)
```

The `KernelSU` submodule was a **shallow clone**
(`.git/modules/KernelSU/shallow` existed), so `rev-list --count HEAD` returned
**1**:

```
30000 + 1 + 700 = 30701     <- exactly the number the manager reported
```

The manager needs `KSU_VERSION >= 35040`, i.e. ≥ 4340 commits of history. A
depth-1 clone can never reach that. Kbuild's own unshallow guard is conditioned
on `[ -f ../.git/shallow ]`, which is the wrong path for a submodule (its git
metadata lives in `.git/modules/KernelSU/`), so it never fired.

Two consequences, both invisible to any compile check:

* `KSU_VERSION` = 30701 → the manager refuses to start its UI at all.
* `git describe --abbrev=0 --tags` failed (`fatal: No names found`), so
  `KSU_TAG_NAME` silently fell back to the hardcoded `"v4.1.0"` instead of the
  real tag.

`KSU_VERSION` reaches userspace via `kernel/supercall/dispatch.c:881`
(`cmd.version_full`) and `kernel/core/init.c:177-184`.

**Fix**

1. `git -C KernelSU fetch --unshallow origin` → commit count **1 → 4454**, HEAD
   still pinned at `6ec8d9a8a8be30878c388504cacf8ae7849c757b`, all tags restored
   (`v4.2.0-rc2` now describes HEAD).
2. `KSU_VERSION = 30000 + 4454 + 700 = **35154**` — above the manager minimum.
3. `scripts/build_susfs.sh` gained a pre-`make` gate: if the submodule is
   shallow (or reports ≤ 1 commit) it runs `fetch --unshallow origin`, prints
   the resulting `KSU_VERSION`, and **exits 1** if it is below
   `${KSU_MIN_VERSION:-35040}`. A manager-rejecting kernel can no longer be
   produced by the script.

Build-log proof from the replacement build:

```
==> KernelSU commits: 4454 -> KSU_VERSION: 35154
-- ReSukiSU version code: 35154
-- ReSukiSU version name: v4.2.0-rc2-6ec8d9a8@ReSukiSU
```

> **Standing rule.** Any clone or CI must give the `KernelSU` submodule its
> full history (`git submodule update --init --recursive` with no `--depth`, or
> `git -C KernelSU fetch --unshallow origin`) **before** building, and the
> `-- ReSukiSU version code:` line must be asserted against the manager
> minimum before release. This bug class does not produce a compile error — the
> build succeeds, the kernel boots, and userspace rejects it.

### 10.3 Deep audit — hunk coverage (101 hunks)

97 hunks are byte-identical to the reference patch. The 4 that are not each
differ by exactly one added line, and every one of them is a typo in the
reference patch that was deliberately corrected:

| Location | Reference text | This branch | Verdict |
|---|---|---|---|
| `fs/namei.c` hunk@1652 | `\t\treturn dentry;\t` | `\t\treturn dentry;` | reference has a stray trailing tab |
| `fs/namespace.c` hunk@208 | `goto  out_free_id;` | `goto out_free_id;` | reference has a double space |
| `fs/namespace.c` hunk@1109 | `susfs_alloc_non_unshare_ksu_vfsmnt(name ?:"none")` | hoisted `const char *name`, passes `name` | equivalent — see 10.4.1 |
| `fs/susfs.c` hunk@1 | `void susfs_init(void) {\` | `void susfs_init(void) {` | reference has a **stray backslash — a C syntax error**; keeping it would not compile |

### 10.4 Deep audit — context drift, all verified as 4.19 adaptations

**10.4.1 `fs/namespace.c` — hook relocated from `vfs_kern_mount()` to `vfs_create_mount()`**

The reference injects the `SUS_MOUNT` fake-`mnt_id` hook immediately before
`alloc_vfsmnt(name)` inside `vfs_kern_mount()`, with `goto bypass_orig_flow`
landing on `if (!mnt) return ERR_PTR(-ENOMEM);`.

This 4.19 tree split `vfs_kern_mount()` into the fs_context API: it now calls
`fc_mount(fc)` → `vfs_create_mount(fc)`, and `alloc_vfsmnt()` is `static`. The
hook therefore lives in `vfs_create_mount()` at the same place — before
`mnt = alloc_vfsmnt(name);` — with the same `bypass_orig_flow:` label and the
same `if (!mnt) return ERR_PTR(-ENOMEM);` target.

Completeness was checked by enumerating **every** caller of `alloc_vfsmnt()`
in the tree: there are exactly two — `fs/namespace.c:1120` (inside
`vfs_create_mount()`, hooked) and `fs/namespace.c:1247` (inside `clone_mnt()`,
covered by the reference's own `clone_mnt` hunk, which is present verbatim).
Since 4.19's `vfs_kern_mount()` reaches `vfs_create_mount()` through
`fc_mount()`, no path is left unhooked. The reference context line
`return ERR_PTR(-ENODEV)` belongs to `vfs_kern_mount()`'s `if (!type)` check,
which has no counterpart in `vfs_create_mount()`.

**10.4.2 `fs/proc/task_mmu.c` — `show_smaps_rollup()` loop shape**

The reference uses the 5.x form `for (vma = priv->mm->mmap; vma; vma = vma->vm_next)`.
This tree's loop is `for (vma = priv->mm->mmap; vma;)` with an explicit
`vma = vma->vm_next;` at the end of the body (needed so the
`goto bypass_orig_flow` skip does not skip the advance). Verified:

```c
	for (vma = priv->mm->mmap; vma;) {
#ifdef CONFIG_KSU_SUSFS_SUS_MAP
		if (vma->vm_file) {
			if (vma->vm_file && SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))
				goto bypass_orig_flow;
		}
#endif
		smap_gather_stats(vma, &mss);
#ifdef CONFIG_KSU_SUSFS_SUS_MAP
bypass_orig_flow:
#endif
		last_vma_end = vma->vm_end;
		...
		vma = vma->vm_next;
	}
```

`goto bypass_orig_flow` skips **only** `smap_gather_stats()`; `last_vma_end` is
still assigned and `vma` still advances. Functionally identical to the
reference.

**10.4.3 `fs/proc/task_mmu.c` — `pagemap_read()` mmap_sem API**

Reference: `down_read_killable(&mm->mmap_sem)` / `up_read(&mm->mmap_sem)`.
This tree (which backported the 5.8 mmap-lock API): `mmap_read_lock_killable(mm)`
/ `mmap_read_unlock(mm)`. Verified that `bypass_orig_flow` skips only
`walk_page_range()` and that the unlock still executes on every path, and that
`start_vaddr = end` keeps making progress so the loop always terminates.

**10.4.4 `mm/memory.c` — `__access_remote_vm()`**

Same API adaptation for the lock. The `CONFIG_KSU_SUSFS_SUS_MAP` block itself —
`vma = find_vma(mm, addr);` after the lock, and the
`if (vma && vma->vm_file && SUSFS_IS_INODE_SUS_MAP(...)) break;` at the top of
the loop — is **byte-identical** to the reference.

**10.4.5 Include placement**

* `fs/proc/task_mmu.c`: reference inserts after `linux/mm_inline.h` +
  `linux/ctype.h`; both are 5.x-only and absent here, so the identical
  `#if defined(SUS_KSTAT) || defined(SUS_MAP) || defined(OPEN_REDIRECT)` guard
  + `#include <linux/susfs_def.h>` sits after `linux/pkeys.h`.
* `mm/memory.c`: reference inserts after `asm/pgtable.h`; this tree has no such
  header, so the identical `#ifdef CONFIG_KSU_SUSFS_SUS_MAP` guard sits after
  `linux/pgtable.h`, before `#include "internal.h"`.

### 10.5 Deep audit — feature completeness

| Check | Result |
|---|---|
| `CMD_SUSFS_*` ioctl commands | **23 / 23** present, none missing, none extra |
| `susfs_*` symbols from the reference | **85 / 85** present in this tree |
| `CONFIG_KSU_SUSFS_*` feature guards | all 10 present, each with a count ≥ the reference's |
| `susfs_ksu_sid` / `susfs_priv_app_sid` | `extern` in `security/selinux/avc.c` (as in the reference), defined in `KernelSU/kernel/selinux/selinux.c` — no duplicate definition |
| `fs/Makefile` | `obj-$(CONFIG_KSU_SUSFS) += susfs.o` present |
| `even_defconfig` | `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y` + all nine sub-features `=y`; `CONFIG_KSU_MANUAL_HOOK` and `CONFIG_KSU_TRACEPOINT_HOOK` unset (correct for the inline-hook choice) |
| `drivers/kernelsu` | symlink → `../KernelSU/kernel` intact |
| `fs/susfs.c susfs_init()` | no stray backslash |
| `.rej` / `.orig` | none introduced (the five `.bak` under `drivers/*/mediatek/gpu_mali/` are pre-existing vendor files) |
| stray `.o` in source dirs | removed (gitignored; the shipped build uses `O=out`) |

**Conclusion: no defect in the SUSFS integration itself.** The only bug in
this round was the `KSU_VERSION` build-environment bug of §10.2.

### 10.6 Release

`release/susfs-4/` — `Zenium-Kernel-RUI4-V1.6-susfs-4.zip` (20,618,357 B,
sha512 `9bc8a83c…be342`), `Image.gz-dtb` 18,060,527 B, `System.map`,
`even_defconfig.config`, `RELEASE_NOTES.md`. Built by `bash
scripts/build_susfs.sh` (defconfig `even_defconfig`, `-j2`, Android clang
12.0.5 r416183b, `LLVM=1 LLVM_IAS=1`, `ld.lld`), exit 0, 0 compile errors.

Build-log assertions for this release:

* `==> KernelSU commits: 4454 -> KSU_VERSION: 35154`
* `-- ReSukiSU version code: 35154`, `-- ReSukiSU version name: v4.2.0-rc2-6ec8d9a8@ReSukiSU`
* `-- ReSukiSU: using SuSFS Inline hook`, `-- SUSFS_VERSION: v2.3.0`
* all 7 `susfs_inline` hook checks found (`ksu_handle_{setresuid,execveat,faccessat,sys_read,stat,sys_reboot,input_handle_event}`)
* `write_op` and `sel_handle_status_ops` symbol exports found
* 66 `susfs` symbols in `System.map`; all 10 hook symbols present exactly once

`release/susfs-3-final/RELEASE_NOTES.md` now carries a prominent
"SUPERSEDED — DO NOT FLASH" banner pointing at `susfs-4`.

#### 10.6.1 Independent clean-rebuild confirmation

The shipped `Image.gz-dtb` came from an incremental `build_susfs.sh` run. To
rule out any dependence on the pre-existing `out/` tree, the whole pipeline was
then re-run **from scratch**: fresh `git submodule update --init KernelSU`
(full history), fresh toolchain provisioning by `scripts/setup_build_env.sh`,
empty `out/`, `make even_defconfig` -> full `-j2` build. That run also returned
**EXIT=0 with 0 compile errors** and printed, from its own log:

```
==> KernelSU commits: 4454 -> KSU_VERSION: 35154
-- ReSukiSU version code: 35154
-- ReSukiSU: using SuSFS Inline hook
-- SUSFS_VERSION: v2.3.0
```

(all 7 `susfs_inline` hook checks found in both the pre-link and the post-link
pass = 14 hits; `write_op` and `sel_handle_status_ops` export checks found).

The freshly built `Image.gz-dtb` measured 18,060,521 B against the shipped
18,060,527 B - a 6-byte delta attributable to embedded build metadata (compile
timestamp / build-id strings in `init/version.c` and `.comment`), not to code:
both images come from the same source tree, the same `even_defconfig`, the same
clang 12.0.5 r416183b toolchain and the same make flags. The committed artifact
is therefore representative of what `bash scripts/build_susfs.sh` produces on a
clean checkout.

Note that the build sandbox periodically resets the workspace to the committed
git state, which wipes gitignored directories such as `out/` and
`.kernel-tools/` (and, at one point, the `KernelSU` submodule checkout).
Anything that must survive has to be committed. Recovering the submodule is a
single `git submodule update --init KernelSU`, which yields the full 4454-commit
history by default - the shallow clone that caused the §10.2 bug came from an
explicit `--depth` in the original provisioning, not from default behaviour.
---

# Round 5 - NoMount v2.0.0 integrated on top of the SUSFS build

## 11. NoMount v2.0.0 (maxsteeel/nomount)

### 11.1 What was added

`fs/nomount/` with the four upstream files, **byte-identical** to
`maxsteeel/nomount@6b1be18` (`kernel/src/`):

| File | Size | MD5 |
|---|---:|---|
| `fs/nomount/Kconfig` | 234 B | `e949ee4cc82260a9f042c8e3f35355b5` |
| `fs/nomount/Makefile` | 117 B | `30fa955d481445c4804b7974d45034e2` |
| `fs/nomount/nomount.c` | 62,149 B | `aae755a4f44464519b72d9d43916453b` |
| `fs/nomount/nomount.h` | 11,840 B | `8fb4ee12b139d3645a1412498f946c1a` |

`nomount.h:17` `#define NOMOUNT_VERSION "20"` - i.e. v2.0.0.
`MODULE_VERSION(NOMOUNT_VERSION)`, `MODULE_AUTHOR("maxsteeel")` and
`MODULE_DESCRIPTION("NoMount Path Redirection VFS Subsystem")` are all present
in the source.

Upstream master (`6b1be18`) was chosen over the revision on the user's older
branch `1.5.2_sus_Nomount-v2.0.0`, which carries the *same* version string
(`"20"`) but older code (57,755 B `nomount.c` / 10,106 B `nomount.h` vs
62,149 B / 11,840 B). Master is therefore the true latest v2.0.0.

### 11.2 Integration points - only three lines added to existing files

| File | Line | Change |
|---|---|---|
| `fs/Kconfig` | 331 | `source "fs/nomount/Kconfig"` - placed immediately before the last `endmenu`, matching the placement upstream's own `setup.sh` uses |
| `fs/Makefile` | 19 | `obj-$(CONFIG_NOMOUNT) += nomount/` - directly under the existing `obj-$(CONFIG_KSU_SUSFS) += susfs.o` on line 18 |
| `arch/arm64/configs/even_defconfig` | 5113-5114 | `# NoMount v2.0.0 (maxsteeel) ...` + `CONFIG_NOMOUNT=y`, inserted after the last `CONFIG_KSU_SUSFS_*` line and before the File systems menu |

The `Kconfig`/`Makefile` of the older-branch revision are byte-identical to
master's, which confirms the three integration points are unchanged between
NoMount revisions.

### 11.3 Why this cannot disturb SUSFS v2.3.0 or ReSukiSU

1. **No file overlap.** NoMount is self-contained in `fs/nomount/`. The three
   lines above are the *only* changes to pre-existing files. The 25 SUSFS-patched
   files (`fs/{exec,open,read_write,stat,namei,namespace,super}.c`,
   `fs/proc_namespace.c`, `fs/readdir.c`, `fs/statfs.c`, `fs/proc/*.c`,
   `fs/notify/fdinfo.c`, `fs/susfs.c`, `mm/memory.c`,
   `kernel/{kallsyms,sys,reboot}.c`, `drivers/input/input.c`,
   `security/selinux/avc.c`, headers) are untouched.
2. **No KernelSU/ReSukiSU coupling.** `grep -rin nomount KernelSU/` returns
   **zero hits** in the ReSukiSU submodule: no NoMount code, hooks, or config
   exists there. NoMount does not depend on KernelSU, and KernelSU does not
   depend on NoMount. (Upstream NoMount has no KSU hooks, no ftrace and no
   kprobe - it hijacks VFS `i_op`/`d_op`/`s_op` in place.)
3. **Different mechanism.** SUSFS works by inline hooks inside existing
   syscall/VFS entry points; NoMount works by replacing the
   inode/dentry/super operation tables of specifically targeted inodes when a
   rule is registered. They act on different code paths and different data
   structures.
4. **Disjoint symbol namespaces.** NoMount exports only `nomount_*` / `nm_*`,
   SUSFS only `susfs_*`, ReSukiSU only `ksu_*`. The final link produced no
   duplicate definitions.
5. **No init ordering dependency.** `nomount_init()` is a plain `fs_initcall()`
   whose only job is `register_key_type(&nm_key_type)`; `susfs_init()` is called
   from KernelSU. Neither waits on the other.
6. **Prior art.** The user's own branch `1.5.2_sus_Nomount-v2.0.0` runs
   susfs v2.2.0 + ReSukiSU v35040 + NoMount v2.0.0 together, so the combination
   is a known-good configuration.

### 11.4 NoMount control channel (relevant to "does it interfere?")

NoMount exposes **no device node, no procfs file and no ioctl on a special
file**. It registers a kernel `key_type` named `"nomount"`, and the userspace
`nm` CLI calls `add_key("nomount", ...)` with the address of a 4096-byte
payload page. `nm_key_preparse()` requires `capable(CAP_SYS_ADMIN)`, calls
`nm_process_payload()`, and then returns `-ECANCELED` so the key is never
actually instantiated. That is the whole interface - it cannot collide with any
KernelSU/ReSukiSU interface either.

### 11.5 4.19 compatibility pre-flight

Every `LINUX_VERSION_CODE` guard in `nomount.c` was resolved against this tree
*before* compiling:

| Guard | Arm taken on 4.19 | Verified |
|---|---|---|
| `< 5.12` | no `mnt_idmap` in `inode_operations` | `include/linux/fs.h` 4.19 `inode_operations` has no `mnt_idmap` member |
| `< 6.6` | uses `iterate` | `include/linux/fs.h:1813-1814` has **both** `iterate` and `iterate_shared` |
| `< 6.16` | no `mmap_prepare` | 4.19 `vm_operations_struct` has no `mmap_prepare` |
| `< 6.14` | old `d_revalidate(dentry, flags)` | `include/linux/dcache.h:135` matches |
| `< 5.0` | no `MODULE_IMPORT_NS` | not present in 4.19; code path not taken |
| `< 4.11` | old path-based `getattr` | **matches this tree** - `include/linux/fs.h:1873` `getattr(const struct path *, struct kstat *, u32, unsigned int)` (backported path-based form) |
| `< 4.19` (`DCACHE_DONTCACHE`) | guarded away | NoMount `#ifdef`s its own `DCACHE_DONTCACHE` use |

Also confirmed available in 4.19: `register_key_type()`,
`struct key_preparsed_payload`, `S_NOCMTIME`, `d_backing_inode()`,
`IOP_NOFOLLOW`. All guards resolve to the `< 5.12` / `< 6.6` / `< 6.16` arms.

### 11.6 Build verification

* `make O=out even_defconfig` -> `out/.config:5344 CONFIG_NOMOUNT=y`, and
  `CONFIG_NOMOUNT=y` in `out/include/generated/autoconf.h`.
* Targeted `make ... fs/nomount/` -> **rc=0, 0 errors, 0 warnings**;
  `out/fs/nomount/nomount.o` 43,272 B.
* Full `bash scripts/build_susfs.sh` -> **rc=0**, `Image.gz-dtb`
  **18,073,325 B** (the SUSFS-only `susfs-4` image was 18,060,527 B, so NoMount
  adds ~12.8 KB), log `fullbuild_log.txt`.

Build-log assertions (unchanged from the SUSFS-only build, i.e. NoMount
disturbed nothing):

```
==> KernelSU commits: 4454 -> KSU_VERSION: 35154
-- ReSukiSU version code: 35154
-- ReSukiSU version name: v4.2.0-rc2-6ec8d9a8@ReSukiSU
-- ReSukiSU: using SuSFS Inline hook
-- SUSFS_VERSION: v2.3.0
```

* all 7 `susfs_inline` hook checks found (14 hits, pre- and post-link)
* `write_op` and `sel_handle_status_ops` exports found
* 0 `error:` lines in the whole log
* no warning mentioning `nomount` or `susfs`

Symbols in the shipped `System.map`:

| Check | Result |
|---|---|
| `susfs` symbols | **66** - identical to the SUSFS-only build |
| `nomount_*` symbols | **13** |
| `nm_*` symbols | **33** |
| `nomount_init` | present (`__initcall_165_1706_nomount_init5`, the `fs_initcall`) |
| `nomount_hijacked_lookup` | present |
| `ksu_handle_{setresuid,execveat,execveat_sucompat,post_execveat_sucompat,faccessat,sys_read,stat,sys_reboot,input_handle_event,vfs_fstat}` | each present **exactly once** |
| `CONFIG_KSU_SUSFS_*` in `out/.config` | all 10 present, plus `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y`; `CONFIG_KSU_MANUAL_HOOK` / `CONFIG_KSU_TRACEPOINT_HOOK` unset |
| `CONFIG_NOMOUNT` | `y` at `out/.config:5344` and in `autoconf.h` |
| duplicate symbol definitions at link time | none |

Strings confirmed present in the built `vmlinux`:

* `NoMount: Loaded successfully`, `NoMount: Unloaded successfully`
* `NoMount: Successfully added whiteout rule: %s`
* `NoMount: Successfully added injection rule: %s -> %s`
* `NoMount: Superblock successfully hijacked for dev: 0x%x`
* `NoMount: [DEBUG] Successfully hijacked VFS ops for parent dir (ino: %lu)`
* `NoMount: [ERROR] Failed to register key type (err: %d)`
* `nomount.c` and the bare `nomount` key-type name
* `susfs is initialized! version: v2.3.0`
* `v4.2.0-rc2-6ec8d9a8@ReSukiSU`

### 11.7 Not verified

* **No on-device runtime test.** NoMount's rule engine, the `nm` CLI round-trip
  and the SUSFS ioctls were never exercised on hardware. Verification here is
  compile / link / symbol / string level only.
* `nm_process_payload()` is `static`, so it does not appear in `System.map`; its
  presence is proven by the `NoMount: ...` strings and by `nomount_init` linking.
* NoMount rules are volatile (kernel memory only) and are **not** re-applied
  automatically after a reboot.

### 11.8 Release

`release/susfs-4/` regenerated: `Zenium-Kernel-RUI4-V1.6-susfs-4-nomount.zip`
(20,630,530 B, sha512 `b6f9d1e5...18ab`), `Image.gz-dtb` 18,073,325 B
(sha512 `707359f2...1ff3`), `System.map`, `even_defconfig.config`,
`RELEASE_NOTES.md`. Release tag and GitHub release `susfs-4` were re-pointed at
the amended single commit and their notes updated to describe the SUSFS +
NoMount combination.
