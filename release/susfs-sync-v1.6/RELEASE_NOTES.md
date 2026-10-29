# Zenium Kernel RUI4 — V1.6 (SUSFS patchset sync + packaging fixes)

Build date: 2026-10-29
Target: Realme Narzo 50A / RMX3430 family (MT6768 Helio G85, 4 GB, 4.19 non-GKI "rui4-clean")

## Bugs found and fixed in this release

The previous zip flashed fine but advertised the wrong build. Three defects, all
in the packaging and build metadata rather than the kernel logic:

### 1. The flashable zip advertised a different build than the one inside it

The AnyKernel3 installer prints `kernel.string` from `anykernel.sh` on screen
while flashing. That line had been carried forward unchanged from an older
release template, so flashing `...-V1.9-susfs-sync.zip` printed:

```
Zenium-Kernel-RUI4-V1.8-susfs-4-bakasu-nomount-2.1-hz250
```

— a stale version number and a stale component list, neither of which matched
the zip's actual contents. The kernel image inside was correct; only the label
was wrong.

**Fix:** `kernel.string` is now `Zenium-Kernel-RUI4-V1.6 by Rocker14427c`.
The component list has been dropped from the string entirely, because a
hand-maintained feature list is exactly what went stale here — it has to be
edited by hand on every component bump and it wasn't. Identity and version only;
the component detail lives in the release notes and the zip filename.

The generator in `run.sh` was fixed the same way, so re-running the upstream
builder produces the same string instead of reintroducing the drift.

### 2. The kernel version had drifted upward

`run.sh` declares `version=-V1.6`, which is the version of the kernel this tree
is forked from. The `kernel.string` had nevertheless been hand-edited to
`V1.8` and then `V1.9` over successive releases.

**Fix:** the version is back to **V1.6** and is no longer hand-edited — it comes
straight from `run.sh`'s `version` variable. Nothing about the kernel itself
changed; this is a naming correction only.

### 3. The kernel banner leaked the build machine's identity

`scripts/mkcompile_h` derives the `(user@host)` part of the kernel banner from
`KBUILD_BUILD_USER` / `KBUILD_BUILD_HOST`, falling back to `whoami`@`uname -n`
when they are unset. `scripts/build_susfs.sh` never set them, so every image
built here carried the build host's identity:

```
Linux version 4.19.325-cip136-st20-Zenium (user@e2b.local) (Android ...)
```

**Fix:** both variables are now pinned in `scripts/build_susfs.sh` (overridable
from the environment for reproducible builds), and `run.sh`'s `BUILDER` /
`BUILD_HOST` are set to match. The banner now reads:

```
Linux version 4.19.325-cip136-st20-Zenium (Rocker14427c@Rocker14427c) (Android ...)
```

Verified in the built image: no occurrence of the previous build host anywhere in
`Image.gz-dtb`.

### Root cause

`scripts/build_susfs.sh` only ever built the kernel; the AnyKernel3 template was
copied forward verbatim from the previous release's zip each time, so
`kernel.string` was never regenerated and silently aged. Both `build_susfs.sh`
and `run.sh` now produce the string from a single definition, and the version
comes from `run.sh`'s `version` variable rather than being typed by hand.

## Kernel contents — unchanged from the previous release

No kernel source, config, or driver changed. The only differences are the
`kernel.string` label and the banner identity above.

| Component | Version | Status |
|---|---|---|
| SUSFS | v2.3.0 | patchset synced to `118ac2bc4f` (previous release) |
| BakaSU | 35222 (`5b76b884`) | unchanged — still pinned |
| NoMount | v2.2.0 | unchanged |
| CPU scheduler | `CONFIG_HZ=250` | unchanged |
| cpufreq / DVFS | stock vendor tables | unchanged |

The two SUSFS fixes from the previous release are still in: the `clone_mnt()`
`is_mnt_ksu_unshared` correction (`fs/namespace.c`) and the
`KSTAT_SPOOF_CTIME_TV_SEC` bitmask correction (`include/linux/susfs.h`).

## Build verification

- Build exit code **0**, **0** `error:` lines, **0** warnings from
  susfs / namespace / nomount / cpufreq / KernelSU code (74 total, all
  pre-existing vendor).
- **14 / 14** `susfs_inline` hooks present.
- All 10 SUSFS hook symbols present **exactly once** each in `System.map`.
- Config: `CONFIG_NOMOUNT=y`, `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y`,
  `CONFIG_KSU_SUSFS_SUS_MOUNT=y`, 9/9 `CONFIG_KSU_SUSFS_*` sub-features,
  `CONFIG_HZ=250`.
- Symbols: 65 `susfs_*`, 226 `ksu_*`, 59 `nm_*`, 2 `nomount_*`
  (`nomount_init`, `nomount_exit`).
- In-image strings: `v4.2.0-rc3-5b76b884@BakaSU`,
  `susfs is initialized! version: v2.3.0`, `NoMount: Loaded successfully`.
- 0 TAGLMK, 0 ReSukiSU strings.
- No `.rej` / `.orig` files anywhere in the tree.
- Only `scripts/build_susfs.sh`, `run.sh`, the `anykernel.sh` label and the
  release directory differ from the previous commit.

## Files

- `Image.gz-dtb` — 18,080,032 bytes, sha512 `96bfe3ec30055366e51a10119de02bce…`
- `System.map`, `even_defconfig.config` — full symbol map and defconfig output

## Flashing

Flash `Zenium-Kernel-RUI4-V1.6-susfs-sync.zip` from AnyKernel3 recovery.
`BLOCK=/dev/block/by-name/boot`, `IS_SLOT_DEVICE=0`.

On screen the installer will now print:

```
Zenium-Kernel-RUI4-V1.6 by Rocker14427c
```

Clean flash over the previous build — no module changes needed, the NoMount
userspace module stays at v2.2.0.
