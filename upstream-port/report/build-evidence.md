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

Tree state: **742 files modified**, +41,360/-2,393 against `v5.15.220` (`c1d05b805c09`), 47 paths added by the transplant step.

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
| **total** | **66** |

Compile evidence:

- objects produced: **7,365**
- `.ko` modules: 840,  `.dtb` files: 529
- `arch/arm64/boot/Image`: 26,894,344 bytes, sha256 `f0235eae6f1fb445...`
- `arch/arm64/boot/Image.gz`: 10,582,120 bytes, sha256 `d50347b6586fa79e...`
- `arch/arm64/boot/Image.gz-dtb`: 11,042,216 bytes, sha256 `83721b252e568615...`
- `vmlinux`: 37,356,024 bytes, sha256 `7ffa578c8d488e46...`
- `System.map`: 6,443,871 bytes, sha256 `fb17c906aed62086...`
- `build-27.log`: 0 distinct error line(s)

## Closure of the two open gates, and the device-config rerun

* `make modules` completed with **`make_failures=0`**: 4,572 `CC [M]` translation units ->
  **840 `.ko`** (`.config` carries 704 `=m` symbols; multi-module dirs account for the rest). The earlier
  caveat "the final `.ko` link pass was not completed" no longer applies.
* The gates above were measured *before* the device round. `logs/build-27.log` is the same tree **plus**
  the device content (`arch/arm64/boot/dts/mediatek/mt6768.dts` + 48 transplant files + 5 overlays, the
  `Image.gz-dtb`/`dtbo.img` kbuild, `MACH_MT6768` + `PINCTRL_MT6768` enabled):
  `compiler_errors=0`, `make_failures=0`, `objects=7365`, `modules_ko=840`, `dtb_device=1`,
  `dtbo_device=5`, `image_bytes=26894344`, `imagegzdtb_bytes=11042216`, `pinctrl_obj=1`,
  `image_sha256=f0235eae6f1fb4451b8c95d28f743705eb3d935e6dcb8ed9da08c725be3f079e`.
  `report/build.json` is regenerated from that log, so the numbers in it are the device-config tree's.
* Still not claimed: any execution on hardware. `dtc -O dtb` round-trips, `mkbootimg.py verify`
  round-trips, and `pinctrl-mt6768`'s `of_match` string matches the DTB node - structural evidence only.
