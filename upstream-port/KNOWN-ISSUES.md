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

## 9. Display/video round, SMI substrate (0078): what is deliberately missing

The SMI port is a *clock-and-keep* substrate: it exists so M4U and the BSP display/video
clients can take and release each larb's clocks the way the 4.19 tree does. Three things the
BSP's SMI stack does are not in it, each with a consequence that is real on hardware.

9.1 **No bandwidth control, and `mtk_smi_conf_set()` writes nothing.** The BSP's `smi_conf_get()`
loads per-larb register/value tables from `drivers/misc/mediatek/smi/mt6768/smi_conf.h`
(conf pairs plus per-scenario pairs) and `smi_drv.c` drives them from BWC scenarios (normal,
game, touch, ...). None of that is ported, so `mtk_smi_conf_set()` is present (M4U calls it) but
iterates `nr_conf_pairs == 0` / `nr_scen_pairs == 0` and returns without writing. That is the
chosen failure mode: an empty table is a no-op, whereas porting the register offsets without the
scenario selection logic would have written uncoordinated values into SMI control registers.
Cost: SMI arbitration stays at bootloader/UEFI defaults. Nobody's clocks are wrong, latency and
throughput under multi-client load are simply unmanaged. Revisit with the display round's MML-R
/BWC work, and note the tables also feed `emimbw`/`mmdvfs_pmqos`, which are not in the port.

9.2 **`smi_register()` is not ported, so no larb is enabled at init and the driver keeps no
"subsys on" state.** The BSP's init function (smi_drv.c:1330-1393) creates the BWC misc device,
initialises `smi_drv.table`, ioremaps the phandle property `mmsys_config` off the common node,
enables the larbs that the display subsystem needs, and registers a power-gating callback. It
cannot run against this DT: `of_parse_phandle(<smi_common node>, "mmsys_config", 0)` fails and
the function returns `-ENOMEM`, because this board's `smi_common@14002000` carries only
`compatible`, `reg` and `mediatek,smi-id`. Adding the property would be exactly the speculative
DT surgery this port forbids, so the function is left out and documented instead. Consequence:
clocks are taken per client call (`smi_bus_prepare_enable()`, which is what
`m4u_hw.c:1113` does) rather than being held from boot; a client that forgets to keep them sees
register accesses to an unclocked larb, same as it would on the BSP if it skipped the API.

