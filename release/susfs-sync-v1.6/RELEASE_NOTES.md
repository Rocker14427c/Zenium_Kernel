# Zenium Kernel RUI4 — V1.6 (SUSFS upstream sync + priority-UID filter + AAL)

Realme C25 / Narzo 50A (RMX3430, "even") · MT6768 Helio G85 · 4.19.324 non-GKI

**Download:** `Zenium-Kernel-RUI4-V1.6-susfs-sync.zip` (AnyKernel3 flashable)

Kernel: `4.19.324-cip136-st20-Zenium` · SUSFS **v2.3.0** · NoMount **v2.2.0** ·
BakaSU `v4.2.0-rc3-5b76b884` (KSU_VERSION 35222) · `CONFIG_HZ=250`

---

## 1. SUSFS re-synced to the current upstream patchset

SUSFS has been re-synced to upstream `JackA1ltman/NonGKI_Kernel_Build_2nd`
`mainline` (patchset `cf9657f309`, state as of 2026-10-30). Two upstream commits
landed after the previous build's base:

| commit | date | change |
|---|---|---|
| `38bbbd593d` | 2026-10-30 | "merged latest commits" — adds the **priority-UID filter** |
| `2464d7a283` | 2026-10-30 | "fix: have no statx_basic_stats" — `vfs_getattr()` guard |

### Priority-UID filter (new feature)

`susfs_is_priority_uid_filtered()` plus hooks in `ioprio_set`/`ioprio_get`
(`block/ioprio.c`) and `setpriority`/`getpriority` (`kernel/sys.c`). An app
process (UID ≥ 10000) querying a filtered UID gets the same answer as a
non-existent UID, instead of learning that the UID exists. UIDs are held in an
RCU-protected bitmap, populated through the new ioctl
`CMD_SUSFS_SET_PRIORITY_UID_FILTER` (`0x60030`), and resolved by a kthread
because app-name → UID resolution needs the KernelSU SELinux domain.

**This feature is inert in this build, and that is expected.** The bitmap starts
`NULL` and the lookup returns `false` for every UID while it is, so all four
hooked syscalls take exactly their original path — **no behavioural change at
all**. It only activates once a manager issues the new ioctl, and the pinned
BakaSU revision does not implement it yet. The kernel side is complete and
forward-compatible.

### Two real bugs fixed

**`susfs_get_enabled_features()` NULL-dereference.** Upstream found this one:

```c
struct st_susfs_enabled_features *info = kzalloc(...);
if (!info) {
        info->err = -ENOMEM;   /* <-- dereferences the NULL pointer */
        goto out_copy_to_user;
}
```

On allocation failure this writes through a NULL pointer — a kernel oops. Now
reported to userspace via `copy_to_user()`.

**`susfs_update_sus_kstat()` stale device.** Upstream dropped
`new_entry->target_dev = tmp_entry->target_dev;` so `target_dev` comes from the
freshly resolved inode. Without it, a re-installed app keeps the *previous*
device/inode pairing and its kstat spoofing silently stops matching.

**Not adopted:** upstream's `fs/susfs.c` still carries a stray backslash after
`void susfs_init(void) {` — a C syntax error. Corrected form kept. Upstream also
reformatted `susfs_starts_with()` from tabs to spaces; tab style kept.

---

## 2. `CONFIG_MTK_AAL_SUPPORT` is now enabled

This was requested after the Logfox message
`E AAL : [ERROR] Kernel does not support AAL, please enable CONFIG_MTK_AAL_SUPPORT in kconfig.`

**What it changes.** With `CONFIG_MTK_PLATFORM="mt6768"` and
`CONFIG_LEDS_MTK_DISP is not set`, the active backlight driver is
`drivers/misc/mediatek/leds/mt6768/mtk_leds.c`. Enabling AAL switches its
brightness write from:

```c
mt_mt65xx_led_set_cust(&led_data->cust, level);   /* LED driver writes the panel directly */
```
to:
```c
disp_aal_notify_backlight_changed(level);         /* handed to the AAL/DRE engine */
```

and `mtkfb_set_backlight_level()` switches from `primary_display_setbacklight()`
to `primary_display_setbacklight_nolock()`.

