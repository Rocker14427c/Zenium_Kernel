# Zenium Kernel RUI4 — V1.6 (BakaSU + SUSFS v2.4.0 + NoMount v2.3.0)

Realme C25 / Narzo 50A (RMX3430, “even”) · MT6768 Helio G85 · 4.19.325 non-GKI

**AnyKernel3 package:** `Zenium-Kernel-RUI4-V1.6-susfs-sync.zip`

- BakaSU `v4.2.0-rc3-5d6d1843@BakaSU` · `KSU_VERSION=35261`
- SUSFS **v2.4.0** · NoMount **v2.3.0**
- `CONFIG_HZ=250` · `CONFIG_MTK_AAL_SUPPORT` remains **disabled**

---

## Upstream refresh

This build refreshes the three kernel components requested:

- **BakaSU:** updated the KernelSU submodule to `5d6d1843c8937f5ff2a145dc89a0cf46030ae6f8` (full history, 4,561 commits). Its SUSFS compatibility check passes. This revision requires SELinux helper symbols to be visible to its resolver, so `security_dump_masked_av()` and `context_struct_compute_av()` are non-static in `security/selinux/ss/services.c`; their implementation and call flow are unchanged.
- **SUSFS:** updated against the requested `JackA1ltman/NonGKI_Kernel_Build_2nd` `mainline` 4.19 patch, blob `5ca22e314e816a24b1c1349b95c491eb142d5cb1`, version **v2.4.0**. Adopted the kernel-read signature detection (rather than relying only on kernel version), the uniquely named pre-4.12 allocation fallback, refreshed path-filter code, and the removal of the obsolete `susfs_get_data_path()` readdir route. The priority-UID syscall hooks are now behind the explicit `CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER` opt-in; BakaSU does not dispatch that new command yet, so the filter remains disabled and has no syscall behavior change.
- **NoMount:** updated the in-tree kernel driver to **v2.3.0** (`maxsteeel/nomount` tag `v2.3.0-720`, source commit `ab93ee32a589ccb021257b3c1f280e058520d844`). This release includes fixes for rule-selection bounds, RCU lifetime/UAF handling, virtual dentry operations and cross-superblock/FUSE lookups, plus more efficient rule and directory lookup paths.

**NoMount pairing:** upstream recommends updating its metamodule together with the kernel driver. The metamodule is not bundled into this kernel AnyKernel3 zip; update the NoMount userspace module to v2.3.0 as well. Release: https://github.com/maxsteeel/nomount/releases/tag/v2.3.0-720

## Compatibility changes preserved

The current upstream patch is not a blind overwrite of this vendor tree. Existing device-specific KSU hooks and prior SUSFS fixes remain in place, including the statx private-mask handling and `clone_mnt()` allocation fix. Two known upstream patch typos/style changes are deliberately corrected/retained here: the stray backslash after `susfs_init()` is removed, and the established tab formatting in `susfs_starts_with()` is kept.

The newer BakaSU static-export check initially stopped the build because those SELinux helpers were static. Making the two functions non-static satisfied the check without enabling `CONFIG_KALLSYMS_ALL` or changing their logic. All four BakaSU SELinux symbol checks pass in the final build.

## Configuration and safety

- `CONFIG_MTK_AAL_SUPPORT` is **not set**, restoring the vendor backlight path. As previously established, the Logfox AAL message comes from the userspace PQ HAL, so this kernel config change does not promise to remove that log message.
- `CONFIG_MTK_DRE30_SUPPORT` and `MTK_OD_SUPPORT` remain off.
- `CONFIG_HZ=250`, `CONFIG_KSU_SUSFS=y`, all existing SUSFS subfeatures, and `CONFIG_NOMOUNT=y` remain enabled.
- BakaSU does not yet dispatch the new SUSFS priority-UID filter ioctl; the associated hooks are opt-in and are not enabled in this build.

No device was available for runtime testing. The build and static checks establish compile/link integrity, but cannot verify on-device NoMount rule behavior, SELinux hide behavior, or display behavior. Back up important data and keep a recovery/known-good kernel available when flashing.

## Build verification

- Build completed successfully (`BUILD_EXIT=0`), producing `Image.gz-dtb` (**18,100,340 bytes**).
- Kernel banner: `Linux version 4.19.325-cip136-st20-Zenium (Rocker14427c@Rocker14427c)`.
- In-image strings: `v4.2.0-rc3-5d6d1843@BakaSU`, `susfs is initialized! version: v2.4.0`, `NoMount: Loaded successfully`.
- All four BakaSU static-export checks passed; SUSFS and NoMount objects linked into the kernel.
- No compiler errors. Remaining warnings are from existing vendor Kconfig/driver code; none were emitted from the changed BakaSU, SUSFS, NoMount, namespace, or SELinux integration files.
- AAL remains disabled in both `even_defconfig` and the built `.config`.
- `kernel.string=Zenium-Kernel-RUI4-V1.6 by Rocker14427c`

The kernel version remains **V1.6**.
