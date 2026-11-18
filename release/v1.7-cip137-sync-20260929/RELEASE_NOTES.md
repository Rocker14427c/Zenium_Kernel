# Zenium Kernel RUI4 V1.7 — CIP137 sync

Latest build for Realme C25 / Narzo 50A (`even` family), built from source commit `aa782965ee5921a26e71e9eea8533fed6fd69285`.

## Kernel and included components
- Kernel release: `4.19.325-cip137-st21-Zenium-V1.7-Even`
- Linux 4.19.325 CIP137 update
- BakaSU submodule `5d6d1843c8937f5ff2a145dc89a0cf46030ae6f8` (`KSU_VERSION=35261`)
- SUSFS v2.4.0
- NoMount v2.3.0
- `CONFIG_HZ=250`; `CONFIG_MTK_AAL_SUPPORT` is disabled

## Device compatibility and flashing
The AnyKernel3 package targets `RMX3430`, `RMX3191`, `RMX3193`, `RMX3195`, `RMX3197`, and `even`. It flashes the kernel image only and does not apply sample ramdisk modifications. Use only on a compatible Realme C25 / Narzo 50A device. Keep a known-good boot image and recovery method available. No device was available for runtime/boot testing.

Pair the kernel's NoMount v2.3.0 driver with the compatible NoMount userspace module.

## Download
[Download the flashable AnyKernel3 ZIP](https://github.com/Rocker14427c/Zenium_Kernel/raw/v1.7-cip137-sync-20260929/release/v1.7-cip137-sync-20260929/Zenium-Kernel-RUI4-V1.7-CIP137-SUSFS-2.4.0-NoMount-2.3.0-Even.zip?download=1).

## Package integrity
- ZIP archive integrity check passed; embedded `Image.gz-dtb` matches the verified build output.
- ZIP SHA-256: `89152503eb72e7d9ff505c94b23adfd720bca590acc8f909939f1437f2566934`
- Build image SHA-256: `91933583c0ac4d270a330c26bfcd7f18ce93b362d511ca75b63b1c5a71e79810`
