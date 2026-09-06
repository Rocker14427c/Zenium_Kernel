# Maturity ladder — what this port actually is, level by level

Five levels. A claim only moves up when the evidence named beside it exists in this
repository, and everything still missing is listed under *Blockers* instead of being
described as "ready". Nothing in this directory claims a device boots.

**92 patches** (`patch-series/0000-cover-letter.eml` + `0001..0092`), base `v5.15.220`, tree **`b5d70973e7f154d47f556bd7abac4aeca4d4176c`**. Reproducibility gate re-run on this state at publish time by `bin/publish.py` itself (`git am` of the 4-digit glob -> rc 0, tree byte-identical, and the 0001-0091 prefix reproduces `3483759c24eb…` exactly), and twice before that by accident - a sandbox reset on 2026-09-06 wiped the build workspace and `restore.sh` rebuilt the same tree from the `.eml` set alone. Regenerate with `bin/publish.py` (never `bin/mkcommits.sh`, which is the mechanical-grouping generator from the first phase); when applying, use the 4-digit glob and *assert the tree hash* - a non-matching 3-digit glob leaves `git am` succeeding with an empty patch list.

| level | what it means | status | primary evidence |
|---|---|---|---|
| **source-complete** | the port exists as reviewable, reproducible commits; a third party gets a byte-identical tree | **DONE** | `patch-series/` (91 `.eml`), `report/ledger.csv`, `report/verify.json`, tree hash below |
| **build-complete** | the ported tree compiles and links: `Image`, `vmlinux`, every DTB, and loadable modules | **DONE for the tree any user builds** - at the 0092 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,269 B, the device's own `mt6768.dtb` 122,474 B (sha `34a7e6b536a3…`), 0 `error:` lines and 0 undefined references. Two honest qualifiers: the display objects behind `CONFIG_MTK_DISP_BRINGUP` deliberately do **not** link (160 deferred reference lines / 57 distinct names, §Round 0082-0092), and the 529-DTB / 840-`.ko` figures are `build-37`'s - modules and the DTB sweep have not been re-measured since 0081 | `report/build-evidence.md`, `report/build.json` (gate `l2_disp_record_publish50`), `report/subsystem-audit.md` |
| **flash-ready** | the artifacts the device's partitions expect exist, with the right header/format/geometry, and could be written to the phone | **PARTIAL — structurally complete, never flashed** | `out/Image.gz-dtb`, `out/boot.img`, `out/dtbo.img` (paths under the build workspace; hashes in `report/artifacts.json`) |
| **boot-tested** | the device reaches userspace with this kernel | **NOT DONE — no hardware here** | nothing; see blocker B1 |
| **function-tested** | touch/display/GPU/Wi-Fi/BT/audio/camera/modem/charging verified working | **NOT DONE** | `report/subsystem-audit.md` explains why it would fail today |

## 1. source-complete (DONE)

* The delta is expressed as `git am`-able commits, one per subsystem/cluster, and the
  series is what produced the built tree — the built tree is not a separate hand edit.
* Reproduced by re-cloning the target base and applying the series:

  ```sh
  git clone --branch v5.15.220 https://github.com/gregkh/linux linux-5.15
  git -C linux-5.15 checkout -b port/v5.15.220
  git -C linux-5.15 am <patch-series>/0[0-9][0-9][0-9]-*.eml
  git -C linux-5.15 rev-parse HEAD^{tree}        # must equal the hash printed in README.md
  ```

  The assertion that matters is the **tree hash**, not the exit code: a non-matching glob
  silently applies nothing and still returns 0 (this happened during the work and is why
  `bin/mkcommits.sh` and the docs now check the hash).
* Verification of *content* (not just that `git am` succeeded) lives in
  `report/verify.json`: post-image presence, pre-image uniqueness, per-file line deltas.
* What "source-complete" does **not** mean: it does not mean every vendor change is in.
  `report/decisions.json` records each hunk that was deliberately not carried over, and
  `report/subsystem-audit.md` counts what is still vendor-only.

## 2. build-complete (Image + dtbs done; modules gated)

