# Zenium Kernel RUI4 V2.0.0 — KernelSU-Next + SUSFS + NoMount

**Build date:** 2026-09-29 (UTC)  
**Kernel:** Linux 4.19.325, ARM64  
**Source commit:** `3dc1a2de2`  
**Target family:** Realme C25 / Narzo 50A (Even), RUI4; RMX3430, RMX3191, RMX3193, RMX3195, RMX3197, and `even`

## Integrated components

- KernelSU-Next legacy driver version **33327**, from pinned submodule commit `e5f5ec998de88b9fc43c62cff8f7ae12d3f4800a`; manual hooks are enabled.
- SUSFS **v2.4.0**, with the configured path, mount, kstat, uname/cmdline spoofing, open-redirection, and map features.
- NoMount **v2.3** (kernel version constant `23`).
- Fixed SUSFS AVC-log spoofing integration for KernelSU-Next: the kernel resolves the `su` and `priv_app` SELinux SIDs when userspace enables the feature, instead of referencing symbols that do not exist in KernelSU-Next.
- AAL remains disabled. SUSFS priority UID-filter options remain disabled.

## Build and verification

The `even_defconfig` kernel and device-tree image built successfully with Android Clang 12 and was packaged as an AnyKernel3 flashable ZIP. The kernel build/link completed; the package includes the matching `System.map` and defconfig snapshot.

This artifact has **not** been booted or tested on a physical device. In particular, Wi-Fi scanning has not been validated here; the reported V1.7 scan issue is not claimed fixed. Back up the current boot image and use only on a compatible RUI4 device.
