# Zenium Kernel — RUI4 (Realme C25 / Narzo 50A "even") with SUSFS v2.3.0

Linux 4.19 non-GKI kernel (`even_defconfig`, arch/arm64) with
**ReSukiSU + SUSFS v2.3.0 inline hooks** fully integrated, following the
integration method of
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd/).

## What's in this release

| Asset | Description |
|---|---|
| `Zenium-Kernel-RUI4-V1.6-susfs-1.zip` | **AnyKernel3 flashable zip** — flash from recovery. Includes the kernel, the five project dtbo overlays and a banner. |
| `Image.gz-dtb` | Raw kernel image (`arch/arm64/boot/Image.gz-dtb`) |
| `Image` | Uncompressed kernel image |
| `vmlinux` | Unstripped ELF (for debugging / symbolisation) |
| `System.map` | Symbol map |
| `even_defconfig.config` | The exact `.config` this build used |

Flashable on: RMX3430, RMX3191, RMX3193, RMX3195, RMX3197 (codename `even`).
`BLOCK=/dev/block/by-name/boot`, `IS_SLOT_DEVICE=0`, `do.modules=0`.

## Configuration

```
CONFIG_KSU=y
# CONFIG_KSU_MANUAL_HOOK is not set
CONFIG_KSU_SUSFS=y
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

All Oplus/Realme/vendor code, drivers, KernelSU/ReSukiSU functionality and
kernel behaviour are unchanged apart from the SUSFS additions and the
manual-hook → inline-hook conversion that SUSFS mode requires. Full details in
`SUSFS_INTEGRATION.md` on the branch.

## Build

Built with Android clang r416183b (clang 12.0.5), `LLVM=1 LLVM_IAS=1`,
`CROSS_COMPILE=aarch64-linux-gnu-`, 2 jobs, no errors and no new warnings.
Reproduce with:

```sh
bash scripts/setup_build_env.sh     # fetches clang + bison/flex/m4 + bc shim
bash scripts/build_susfs.sh         # make even_defconfig && make
```

## SHA512 (AnyKernel3 zip)

```
eec867ac82b51fbc208cadf6683b2a841b5e517b0016e31dfddfd31068fa8b606382c09075004256181740df0f5b5ce2a1feb1764c2a940a3c3b2c0a09eefee8  Zenium-Kernel-RUI4-V1.6-susfs-1.zip
```

## Note on release assets

GitHub release-asset uploads (`uploads.github.com`) are unreachable from the
machine that produced this build, so the artifacts are committed directly to the
branch instead:

```
release/susfs-1/Zenium-Kernel-RUI4-V1.6-susfs-1.zip   (AnyKernel3, flashable)
release/susfs-1/Image.gz-dtb                          (raw kernel image)
release/susfs-1/System.map
release/susfs-1/even_defconfig.config
```

Download them from the `release/susfs-1/` directory of this branch, or rebuild
locally with `scripts/build_susfs.sh`.
