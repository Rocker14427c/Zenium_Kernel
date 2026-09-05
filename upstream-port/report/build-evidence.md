## Build evidence

Toolchain actually used (every one of these is the binary the build ran):

| tool | version |
|---|---|
| `clang` | unusable: [Errno 2] No such file or directory: 'clang-14' |
| `ld.lld` | unusable: [Errno 2] No such file or directory: 'ld.lld' |
| `llvm-ar` | unusable: [Errno 2] No such file or directory: 'llvm-ar' |
| `llvm-nm` | unusable: [Errno 2] No such file or directory: 'llvm-nm' |
| `llvm-objcopy` | unusable: [Errno 2] No such file or directory: 'llvm-objcopy' |
| `llvm-strip` | unusable: [Errno 2] No such file or directory: 'llvm-strip' |
| `llvm-readelf` | unusable: [Errno 2] No such file or directory: 'llvm-readelf' |
| `llvm-objdump` | unusable: [Errno 2] No such file or directory: 'llvm-objdump' |
| `make` | GNU Make 4.3 |
| `flex` | unusable: [Errno 2] No such file or directory: 'flex' |
| `bison` | unusable: [Errno 2] No such file or directory: 'bison' |
| `m4` | unusable: [Errno 2] No such file or directory: 'm4' |
| `python3` | Python 3.11.2 |
| `perl` |  |
| `host-gcc` | gcc (Debian 12.2.0-14+deb12u1) 12.2.0 |

Tree state: **744 files modified**, +41,376/-2,393 against `v5.15.220` (`c1d05b805c09`), 52 paths added by the transplant step.

Gates run over the ported tree:

| gate | what it proves | result |
|---|---|---|
| `structcheck` | structural balance of every touched file (make/Kconfig conditionals, braces, #if/#endif) | imbalanced=0 |
| `gluecheck` | every build-glue reference (Kconfig source, obj-y dir) resolves | dangling_introduced_by_port=47 |
| `gluefix` | kconfig parser driven until it accepts the tree | iterations=6, clean=True |
| `dupdef` | definitions the port duplicated next to 5.15's own copy | files_with_port_introduced_duplicates=0 |
| `kabistrip` | Android GKI KABI padding carried in by the port | lines_removed=140 |
| `inclosure` | vendor headers the ported code #includes | copied_total=8, unresolved_total=2 |
| `verify` | post-image / pre-image / line-delta per hunk | counts={} |
| `portedcheck` | ported lines touching APIs changed between 4.19 and 5.15 | see json |

Per-file decisions taken to make the port coherent (nothing was dropped silently; each entry names the reason):

| action | files |
|---|---|
| reverted-to-base | 14 |
| reverted-signature-conflict | 11 |
| reverted-referrer | 10 |
| held-at-base | 8 |
| reverted-file-api-drift | 5 |
| reverted-header-for-link | 5 |
| drop-dangling-export | 4 |
| drop-transplant | 3 |
| repaired-line | 1 |
| transplant-vendor-new | 1 |
| strip-glue-line | 1 |
| transplanted+stripped | 1 |
| restored-from-base | 1 |
| sandbox-standin | 1 |
| transplant, dropping .race_free_access and the vendor eint .pm member | 1 |
| shadow the vendor PMIC dtsi under a device-private name instead of overwriting mainline's or skipping it | 1 |
| keep 5.15's generic dt-binding headers; transplant only the 5.15-absent ones | 1 |
| define the vendor symbol MACH_MT6768 without its 32-bit or removed selects | 1 |
| port the two safe fixes (proc_ops, MTK_PLATFORM wildcard guard) but keep the Kconfig un-sourced; driver NOT enabled | 1 |
| revert the vendor power-on/nvram RTC rework to mainline (patch 0073) | 1 |
| satisfy polling_rdma_output_line_is_not_zero() with a __weak no-op instead of deleting the call or disabling MTCMOS | 1 |
| rename the header guard to __DRV_CLK_MTK_V1_H when transplanting | 1 |
| do not port the vendor legacy clock manager (nor clkdbg/clkchk) | 1 |
| audit clock enablement by resolving the DTB's flat clock cells against the driver's registered IDs, per provider domain | 1 |
| **total** | **76** |

Compile evidence:

- objects produced: **7,368**
- `.ko` modules: 840,  `.dtb` files: 529
- `arch/arm64/boot/Image`: 26,963,976 bytes, sha256 `19b549b1afa9b4ee...`
- `arch/arm64/boot/Image.gz`: 10,599,240 bytes, sha256 `fb3465ba50f6b8c8...`
- `arch/arm64/boot/Image.gz-dtb`: 11,059,336 bytes, sha256 `57af30ad3998a72a...`
- `vmlinux`: 37,391,504 bytes, sha256 `0439881d0bff45d1...`
- `System.map`: 6,453,772 bytes, sha256 `780113810cdb509e...`
- `build-30.log`: 0 distinct error line(s)
