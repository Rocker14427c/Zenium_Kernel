Both kernels are built from their own branch on a clean GitHub runner and packaged
with the AnyKernel3 scaffold this project has always used. **Nothing here has been
booted on a device** — flash at your own risk, keep a known-good `boot` image.

## Assets

| File | Branch | Root backend | SUSFS | NoMount |
|---|---|---|---|---|
| `Zenium-Kernel-BakaSU-*-sync-unofficial.zip` | `BakaSU` | BakaSU (`Baka-SU/BakaSU`) | v2.4.0 | v2.3.0 |
| `Zenium-Kernel-KSUN-*-sync-unofficial.zip` | `KSU-N` | KernelSU-Next (`legacy`) | v2.4.0 | v2.3.0 |

Targets: Realme C25 / Narzo 50A `even` family — RMX3430, RMX3191, RMX3193,
RMX3195, RMX3197. Flashes the `boot` partition only (`IS_SLOT_DEVICE=0`).

## Which one do I want?

* **BakaSU** — the line that has been shipping. Pair it with a **BakaSU manager**
  (`Baka-SU/BakaSU`, the project formerly called ReSukiSU). The kernel image prints
  its own driver version (`BakaSU version code: ...`) in the build log.
* **KSU-N** — the **KernelSU-Next `legacy`** integration. Pair it with a
  **KernelSU-Next manager of the same driver version**, not a BakaSU manager.
  The two userspaces are not interchangeable: a mismatched pair gives
  "KernelSU driver too old/broken".

## What changed in this sync

* SUSFS `sus_path` now flags and tests `inode->i_state` — upstream fixed this
  because `i_mapping->flags` is not the right field; the old code could hide the
  wrong inodes or none at all after a reclaim cycle.
* KSU-N: the two KernelSU-Next manual hooks that were missing from `fs/stat.c`
  (`ksu_handle_newfstat_ret`, `ksu_handle_fstat64_ret`) are wired. Without them a
  manual-hook build either fails the hook check or silently drops `KSU_MANUAL_HOOK`.
* KSU-N: `CONFIG_KSU_SUSFS_SUS_PATH_UID_FILTER` and
  `CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER` were referenced by `fs/susfs.c` but never
  declared in `fs/Kconfig`, so they could not be enabled. Both are declared now.
* NoMount stays at upstream v2.3.0 with the 4.19 `rcu_guard()` back-port.

## Before you flash

1. Confirm your manager matches the kernel's driver version.
2. Back up the current `boot` image (or make sure a fastboot cable and a stock
   boot image are within reach).
3. Install NoMount userspace only if you actually use it; the kernel side is
   independent of the root manager.

## Reporting a problem

Grab `dmesg` from right after the problem, plus the kernel banner
(`uname -a`). SUSFS/NoMount/KSU bring-up messages print there and usually name the
component that gave up.
