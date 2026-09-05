# Known issues and hard limits of the ported tree

Read this before using `upstream-port/patch-series/`.  Every item here was measured on the
tree the series produces (tree `3ef43034ffc629d0808703917f01aceb7cfe632e`), not assumed.

## 1. It is a compiling kernel, not a booting device kernel

What is proven on the tree this series produces: `make ARCH=arm64 LLVM=1 Image` and `dtbs` run with
**0 compiler errors** — `arch/arm64/boot/Image` 26 877 960 bytes (sha256 in `report/build.json`;
an earlier session measured 28 450 824 bytes with a slightly wider debug config, recorded in
`report/build-evidence.md`), 529 arm64 DTBs (incl. this board's), plus the **device's own** `mt6768.dtb` (122,474 B in the product config, re-measured by forced rebuild; how that number was settled is KNOWN-ISSUES 7.1) and **and, now measured on the product tree too**: `compiler_errors=0`, `make_failures=0`, 840 `.ko` (`logs/build-27.log` quoted in `report/build.json`)
five `dtbo` overlays built from the transplanted vendor closure.  The `modules` target's outcome is
reported verbatim in `report/build.json` (it is the last gate to close, and it is *not* smoothed).
Nothing was executed: no device, no emulator run, no boot log.  Absence of compile errors means the
C is coherent; it says nothing about whether the `even` hardware comes up.

What is missing for that (see `FEATURE-PARITY.md` for the per-subsystem list):

* **The device tree now builds, and mostly describes hardware nothing binds.**  `even`'s base
  DTB is `arch/arm64/boot/dts/mediatek/mt6768.dts` (`CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES`
  in `even_defconfig`), with `/plugin/` overlays `oplus6769_2167A`, `oplus6769_216AF`,
  `oplus6768_20761`, `oplus6769_226AF`, `oplus6769_226BE`; `bin/dtsport.py` transplants that
  55-file closure and the board compiles on 5.15 after three kbuild/DTS fixes (dtc include paths,
  a private shadow copy for `mt6358.dtsi`, and `-D` re-materialization of the vendor `CONFIG_*`
  guards).  Of the **417** distinct compatibles in that closure, **34** bind to a driver that
  exists in 5.15 and **383** do not: the DTB is data, not functionality.
* **Packaging exists as tooling, not as a validated ROM.**  `bin/bootpack.py` ports the
  `Image.gz-dtb` / DTBO kbuild machinery and `bin/mkbootimg.py` produces a header-v2 `boot.img`
  with the device's own geometry; `dtbo.img` is packed with the vendor's `scripts/mkdtboimg.py`.
  Still untouched: AVB/vendor_boot, `super`/`vbmeta` assembly, ramdisk, `dtbo` board-id mapping
  (see item 7 below).
* **Vendor modules are out of tree.** The Mali-G52 Bifrost DDK (r32p0), ASoC machine drivers,
  connac2 Wi-Fi/BT, CCCI modem, mtkcam/IMGTOP and the charging stack are `vendor-new` files that
  the 5.15 Kbuild does not even reference; they were never intended to be hunk-ported.

## 2. The build used a translated config, not `even_defconfig`

`arch/arm64/configs/even_defconfig` is a 4.19 vendor config; most of its symbols do not exist in
5.15, so `make even_defconfig` cannot be the verification config.  The tree was built with
`arm64 defconfig` plus the MediaTek knobs the device needs (`ARCH_MEDIATEK`, `MTK_PMIC_WRAP`,
`COMMON_CLK_MT6765/MT6779`, `IOMMU_IO_PGTABLE_LPAE`, `DRM_MEDIATEK`, `SND_SOC_MEDIATEK`), with
`DEBUG_INFO=n` and these deliberate off-settings, each justified by the device config:

| symbol | why |
|---|---|
| `CONFIG_ACPI=n` | the device firmware is DT-only; ACPI also dragged in `EFI_ESRT` |
| `CONFIG_EFI=n`, `CONFIG_EFI_ESRT=n`, `CONFIG_EFI_VARS=n` | `even_defconfig` has only `CONFIG_EFI_PARTITION` |
| `CONFIG_SYSTEM_TRUSTED_KEYS=""` | no vendor keyring material in this repo; `SYSTEM_TRUSTED_KEYRING` stays on because `crypto/asymmetric_keys/asymmetric_type.c` references `restrict_link_by_builtin_trusted` unguarded, so `y` is the only self-consistent setting |
| `CONFIG_MODULES=y` | needed to compile the `=m` MTK drivers |

`olddefconfig` silently re-enables anything a visible symbol selects, so the *selector* has to be
disabled (e.g. `EFI_ESRT`), not the leaf symbol.  A production config must be rebuilt from
`even_defconfig` symbol by symbol.

## 3. Content the port gave up (all of it itemised in `report/decisions.json`, 100 entries)

The engine applies a hunk only on an exact pre-image match, and every hunk that later made the
tree incoherent was rolled back with a written reason.  The largest rolls:

* `drivers/gpu/drm/` (27 files) — the vendor display plumbing (`struct mtk_panel_ext`,
  `DDPINFO`/`DDPPR_ERR`, `PLANE_PROP_*`, `color_enc_fmt` in `struct drm_connector`) is 4.19
  shaped; 5.15's DRM core has no such members, so the whole DRM tree is held at base.  Display
  bring-up is a manual milestone, not a mechanical port.
* `net/` — 15 ported `.c` files plus `include/net/dst.{h,ops.h}` held at base, because 5.15
  changed the `dst_ops::garbage_collect` signature (`net/ipv6/route.c` type mismatch) and the
  vendor netfilter/ifb edits reference 4.19 internals.
* `mm/`, `kernel/exit.c`, `include/linux/oom.h` — the ULMK/low-memory cluster and 4.19's
  `dead_special_task()` rewrite of `find_lock_task_mm()` (5.15 removed that helper entirely).
* `drivers/thermal/`, `security/security.c`, `kernel/sysctl.c`, `drivers/usb/{core,host,musb}`,
  `net/unix/af_unix.c`, `fs/overlayfs`, `fs/fuse`, `drivers/usb/gadget`, `drivers/scsi/ufs`,
  `drivers/media`, `drivers/misc` (79 files) — vendor extensions of generic subsystems whose
  4.19 call shapes do not survive 5.15.
* `lib/lz4/Makefile` — the port replaced 5.15's object list with 4.19 file names; base restored.

Net effect: 1 016 files received hunks, **746 still carry ported content**; ~1 300 ported `+`
lines were given up.  `portclassify.py verify` therefore reports 1 508 `POST_NOT_FOUND` — those
are exactly the hunks rolled back afterwards, not misapplications; the authoritative fidelity
check is that the shipped series reproduces the built tree hash exactly.

## 4. 47 dangling build-glue lines are inert only because the config is off

`report/gluecheck.json` lists 47 `obj-$(CONFIG_FOO) += vendor-dir/` lines introduced by the port
(`drivers/kernelsu/`, `drivers/input/oplus_secure_driver/`, `sound/soc/mediatek/aw87519/`, …)
whose directories do not exist.  **All 47 are conditional on an unset symbol**, so kbuild never
descends — enabling any of them requires transplanting the vendor directory first (the tool
`bin/glueclose.py` automates exactly that, and was used for the 9 files/2 directories that had to
come along for the built-in set).  3 further findings are `arch/$(SRCARCH)/Kconfig`-style
pre-existing false positives.

## 5. Sandbox-only build glue (never commit this, and never depend on it)

The container has no OpenSSL development package, so `scripts/extract-cert.c` cannot link against
`libcrypto`.  The *unmodified upstream source* is instead compiled against a no-op libssl stub
(`tools/sslshim/`: headers generated from the four `#include <openssl/*.h>` the script needs, plus
18 stub symbols): it returns 0 on an empty key list (upstream's own "no trusted keys" path) and 1
on a real key file, so it can never silently emit a wrong trust chain — but no production
`MODULE_SIG` / verified-keyring flow is exercised by this build either.  Everything else the sandbox
needs lives outside the tree: clang-r437112 + lld 14 (`tools/arrow-clang`), and 64-bit
`bison 3.8.2` / `m4 1.4.19` / `flex 2.6.4` / `bc` / `toybox` / `xz` from
`LineageOS/android_prebuilts_build-tools` branch `lineage-21.0` (`tools/bt`, needing `linux-x86/bin`
*and* `common/bison` + `common/m4`), exposed through `tools/bin64/env.sh`; the AOSP
`prebuilts/misc` bison is 32-bit and unusable.  **No file in the kernel tree was patched to
accommodate the sandbox.**  On a normal machine:
`apt install build-essential flex bison bc libssl-dev && make ARCH=arm64 LLVM=1 Image`.

## 5A. Flash-image caveats (read before wiring this into a device build)

* `boot.img` here has **no ramdisk section**: it is kernel(`Image.gz-dtb`)+dtb only.  If the stock
  `boot.img` carries a vendor ramdisk it must be passed to `mkbootimg.py --ramdisk`, or first-stage
  init fails regardless of the kernel.
* `BOARD_AVB_ENABLE` uses AOSP **test** keys with `--flags 3`; a locked bootloader rejects the image.
  Use `fastboot flash --disable-verification`/your own AVB key, and note the test-key path is only in
  the recovery/vbmeta chain of the device config.
* `dtbo.img` entries get sequential ids 0-4 (the vendor `scripts/Makefile.dtbo` override does this on
  purpose — identical ids make LK apply every overlay), but the `rev`/`custom` board-id fields are the
  packer's defaults.  Multi-variant flashing needs the real mapping from the stock `dtbo.img`.
* The overlays are compiled with kbuild's `cmd_dtc` (`-b 0`, no `-@`), so a `dtbo` carries
  `__fixups__`/`__local_fixups__` but no `__symbols__` section — fine for one-overlay-on-base merging,
  not for chained overlays.
* The config is `arm64 defconfig` + trims + `dev/even.fragment`; it is **not** `even_defconfig`, so
  "flashable geometry" does not mean "same driver set as the working 4.19 kernel".

## 5B. Numbers that must be re-measured, not quoted from docs

Every count in these documents is regenerated by `bin/mkreport.py` / `bin/buildreport.py` from the
tree and the build log; `report/*.json` is the authority.  If you change the series, re-run them —
a stale `.ko` or DTB count in a markdown file is exactly the kind of error this directory has
corrected twice already (a truncated log once yielded a "1465 modules" figure that was really 0).

## 5C. Other caveats

> **`bin/hwenable.py --out-md` overwrites the file it is pointed at.** It did so mid-round to
> `report/hardware-enablement.md`, which is hand-curated on top of the tool's table, and the
> curated sections were only recoverable from git. Run the tool to a scratch/rows file
> (`report/hardware-enablement.rows.md`) and keep prose in the report itself; same caution
> applies to `--fragment`, which is why the curated `dev/even-hardware.fragment` is never
> passed to it.


* No module ABI continuity: 150 `EXPORT_SYMBOL*`/KABI annotations the port would have added were
  removed, and 38 files had port-introduced duplicate definitions stripped; a 4.19 vendor `.ko`
  will not load here (expected — they must be rebuilt against 5.15 headers).
* Toolchain coverage is clang-r437112 + lld only (`-Werror` on).  GCC 9/10 were not exercised.
* `CONFIG_SECURITY_SELINUX`/`SELINUX_ANDROID` extensions, `proc_ops`, `set_fs`, `ion`, `strlcpy`,
  `timespec` hazards in vendor-new code were counted, not fixed: 22 950 files / 15.9 M lines
  audited in `report/hazard.json` (set_fs 1 097, ion 1 009, proc_ops 777, timespec 583 …).
  Those files are not in the 5.15 Kbuild yet, so the tree is clean but the transplant is ahead.

## 6. Device-round findings (pin control, clocks, overlays, tooling)

- **A ported Kconfig is not a ported driver.** The series carried `PINCTRL_MT6768`'s Kconfig text
  but neither the vendor `MACH_MT6768` definition that gates it nor an `obj-` line referencing the
  source, so the device's pin controller could not be enabled even though "pinctrl" looked ported in
  the audit table. Fixed by patches 0069/0072 (symbol + `pinctrl-mt6768.c`/`pinctrl-mtk-mt6768.h`).
  No automated gate for this class yet; the cheap version would be "every `config` the series adds
  that names this device must appear in some `obj-` line". Corollary that bit twice now (RTC, devapc):
  **content ported behind an off Kconfig is uncompiled, not verified** - `build.json`'s "0 errors"
  says nothing about it.
- **`drivers/clk/mediatek/clk-mt6768.c` is the vendor BSP's *partial* CCF driver.** Its
  `peri_clks[]` holds exactly **one** gate (`CLK_PERIAXI_DISABLE`), because on 4.19 pericfg clock
  gating was driven by the legacy `mt6768_clkmgr.c`/`clkbuf` by *name* rather than by DT phandle.
  Registering a near-empty provider for `mediatek,pericfg` is the dangerous shape here: a DT index
  that collides with that one entry would hand a consumer an unrelated clock with no error anywhere.
  `bin/clkaudit.py` settles it on the device's own numbers - 231 clock refs, 209 resolving to a
  registered ID, **0** in the peri space, 0 cross-domain collisions - which is what makes enabling
  `COMMON_CLK_MT6768` defensible *for this DTB*. Do not read "clocks ported" as "clocks complete".
  *Superseded, and it matters:* the residual 22 ("unresolved_provider": 22) was carried forward into
  the SMI round as a claimed functional gap and turned out to be a defect of the audit - 8.7. Current
  numbers on the packaged DTB: **234 refs, 234 registered, 0 unresolved, 0 foreign, 0 collisions**.
- **The MTCMOS path calls into the unported display driver.** `clk-mt6768-pg.c`'s `mm_polling()`
  calls `polling_rdma_output_line_is_not_zero()`, defined by the vendor in
  `drivers/misc/mediatek/video/mt6768/dispsys/ddp_rdma_ex.c:1588`. It is answered by a `__weak`
  no-op in the pg file (see patch 0074 for why the alternatives were worse), and the concrete loss
  if display ever lands without the strong definition winning is a transient panel underflow on
  mid-frame `mm_sel` re-parents in command mode.
- **Three bugs in the DTB-parsing audit tool, each of which could have produced a false verdict**
  (and the general lesson for every DT-tooling claim in this port): `dtc -O dts` prints a node as
  `label: name@addr {`, so a regex that only accepts `name@addr {` silently loses labeled provider
  nodes and makes *every* phandle reference look dangling; multi-string `compatible` prints as one
  quoted string separated by `\0` (`"mediatek,topckgen\0syscon"`) so provider→domain mapping fails
  unless it is split; and attributing only `*_clks[]` tables (not mux/divider/factor arrays) made
  topckgen read 5/65 registered when it is 65/65. A summary line that says "no problems" and one
  that says "nothing parsed" are indistinguishable unless the tool reports what it parsed.
- **The `.dtbo` files are built without `-@`** (5.15 kbuild's `cmd_dtc` has no `@` in `DTB_FLAGS`),
  so they carry `__fixups__`/`__local_fixups__` but **no `__symbols__`**: correct for the vendor's
  one-overlay-on-base merge, not for chained overlays or runtime label lookup. The vendor flow has
  the same shape - do not "improve" it by adding `-@` without checking LK's merger.
- **`report/*.json` are point-in-time.** `build.json`, `dtsport.json`, `hardware-enablement.json`,
  `subsystem-audit.json`, `clkaudit.json` are regenerated by `bin/buildreport.py`, `bin/dtsport.py`,
  `bin/hwenable.py`, `bin/subsysaudit.py`, `bin/clkaudit.py`; the docs quote their numbers, so re-run
  them after any tree change. Quoting a stale report is how two superseded `Image` sizes lived in this
  file for a while. Note `--buildlog` must point at a **full** pass: `subsysaudit.py` reported
  "0 objects" when handed a no-op second pass.

- **A DTB can be built "successfully" with content silently missing, and the size is the only
  visible symptom.** This board's `mt6768.dts` contains
  `#if (CONFIG_MTK_GAUGE_VERSION == 30)` / `#include "mediatek/bat_setting/mt6768_battery_prop.dtsi"`.
  The include *does* resolve - `bat_setting/` is transplanted and `bin/dtsport.py` now reports
  **0** unresolved includes for this tree (its earlier single entry was `generated/autoconf.h`, a
  kbuild-provided header, which is demoted to informational rather than treated as missing; a
  previous version of this entry blamed the delta on that entry, which was wrong). So the cause of
  the size difference is **open**, not explained: two builds of what look like
  the same tree produced `mt6768.dtb` at 122,474 B and at 89,053 B; the 12-node / ~33 KB delta is  [SUPERSEDED - resolved in 7.1 below: the node sets are in fact identical and 89,053 came from a build that failed mid-rule]
  the battery OCV profile block (`battery0_profile_t0..t4_col`, `battery1_*`). Consequences worth
  stating plainly: (1) an unresolvable `#include` inside a preprocessor guard degrades to "block
  absent", so `make dtbs` stays green while the gauge calibration data disappears; (2) any claim
  about *this* DTB must name the config and the byte size it was built with; (3) `bin/dtsport.py`
  `bin/dtsport.py` now refuses `--apply` while a *board* include is unresolved (tested both ways
  against a synthetic vendor tree: missing include -> exit 1 with nothing written to the target;
  clean tree -> exit 0), which is the general protection against this failure mode - it is **not**
  the explanation of this particular delta.
- **Open item, deliberately left open.** To close it: rebuild `dtbs` from the *same* commit in both
  trees and diff the preprocessed `.*.dts` intermediate (`build/arch/arm64/boot/dts/mediatek/.mt6768.dts`),
  plus the `dtc` command line each used, rather than comparing the .dtb sizes and guessing. Until
  that is done, `mt6768.dtb` must always be quoted with its config *and* its byte size.
- **`bin/dtsport.py`'s "N bound in 5.15" count is not the enablement number.** A re-run printed
  `407 bound / 10 orphan` where `bin/hwenable.py` - which resolves each compatible through the
  target's `of_match` tables and then through Kconfig - says **34 bound of 417**. dtsport's figure
  counts a compatible as bound if the string appears anywhere under `drivers/`, which matches
  `simple-bus`-style noise and vendor DT-only mentions; the authoritative enablement source is
  `report/hardware-enablement.json`, and dtsport's number should be read as "compatibles
  mentionable in the tree", nothing more.

## 7. Closed and corrected this round (PMIC + a measurement lesson)

1. **The `mt6768.dtb` size question is closed, and both causes I published for it were
   wrong.** A forced rebuild in the product tree (`make -B arch/arm64/boot/dts/mediatek/
   mt6768.dtb`) and `make dtbs` now both give **122,474 B**, byte-identical in node content
   to `build2` and to `portwork/dts/mt6768.dts.dump` (4,288 decompiled lines; `comm` of the
   two sorted node-name lists: 0 reference-only, 0 ours-only). The 89,053 B file was left
   behind by *my own* experiment - a temporary edit to `arch/arm64/boot/dts/mediatek/Makefile`
   whose `make` run exited `rc=2` mid-rule - so "the cause is an unresolved battery
   `#include`" (retracted already) and "the 89,053 build is the correct product output and
   122,474 is stale" (written in `94dfe346d`) are **both retracted**. What survives is
   procedural, and is now enforced by a tool rather than by memory: `bin/clkaudit.py` hashes
   the DTB it reads, stores `inputs.dtb_provenance` (size, sha256-16, mtime-compared list of
   sources newer than the DTB) in its JSON, prints a `STALE INPUT` warning to stderr, and
   `--require-fresh` turns that warning into exit 2.
   Two related facts worth keeping: this board's DTS contains ten
   `#if defined(CONFIG_MTK_*)` / `#if (CONFIG_MTK_GAUGE_VERSION == 30)` sites, and
   `arch/arm64/boot/dts/mediatek/Makefile:37` carries a `DTS_CPPFLAGS += -DCONFIG_...` line
   for exactly those symbols - so a DTB size is only meaningful with its tree + `.config` +
   target named. I did **not** determine whether `DTS_CPPFLAGS` reaches `cmd_dtc`'s
   preprocessor in 5.15 (`.mt6768.dtb.cmd` records `-D__DTS__` and no `-DCONFIG_*`, which
   would predict the smaller figure). **Now explained by measurement, not by guessing: see 8.1** -
   the two targets differ in whether the board Makefile's `DTS_CPPFLAGS` are in scope, and the
   packaging path (the one that fills boot.img) is the one that loses them. 8.1 supersedes any
   conclusion above about which size is "the correct product output".
2. **`SND_SOC_MTK_BTCVSD` was defined twice in `sound/soc/mediatek/Kconfig`** - my ASoC
   Kconfig transplant (commit `e5462a25cb`) added a `bool` copy of a symbol vanilla 5.15
   already defines as `tristate`. Consequences while it was wrong: kconfig warned
   `ignoring type redefinition of 'SND_SOC_MTK_BTCVSD' from 'bool' to 'tristate'` on every
   configuration pass and kept the *first* (vendor) type, silently overriding mainline's.
   Nothing in-tree selects it, so the fix is removal of my block, not a behaviour change:
   verified 1 definition remains and `make olddefconfig` now prints 0 warnings.
3. **`MEDIATEK_MT6577_AUXADC` is enabled but cannot bind** (5.15's list lacks
   `mt6768-auxadc`/`mt6358-auxadc`). Battery temperature/Ra therefore still have no 5.15
   provider, and the OPLUS charging round inherits that dependency. Recorded as an open
   alias with the driver's exact supported strings, not as "auxadc works".
4. **Aggregate counts from `bin/hwenable.py` are not comparable across invocations.** The
   current run on the fresh DTB reports 413 nodes-with-compatible / 19 bound / 13 enabled /
   13... vs the "417 compatibles, 34 bound" published earlier, which used a different DTB
   state and `--compat-index`. The per-compatible rows (the `driver=` column) are the part to
   trust; the aggregates need `dtb_provenance` recorded the same way clkaudit now does, which
   `hwenable.py` does **not** yet do - next round.
5. `portwork/out/{boot.img,Image.gz,dtbo.img}` still predate both the clock and PMIC
   enablement, so nothing in `out/` should be described as flash-ready or repackaged-candidate
   until rebuilt from the committed tree.

## 8. New this round (AUXADC / regulators / eMMC), and one packaging defect

Items below are cited as `KNOWN-ISSUES 8.<n>` by list position (1-6), which is how the commit
messages and MANIFEST refer to them. Section numbering elsewhere in this file is append-only by
round, so 7.x = the PMIC round and 8.x = this one; the earlier loose ends were moved to 5A-5C
rather than renumbered, to keep existing citations resolving.

1. **`make Image.gz-dtb` packages a different (smaller) `mt6768.dtb` than `make dtbs` builds.**
   Same tree, same sources: `dtbs` applies `arch/arm64/boot/dts/mediatek/Makefile:37`'s
   `DTS_CPPFLAGS` (`-DCONFIG_MTK_GAUGE_VERSION=30`, `-DCONFIG_MTK_M4U=1`,
   `-DCONFIG_MTK_SEC_VIDEO_PATH_SUPPORT=1`, `-DCONFIG_CHARGER_RT9471=1`,
   `-DCONFIG_TCPC_RT1711H=1`, `-DCONFIG_MTK_ENABLE_GENIEZONE=1`) - recorded in
   `.mt6768.dtb.cmd` as 6 `-D` flags, 163,417-byte preprocessed intermediate, 122,474-byte DTB,
   413 compatible-bearing nodes. The packaging path (`arch/arm64/boot/Makefile:47`,
   `$(obj)/Image.gz-dtb: $(obj)/Image.gz $(DTB_OBJS)`) references the `.dtb` from a directory
   where that variable is out of scope: 0 `-D` flags in its `.cmd`, 118,235-byte intermediate,
   **89,053-byte DTB, 399 nodes, no M4U/IOMMU content**. So the DTB embedded in the image we
   built was missing every `#if defined(CONFIG_MTK_*)` block in the board DTS. This also settles
   7.1: my two earlier causes ("failed battery include", "stale artifact / 89,053 is the correct
   product output") were both descriptions of this one target-dependent difference - only the
   measurement was ever reliable.

   **RESOLVED (commit 0077).** `scripts/Makefile.lib:355` owns the `%.dtb` rule and its recipe
   ends with `$(DTS_CPPFLAGS)` (`:229`), which is directory-local: `dtbs` evaluates it with
   `$(src)` = the board directory, the packaging path with `$(src)` = `arch/arm64/boot`. Because
   the two `cmd_dtc` strings differed, `if_changed` could never be satisfied for both - each
   target rebuilt the `.dtb` its own way, which is exactly why the size oscillated. The flag list
   now lives in `arch/arm64/boot/dts/mediatek/dts-cppflags.mk`, included by the board Makefile
   (as before, from one place) and by `arch/arm64/boot/Makefile` under `CONFIG_ARCH_MEDIATEK`.
   Making `Image.gz-dtb` depend on the phony `dtbs` was rejected: it cannot work, since the two
   rules still differ and the image's content would depend on build order. Global `-D` injection
   was rejected: it would touch every vendor's `.dts` and dirty unrelated `.cmd` state.
   Verified: `dtbs` -> `.dtb` -> `Image.gz-dtb` -> `dtbs` now leave one stable 122,474-byte file
   (6 flags, md5 `a2522a615fd6...`); the byte-identical DTB sits inside `Image.gz-dtb` at offset
   10,603,132 immediately after the gzip stream, ahead of the 5 overlays (6 FDT blobs);
   `Image.gz-dtb` 11,063,228 -> 11,096,649 B with `Image` unchanged; `dtc` round-trips it to
   byte-identical output with 413 `compatible` properties and the `mediatek,m4u` and
   gauge/battery blocks present. Both report/clkaudit.json (passes `--require-fresh`) and
   report/hardware-enablement.json were then regenerated *from the packaged DTB*, so the audits
   describe the image we ship. Consequence for the earlier boot.img: its kernel section carried
   the 89,053-byte DTB while its dtb section carried the 122,474-byte one - two different device
   trees in one image; that mismatch is gone (see report/artifacts.json, build-33 pack).
2. **AUXADC calibration seam is intentionally open.** The ported MT6358 PMIC ADC registers its
   IIO channels but does not call the vendor's `pmic_auxadc_chip_init()`, so no `cali_fn` is
   registered (battery voltage uncalibrated) and BAT_TEMP's `convert_fn` pre/post step is
   skipped (battery temperature not trustworthy). `auxadc_set_convert_fn()` /
   `auxadc_set_cali_fn()` remain exported for the charging/fuel-gauge port to use. `md_auxadc`
   (modem ADC) and `mt6358-misc` still have no 5.15 driver.
3. **`ldo_va09` is in this DTB but has no descriptor in mainline's `mt6358_regulators[]`**
   (41 names, all matched; 42 children, one unmatched). Any future consumer of VA09 would
   defer; nothing on the boot path uses it.
4. **I2C: resolved as an investigation, still not enabled (see the I2C section of
   `report/hardware-enablement.md`).** The stock kernel drives these buses with the vendor's
   `drivers/i2c/busses/i2c-mtk.c` (`even_defconfig:2822 CONFIG_I2C_MTK=y`, `I2C_MT65XX` unset),
   which matches this DT's `"mediatek,i2c"` and registers *numbered* adapters - so the absent
   `#address-cells`/`#size-cells` are by design, not damage, and the pad configuration comes from
   the node's `pu_cfg`/`rsel_cfg`/`eh_cfg` ioconfig writes rather than pinctrl (the board DT has no
   i2c pin groups). Measured against 5.15: `i2c-mt65xx.c`'s `mt_i2c_regs_v1[]` and the vendor's
   `i2c-mtk.h` `I2C_REGS_OFFSET` agree offset-for-offset (and so do the DMA blocks), mainline's
   mandatory `"main"`/`"dma"` clocks are already present in these nodes (`"arb"` is optional in
   5.15), and 5.15's driver asks for no pinctrl states - so the *only* structural gap is
   adapter-ness plus the missing i2c pin groups. Two viable routes are written up with citations;
   enabling is deferred to the touch round, where the pin groups and the first client arrive
   together, because a standalone I2C enablement would buy an empty bus. Nothing was flipped.
5. **`MMC_MTK` and `MMC_MTK_PRO` are mutually exclusive by Kconfig, deliberately.** The same
   DTB describes MSDC twice - `mmc@...` (`mediatek,mt6768-mmc`, mainline binding) and
   `msdc@...` + `msdc0_top@...` (`mediatek,msdc`/`mediatek,msdcN_top`, the BSP's proprietary
   host). Enabling both would put two drivers on one controller; `depends on !MMC_MTK` prevents
   it. CQ enabled state: mainline keys CQ off the `supports-cqe` property, which this DTB does
   not carry, so eMMC runs without CQ (stated, since `CONFIG_MMC_CQHCI=y` alone can mislead).
6. `bin/hwenable.py`'s aggregate row for `mediatek,mt6768-mmc` reported "NO DRIVER" even though
   `mtk-sd.o` contains the string and the table entry (verified by `strings`/`nm`). Its per-row
   grep resolution is not the authority for entries added to an existing table; the aggregate
   also moved (413 -> 399 compatible nodes) purely because it read the packaging-built DTB (see
   8.1). Both facts recorded instead of the tool being quietly trusted. (Since 0077 both targets
   agree, so the two figures are the same 413 again - the divergence was the packaging bug, not
   the tool.)

7. **Resolved: the "22 unresolved clock refs" were an audit blind spot, not a port gap.** All 22
   pointed at one provider - `scpsys@10001000`, `compatible = "mediatek,scpsys\0syscon"`,
   `#clock-cells = <1>` - and that node is already claimed by content ported in 0074:
   `drivers/clk/mediatek/clk-mt6768-pg.c:3764` matches `"mediatek,scpsys"`, and
   `clk_mt6768_scpsys_probe()` -> `init_clk_scpsys()` registers `scp_clks[]` (13 entries, ids
   `SCP_SYS_MD1`..`SCP_SYS_VDEC` = 0..12 with no holes) and publishes it via
   `of_clk_add_provider(node, of_clk_src_onecell_get, clk_data)` (`:3603-3610`), sized by
   `SCP_NR_SYSS 13` (`include/dt-bindings/clock/mt6768-clk.h:411`). The cells the board DT actually
   uses are 1,3,4,5,7,8,9,10,11,12 - `SCP_SYS_CONN/DIS/MFG/ISP/MFG_CORE0/MFG_CORE1/MFG_ASYNC/CAM/
   VENC/VDEC` - all in range, and each matches its consumer semantically (smi_larb1 -> VDEC, larb2 ->
   ISP, larb3 -> CAM, larb4 -> VENC, gpufreq -> the three MFG cores, consys -> CONN), which is the
   cross-check that says the BSP intends this provider for exactly these references. `clkaudit.py`
   could not see it because it mapped compatibles only onto `CLK_*` ids and read a single driver file;
   it now models the `SCP_SYS_*` family, the `scp_clks[]` table, the `mediatek,scpsys` provider, and
   takes several `--driver` files. No kernel source changed this round, so build-33 stays the
   reference build. Consequence for the plan: **SMI/M4U has no clock-provider gap to close**, which is
   what makes the vendor-stack route viable with the device tree untouched
   (`report/hardware-enablement.md`, S1/S2-S3 section). Lesson kept from this: an audit number that
   cannot name its rows is not evidence - `clkaudit` now emits the triples (`unresolved_refs`) and a
   markdown table of them, and the same round's conclusion changed the moment it did.
