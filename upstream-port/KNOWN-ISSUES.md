# Known issues and hard limits of the ported tree

Read this before using `upstream-port/patch-series/`.  Every item here was measured on the
tree the series produces (tree `a8bd53370bb2c649e9f3bef03db4af5c7e6faa99`), not assumed.

## 1. It is a compiling kernel, not a booting device kernel

What is proven: `make ARCH=arm64 LLVM=1 Image`, `dtbs` and `modules` run with **0 compiler
errors**, producing `arch/arm64/boot/Image` (28 450 824 bytes) and 528 DTBs (including
`mt6779-evb.dtb`, an MT67xx-family SoC).  Nothing was ever executed — there is no device, no
emulator run, no boot log.  Absence of compile errors means the C is coherent; it says nothing
about whether the `even` hardware comes up.

What is missing for that (see `FEATURE-PARITY.md` for the per-subsystem list):

* **No board device tree for `even`.** The vendor tree has 406 `*.dts*` files under
  `arch/arm64/boot/dts/mediatek/`; none of them was ported (the port deliberately reverted the
  7 upstream-only board DTS files the hunk engine had touched, because the vendor versions
  `#include` downstream-only `.dtsi` paths).  A `k6769`/`even` board file must be authored
  against 5.15 bindings: of the 404 distinct compatibles the vendor device trees use, only
  **32 (7 %)** bind to anything that exists in vanilla 5.15.
* **No DTBO, no AVB/vendor_boot, no ramdisk, no partition images.** Boot-image packaging
  (`mkbootimg`, DTBO overlay with `fdtoverlay`, `avbtool`) is untouched work.
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

## 5. Sandbox-only build glue (never commit this)

This container has no OpenSSL development package, so `scripts/extract-cert` cannot link.  A
stand-in implementing *only* the empty-`CONFIG_SYSTEM_TRUSTED_KEYS` case was compiled into the
object tree as the gitignored artifact kbuild would have produced; it exits non-zero for any real
key list so it can never silently produce a wrong trust chain.  Wrapper scripts, `bin64/env.sh`,
the bison/m4 pair and the clang/lld download all live under `~/.cache/tools/`, outside the kernel
tree — **no file in the tree was patched to accommodate the sandbox**.  On a normal machine:
`apt install build-essential flex bison bc libssl-dev && make ARCH=arm64 LLVM=1 Image`.

## 6. Other caveats

* No module ABI continuity: 150 `EXPORT_SYMBOL*`/KABI annotations the port would have added were
  removed, and 38 files had port-introduced duplicate definitions stripped; a 4.19 vendor `.ko`
  will not load here (expected — they must be rebuilt against 5.15 headers).
* Toolchain coverage is clang-r437112 + lld only (`-Werror` on).  GCC 9/10 were not exercised.
* `CONFIG_SECURITY_SELINUX`/`SELINUX_ANDROID` extensions, `proc_ops`, `set_fs`, `ion`, `strlcpy`,
  `timespec` hazards in vendor-new code were counted, not fixed: 22 950 files / 15.9 M lines
  audited in `report/hazard.json` (set_fs 1 097, ion 1 009, proc_ops 777, timespec 583 …).
  Those files are not in the 5.15 Kbuild yet, so the tree is clean but the transplant is ahead.
