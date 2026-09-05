# Maturity ladder — what this port actually is, level by level

Five levels. A claim only moves up when the evidence named beside it exists in this
repository, and everything still missing is listed under *Blockers* instead of being
described as "ready". Nothing in this directory claims a device boots.

**75 patches** (`patch-series/0000-cover-letter.eml` + `0001..0075`), base `v5.15.220`, tree **`9cbd8183f306c74e4ce753022a882f4d3d802ef9`**. Reproducibility gate re-run on this state: fresh `git worktree add --detach ref/linux v5.15.220`, `git am` of the four-digit glob → rc 0, resulting tree hash byte-identical to the tree that was built. Regenerate with `bin/mkcommits.sh`; when applying, use the 4-digit glob and *assert the tree hash* — a non-matching 3-digit glob leaves `git am` succeeding with an empty patch list.

| level | what it means | status | primary evidence |
|---|---|---|---|
| **source-complete** | the port exists as reviewable, reproducible commits; a third party gets a byte-identical tree | **DONE** | `patch-series/` (69 `.eml`), `report/ledger.csv`, `report/verify.json`, tree hash below |
| **build-complete** | the ported tree compiles and links: `Image`, `vmlinux`, every DTB, and loadable modules | **DONE** - `Image` 26,894,344 B, `Image.gz-dtb` 11,042,216 B, 529 DTBs incl. the device's own `mt6768.dtb` + 5 `.dtbo`, 840 `.ko`, 0 errors / 0 make failures | `report/build-evidence.md`, `report/build.json`, `report/subsystem-audit.md` |
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
| clock provider | audited, not just enabled: 231 `clocks`/`assigned-clocks` refs in this board's DTB, **209 resolve to an ID `clk-mt6768.c` registers**, 0 foreign-numbering, 0 cross-domain collisions, 22 hit providers no 5.15 driver claims (`report/clkaudit.json`) |
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
Next gates before PMIC can be called up: (1) auxadc alias decision with register evidence,
(2) a real boot to see `pwrap` probe + `mt6358-regulator`/`rtc-mt6397` bind, (3) the
repackaged `boot.img`, which still predates both the clock and PMIC work.