Measured on the ported tree with clang r437112 / LLD 14 (`ARCH=arm64 LLVM=1`), host gcc
for `scripts/`, `make -k -j2`:

| target | result |
|---|---|
| `Image` | built, 26,877,960 B, **0** `error:` lines, stable across two passes (710 s then 26 s no-op) |
| `vmlinux` | links; carries the transplanted MTK symbols (see `report/build-evidence.md`) |
| `dtbs` (all) | 529 arm64 DTBs, incl. this board's `mt6768.dtb` (122,474 B in the product config, forced rebuild) |
| `modules` | 4,572 `CC [M]` → **840 `.ko`**, `make_failures=0` (`build-26.log`); re-run after the clock enablement: still 840 / 0 (`build-30.log`) |
| clock provider | audited, not just enabled: 234 `clocks`/`assigned-clocks` refs in the packaged DTB, **234 resolve to an ID `clk-mt6768.c` registers**, 0 foreign-numbering, 0 cross-domain collisions (`report/clkaudit.json`). The "22 refs that hit an "
  unclaimed provider" this row used to report was an audit blind spot - those cells belong to the "
  MTCMOS power-gate provider in `clk-mt6768-pg.c` - see KNOWN-ISSUES 8.7 |
| device image | `Image` 26,963,976 B (with `COMMON_CLK_MT6768=y`; 26,894,344 B without it), `Image.gz-dtb` 11,059,336 B, `dtbo.img` 371,235 B (5 overlays, sequential `--id=0..4`); `boot.img` 10,823,680 B is structural-only - see `report/artifacts.json` |
| `dtbs` (device) | `mt6768.dtb` 122,474 B in the product config - the same size the earlier sandbox tree reported, node-for-node identical to the reference decompile; the 89,053 B number in earlier drafts came from a build that failed mid-rule (KNOWN-ISSUES 7.1) |
| `modules` | see `report/build.json` — recorded verbatim from the build log, including `.ko` count |

Device-tree build needed three real kbuild/DTS fixes (all in the series, none sandbox-only):

1. **dtc preprocessor include paths** — 5.15's `dtc_cpp_flags` only gets
   `scripts/dtc/include-prefixes`; a vendor DTS tree uses `"mediatek/foo.dtsi"` across
   sibling directories and `<generated/autoconf.h>` for `CONFIG_` conditionals. The three
   `-I` entries the 4.19 tree defines were ported, plus a `DTS_CPPFLAGS` hook.
2. **name collisions with mainline dtsi** — `mediatek/mt6358.dtsi` exists in 5.15 with
   different contents (no `mt_pmic_*_buck_reg` labels), so `make dtbs` aborted with
   `ERROR (phandle_references)`. The device now gets a private shadow copy
   (`mt6358-mt6768.dtsi`) and the board's `#include` is rewritten to it, leaving
   `mt8183-*` boards on mainline's file. `bin/dtsport.py` decides this per file by
   counting consumers outside the closure.
3. **vendor `CONFIG_*` guards in DTS** — 8 guarded symbols, 6 re-materialized as
   `-D` flags for dtc from `even_defconfig` (2 are explicitly disabled there, so they
   stay off). This keeps the DTB *complete* even though those Kconfigs do not exist in
   5.15, which is what the vendor build did through `autoconf.h`.

Image packaging for the device (`bin/bootpack.py`) ports `scripts/mkdtboimg.py`, the
`BUILD_ARM64_APPENDED_DTB_IMAGE` / `DTB_OVERLAY_IMAGE` Kconfig block, the `Image.gz-dtb`
rule and the `%.dtb`/`%.dtbo` pass-through, so `arch/arm64/boot/Image.gz-dtb` is produced
by kbuild exactly like the 4.19 vendor flow (`KBUILD_IMAGE := $(boot)/$(APPENDED_KERNEL_IMAGE_NAME)`).

## 3. flash-ready (PARTIAL: right formats, never flashed)

Produced in this workspace (`portwork/out/`, hashes in `report/artifacts.json`):

