# Known issues and hard limits of the ported tree

Read this before using `upstream-port/patch-series/`.  Every item here was measured on the
tree the series produces (tree `ad82b1376943068d31f7f06f223240a7bd0be7a0`), not assumed.

## 1. It is a compiling kernel, not a booting device kernel

What is proven on the tree this series produces: `make ARCH=arm64 LLVM=1 Image` and `dtbs` run with
**0 compiler errors** — `arch/arm64/boot/Image` 26 877 960 bytes (sha256 in `report/build.json`;
an earlier session measured 28 450 824 bytes with a slightly wider debug config, recorded in
`report/build-evidence.md`), 529 arm64 DTBs (incl. this board's), plus the **device's own** `mt6768.dtb` (122 474 B) and **and, now measured on the product tree too**: `compiler_errors=0`, `make_failures=0`, 840 `.ko` (`logs/build-27.log` quoted in `report/build.json`)
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

## 3. Content the port gave up (all of it itemised in `report/decisions.json`, 63 entries)

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

## 7. Flash-image caveats (read before wiring this into a device build)

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

## 8. Numbers that must be re-measured, not quoted from docs

Every count in these documents is regenerated by `bin/mkreport.py` / `bin/buildreport.py` from the
tree and the build log; `report/*.json` is the authority.  If you change the series, re-run them —
a stale `.ko` or DTB count in a markdown file is exactly the kind of error this directory has
corrected twice already (a truncated log once yielded a "1465 modules" figure that was really 0).

## 6. Other caveats

* No module ABI continuity: 150 `EXPORT_SYMBOL*`/KABI annotations the port would have added were
  removed, and 38 files had port-introduced duplicate definitions stripped; a 4.19 vendor `.ko`
  will not load here (expected — they must be rebuilt against 5.15 headers).
* Toolchain coverage is clang-r437112 + lld only (`-Werror` on).  GCC 9/10 were not exercised.
* `CONFIG_SECURITY_SELINUX`/`SELINUX_ANDROID` extensions, `proc_ops`, `set_fs`, `ion`, `strlcpy`,
  `timespec` hazards in vendor-new code were counted, not fixed: 22 950 files / 15.9 M lines
  audited in `report/hazard.json` (set_fs 1 097, ion 1 009, proc_ops 777, timespec 583 …).
  Those files are not in the 5.15 Kbuild yet, so the tree is clean but the transplant is ahead.