9.3 **No MTCMOS re-enable hook.** The BSP registers `pg_callbacks`
(`after_on = smi_subsys_after_on`, `before_off = smi_subsys_before_off`) so that after a
subsystem power cycle the SMI clocks are re-enabled in the right order. `register_pg_callback()`
*is* available in this tree (0074's `clk-mt6768-pg.c` exports it) and the hook body would be
small, but it depends on the BSP's `smi_subsys_to_larbs[]`/`smi_subsys_on` bookkeeping, i.e. on
9.1/9.2. Deferred deliberately; if display clients start showing "larb clocks gone after
suspend", this is the first thing to look at, and the fix is to port the callback plus the
subsys-to-larb mask rather than to re-enable clocks from the pm paths of each client.

9.4 **What this does not tell us yet.** All of the above is compile-, link- and DT-binding-level
verification; no SMI device has actually been probed, because nothing is on the board and no
client is bound yet (`mediatek,m4u` still has no driver: `NO_DRIVER` in the bind audit). In
particular the clock lookups (`devm_clk_get(dev, "img-larb2")` etc.) resolve in the audit
because every cell those six nodes reference is registered by the ported clock drivers, but the
`clock-names`/`clocks` pairing at runtime is only proven once a client binds - which is the M4U
step, not this one.

9.5 **Tool caveat now fixed, but relevant to anyone reading older reports.**
`bin/hwenable.py` used to key its audit on the whole DTB `compatible` blob. This DT stores
several compatibles per property (`"mediatek,smi_larb0\0mediatek,smi_larb"`), and `of_match_node()`
tests each NUL-separated entry, so any match on a non-first entry was invisible. Numbers in
reports generated before 0078 (339 distinct / 21 bound / 15 enabled / 318 driverless) are
therefore undercounts of *bindings*; rows are trustworthy again from build-34 on
(349 distinct / 33 bound / 24 enabled / 316 driverless), and that is also why aggregate counts
must never be compared across tool versions (see 5B).

## 10. M4U's ION dependency: measured, and deliberately not satisfied

The 4.19 Kconfig says `MTK_M4U: depends on MTK_ION`, and 5.15.220 has no ION in tree (our tree's
`drivers/staging/android/` is ashmem only). That combination invites two wrong moves - transplanting
the ION subsystem to satisfy a one-line dependency, or rewriting M4U onto dma-buf "because ION is
gone". Both are unnecessary and were checked rather than assumed:

- M4U's only ION code is `m4u_test_ion()` (`2.0/m4u_debug.c:338-398`), inside
  `#ifdef CONFIG_M4U_TEST_ION`, a symbol the BSP defines nowhere and `even_defconfig` does not set.
  Stock therefore builds M4U with **no** ION code. The port keeps that file verbatim and leaves the
  same symbol undefined - no deletion, no stub.
- `m4u_alloc_mva()` (`2.0/m4u.c:694`) takes a VA (M4U then builds the scatterlist itself via
  `m4u_create_sgtable()`, using `vmalloc_to_page`/`follow_pte`) or a caller-supplied `sg_table`
  (`M4U_FLAGS_SG_READY`). No fd, no `ion_handle`. So M4U is an MVA + pgtable engine, not a client of
  any allocator.

What this *does* leave open, and is not hidden:

10.1 **The clients still want MTK's ION extensions.** `video/mt6768`, `ccu`, `cameraisp/mt6768`,
`mdp` use `ion_client_create`/`ion_alloc(ION_HEAP_MULTIMEDIA_MASK)`/`ion_kernel_ioctl(ION_CMD_MULTI-
MEDIA)`, `ion_mm_data`, `ION_LOG_*`, `ION_DECOUPLE_*`, `ION_GAINCONTROL_*` - MTK heap behaviour
(heap-side owner/MVA booking, compression, secure decouple, gain control), which mainline dma-buf
heaps have no equivalent of. Porting those clients means deciding per feature: dma-buf heap + M4U's
own `struct m4u_buf_info` bookkeeping covers ownership; LOG/decouple/gain-control have no upstream
counterpart and stay off rather than faked. Userspace also changes ABI (`/dev/ion` vs
`/dev/dma_heap/*`), which affects what the device's existing media HALs can do unchanged.
The equivalence table and the call-site census are in `report/m4u-ion-audit.md`.

10.2 **`CONFIG_DMABUF_HEAPS` is still off on purpose.** `system_heap.c`/`cma_heap.c` are in the tree
but nothing ported allocates yet, so enabling heaps now would be the same kind of speculative config
flip that kept `CONFIG_MEDIATEK_SMI`/`CONFIG_MTK_IOMMU` from being used for SMI. Heaps get enabled
with the first ported client that allocates.

10.3 **Two SMI entry points are declared and not defined.** `smi_public.h` (ported from the BSP for
M4U's `#ifdef CONFIG_MTK_SMI_EXT` include) declares `smi_debug_bus_hang_detect()` and
`smi_sysram_enable()`; this port does not define them, because their bodies need the GCE debug and
sysram/BWC infrastructure that is deliberately out. A client that calls one gets a link error - the
intended loud answer, as opposed to the `((void)0)` no-op the BSP's own `#else` branch would hand it.

10.4 **`smi_mm_first_get()` returns false here.** In the BSP the mask behind it is set by
`smi_register()`, which this port does not carry (see 9.2). MT6768 is unaffected - `m4u.c` reads that
value only under `CONFIG_MACH_MT6765 || CONFIG_MACH_MT6761` - but it is a state difference from stock
that should be known when MDP/mmlw work starts.

## 11. M4U landed (0080, build-36): the adaptations it needed, the surfaces left out, one defect kept

`report/m4u-port.md` is the execution record for this commit; the points below are the ones a later
reader must not "fix" or re-litigate without re-measuring.

11.1 **`struct proc_ops` is now used at every M4U proc node, and one of them leans on
`inode->i_private`.** v5.6 took /proc files off `file_operations`. The port converts the vendor's
`DEFINE_PROC_ATTRIBUTE` macro (9 nodes), the six hand-written `m4u_proc_*_fops` (`m4u_debug.c`,
`m4u_pgtable.c:1090`) and `m4u_fops`' proc twin in `m4u.c` - same callbacks, `generic_file_llseek`
becoming `default_llseek`. The macro still copies the inode to move `PDE_DATA()` into `i_private`,
because 5.15's `simple_attr_open()` reads `inode->i_private` (fs/libfs.c). Upstream deleted
`i_private` in 6.9, so at the next rebase that copy is the line to remove, not the vendor hack to
defend. `struct proc_ops` has no flush callback; `MTK_M4U_flush()` is a no-op in the vendor driver,
and `proc_ioctl`/`proc_compat_ioctl` exist, so `/proc/m4u` keeps everything except a call that did
nothing.

11.2 **M4U's mmprofile trace events are compiled out - by the vendor's own switch.**
`mt6768/m4u_priv.h:89` defines `M4U_PROFILE` unconditionally, so `m4u.c`'s event registration and its
15 trace call sites are live source; they resolve to the `static inline` no-ops in
`drivers/misc/mediatek/mmp/mmprofile.h`'s `!CONFIG_MMPROFILE` branch, which exists for exactly this
purpose ("Put dummy API implementation here"). Stock builds `CONFIG_MMPROFILE=y`
(`even_defconfig:1712`) and does emit Alloc/DeAlloc MVA, Config Port, M4U ERROR, CACHE_SYNC and
Toggle_CG into the MMP buffer. Nothing here does, because `mmp/src` is not ported. If MVA timing work
starts, the missing input is the MMP framework, not an M4U change.

11.3 **The 32-bit compat M4U ioctls cannot be built on this base at all.** `MTK_M4U_COMPAT_ioctl`
translated four commands through `compat_alloc_user_space()`, which lives in `fs/compat.c` - and this
5.15.220 tree has no `fs/compat.c` (`git ls-files fs/ | grep compat` returns only
`compat_binfmt_elf.c`). Rather than invent a substitute, the port takes the vendor's own alternative:
the condition became `IS_ENABLED(CONFIG_COMPAT) && defined(M4U_HAVE_COMPAT_TRANSLATION)`, which
selects the BSP's `#else` branch defining `MTK_M4U_COMPAT_ioctl` as `NULL`. A 32-bit caller gets
`ENOTTY` instead of a translation it cannot have; the native 64-bit ioctls are untouched. Restore
`fs/compat.c` (or rebuild the four cases on `m4u_ioctl()`'s helpers) and define
`M4U_HAVE_COMPAT_TRANSLATION` to bring it back.

11.4 **`show_pte()` is no longer reachable from a driver, so two M4U error paths lost their raw PTE
dump.** In 5.15 arm64 it is `static void show_pte(unsigned long addr)` inside
`arch/arm64/mm/fault.c`; the vendor's extern declaration compiles and then fails at link
(`ld.lld: error: undefined symbol: show_pte` - the only link failure of this round). The calls in
`m4u_fill_sgtable_user()` are replaced by a comment: `m4u_user_v2p()` immediately above walks
pgd/p4d/pud/pmd/pte and prints which level rejected the address, which is the actionable half. What is
gone is the pte value itself. Do not "restore" it by un-static'ing arch code.

11.5 **One vendor defect is carried on purpose: `mt6768/m4u_hw.c:1723`.** The port-attribute skip reads
`if ((port_array->ports[port] && M4U_PORT_ATTR_EN) == 0)`; clang flags it
(`-Wtautological-constant-compare`) because `&&` with a bit mask is always true, so no port is skipped
by that test. It sits in hardware programming on a shipping SoC and stock builds the same line, so
correcting it here would change which M4U ports get configured - the kind of "improvement" this port
defers. It is the single warning this directory adds (1 warning in 3,074 lines, present in 4.19 too).

11.6 **`MTK_M4U` depends on `MTK_SMI_EXT`, not `MTK_ION`, and the substitution is forced:** `grep -rn
"config MTK_ION"` over the 5.15 tree returns nothing, so the BSP's `depends on MTK_ION` would leave the
symbol unreachable. `MTK_SMI_EXT` is the dependency M4U really has (its larb keeps are
`#ifdef CONFIG_MTK_SMI_EXT`, and any other spelling would compile the no-op
`smi_bus_prepare_enable` out of `smi_public.h` - see 9.1 and 0079).

11.7 **M4U being in the image does not make display/video work.** No client calls it yet, so the
multimedia allocation ABI the BSP's clients expect (`ION_CMD_MULTIMEDIA` heap-side booking,
`ion_mm_data`, `ION_LOG_*`, `ION_DECOUPLE_*`, `ION_GAINCONTROL_*`, `ion_phys`, `ion_map_kernel`,
`/dev/ion`) stays unavailable, and `CONFIG_DMABUF_HEAPS` is still off because no ported client has
asked for it (10.1). The first MM client is where that decision gets made, from its actual calls.

## 12. Display M4U client (0081, build-37): what is in the image and what is not

12.1 **The client is built and linked, and has no caller.** `CONFIG_MTK_DISP_M4U=y` compiles
`drivers/misc/mediatek/video/mt6768/dispsys/ddp_m4u.o` (249 lines, from the vendor's 400) and
`video/mt6768/videox/disp_helper.o` (452 of 453), and all five of its M4U references resolve into
the ported driver (`m4u_alloc_mva`/`m4u_create_client`/`m4u_mva_map_kernel` in `m4u/2.0/m4u.o`,
`m4u_config_port`/`m4u_register_fault_callback` in `mt6768/m4u_hw.o`). Nothing calls
`disp_m4u_init()`/`config_display_m4u_port()`: doing so from a partial probe would set
`Virtuality=1` on the four display ports while LK keeps scanning the logo out of physical addresses,
and the register layer that owns the LARB side (`ddp_reg.h`, 299 lines plus the cmdq and
display_recorder closure) is not ported. That is a panel-blackening risk, not a nicety, so the
binding stays `NO_DRIVER` for `mediatek,dispsys`/`mediatek,mtkfb` on purpose (see
`report/display-m4u-client.md` section 7).

12.2 **Vendor sequencing, measured:** MT6768 calls `disp_m4u_init()` at `ddp_drv.c:557` but
`disp_helper_option_init()` only at `ddp_drv.c:593`, while `disp_helper.c:71` defaults
`{DISP_OPT_USE_M4U, 0, "must enable"}`. So on stock the *else* branch of `disp_m4u_init()` is live
code at dispsys probe and clears `MMU_EN` in `SMI_LARB0` `CON0..CON3`. The ported file keeps the
log line and does **not** write those registers (they belong to `drivers/memory/mtk-smi`, 0078/0079);
whoever ports the dispsys core has to decide where `MMU_EN` is managed. The harness reproduces the
ordering: the option reads 0 before `disp_helper_option_init()` and 1 after.

12.3 **`struct m4u_port_config_struct.domain` is never initialised by the client.**
`config_display_m4u_port()` fills ePortID/Virtuality/Security/Distance/Direction and leaves
`domain`, so the driver receives whatever was on the stack - the host test sees the `0xa5a5a5a5`
poison in all four calls. It is harmless today only because MT6768 M4U v2.0 has one domain
(`m4u_hw.c:23 static struct m4u_domain gM4uDomain`) and `m4u.c:806/995` derive it from the port
with `m4u_get_domain_by_port()`. Do not copy that call site into a multi-domain configuration
without setting the field.

12.4 **The MVA the display client pre-sets is not honoured.** `disp_hal_allocate_framebuffer()`
assigns `*mva = pa_start & 0xffffffff` and then calls `m4u_alloc_mva()` with `flags = 0`, while
`m4u.c` only honours a requested MVA under `M4U_FLAGS_FIX_MVA` (or `M4U_FLAGS_START_FROM` as a
hint). The value the caller must program is the one returned *through* `*pMva`. Do not reason about
the boot logo as if MVA == PA; the host test asserts the returned value instead.

12.5 **The ION half is deleted, not stubbed, and stock also compiled it out.** All 41 `ion_`
references in `ddp_m4u.c` sit inside seven `disp_ion_*()` wrappers whose bodies are guarded by
`MTK_FB_ION_SUPPORT`, a macro that appears in no Kconfig and no Makefile in the tree (it comes from
the Android userspace build), so a kernel-only build never compiled them. The wrappers were removed
with the `mtk_ion.h`/`ion_drv.h`/`ion_priv.h` includes because their *prototypes* still need
`struct ion_client`, `struct ion_handle` and `enum ION_CACHE_SYNC_TYPE`, which v5.15 does not
provide. No file in the ported tree references them. A client that needs `ION_CMD_MULTIMEDIA`
booking starts from `report/m4u-ion-audit.md` section 8 - that ABI stays unavailable by decision,
not by oversight (11.5, 10.1).

12.6 **Log routing differs on purpose.** Vendor `ddp_log.h` and `disp_drv_log.h` mirror every
message through `dprec_logger_pr()` (`display_recorder.c`, 1,657 lines) and gate some levels on
`ddp_debug.c` (964) plus the `g_mobilelog` switch. Neither is part of this client's closure, so
`video/mt6768/dispsys/ddp_log.h` in this tree maps `DDPMSG`/`DDPERR`/`DDPDBG` and
`DISP*` onto the vendor's fallback arms (`pr_info`/`pr_err`/`pr_debug`). Consequences: no
`/dev/pmsg/dprec` copy of display M4U events, `DDPMSG` is unconditional, and the register-dump arm
of the fault callback is absent (12.1). `DISPINFO`/`DISPMSG`/`DISPCHECK` stay `pr_debug`, so they
are invisible unless dynamic debug is enabled, matching stock.

12.7 **`disp_helper.c` is the vendor file minus two videox couplings.** The DynFPS hook
(`primary_fps_ctx_set_wnd_sz`, `primary_display.c`) is removed from `disp_helper_set_option()`, so
`DISP_OPT_FPS_CALC_WND` is a plain table entry; the `FAKE_LCM_WIDTH/HEIGHT` cases, which ask
`primary_display_get_virtual_width()`/`DISP_GetScreenWidth()`, are wrapped in
`#ifdef CONFIG_MTK_FB` and therefore fall back to the table (0 = no fake LCM) while videox is not
ported. `disp_global_stage` still initialises to `DISP_HELPER_STAGE_NORMAL` because
`CONFIG_FPGA_EARLY_PORTING` is unset, the same as stock, so the stage-gated options read the same
values they do on the device.

12.8 **Two assumptions about the stock build were wrong and are corrected here.** (a)
`CONFIG_MTK_VIDEOX` gates nothing: it exists only in `video/Kconfig` and in zero Makefiles, so with
`CONFIG_MTK_FB=y` the whole legacy `videox/` path *is* built (36,982 lines) - the earlier reading
that `MTK_VIDEOX=n` excluded it would have mis-scoped this port. (b) `mtdummy/` is excluded by
`video/Makefile:32` (`ifneq ($(CONFIG_MTK_LCM), y)`) and `common/mtkfb_dummy.o` by
`common/Makefile:103` (`ifneq ($(CONFIG_MTK_FB), y)`), so neither dummy fbdev is in stock's image -
and `common/mtkfb_dummy.c` would not have exercised M4U anyway, because its `CONFIG_OF` branch uses
a local allocator that never calls M4U. Also relevant to any boot claim: the packaged
`mt6768.dtb` carries 0 `atag,videolfb-*` properties, which is what the vendor fb path reads for the
logo region, so that content must come from LK at boot.

12.9 **A config-recipe footgun, now guarded.** `./build.sh configure` regenerates `.config` from
arm64 `defconfig`; a re-run mid-round silently dropped `MACH_MT6768` (and `PINCTRL_MT6768`,
`MTK_DEVAPC`, `COMMON_CLK_MT6768`, `MEDIATEK_MT6577_AUXADC`, `MT635X_AUXADC`,
`RTC_DRV_MT6397`) plus `BUILD_ARM64_APPENDED_DTB_IMAGE` and both `*_NAMES` strings. Nothing
in the build log says so; the only evidence was `Image` being 20,480 bytes *smaller* while code was
added, and `Image.gz-dtb` coming out as a byte-for-byte copy of `Image.gz` (no DTB appended at
all). `portwork/configs/apply.sh` now carries the full recipe and fails if any of those symbols is
missing after `olddefconfig`; the rejected build is kept as `logs/build-37a-rejected.log`.

## 13. The DT surface: 0089's driver links, is enabled by config, and still has no device

Found while gating 0089, and left open on purpose (decision 151, confirmed by the human on 2026-09-06),
because resolving it is an architectural choice about what this port's device tree *is*, not a missing
line of code.

What was measured, in the tree at the 0089 tip:

- the appended DTB is `mediatek/mt6768` (`CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES="mediatek/mt6768"`,
  built from `arch/arm64/boot/dts/mediatek/mt6768.dts`);
- that DTB **does** contain the MT6370 configuration node - decompiled, `mt6370_pmu_dts` with
  `interrupt-controller`, `#interrupt-cells = <1>`, `mt6370,intr_gpio = <&pio 3 0>`, the legacy
  `mt6370,intr_gpio_num = <3>`, and the `mt6370_dsvp`/`mt6370_dsvn` cells carrying
  `regulator-name = "dsv_pos"/"dsv_neg"` - and it **does** contain `i2c5@11016000`
  (`compatible = "mediatek,i2c"`, no `status`, so enabled);
- it does **not** contain any I2C client for the chip: `subpmic_pmu@34 { compatible =
  "mediatek,subpmic_pmu"; reg = <0x34>; }` is at
  `arch/arm64/boot/dts/oplus6768_20761/cust.dtsi:151`, and that directory holds one file and no `.dts`,
  so nothing compiles it;
- the landed `i2c5` node also lacks `#address-cells`/`#size-cells` (a child with `reg` needs them) and the
  bus properties the board file sets on it (`clock-frequency = <3400000>`, `mediatek,use-push-pull`).

Consequence, stated plainly: `mt6370_pmu_i2c.c`'s driver would match the board node's compatible
(`mt6370_pmu_i2c.c:342-347` lists both `"mediatek,mt6370_pmu"` and `"mediatek,subpmic_pmu"`), so no driver
edit is needed for either answer - but with no node there is no `i2c_client`, no probe, no
`mt6370_pmu_dts` repointing via `rt_config_of_node()`, and therefore no regulator named `dsv_pos`. The
bias calls `ddp_drv.c` makes will `regulator_get()` and fail the way stock's code handles a missing
supply. Nothing in the series claims otherwise; the wording is in the 0089 commit message and in
`patch-series/0000-cover-letter.eml`'s not-claimed section.

The three options, costed, unchosen: (a) copy the board's client node and the two cell properties into
`mt6768.dts` - about 8 lines, makes it probe, but writes a board decision into a SoC file and invalidates
the node census every earlier round published (450 nodes / 34 bound / 25 enabled); (b) land the vendor's
board `.dts` and move `APPENDED_DTB_IMAGE_NAMES` to it - closest to what the phone actually boots, and it
would also bring `/chosen` (the LK `parse_tag_lcm()` handover this port cannot otherwise see), but it
re-opens the 0070 transplant decisions; (c) leave it, which is what was chosen, because nothing the display
path needs *next* depends on the answer.

Two smaller things recorded here rather than in a commit message, both from the same CONFIG/DT census:
`CONFIG_DEBUG_FS` is `y` in this tree and not set in `even_defconfig`, so the port exposes
`/sys/kernel/debug/mtk_dsv` where stock exposes nothing (246 debug-only lines, no hardware access, not
"fixed" by deleting the file stock also builds); and `mt6370_pmu_subdevs.c`'s cell table still lists the
charger/fled/bled/rgbled/ldo compatibles whose drivers were not ported, so on a device with the DT wiring
those cells become unbound platform devices - which is what the vendor code does for any absent
sub-driver, and which is why they were left rather than trimmed.

## 14. The CMDQ record adapter (0091) links, encodes like the vendor, and cannot be exercised

`drivers/soc/mediatek/mtk-cmdq-disp-record.c` answers `cmdqRecWrite`, `cmdqRecWaitNoClear` and
`cmdqRecSetEventToken`, the three names 0090's `ddp_path.c` opened, and the whole-tree open-name count moves
65 -> 62 with each of the three defined exactly once tree-wide. It is *not* the vendor's record engine, and
three differences are deliberate, each one measured before it was accepted:

1. **No prefetch traffic.** Stock's `cmdq_append_command()` (v3/cmdq_record.c:970) consults
   `cmdq_get_func()->shouldEnablePrefetch()` and, when enabled, brackets writes with a prefetch-disable and a
   mark instruction. That policy lives in v3/cmdq_virtual.c, which this series does not build. A record built
   here therefore matches a stock record whose prefetch policy was *off*, word for word, and differs from one
   where it was on by those two instructions per write. No landed code can observe this today, and no
   hardware behaviour is inferred from it.
2. **Unresolvable addresses are refused, not detoured.** Stock takes an address no subsys row covers and
   loads it into `CMDQ_SPR_FOR_TEMP` with a `CMDQ_CODE_LOGIC`/`CMDQ_LOGIC_ASSIGN` instruction, then writes
   through that register. This tree has no SPR allocator and `mtk-cmdq-helper.c` exposes no primitive for it,
   so the adapter returns `-EINVAL` and logs once. It cannot pack 99 into the field instead: the 5-bit
   `sop` would turn `CMDQ_SPECIAL_SUBSYS_ADDR` into subsys 3 and write somewhere else silently - which the
   harness carries as its own case. Measured, the only landed addresses needing a detour
   (`0x1100e000`, `0x1100d000`) are unreachable through this entry point, and `video/mt6768` plus
   `video/common` contain zero references to `CMDQ_REG_VALUE`, `CMDQ_REG_EXT_VALUE` or
   `cmdq_reg_val_to_reg_str()`.
3. **Register-typed operands are refused.** `cmdqRecWrite()` takes `u32 value` in this tree's header
   (v3/cmdq_record.h:167), so the vendor's `CMDQ_DATA_BIT` tag is 0 by construction and `value_type == 1` is
   unreachable; the branch is kept as a rejection so that anyone landing `cmdqRecWriteFromDataRegister()`
   later meets a documented hole rather than a plausible-looking wrong encoding.

The larger honesty point: **nothing in this tree can build a record.** `cmdqRecCreate()` is referenced only by
the `DISP_REG_VAL_SET()` macro at `ddp_reg.h:272`, which no landed object expands, so there is no handle to
pass and the layer is required at link time and unreachable at run time. That is why landing it did not and
does not move the maturity level past "compiles and links", why the display path still cannot be called
functional, and why the first live callsite will need a `cmdq_pkt_create()`-owning caller and a mailbox
channel - at which point the prefetch question and the `#if !defined(CONFIG_MTK_CMDQ_MBOX_DRV)` binding of
the header (the eight header warnings this file inherits, including `mtk-cmdq-mailbox.h:91`'s
`struct mbox_chan` scope wart, which pre-dates 0091 and affects every includer) become live engineering
questions rather than documented omissions.

## 15. Why the engine files are not landed yet, and which two files must never be (measured at 0092)

0092 was queued as `ddp_rdma_ex.c` + `ddp_wdma_ex.c` + `ddp_matrix_para.h`. It is not landed, because
pricing that set against the tree of record showed it costs more names than it pays: it compiles clean
and closes 10 open names while opening 21, so the whole-tree link would have gone 62 -> 73 open names
instead of 62 -> 57. Every number is in `report/l2-slice-0092-before-after.md`; the three findings that
decide it are here, so that no later round re-derives them.

1. **13 of the 21 opened names are the record lifecycle, and in the vendor they are not encoders.**
   `cmdqRecCreate`, `cmdqRecDestroy`, `cmdqRecReset`, `cmdqRecFlush`, `cmdqRecFlushAsync`, `cmdqRecWait`,
   `cmdqRecPoll`, `cmdqRecWriteSecure`, `cmdqRecWriteSecureMetaData`, `cmdqRecSetSecure`,
   `cmdqRecSecureEnableDAPC`, `cmdqRecSecureEnablePortSecurity` and `cmdqRecBackupUpdateSlot` are each a
   3-4 line trampoline in `cmdq/v3/cmdq_record.c` (lines 3808-4098) into `cmdq_task_*` / `cmdq_op_*`:
   per-subsys session pools, the `gce_plat` lock, mailbox submission. That is the engine this port
   refuses to land - the reason 0082 exists as a revert. Answering them means either growing the
   adapter into a session model (an architectural change, not a slice) or landing v3 (dead on
   measurement). The other 8 opened names are `videox` debug state (`dbg_urg_low`, `dbg_urg_high`,
   `dbg_ultlow`, `dbg_ulthigh`, `dbg_prehigh`, `_cmdq_insert_wait_frame_done_token_mira` in
   `mt6768/videox/debug.c`), `set_rdma_width_height` (`videox/disp_lowpower.c`) and
   `primary_display_is_decouple_mode` (`videox/primary_display.c`) - i.e. the panel-handover side of the
   cut. `ddp_ovl.c` is the same story at smaller scale: it compiles (with the platform
   `dramc/mt6768/mtk_dramc.h`, 195 ln, landed for it) and closes 6 names but opens 10, for a net +4.
2. **`common/rdma20/ddp_rdma.c` and `common/wdma20/ddp_wdma.c` must not be landed at all.** They look
   like the natural companion to the platform files, but `video/common/Makefile:70-78` descends into
   those two directories only for `CONFIG_MACH_MT6799` (and into `rdma10`/`wdma10` for
   MT6757/KIBOPLUS/MT6797/MT6795/MT8167), so mt6768's vendor build never compiled them. That is also why
   `DDP_REG_BASE_DISP_RDMA0`, which `ddp_rdma.c:25` returns, is defined nowhere in the whole vendor tree
   (grep over `drivers/` and `include/` finds only that use): it is MT6799 code sitting in a shared
   directory, in the same class as the `cmdq/v3/*.c` files this port carries as headers only. The
   mt6768 providers of `rdma_get_address`, `rdma_dump_reg`, `wdma_dump_reg` and friends are the platform
   `ddp_rdma_ex.c` / `ddp_wdma_ex.c`.
3. **`ddp_wdma_ex.c:19`'s `#include <ion_sec_heap.h>` needs the one-line comment-out, and the reason is
   measurable.** This port carries the ION *types* (`drivers/staging/android/mtk_ion/ion.h`, whose line 31
   is `#define ion_phys_addr_t unsigned long`) and not the ION driver, which is the boundary 0080 drew;
   the vendor header the file asks for lives under `mtk_ion/mtk/` and includes `ion_drv.h`, i.e. landing it
   means landing ION. In this file the include contributes nothing that `ion.h` does not: its only type use
   is the `ion_phys_addr_t sec_hdl = -1;` declaration at line 1260, and the only call that needs the
   header, `ion_hdl2sec_type()` at line 1262, is inside `#ifdef CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM`
   (`=y` at `even_defconfig:1977`, absent from this port's config of record). So the fix when RDMA/WDMA
   land is the pattern already at `ddp_drv.c:36` (`/* #include <linux/ion.h> */`) - one commented line,
   `diff`-verifiable against the vendor file, behaviour-preserving in this configuration, and it must be
   re-enabled together with an ION driver if `CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM` is ever set.

One smaller recorded non-issue from the same round: the vendor passes `ccflags-y +=
-DDEFAULT_MMP_ENABLE` when `CONFIG_MMPROFILE=y` (`dispsys/Makefile:109-111`;
`even_defconfig:1711-1712` sets both MMPROFILE symbols), and `ddp_mmp.c`'s `ddp_mmp_init()` body is
inside that define. 0092 lands the file without the define, because the port's dispsys Makefile carries
no `-D` flags at all since 0085's filtered generation and because the guarded body is one `DDPMSG`
plus `mmprofile_enable(1)` / `init_ddp_mmp_events()` / `mmprofile_start(1)`, whose first and third are
static-inline no-ops in the landed `mmp/mmprofile.h:212/216` (that header's `#else` branch of
`#ifdef CONFIG_MMPROFILE`, matching this config) and whose middle only registers event names through the
`mmprofile_register_event()` dummy at `:131`. If the port ever lands `drivers/misc/mediatek/mmp/` as a
driver rather than a header, the define and the real mmprofile behaviour come back together.