**What this means in practice.** Brightness is now applied through the MediaTek
AAL engine (ambient-light adaptive luma / DRE / CABC) instead of being written
straight to the LED controller. Expect the brightness curve and the feel of
auto-brightness to change, and expect the AAL engine to consume a little more
CPU. If brightness feels wrong — steps too coarse, auto-brightness hunting, or
a dim/bright display — this is the knob responsible.

**I could not verify the on-device display behaviour from here.** The build
verifies that it compiles, links and wires up correctly; only your device can
confirm how the panel actually responds. If it misbehaves, say so and it comes
straight back out — it is a one-line config change plus a rebuild.

**What was deliberately left alone:**
- `CONFIG_MTK_DRE30_SUPPORT` stays **off**. DRE30 is a separate companion
  feature (dynamic range enhancement v3); you asked for AAL, and the vendor
  ships it off too. Enabling it would be a further, independent change to
  colour/dynamic-range behaviour. Say the word if you want it tried.
- `MTK_OD_SUPPORT` (overdrive) also stays off.

**Build-safety notes** (checked before enabling, because this could have gone
wrong two ways):
- `CONFIG_DRM_MEDIATEK` is **not** set on this device, so
  `drivers/gpu/drm/mediatek/mtk_disp_aal.o` is never built. That matters
  because `disp_aal_is_support()` and `disp_aal_notify_backlight_changed()`
  are *both* defined in `mtk_disp_aal.c` and in
  `video/common/aal30/ddp_aal.c` — had the DRM path been built, enabling AAL
  would have produced duplicate-symbol link errors. Only `ddp_aal.c` is
  linked, so there is no clash.
- `LOAD_AAL_SUPPORT_FROM_DTS` is only defined for `CONFIG_MACH_MT6757`/`MT6771`,
  not for `MT6768`, so `disp_aal_is_support()` is purely config-driven and
  simply returns `true`. The AAL register block is real on this SoC
  (`mt6768.dts:3085 disp_aal0@14011000`).
- `MTK_AAL_SUPPORT` has no `depends on` and nothing `select`s it, so enabling
  it pulls in no other config symbols.

---

## 3. Everything else is unchanged

NoMount remains byte-identical to upstream `v2.2.0` (`bf1847f98f`) — verified
file-by-file. BakaSU remains pinned at `5b76b884` as instructed (its `main` tip
still aborts the build with `$(error Please wait susfs update.)`).

## Verification

- Build rc=0, 0 `error:`, no warnings from susfs / namespace / nomount /
  cpufreq / KernelSU / ioprio / sys / leds.
- **`disp_aal_is_support()` verified in the compiled object** — disassembles to
  `mov w0, #1 ; ret` (it was `#0` before), and `mt6768/mtk_leds.o` now carries
  a relocation against `disp_aal_notify_backlight_changed`.
- Banner: `Linux version 4.19.324-cip136-st20-Zenium (Rocker14427c@Rocker14427c)`
- Symbols: 76 `susfs_*`, 241 `ksu_*`, 60 `nm_*`, 3 `nomount_*` — identical to
  the previous build, i.e. no SUSFS/NoMount regression from the AAL change.
- `susfs_is_priority_uid_filtered` present in the symbol table.
- 287 `CONFIG_KSU_SUSFS` guards, 23 `CMD_SUSFS_*` ioctls.
- `CONFIG_NOMOUNT=y`, `CONFIG_KSU_SUSFS=y`, `CONFIG_KSU_SUSFS_SUS_MOUNT=y`,
  `CONFIG_HZ=250`, `CONFIG_MTK_AAL_SUPPORT=y`, `# CONFIG_MTK_DRE30_SUPPORT is not set`.
- In-image strings: `v4.2.0-rc3-5b76b884@BakaSU`,
  `susfs is initialized! version: v2.3.0`, `NoMount: Loaded successfully`.
- 0 TAGLMK, 0 ReSukiSU, no `e2b.local`, no stale author string.
- `kernel.string=Zenium-Kernel-RUI4-V1.6 by Rocker14427c`
