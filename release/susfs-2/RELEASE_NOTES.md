# Zenium Kernel RUI4 — V1.6 susfs-2

**SUSFS v2.3.0 (NON-GKI variant) + ReSukiSU, integrated for the 4.19.325
`rui4-clean` Oplus/Realme tree.**

This is the second SUSFS release of this branch. It contains the
cross-branch review fixes described in `SUSFS_INTEGRATION.md` §9.

## Build

| | |
|---|---|
| Kernel | 4.19.325 (`rui4-clean`, non-GKI, Oplus/Realme RMX3430 / RMX319x family) |
| Toolchain | Android clang 12.0.5 (r416183b), `ld.lld`, `LLVM=1 LLVM_IAS=1` |
| Config | `arch/arm64/configs/even_defconfig` (all 10 SUSFS symbols enabled) |
| Deliverable | `out/arch/arm64/boot/Image.gz-dtb` |
| Status | builds clean, 0 errors; only pre-existing vendor warnings remain |

## What is in this release

* SUSFS v2.3.0 core (`fs/susfs.c`, `include/linux/susfs.h`, `include/linux/susfs_def.h`),
  101/101 hunks of `susfs_patch_to_4.19.patch` verified present.
* ReSukiSU + SUSFS **inline-hook** method (not the manual-hook path) —
  all seven required hook symbols linked: `ksu_handle_setresuid`,
  `ksu_handle_execveat`, `ksu_handle_execveat_sucompat`,
  `ksu_handle_post_execveat_sucompat`, `ksu_handle_faccessat`,
  `ksu_handle_sys_read`, `ksu_handle_stat`, `ksu_handle_sys_reboot`,
  `ksu_handle_input_handle_event`, `ksu_handle_vfs_fstat`.
* All nine SUSFS features enabled in `even_defconfig`:
  `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`, `SPOOF_UNAME`, `ENABLE_LOG`,
  `HIDE_KSU_SUSFS_SYMBOLS`, `SPOOF_CMDLINE_OR_BOOTCONFIG`,
  `OPEN_REDIRECT`, `SUS_MAP`.
* All existing Oplus/Realme/vendor code, drivers and KernelSU
  functionality preserved; no `.rej`/`.orig` leftovers.

## Fixes in this release (cross-branch review, §9)

1. **`fs/notify/fdinfo.c` — latent build break fixed.**
   The `inotify_fdinfo()` signature was guarded by
   `#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT` while `show_fdinfo()`'s callback
   type is guarded by `#if defined(SUS_MOUNT) || defined(SUS_KSTAT)`.
   `fanotify_fdinfo()` was left completely unguarded (2-arg).
   Both are now guarded with the same predicate as `show_fdinfo()`.
   Reproduced before the fix:
   * `SUS_MOUNT=n, SUS_KSTAT=y` →
     `fs/notify/fdinfo.c:174: error: incompatible function pointer types …`
   * `SUS_MOUNT=y, SUS_KSTAT=y, CONFIG_FANOTIFY=y` →
     `fs/notify/fdinfo.c:236: error: incompatible function pointer types …`
   The shipped `even_defconfig` (all features on, `FANOTIFY` off) was not
   affected, so this was a latent config-permutation defect.
2. **`fs/namei.c` — removed a stray trailing tab** left behind by the
   `CONFIG_KSU_SUSFS_SUS_PATH` `#ifdef` wrapping of `__lookup_hash()`.
3. **`fs/namespace.c` — `goto  out_free_id;` double space** in
   `susfs_alloc_non_unshare_ksu_vfsmnt()` corrected.

Because all three fixes are compile-time/cosmetic for the shipped
configuration, `Image.gz-dtb` is functionally identical to susfs-1.

## Flashing

| | |
|---|---|
| Device | RMX3430 / RMX3191 / RMX3193 / RMX3195 / RMX3197 / `even` |
| Partition | `/dev/block/by-name/boot` |
| Slot device | no |
| Modules | not included (`do.modules=0`) |

Flash `Zenium-Kernel-RUI4-V1.6-susfs-2.zip` from a rooted recovery
(AnyKernel3). Keep a backup of your current boot image first.

## Reproducing the build

```sh
bash scripts/setup_build_env.sh     # toolchain: clang, bison, flex, m4, bc shim
bash scripts/build_susfs.sh         # full build into out/
# or: bash run.sh --choose=1
```

Artifacts: `out/arch/arm64/boot/Image.gz-dtb`.

## Notes / uncertainty

* No on-device runtime test was performed. SUSFS features are dormant
  until userspace enables them through the `ksu_susfs` ioctl interface.
* Verified: 10/10 SUSFS config permutations compile clean, forced
  recompile of every modified file with 0 warnings, `KernelSU/kernel/Kbuild`
  inline-hook + static-export gates pass unmodified, `vmlinux` links with
  66 `susfs` and 331 `ksu` symbols.
