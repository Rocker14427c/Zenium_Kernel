# Zenium SUSFS v2.3.0 – 2026-09-29 – ThinLTO

- Commit:  (`arena/01a0eb9a-zenium-kernel`, also `susfs-2`)
- Base: rui4-clean 7d5fb409 (4.19.325, MT6768 even)
- SUSFS v2.3.0 NON-GKI, 9 features: SUS_PATH, SUS_MOUNT, SUS_KSTAT, SPOOF_UNAME, ENABLE_LOG, HIDE_KSU_SUSFS_SYMBOLS, SPOOF_CMDLINE_OR_BOOTCONFIG, OPEN_REDIRECT, SUS_MAP
- ReSukiSU 6ec8d9a inline hooks 7/7 found (post_execve now included)
- Defconfig: even_defconfig, ThinLTO (LTO_CLANG + THINLTO), MODULE_SIG=n
- Artifacts: Image 39M, Image.gz 14M, AnyKernel3 zip 20M

## Verification
- Kbuild: ReSukiSU inline + SUSFS_VERSION v2.3.0
- Symbols: 67 susfs*, 242 ksu*, all ksu_handle_* present, no manual bools
- Hook wiring: 12+ bl ksu_handle_*, 30+ susfs_* confirmed via llvm-objdump
- Warnings: 73 total, 0 in touched files

## Flash
- AnyKernel3 zip via TWRP / KernelSU Manager / 
- Or replace Image in boot.img (magiskboot)

## Notes
- No QEMU/device runtime test (no emulator). Test root, module mounts, hidden paths/mounts with manager + ksu_susfs tool.