| artifact | size | how |
|---|--:|---|
| `Image.gz` | 10,574,423 | gzip -9 -n of the linked `Image` |
| `mt6768.dtb` | 122,474 B (product config, `make -B` and `make dtbs` agree) | kbuild `dtbs`, transplanted vendor closure |
| `Image.gz-dtb` | 10,696,897 | byte-exact concatenation (verified: magic + `totalsize`) |
| `boot.img` | 10,823,680 | `bin/mkbootimg.py`, header v2, page 2048, kernel @ page 1, dtb section @ page 5225; **fits** `BOARD_BOOTIMAGE_PARTITION_SIZE=33554432` (32 %) |
| `dtbo.img` | 371,235 | `scripts/mkdtboimg.py` (the vendor's own packer), 5 entries, ids 0-4, page 4096; fits 8 MiB partition |

Geometry comes verbatim from the device's `BoardConfig.mk`:
`base 0x40078000`, `kernel_offset 0x00008000`, `ramdisk_offset 0x07c08000`,
`tags_offset 0x0bc08000`, `second_offset 0x00e88000`, `dtb_offset 0x0bc08000`,
pagesize 2048, header v2, cmdline `bootopt=64S3,32N2,64N2`,
`BOARD_INCLUDE_DTB_IN_BOOTIMG=true` (so `boot.img` carries the DTB *both* appended and in
the v2 dtb section — LK finds it either way), `BOARD_KERNEL_SEPARATED_DTBO=true`.

Why this is still only "structurally ready":

* **no ramdisk section**: `boot.img` here contains kernel + DTB only. If the device's
  stock `boot.img` carries a vendor ramdisk, it must be added
  (`mkbootimg.py pack --kernel Image.gz-dtb --ramdisk vendor-ramdisk.cpio.gz --dtb mt6768.dtb ...`),
  otherwise first stage init fails.
* **AVB**: the device config uses AOSP **test** keys (`testkey_rsa4096.pem`) and
  `--flags 3` on vbmeta; a locked bootloader will reject this image. Flashing needs
  `fastboot --disable-verification`/patched vbmeta, or your own AVB key.
* **module delivery**: `MODULE_SIG` is off in this config; out-of-tree modules (Mali DDK,
  connac, mtkcam) must be installed by the device build, which expects a specific
  `modules.load`/`vendor/lib/modules` layout.
* **dtbo board selection**: entry ids 0-4 are assigned by `scripts/mkdtboimg.py` in the
  order the Makefile lists them; the *board id* fields (`rev`/`custom`) still carry the
  defaults, and real LK/dtbo merge picks an overlay by matching those. That mapping has to
  come from the stock `dtbo.img` or OPLUS' LK config before this is flashable on more than
  one variant.

## 4. boot-tested (NOT DONE)

No device, no recovery, and no QEMU model of this SoC exists here. The first things that
would break on hardware, with the measurements that say so:

* the config is `arm64 defconfig` + device trims, **not** `even_defconfig` (which names
  ~200 MTK-only symbols this tree does not have: see `report/subsystem-audit.md`),
  so `mtk_pmic_wrap`, the vendor clock tables, SMI, CMDQ and the display driver are absent as
  *drivers* - the DTB describes them, nothing binds them. **Pin control is the one exception
  closed this round**: `drivers/pinctrl/mediatek/pinctrl-mt6768.c` + its 2,742-line table are
  ported, compile in this config (`pinctrl_obj=1` in `build-27.log`), and match the base DTB's
  `mediatek,mt6768-pinctrl` compatible, so that node will bind on device.
  *drivers* — the DTB describes them, nothing binds them;
* of the 417 distinct `compatible` strings in this device's tree, **34** have a driver in
  5.15 and **383** have none (`report/dtsport.json`);
* the vendor `chosen`/`bootargs` handling, `atag`/LK handoff and `earlycon` path are
  untested on 5.15 for this platform; `CONFIG_CMDLINE_FROM_BOOTLOADER=y` is what the
  vendor used and is what this build uses.

## 5. function-tested (NOT DONE)

Requires level 4 plus the driver work. Ordered by dependency, with the 4.19 file counts
that have no 5.15 counterpart (from `report/subsystem-audit.md`):

1. `drivers/misc/mediatek/pmic_wrap` + `pmic` (7 + 231 files) — PMIC bus and regulators;
2. `drivers/clk/mediatek` — **mt6768 clock provider ported** (patch 0074: `clk-mt6768.c` + the MTCMOS `clk-mt6768-pg.c` + `clk-mtk-v1` locks), enabled in the device config and audited against the board DTB. Open inside it: the BSP's `peri_clks[]` is a **1-entry stub** (pericfg CGs lived in the vendor legacy clkmgr, not in DT phandles) — the base DTB makes **0** `CLK_PERI` refs so nothing here is blocked today, but a mainline-style driver added later that asks for a pericfg gate needs that table filled from the vendor CG data, and the 22 refs to unclaimed providers (smi/m4u/cmdq-side clocks) still wait on their subsystems;
   as a header, 53/66 of the shared `clk-mtk-*` files ported). `drivers/pinctrl/mediatek` is
   **done for this board**: `pinctrl-mt6768.c` + `pinctrl-mtk-mt6768.h` ported behind the newly
   defined `MACH_MT6768`; the pin-function header arrived earlier as data only, and the two
   dropped 4.19-only struct members are recorded in `KNOWN-ISSUES.md`;

