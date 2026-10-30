# Zenium Kernel RUI4 — V1.6 (SUSFS upstream sync + priority-UID filter)

Realme C25 / Narzo 50A (RMX3430, "even") · MT6768 Helio G85 · 4.19.324 non-GKI

**Download:** `Zenium-Kernel-RUI4-V1.6-susfs-sync.zip` (AnyKernel3 flashable)

Kernel: `4.19.324-cip136-st20-Zenium` · SUSFS **v2.3.0** · NoMount **v2.2.0** ·
BakaSU `v4.2.0-rc3-5b76b884` (KSU_VERSION 35222) · `CONFIG_HZ=250`

---

## What this build changes

SUSFS has been re-synced to the current upstream `mainline` revision of
`JackA1ltman/NonGKI_Kernel_Build_2nd` (patchset `cf9657f309`, the state as of
2026-10-30). Two upstream commits landed after the previous build's base:

| commit | date | change |
|---|---|---|
| `38bbbd593d` | 2026-10-30 | "merged latest commits" — adds the **priority-UID filter** |
| `2464d7a283` | 2026-10-30 | "fix: have no statx_basic_stats" — `vfs_getattr()` guard |

### 1. Priority-UID filter (new feature)

Adds `susfs_is_priority_uid_filtered()` and hooks it into the four syscalls an
app can abuse to enumerate which other UIDs exist on the device:

- `block/ioprio.c` — `ioprio_set()` / `ioprio_get()`
- `kernel/sys.c` — `setpriority()` / `getpriority()`

When the filter is populated, an app process (UID ≥ 10000) querying another
UID that is on the list gets the same answer as a non-existent UID, instead of
learning that the UID exists. The UID→bitmap is RCU-protected and resolved
asynchronously by a kthread, because resolving app package names to UIDs needs
the KernelSU SELinux domain.

The filter is populated through the new ioctl
`CMD_SUSFS_SET_PRIORITY_UID_FILTER` (`0x60030`), which passes a
comma-separated list of app package names; the kernel resolves each name to a
UID inside the app range 10000–19999.

**Important — this feature is currently inert, and that is expected.** The
bitmap starts out `NULL`, and `susfs_is_priority_uid_filtered()` returns
`false` for every UID while it is `NULL`. All four hooked syscalls therefore
take exactly their original path — there is **no behavioural change at all**
in this build. The filter only starts doing something once a manager issues
the new ioctl, and the pinned BakaSU revision does not implement it yet.
The kernel side is complete and forward-compatible; nothing is lost or broken
by having it.

### 2. `susfs_get_enabled_features()` NULL-dereference fix

Upstream found (and fixed) a real bug in the `CMD_SUSFS_SHOW_ENABLED_FEATURES`
handler:

```c
struct st_susfs_enabled_features *info = kzalloc(...);
if (!info) {
        info->err = -ENOMEM;   /* <-- dereferences the NULL pointer */
        goto out_copy_to_user;
}
```

On allocation failure this writes through a NULL pointer — a kernel oops. It is
now reported to userspace via `copy_to_user()` and returns cleanly. This is
adopted here.

### 3. `susfs_update_sus_kstat()` stale-device fix

Upstream dropped `new_entry->target_dev = tmp_entry->target_dev;` from the
update path, so `target_dev` comes from the freshly resolved inode rather than
being carried over from the old entry. Without this, a re-installed app keeps
the *previous* device/inode pairing and its kstat spoofing silently stops
matching.

### 4. Supporting changes

- New includes in `fs/susfs.c` (`bitmap.h`, `limits.h`, `rcupdate.h`,
  `string.h`, `vmalloc.h`) for the bitmap/RCU/kvmalloc use.
- A `kvmalloc()` fallback for pre-4.12 kernels (inert here; this is 4.19).
- `susfs_switch_to_ksu_domain()` / `susfs_restore_creds()` helpers, used by the
  new app-name resolution to reach app data paths under the KernelSU domain.

**Not adopted:** upstream's `fs/susfs.c` still contains a stray backslash after
`void susfs_init(void) {` — a C syntax error that would not compile. The
corrected form is kept. Upstream also reformatted `susfs_starts_with()` from
tabs to spaces; the original tab style is kept. Both are deliberate.

---

## Everything else is unchanged

NoMount remains byte-identical to upstream `v2.2.0` (`bf1847f98f`) — verified
file-by-file. BakaSU remains pinned at `5b76b884` as instructed (its `main` tip
still aborts the build with `$(error Please wait susfs update.)`).

## Verification

- Build rc=0, 0 `error:`, 0 warnings from susfs / namespace / nomount /
  cpufreq / KernelSU / ioprio / sys (the 10 warnings present are pre-existing
  vendor Kconfig notices in the sensor and touchscreen drivers).
- Banner: `Linux version 4.19.324-cip136-st20-Zenium (Rocker14427c@Rocker14427c)`
- Symbols: 76 `susfs_*`, 241 `ksu_*`, 60 `nm_*`, 3 `nomount_*`;
  `susfs_is_priority_uid_filtered`, `susfs_set_priority_uid_filter` and
  `susfs_switch_to_ksu_domain` all present in the linked symbol table.
- `susfs_is_priority_uid_filtered` is intentionally **not** visible in
  `/proc/kallsyms` — that is `CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS` doing
  its job, the same as every other SUSFS symbol.
- 10 `ksu_handle_*` hooks, 287 `CONFIG_KSU_SUSFS` guards, 23 `CMD_SUSFS_*`
  ioctls.
- `CONFIG_NOMOUNT=y`, `CONFIG_KSU_SUSFS=y`, `CONFIG_KSU_SUSFS_SUS_MOUNT=y`,
  `CONFIG_HZ=250`; 0 TAGLMK, 0 ReSukiSU.
- In-image strings: `v4.2.0-rc3-5b76b884@BakaSU`,
  `susfs is initialized! version: v2.3.0`, `NoMount: Loaded successfully`.
- `kernel.string=Zenium-Kernel-RUI4-V1.6 by Rocker14427c`

## Note on `CONFIG_MTK_AAL_SUPPORT`

Logfox reports
`E AAL : [ERROR] Kernel does not support AAL, please enable CONFIG_MTK_AAL_SUPPORT in kconfig.`

That message comes from the vendor's **userspace** picture-quality HAL, not
from this kernel — the string does not exist anywhere in the kernel source. It
is a one-shot probe failure at HAL start-up, and it has been present on the
stock kernel too: `# CONFIG_MTK_AAL_SUPPORT is not set` is the vendor's own
setting in `even_defconfig`, byte-identical at the base commit and here.

**It is deliberately left disabled.** Enabling it would flip this device's
backlight path in `drivers/misc/mediatek/leds/mt6768/mtk_leds.c` from
`mt_mt65xx_led_set_cust()` (the LED driver writes panel brightness directly)
to `disp_aal_notify_backlight_changed()` (brightness is handed to the AAL/DRE
engine instead). The vendor ships userspace calibrated for the non-AAL path,
and the Kconfig help states the feature "requires the cowork of AAL user-space
algorithm process". Separately, the DRM AAL driver cannot bind on this SoC at
all: its `of_device_id` table only lists `mt6885/mt6873/mt6853/mt6877/
mt6833/mt6781-disp-aal`, while this device's node is `mediatek,disp_aal0`.

So enabling it would change display behaviour for no benefit — the HAL message
would still appear, because the probe it fails on is not the one this config
controls.
