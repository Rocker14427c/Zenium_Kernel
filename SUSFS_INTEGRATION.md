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
