# Zenium Kernel RUI4 — V1.9 (SUSFS patchset sync)

Build date: 2026-10-29
Target: Realme Narzo 50A / RMX3430 family (MT6768 Helio G85, 4 GB, 4.19 non-GKI "rui4-clean")

## What changed in this release

**SUSFS synced to the latest upstream `susfs_patch_to_4.19.patch`** from
`JackA1ltman/NonGKI_Kernel_Build_2nd` @ `mainline` (`118ac2bc4f`, 2026-10-15).

The patchset version string is still `v2.3.0` — upstream has not bumped it — but
the patch itself received two real fixes since the revision this kernel was
integrated from (`7030ed35e9`, 2026-09-26). Both are now in.

### 1. `fs/namespace.c` — `clone_mnt()` fix (upstream `118ac2bc4f`)

Before:
```c
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)) {
		if (susfs_is_current_ksu_domain() && (flag & CL_COPY_MNT_NS))
		mnt->mnt.mnt_flags |= VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT;
	}
#endif
```

After:
```c
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (unlikely(is_mnt_ksu_unshared))
		mnt->mnt.mnt_flags |= VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT;
#endif
```

**Why this matters.** When SUSFS un-shares a mount namespace it *re-uses* the
original `mnt_id` instead of allocating one from the `mnt_id_ida`. The only way
`mnt_free_id()` knows not to call `ida_free()` on an id that was never allocated
is this flag:

```c
static void mnt_free_id(struct mount *mnt)
{
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (mnt->mnt.mnt_flags & VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT)
		return;
#endif
	ida_free(&mnt_id_ida, mnt->mnt_id);
}
```

The old code **re-evaluated** `susfs_is_current_ksu_domain()` and the
`susfs_is_sdcard_android_data_not_decrypted` static key at flag-setting time.
Those are the same three conditions used at allocation time
(`not_decrypted && ksu_domain && CL_COPY_MNT_NS`), but they are evaluated a
second time, after the mount has already been allocated. If the state changes in
between — the static key flips as `/sdcard/Android` becomes accessible, or the
process domain changes — the flag is not set while the `mnt_id` was still
re-used, and `mnt_free_id()` then calls `ida_free()` on an id that was never
allocated from the ida. That is an ida corruption / double-free path.

The new code uses `is_mnt_ksu_unshared`, a local variable set at the exact moment
the un-shared mount is allocated and carried through `goto bypass_orig_flow`. It
records what actually happened instead of guessing. `CONFIG_KSU_SUSFS_SUS_MOUNT=y`
in this kernel, so this path is live on your device.

### 2. `include/linux/susfs.h` — `KSTAT_SPOOF_CTIME_TV_SEC` bitmask (upstream `40b190d460`)

```c
-#define KSTAT_SPOOF_CTIME_TV_SEC (1 < 8)     /* == 1, collides with KSTAT_SPOOF_INO */
+#define KSTAT_SPOOF_CTIME_TV_SEC (1 << 8)    /* == 256 */
```

`(1 < 8)` is a comparison that always evaluates to `1`, i.e. bit 0 — the same bit
as `KSTAT_SPOOF_INO`. Consequences:

- **Bit 8 was never tested at all**, so a rule asking to spoof `ctime` did nothing.
- Any rule that *did* spoof the inode number also silently spoofed `ctime`,
  because both were gated on bit 0.

The kstat spoof bitmask is now contiguous 0–11 with no collisions:
`INO`=0, `DEV`=1, `NLINK`=2, `SIZE`=3, `ATIME_TV_SEC`=4, `ATIME_TV_NSEC`=5,
`MTIME_TV_SEC`=6, `MTIME_TV_NSEC`=7, `CTIME_TV_SEC`=8, `CTIME_TV_NSEC`=9,
`BLOCKS`=10, `BLKSIZE`=11.

## Retained deliberate correction (upstream bug, do not "fix" back)

`fs/susfs.c` in the upstream patch still contains:

```c
void susfs_init(void) {\
```

A stray trailing backslash after the opening brace — a C syntax error. This
kernel carries the corrected form (`void susfs_init(void) {`). Upstream has not
fixed it yet, so our `fs/susfs.c` intentionally differs from the patch by that one
character. **Do not re-apply the upstream patch over this file.**

There are also three whitespace-only differences in `fs/namei.c` and
`fs/namespace.c` (a trailing tab, a double space, and `name ?:"none"` vs
`name ?: "none"`). All cosmetic, all kept as-is.

## Nothing else changed

| Component | Version | Status |
|---|---|---|
| SUSFS | v2.3.0 | patchset synced (2 fixes above) |
| BakaSU | 35222 (`5b76b884`) | **unchanged — still pinned** |
| NoMount | v2.2.0 | unchanged |
| CPU scheduler | `CONFIG_HZ=250` | unchanged |
| cpufreq / DVFS | stock vendor tables | unchanged |

**BakaSU is still deliberately pinned to `5b76b884`.** `main` HEAD (`48fa4bb7`)
hard-fails `CONFIG_KSU_SUSFS=y` builds with `$(error Please wait susfs update.)`,
and the author states newer BakaSU against an unsynced SUSFS causes
`selinux_hide` detections. Waiting for the SUSFS side to catch up is the right
order, exactly as you said.

## How the sync was verified

- Confirmed the integration base was `7030ed35e9` by `include/linux/susfs_def.h`
  being **byte-identical** to our tree.
- Diffed the whole patch old→new: the delta is **exactly** the two changes above,
  nothing else.
- After applying them, `include/linux/susfs.h` is **byte-identical** to the latest
  upstream patch, and `fs/susfs.c` differs only by the retained backslash fix.
- Cross-checked every `+` line of the latest patch against our tree: 1260/1263
  present; the 3 absent are the cosmetic whitespace corrections above.
- Confirmed in the compiled objects that the new code is what actually got built:
  - `clone_mnt()` no longer calls `susfs_is_current_ksu_domain()` /
    `static_branch` at flag-setting time (0 references there), while the
    allocation-time checks are still present (3 + 4 relocations). The flag set
    compiles to `tbz w21,#0` + `orr w8,w8,#0x1000`.
  - `susfs_sus_kstat_spoof_generic_fillattr()` now emits **exactly 12 distinct
    bit tests, bits 0–11**, one per spoof field. Before the fix bit 8 was untested
    and bit 0 was tested twice.

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
- Only `fs/namespace.c` (+2/−4) and `include/linux/susfs.h` (+1/−1) differ from
  the previous release; the rest of the kernel tree is untouched.

## Files

- `Image.gz-dtb` — 18,080,032 bytes, sha512 `5c5429a4ee3853da07d87913c455f362…`
- `System.map`, `even_defconfig.config` — full symbol map and defconfig output

## Flashing

Flash `Zenium-Kernel-RUI4-V1.9-susfs-sync.zip` from AnyKernel3 recovery.
`BLOCK=/dev/block/by-name/boot`, `IS_SLOT_DEVICE=0`. Clean flash over V1.9
(`nomount-2.2.0`) — no module changes needed, NoMount is unchanged.