3. `drivers/memory` + `drivers/iommu` + `cmdq` (40 + 57 + 112) — SMI/IOMMU/CMDQ;
4. `drivers/misc/mediatek/video` + `lcm` (1,066 + 146) or mainline `mtk_drm` (40 files in
   5.15, needs mt6768-compatible bindings) — display;
5. `drivers/misc/mediatek/gpu` (3,328) — Mali Bifrost DDK as an out-of-tree module;
6. `drivers/power/oplus` + `supply` (381 + 221) — charging/fuel gauge (`bq25910`,
   `sy6974`, `rt9471` nodes are already in the transplanted DTB);
7. `drivers/input` (28 files modified) — touch (`cust_mt676*_touch_*` DT nodes present);
8. `sound/soc/mediatek` + `audio_ipi` — ASoC machine/AFE;
9. `drivers/misc/mediatek/connectivity` (2,411) — Wi-Fi/BT;
10. `drivers/misc/mediatek/eccci` (177) — modem; `imgsensor`/`cameraisp`/`lens`
    (1,198 + 118 + 142) — camera.

KernelSU (>= v0.7), f2fs/sched/cpufreq tunables, kheaders, the KABI-stripped vendor
exports and the `CONFIG_` trims are already carried by the series — those parts of the
4.19 behaviour are preserved; the list above is not.

## Blockers

* **B1 — no hardware.** Everything above level 3 is blocked on a device (or at least a
  bootloader trace log). No claim is made about booting.
* **B2 — module gate.** `report/build.json` records the `.ko` outcome; while it shows a
  non-zero failure count, "build-complete" stays qualified. Failures found so far were
  always *config* failures of defconfig-vs-vendor drivers, never the ported hunks
  (`report/build-evidence.md` has the per-round counts).
