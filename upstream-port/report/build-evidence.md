## Build evidence

Toolchain actually used (every one of these is the binary the build ran):

| tool | version |
|---|---|
| `clang` | Android (7917927, based on r437112) clang version 14.0.0 |
| `ld.lld` | LLD 14.0.0 (compatible with GNU linkers) |
| `llvm-ar/-nm/-objcopy/-strip/-readelf/-objdump` | same llvm-r437112 tree (in PATH via the sandbox `bin64/env.sh`) |
| `dtc` | DTC 1.6.0-g183df9e9 (built by kbuild from the ported `scripts/dtc/`) |
| `make` | GNU Make 4.3 |
| `host-gcc` | gcc (Debian 12.2.0-14+deb12u1) 12.2.0 |
| `bison`/`flex`/`m4` | AOSP `bt/linux-x86` prebuilt set (exported as `YACC`/`LEX`/`M4`) |
| `python3` | Python 3.11.2 |

> Provenance note: the toolchain and the build tree lived in `~/.cache/` (outside git, by design).
> That scratch directory was recycled by the platform after the last build pass, so the version
> strings above were recorded during the run (they were not re-probed at report-render time, which
> is why an earlier rendering of this table printed "unusable: clang-14 not found").  The artifact
> sizes and hashes below are the values `bin/buildreport.py` measured off the live build tree.

Tree state: **743 files modified**, +42,291/-2,453 against `v5.15.220` (`bf0ea2a0e37c`), 0 paths added by the transplant step.

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
| reverted-file | 164 |
| undo-hunk-with-deletion | 26 |
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
| **total** | **256** |

Config deltas made *for this build* (sandbox constraints, not port issues):

- `CONFIG_DEBUG_INFO=n              2 cores / 3 GB RAM in this build sandbox`
- `CONFIG_ACPI=n                    even_defconfig enables no ACPI symbol at all (MTK Android boots from DT); ACPI-only files are out of scope`
- `CONFIG_EFI=n                     even_defconfig has no CONFIG_EFI (only EFI_PARTITION); EFI runtime/GUI-boot files are out of scope for this SoC`
- `CONFIG_SYSTEM_TRUSTED_KEYS=""    unchanged from the device defconfig; extract-cert is built against a header stub outside the tree and never executed`

Compile evidence:

- objects produced: **6,860**
- `.ko` modules: 0,  `.dtb` files: 528
- `arch/arm64/boot/Image`: 28,450,824 bytes, sha256 `c69819e166280302...`
- `vmlinux`: 38,842,008 bytes, sha256 `5b44f55f1196d7a3...`
- `System.map`: 6,436,072 bytes, sha256 `470ed4305b8a1578...`
- `build-7.log`: 16 distinct error line(s)
- `build-8.log`: 16 distinct error line(s)
- `build-9.log`: 5 distinct error line(s)

### Final tree state, and the one thing that was not re-measured

After the artifact sweep above, three more holds were taken to close the module-only error
clusters (`drivers/media/common/videobuf2/videobuf2-core.c`, `drivers/media/v4l2-core/v4l2-common.c`
used 4.19-shaped helpers / re-exported `v4l2_get_link_freq` that 5.15 owns elsewhere;
`net/bluetooth/hci_core.c` passed a `const char *` into a non-const `strscpy`), plus
`scripts/dtc/.gitignore` was restored so kbuild's rebuilt host tools stay ignored.  That yields the
shipped state:

* **740 files** modified against `v5.15.220`, `+42,200 / -2,433`, tree
  `a8bd53370bb2c649e9f3bef03db4af5c7e6faa99`.
* The 68-patch series reproduces that tree exactly (`git am` -> identical tree hash), verified
  before the scratch dir was recycled.
* `make Image` / `make dtbs` measurements above were taken one hold earlier and stay valid for
  `vmlinux`: the three files reverted afterwards are all `=m` (never linked into `vmlinux`), and a
  targeted recompile of `drivers/media` and `net/bluetooth` afterwards reported **0 error lines**.
* **Not completed:** a full `make modules` relink on the shipped tree.  The last full module pass
  compiled 6,862 objects with exactly 5 error lines - the cluster just described - and the run that
  would have linked the `.ko` set was interrupted when the sandbox was recycled.  So the `.ko`
  count is honestly 0 in the table above: no module *linking* is claimed, only that every module
  translation unit compiled except those five, which are now gone.