* **B3 — OpenSSL for `scripts/extract-cert`.** The sandbox has no libssl-dev, so
  `extract-cert` was built **unmodified** against a no-op stub library
  (`tools/sslshim`): empty `SYSTEM_TRUSTED_KEYS` -> rc 0 (upstream's own empty path), any
  real key file -> rc 1, i.e. it fails loudly and never produces a wrong trust chain. On
  a normal box (`apt install libssl-dev`) the flag is unnecessary; do not ship a config
  with `MODULE_SIG`/`DM_VERITY`/`IMA` relying on this stub.
* **B4 — `even_defconfig` parity.** A device config must be authored for 5.15 (the
  `dev/even.fragment` here carries only the image-packaging symbols); until then the
  build is a *broad* compile test, not the product config.
* **B5 — dtbo board-id mapping** (see §3).
* **B6 — 383 orphan compatibles** (see §4): the DTB is data without consumers; each
  subsystem above is a separate transplant task, not a re-run of this tooling.

## What is deliberately *not* claimed

* No `bImage`/`MT6769` "supported" statement: mainline 5.15 has no MT8365/MT6769 clock,
  pinctrl or display driver (`report/soccompare.json`), which is also why the MT8365
  Genio base idea was rejected by measurement, not by taste.
* No performance/power parity: the tuning hunks were ported, but nothing was measured on
  hardware.
* No security-posture claim: AVB uses test keys, module signing is off, and the trusted
  keyring path is stubbed at build time (B3).

### PMIC round (source + build verified, runtime not)

pwrap/PMIC moved from "no driver binds this board at all" to "the whole PMIC dependency
chain is enabled": `MTK_PMIC_WRAP`, `MFD_MT6397`, `REGULATOR_MT6358`, `RTC_DRV_MT6397`
(the last one could not even be configured before, since it depends on the MFD) and
`MEDIATEK_MT6577_AUXADC` (compiles, does not bind - see KNOWN-ISSUES 7.3). The new
`pwrap_mt6768` description is derived from the vendor's own MT6768 register map, which
agrees with mainline's `mt8183_regs` on all 43 comparable registers and disagrees with
`mt6765_regs` on 14 - evidence and the rejected alternative are in
`report/hardware-enablement.md`.

Maturity axes are unchanged by this: **source-complete yes, build-complete yes, flash-ready
no, boot-tested no, function-tested no.** Nothing about PMIC behaviour has been observed on
hardware; what was proven is that the right compatible strings are in the built objects, that
the register offsets match the vendor's data, that the tree compiles and links with the chain
enabled, and that `RTC_DRV_MT6397`'s dependency is satisfiable.
Next gates before PMIC can be called up: (1) a real boot to see `pwrap` probe +
`mt6358-regulator`/`rtc-mt6397` bind, (2) the repackaged `boot.img`, which still predates the
clock, PMIC and ADC work, (3) the DTB packaging defect (KNOWN-ISSUES 8.1) which currently means
the appended DTB is not the one `make dtbs` produces.

### Boot-path round (AUXADC, PMIC supplies, eMMC)

Added to the same "bindable, built, not runtime-verified" tier: the SoC AUXADC provider
(`mediatek,mt6768-auxadc`, aliased on the strength of the vendor's own mapping to its MT6765
description), the MT6358 PMIC ADC as a transplanted vendor IIO driver behind a new MFD cell,
per-regulator `of_node` binding in `mt6358-regulator.c` (41 of the 42 DT children match its
descriptor names - this is what makes `vmmc-supply` and friends resolvable at all), and the
eMMC host (`mediatek,mt6768-mmc` -> mainline's `mt6779_compat`, field-by-field equal to the
vendor's `mt6768_compat`).

Maturity axes unchanged: **source-complete yes, build-complete yes, flash-ready no,
boot-tested no, function-tested no.** Battery voltage is uncalibrated and battery temperature
untrustworthy by explicit design of this round (KNOWN-ISSUES 8.2) - the ADC *provider* exists,
the conversion layer the vendor stack installs does not. I2C remains open as a binding
question (8.4), not a config flip.

## Round: boot-path drivers + the DTB that actually ships (0076, 0077)

Source-complete and build-complete advanced together, and one thing that is *not* a driver moved
forward: the device tree embedded in `Image.gz-dtb` is now the device tree that was audited.

* **0076** adds both AUXADC providers (SoC block via an alias justified by the BSP's own
  `mt6768-auxadc -> mt6765_compat` mapping; PMIC block by importing the driver variant the board's
  own `even_defconfig` builds), makes PMIC supply phandles resolvable (`of_regulator_match()` over
  `desc.name` -> 41 of the DTB's 42 regulator children match), and keys the MT6768 eMMC host to
  `mt6779_compat` after a field-by-field comparison with the BSP's `mt6768_compat`. I2C was
  deliberately not enabled: the board DT's `i2cN` nodes are not adapters (KNOWN-ISSUES 8.4).
* **0077** fixes `DTS_CPPFLAGS` scope in the packaging path. Before it, `make Image.gz-dtb` appended
  a DTB with 14 fewer compatible-bearing nodes than the one `make dtbs` built (89,053 vs 122,474 B,
  no M4U/IOMMU, no gauge/battery block), and the previous `boot.img` carried two different trees in
  its two DTB locations. That is why the earlier rounds kept disagreeing about the DTB size: only the
  per-target measurement was reliable.
* Artifacts repackaged from build-33 and structurally verified: `boot.img` 11,223,040 B (byte-exact
  `mkbootimg verify` round-trip with `--boot-id` pinned), `dtbo.img` 371,235 B (same header),
  `Image.gz` 10,603,132 B, packaged DTB byte-identical to the audited one.

Maturity ladder unchanged in the important places: **source-complete yes, build-complete yes,
flash-ready no, boot-tested no, function-tested no**. Three concrete blockers on the way to
"flash-ready" are itemised in `report/artifacts.json` (`flash_prereq_missing`); the ADC calibration
seam (8.2) and the I2C binding decision (8.4) are the two blockers on the way to a working device,
and both are documented rather than papered over.

## Round: S1 - the clock-provider gap closed by correcting the audit, not the driver

Directed work on SMI/M4U, with one outcome worth stating bluntly: **the gap recorded as blocking SMI
did not exist in the kernel.** `unresolved_provider: 22`, carried forward from the clock round, came
from `bin/clkaudit.py` being unable to attribute the `mediatek,scpsys` node - which our own 0074
content already binds as a clock provider (`drivers/clk/mediatek/clk-mt6768-pg.c:3764`, publishing
`scp_clks[]`'s 13 `SCP_SYS_*` ids via `of_clk_add_provider()`, `:3603-3610`). Verified at source, not
assumed: the cells the board DT uses (1,3,4,5,7,8,9,10,11,12) are all in range with no holes, and each
matches its consumer semantically - SMI larb1 -> VDEC, larb2 -> ISP, larb3 -> CAM, larb4 -> VENC,
`gpufreq` -> the three MFG cores, `consys` -> CONN.

The audit changed instead: it now models the second id family, the `scp_clks[]` table, the
`mediatek,scpsys` provider, accepts several `--driver` files (a board's providers really are split
across `clk-mt6768.c` and `clk-mt6768-pg.c`), prints the unresolved refs as rows rather than a count,
and documents its two counting quirks. Result on the packaged DTB: **234 refs / 234 registered /
0 unresolved / 0 foreign / 0 collisions.** No kernel source changed, so build-33 is still the
reference build and the flash set is untouched.

That result feeds the deferred decision: with SMI's clocks already served, the BSP's own SMI/M4U
(`CONFIG_MTK_M4U=y`, `MTK_SMI=y`, `MTK_SMI_EXT=y` in `even_defconfig`) needs **no** DT edits, while
mainline's `mtk-smi`/`mtk_iommu` would require three classes of DT surgery for an IOMMU that zero DT
nodes reference. Recommendation recorded in `report/hardware-enablement.md`: sequence SMI+M4U (vendor
route) inside the display/video round. Per instruction, no speculative `iommus`/`#dma-cells` were
added, the M4U architecture decision stays open, and I2C is unchanged.

## Display/video round, first commit: vendor SMI substrate (0078, build-34)

Maturity gates are unchanged by this round and are stated plainly: source-complete yes,
build-complete yes (build-34: 0 errors, 0 new warnings, 7,372 objects, `Image.gz-dtb`
11,099,339 B, `mt6768.dtb` sha256 unchanged), flash-ready no, boots no, functions no.

What moved is the *shape* of the display/video stack. Before 0078 the port had no SMI provider at
all: the six SMI nodes in this board's DTB were `NO_DRIVER`, and M4U - which is the door every
display/video/media client in this BSP goes through - had nothing to take clocks from. Now the
substrate is in-tree and DT-faithful: `CONFIG_MTK_SMI_MT6768=y`, `mediatek,smi_common` (1 node)
and `mediatek,smi_larb` (5 nodes) class `ENABLED` in the bind audit, with `mediatek,m4u`
deliberately still `NO_DRIVER` because M4U is the next commit, not this one. No DT was edited to
get here and no clock driver was added: `clkaudit --require-fresh` was already 234/234 with
0 unresolved providers, and it still is.

Sequencing consequence for the next round, written down rather than discovered later: M4U's
`drivers/misc/mediatek/m4u/mt6768/m4u_hw.c` (3,074 lines) needs exactly two things from SMI, both
now present (`smi_bus_prepare_enable()`/`smi_bus_disable_unprepare()`), and its own include
surface is five mainline headers plus its local headers plus `mt-plat/mtk_lpae.h` - no `ion.h`.
The open question is not SMI any more, it is that the BSP's Kconfig makes `MTK_M4U` depend on
`MTK_ION`: whether M4U's heaps are exposed through ION (still in 5.15 staging, gone in 5.18) or
through the DMA-heaps framework, and that decision is to be settled from the clients' actual
allocation calls before any code is ported.

### M4U/ION: decided from evidence, then ported on that basis

The open question left by the SMI commit - whether M4U's `MTK_M4U depends on MTK_ION` forces an
allocator decision - is closed by measurement rather than by porting: the dependency is vestigial
(its only consumer is `m4u_test_ion()`, behind a `CONFIG_M4U_TEST_ION` the BSP never defines), and
`m4u_alloc_mva()` is already allocator-agnostic because it takes a VA or a caller-built `sg_table`.
So M4U is ported with no ION and with `MTK_M4U depends on MTK_SMI_EXT`; heaps stay off until a
client needs them, and the client-side equivalences and non-equivalences (MTK's `ION_CMD_MULTIMEDIA`
booking, LOG/decouple/gain control, the `/dev/ion` ABI) are written up in
`report/m4u-ion-audit.md` and `KNOWN-ISSUES.md` section 10 instead of being quietly absorbed.

Maturity gates for the SMI substrate after the rename (build-35): source complete, build complete -
0 errors, 0 new warnings, 7,372 objects - flash/boot/function still no, because no client binds yet.
`mediatek,m4u` remains `NO_DRIVER` in the bind audit until the M4U commit lands.
### M4U: engine in the image, no client yet (patch 0080, build-36)

M4U v2.0 for MT6768 is source-complete and builds into `vmlinux` with `CONFIG_MTK_M4U=y`: 16 files /
10,896 lines from the BSP, six 5.15 API adaptations annotated in-file, `mediatek,m4u` measured
`ENABLED` against the packaged DTB (bind counts 33->34 bound, 24->25 enabled), and the driver's own
runtime lookups (`mediatek,smi_common`, `mediatek,smi_larb0..4`) resolved against the same `.dtb`
without touching it. Gates: source yes, build yes - 0 errors, no new warning beyond one inherited
vendor line, 7,377 objects - flash no, boot no, function no, because no client binds to it yet. The
two surfaces knowingly not at parity are mmprofile trace events and the 32-bit compat ioctls
(`KNOWN-ISSUES.md` 11.2, 11.3); the next gate moves when a display/video client lands.

### First display client: traced, ported, host-executed (patch 0081, build-37)

The M4U engine's next gate was "a display/video client lands", and it has: the MT6768
display-side M4U glue (`video/mt6768/dispsys/ddp_m4u.c` + the `disp_helper.c` option table it
reads) is in the tree as `CONFIG_MTK_DISP_M4U=y`, 10 files / 1,116 lines including four new build
files, built with 0 errors, 0 warnings and 0 undefined references (7,379 objects, +2). Its five
M4U references resolve into the ported driver objects, not into stubs. No ION and no dma-buf
heaps were pulled in: every ION call in the vendor file was already compiled out by the vendor's
own `MTK_FB_ION_SUPPORT` gate, and the wrappers were deleted with the ION types their prototypes
need. The device tree is untouched and the bind audit is identical to build-36 (34/25/5/315, zero
changed rows), which is the *expected* result - the client has no `of_match` table and must not
steal `mediatek,dispsys`.

Runtime-wise this round reaches "executed on the host" and no further: `upstream-port/tests/`
compiles the same two files and drives the LK-logo handover, the fault-callback registration and
the four `m4u_config_port()` calls against a recording stub - 43 checks, 0 failures - and proves the
client-facing M4U ABI (port IDs, `struct m4u_port_config_struct` layout, prot/flag values) is
byte-identical to the 4.19 vendor headers. That is what surfaced three real semantics: `USE_M4U`
is 0 until `disp_helper_option_init()` runs *after* `disp_m4u_init()`; `sPort.domain` is left
uninitialised; and the MVA the fb handover pre-sets is ignored unless `M4U_FLAGS_FIX_MVA` is
passed. Flash stays no, boot stays no, function stays no: there is no board, and emulation is
unavailable here (`qemu-system-aarch64` is not installable - apt has no package source), so no MMIO
behaviour has been observed at all. `report/display-m4u-client.md`, `KNOWN-ISSUES.md` 12.

## Round: the display core, its gate, the slot pool and the bias provider (0083-0089)

Six patches, one layer at a time, each gated on a whole-tree link rather than a directory build. Level
status for this slice of the ladder, per the five-level rule at the top: **source-complete yes,
build-complete yes for the default tree and for the gated tree up to its deferred providers,
flash/boot/function no** - no device was touched, and the gated display tree still fails `LD vmlinux`.

| what | level | why that level and not a higher one |
|---|---|---|
| the four CMDQ client entry points (0083) | source + build | `cmdqRegWrite`, `cmdqBackup*` etc. compile and link against mainline 5.15's mailbox core; `cmdqRecWrite` is deliberately absent (29 link references from the display objects remain), because supplying it would mean deciding the GCE binding, which decision 148 left open on stock evidence rather than convenience |
| the dispsys core, 14 CMDQ-free objects + `disp_helper` (0084-0085) | source + build, not link | built only under `CONFIG_MTK_DISP_BRINGUP`; with it on the tree fails to link on the provider closure the plan tracks, so no claim of a working frame is even close |
| the gate itself (0086-0087) | done, and it changed the rules | `make vmlinux` at the tip links again in the state every user builds; the display objects moved behind one switch after 0085's include regression was only visible tree-wide. That round also established, by measurement, that `default <sym>` does not follow a command-line switch while `select` does |
| the CMDQ backup-slot pool (0088) | source + build + host-tested | 222-line provider, address arithmetic checked on the host against a transcription of the stock functions (`tests/mtk_disp_slot_host_check.c`, 37 cases / 0 mismatches); PA-vs-IOVA reachability of the pool stays an open hardware question, recorded not asserted |
| the panel bias consumer + MT6370 provider (0089) | source + build + **not bound** | `lcm_pmic.c` now compiles its real regulator branch instead of its `#else` stubs, and 2,449 lines of `pmic/mt6370/v1/` + 1,646 of `rt-regmap` link into the board image (0 new undefined symbols, 39 new text symbols defined once). But the DTB this tree appends has no I2C client node for the chip - `subpmic_pmu@34` sits in a board `cust.dtsi` this tree does not compile - so nothing probes and no rail is claimed to move. `KNOWN-ISSUES.md` 13 is the open item |

Two things this round added to the ladder's vocabulary rather than to the tree. First, a new kind of
negative result worth its own row above: **linked but not bound** - a driver can compile, link, be enabled
by config, and still have no device, and only a DT-content check on the built `.dtb` shows that (a
`grep` of the decompiled dtb found `mt6370_pmu_dts` and `i2c5@11016000` but no client). Second, the
silent-stub class of defect got a rule: verbatim-ported files get a census of every `CONFIG_*` token they
test, compared against `even_defconfig`, because `#ifdef CONFIG_RT_REGMAP` around `mt6370_pmu_regmap.c`'s
whole body turned a green compile into a NULL-handle call at probe time. Both are in
`report/display-bringup-plan.md` 11.11 and decisions 150-152.
