# Zenium_Kernel: 4.19.325 -> 5.15 migration (attempt, measurement, verdict)

Device: Realme C25 / Narzo 50A (`even`), MediaTek **MT6768/MT6769** (Helio P95/G85),
OPlus downstream kernel `4.19.325-cip135-st19` + `-Zenium`, squashed to **one commit**
(`011d4a1f2`), so this is a *tree-level port*, not a rebase.

Target chosen per instruction: vanilla **5.15 LTS** -> `v5.15.220`
(commit `0996e0926f6b4d6123e1b94407d726bc9810248e`).

---

## 1. TL;DR

| | |
|---|---|
| Delta vs vanilla 4.19.325 | **5,823 modified files** (24,622 hunks, +288,179 / -126,331), **29,064 vendor-new files** (18.2 M lines), 95 deleted |
| Already upstream in 5.15 | **9,507 hunks (38.6 %)** - MTK's "common kernel" is a backport pile; drop it |
| Mechanically portable | **2,959 hunks** -> **2,952 applied** across **1,036 files** (+29,640 / -4,181), **0 rejects** |
| Deliverable | `upstream-port/patch-series/` = **74 commits + cover letter** grouped per subsystem on top of `v5.15.220`; `git am` reproduces tree `0f5d980765dd` exactly (0001-0068 mechanical vendor delta; 0069-0072 device round - packaging kbuild, board DTS/DTBO transplant, `pinctrl-mt6768`, devapc fixes; 0073 revert of the half-ported MT6397 RTC; 0074 mt6768 clock provider + MTCMOS power gating) |
| Needs a human | 4,152 manual + 4,741 near/partial hunks (4,020 manual are device-relevant, in 1,244 files) |
| Not hunk-portable at all | 22,950 vendor-new C files / 16.0 M lines (Mali DDK, mtkcam, AFE audio, CCCI, pwrap/PMIC, connac, SMI/IOMMU, cmdq ...) |
| Compiles and links? | **Yes, all gates, in the *device* config**: `Image` 26,963,976 B, `Image.gz-dtb` 11,059,336 B, `make dtbs` 529 arm64 DTBs incl. this board's `mt6768.dtb` + the five `oplus676*_*.dtbo`, `make modules` 840 `.ko`; `compiler_errors=0`, `make_failures=0` (`logs/build-29.log`, `logs/build-30.log`; `-k -j2`). Nothing was executed on hardware. |
| Boot-ready on 5.15 today? | **No.** 5.15 can bind **32 of 404** device `compatible` strings (7 %) - see section 4 |

The port is real and reproducible, but stated honestly: **the core-kernel delta lands, the BSP
does not.** Nobody upstreams a phone BSP in one sitting; what is delivered here is the whole
mechanical surface, measured and verified, plus the exact blocker list with numbers on it.

---

## 2. What the tree actually is

`git ls-files | wc -l` = 90,746 files vs 61,775 in vanilla 4.19.325.

Vendor-new code by top dir (files / lines), from `report/vendor-new-stats.txt`:

```
   29064    18237871  TOTAL
   16723    10217142  drivers/misc      (drivers/misc/mediatek = 340 MB of vendor core)
    7112     3365694  drivers/gpu       (Mali midgard DDK + mtk DRM glue + ion)
     886     1456005  drivers/input     (touch, fingerprint, keys; huion/goodix/synaptics)
     661      464097  sound/soc         (mt6660 / mt6765 AFE, oplus amplifiers)
     604      397333  arch/arm64        (dts, oplus board trees, Kconfig)
     567      966516  drivers/power     (bq25910, mt6370, gauge, oplus BMS)
```

The vendor also patched core, not just drivers: `block/bio-crypt-ctx.c`, `block/blk-crypto*`,
`block/ssg-iosched.c`, `block/uxio_first/`, `fs/proc/*`, `kernel/bpf/*`.
Config highlights: `CONFIG_PREEMPT=y`, `CONFIG_HZ=300`, `CONFIG_KSU=y` (ReSukiSU submodule +
`drivers/kernelsu`), `CONFIG_ARCH_MTK_PROJECT="k69v1_64_k419"`.

**Why "38 % already upstream" matters more than it looks:** this 4.19.325 base is
`4.19.325-cip135` plus MTK's own backports, so diffing against 5.15 finds 9,507 hunks whose
content 5.15 already has (identical post-image). A human porter burns the first two weeks
rediscovering that. `report/ledger.csv` lists each one per file.

---

## 3. The base question, answered by measurement

Instruction: *verify MT8365 vs MT6769 compatibility before choosing the Genio BSP.*
Result: **the hypothesis is false, and the BSP is unusable as this phone's base.**

| Fact | Evidence |
|---|---|
| MT8365 = **Genio 350**, 4 x Cortex-**A53** | mainline `arch/arm64/boot/dts/mediatek/mt8365.dtsi`: 4 CPUs, all `compatible = "arm,cortex-a53"` |
| MT6769 (this phone) = 2 x A75 + 6 x A55, Mali-G52 **Bifrost** | vendor `mt6765.dts` (8 x `arm,cortex-a53` at the P25/P35 baseline; G85 adds the A75 cluster) + MTK naming table |
| MT8370 = **Genio 510** is an **MT8188** part, not an MT6769 part | mainline `mt8370.dtsi` begins `#include "mt8188.dtsi"`; GPU `compatible = "mediatek,mt8370-mali", "arm,mali-valhall-jm"` (Valhall, not Bifrost); that file's own comment says the compatible override "is a clear indication of nodes not being, well, compatible!" |
| MT8365 does **not exist in 5.15 at all** | `v5.15.220`: no `clk-mt8365.c`, no `mt8365.dtsi`, no `sound/soc/mediatek/mt8365/`. First release with them: **v6.1** (clk) and **v6.4** (dtsi) |
| MT8365 display support is even newer | MTK DRM gained MT8365 for **Linux 6.15** (March 2025): the Genio line has no older display stack to borrow |
| MTK's own phone tree has no MT8365 either | `grep -rl mt8365` in this repo -> **0 hits**; `even_defconfig` offers `MACH_MT6739/6761/6765/6768/6771/6779/6781/6785/6833/6853/6873/6877/6885/6893/8173/8195` - no Genio part |
| IP overlap with the phone is negligible | phone DTS instantiates 404 compatibles, mainline `mt8365.dtsi` uses 77, **shared: 8** (generic ones: `syscon`, `arm,armv8`, `fixed-clock`, ...) |
| MTK Genio SDK is unreachable from here | `gitlab.com/mediatek/aiot/...` TLS blocked (as are kernel.org, go.googlesource.com, deb.debian.org, objects.githubusercontent.com); only GitHub + PyPI are reachable |

Per your decision rule ("otherwise use vanilla 5.15 as the upstream base and selectively
backport/reference the compatible MediaTek BSP components") -> **vanilla `v5.15.220` +
selective backport**, which is what this port sits on.

Free on 5.15 already: `drivers/clk/mediatek` MT6765 CGU (`clk-mt6765.c`, `-mm`, `-audio`,
`-cam`, `-img`, `-mipi0a`, `-vcodec`), MT6765 pinctrl, `mtk-pmic-wrap`, `drivers/soc/mediatek`
glue. Not there: mt6765 DRM (0 hits in `drivers/gpu/drm/mediatek` - 5.15 binds mt2701/mt2712/
mt8167/mt8173/mt8183 only), `mtk_iommu` mt6765, `mtk-sd`, cpufreq, thermal, AFE audio.

Best external reference for the device side: `gitlab.com/mtk-mainline/mt6768/linux` -
"Linux mainline fork with MT6768/MT6769Z patches" (Volla Phone 22). Same silicon family,
panel/regulator/touch work already done. (It lives on GitLab, which this sandbox cannot reach.)

---

## 4. What was ported, and how it was verified

`bin/portclassify.py` extracts the delta (base 4.19.325 -> vendor) and classifies **every
hunk** against the target tree:

```
ALREADY   9507   post-image already present in 5.15            -> dropped
PORTABLE  2959   pre-image found verbatim in 5.15              -> applied (2952)
NEAR      2886   pre-image found only after trimming context   -> left for a human
PARTIAL   1855   all added lines exist, ordering differs       -> left for a human
MANUAL    4152   pre-image not found (semantic conflict)       -> left for a human
plus: 911 files other-arch (skipped), 339 files with no counterpart in 5.15
```

Applied result: 1,036 files touched (+29,640 / -4,181).  After the build-driven repair pass, **743
files still carry ported content** (+42,291 / -2,453, incl. 74 transplanted vendor files) and the
series is 68 grouped commits (`patch-series/0001..0068`); every rolled-back hunk is accounted for
in `report/decisions.json`.

Verification (three independent passes; raw JSON in `report/`):

| check | result |
|---|---|
| post-image of every applied hunk present in ported tree | **2,952 / 2,959** (7 dropped: overlapping regions, listed in `verify.json`) |
| pre-image **unique** in pristine 5.15 -> zero misplacement risk | **2,911 / 2,959** |
| pre-image matched several sites (nearest-to-origin chosen, flagged) | **41** (e.g. `drivers/mmc/host/Kconfig` x23, `drivers/base/power/main.c` x3) |
| per-file line delta == sum of its hunks' deltas | **1,031 / 1,036** |
| series round-trip: `git am` of all 74 patches onto pristine `v5.15.220` reproduces the ported tree | **same git tree hash `0f5d980765dd9a1892a8e52c87f314afcc72f6c8 (tree; the *commit* is 616ddfa52)`** |
| inserted lines referencing APIs changed/removed before 5.15 | **16 hits over 29,640 lines**: `ion_*` x5 (`mtk_drm_gem.c`), `proc_create`/`PDE_DATA` x5 (`phy-mtk-tphy.c`), `strlcpy` x3, `kmap_atomic` x2, `mmap_sem` x1 (`mm/madvise.c`) |
| header-resolution proxy | 6,007 of 12,723 inserted identifiers do not resolve in `include/`; 640 are `MTK_*`/`oplus_*`, most others are locals/Makefile vars and **Android-only APIs** (`ANDROID_KABI_RESERVE`, `android_kabi`, `vma_get_anon_name`) -> see section 5 item 0 |

### Compile and link verification

A real arm64 build was then run against the ported tree, with a downloaded Android toolchain and
no source-tree compromises (the toolchain, the 64-bit bison/m4/flex/bc set and the libssl stub live
in the build workspace under `tools/`, together with `build.sh`/`env.sh`; no file in the kernel tree
was patched to fit the sandbox - see `KNOWN-ISSUES.md` item 5 for the exact package sources):

```
clang      Android (7917927, based on r437112) clang version 14.0.0 (https://android.googlesource.com/toolchain/llvm-project 8671348b81b95fc603505dfc881b45103bee1731)
linker     LLD 14.0.0 (compatible with GNU linkers)
host cc    gcc (Debian 12.2.0-14+deb12u1) 12.2.0
dtc        Version: DTC 1.6.0-g183df9e9

make ARCH=arm64 LLVM=1 HOSTCC=gcc -k -j2 Image      # 24 passes to get here
```

| gate | result |
|---|---|
| `make Image` (device config: `defconfig` + `dev/even.fragment` + `dev/even-hardware.fragment`) | **0 `error:` lines**; `arch/arm64/boot/Image` 26,963,976 B (sha256 `f0235eae6f1f…` at 26,894,344 B before the clock enablement, `bf438d69be7a…` for the pre-device `defconfig` build), `vmlinux` 37,356,024 B. `report/build.json` is generated from `logs/build-30.log` by `bin/buildreport.py`, so the numbers there are the current tree's. |
| `make dtbs` | **0 errors**; 529 arm64 DTBs, incl. `mt6768.dtb` (this board) and `mt6779-evb.dtb` |
| `make modules` | all module translation units compile (6,862 objects); a residual 5-error media/bluetooth cluster was closed by the last 3 holds and re-verified clean per-directory; **no `.ko` link is claimed** |
| objects compiled across the tree | 6,860 |
| `structcheck.py` - structural balance of every touched file | 655 files checked, **0 imbalances** |
| `dupdef.py` - duplicate definitions the port would have introduced | **0** |
| `gluecheck.py` - every `obj-`/`source` reference resolves | **0 unconditional dangling**; 47 `obj-$(CONFIG_*)` lines aim at vendor dirs that were never transplanted, all config-off hence inert |
| `portclassify.py verify` (vs the *initial* apply) | 1,508 `POST_NOT_FOUND` = precisely the hunks rolled back afterwards (66 reasoned entries in `report/decisions.json`), not misapplications |
| series round-trip | `git am` of the 74 patches onto pristine `v5.15.220` yields tree **`0f5d980765dd9a1892a8e52c87f314afcc72f6c8`** - identical to the tree that was compiled and linked. Assert the applied count as well as the hash: an empty glob leaves `git am` succeeding with nothing applied |
| device code really linked in | 687 `mtk_*`/`mt676x`/`pmic_wrap`/`cmdq` symbols in `vmlinux`, incl. `mtk_smi_larb_probe`, `mtk_iommu_probe` |

The failure *pattern* is the finding worth stating: once the mechanical apply was done, every
remaining compiler diagnostic came from a hunk that was textually exact but semantically 4.19-shaped
- helpers 5.15 deleted, Kbuild object lists that were renamed, `EXPORT_SYMBOL` pairs split across
files, and callees whose signature gained a parameter.  Each cluster was resolved by holding the
*upstream* file at base rather than by editing vendor code until it compiled: the latter produces a
tree that builds while silently diverging from both bases, which is the worst possible deliverable.
1,016 files received hunks; **740 still carry ported content** (+42,200 / -2,433, including 71
transplanted vendor files); 27 (DRM) + 79 (generic `=m` subsystems) + 3 (media/bluetooth) + 15
(`net/` .c files, plus `include/net/dst.h`/`dst_ops.h`) + a dozen others were rolled back, each with a written reason.

Two config facts cost the most passes, so they are recorded here rather than in a footnote:
`CONFIG_ACPI=n` (the device firmware is DT-only, and leaving ACPI on drags `EFI_ESRT` -> `PKCS7`
-> `SYSTEM_DATA_VERIFICATION`, which makes `olddefconfig` silently re-enable
`SYSTEM_TRUSTED_KEYRING`), and `CONFIG_SYSTEM_TRUSTED_KEYS=""` - `certs/system_keyring.c` and
`crypto/asymmetric_keys/asymmetric_type.c:492` reference `restrict_link_by_builtin_trusted`
*unguarded*, so `SYSTEM_TRUSTED_KEYRING=y` with an empty list is the only self-consistent setting.
Because this container has no libssl-dev, `scripts/extract-cert` (a build *artifact*) was replaced
by a stand-in implementing only the empty-key-list case, which exits non-zero for any real key file;
on a normal machine that step is simply `apt install libssl-dev`.  Never ship the stand-in.

What is **not** claimed: nothing was executed.  No boot, no display, no touch, no modem, no
`even` DTB - see `KNOWN-ISSUES.md` for the hard limits and `FEATURE-PARITY.md` for the
per-subsystem distance to a working phone kernel.

---

## 5. Remaining work, ranked

0. **Consider `android13-5.15` (AOSP common) instead of vanilla stable as the base.**
   ~640 unresolved symbols are Android-only (`ANDROID_KABI_RESERVE`, `android_kabi`,
   `vma_get_anon_name`): they exist on AOSP common, not on stable. Changing the base removes
   that whole class of work (and gives you GKI symbol lists + KernelSU on GKI for free).
1. **4,020 manual hunks in 1,244 device-relevant files** (`report/ledger.csv`, `status=MANUAL`).
   Heaviest: `fs` (1,384 left), `include` (1,102), `kernel` (938), `net` (721), `mm` (510),
   `drivers/gpu/drm` (439), `drivers/media/platform` (299), `security` (216),
   `drivers/scsi/ufs` (186). Mostly Android ABI/perf patches whose neighbours moved (binder,
   oom, zram, bfq, ksm, dm-verity, f2fs/ext4). Estimate **6-10 engineer-weeks**.
2. **339 files with no counterpart in 5.15** (`NO_TARGET`) -> decision list, not work:
   `drivers/staging/android/ion` (gone 5.18), `lib/lz4*` replacements, KASAN reorg, etc.
3. **Vendor transplant: 22,950 files / 16.0 M lines.** Measured hazard census (uses / files):

   | hazard | uses | files | 5.15 status |
   |---|---|---|---|
   | `set_fs`/`get_fs`/`KERNEL_DS` | 1,097 | 125 | **removed in 5.11** - vendor `copy_to_user` guards get deleted, not adapted |
   | Ion (`ion_*`, `<linux/ion.h>`) | 1,009 | 231 | present in 5.15, removed 5.18; MTK `mtk_memalloc` glue relies on 4.19 Ion internals |
   | `create_proc_entry`/`PDE_DATA` | 777 | 241 | `proc_ops` required since 5.6 - mechanical |
   | `struct timespec`/`current_kernel_time` | 583 | 229 | removed 5.6 (y2038 rework) |
   | `strlcpy`/`strlcat` | 541 | 232 | fine on 5.15, gone in 6.x - fix now |
   | `setup_timer`/`init_timer` | 254 | 151 | `timer_setup()` / `from_timer()` |
   | `kmap`/`kmap_atomic` | 234 | 89 | `kmap_local_page()` since 5.11 |
   | `access_ok(VERIFY_*)` | 149 | 78 | signature changed in 5.0 |
   | `get_user_pages*` | 142 | 56 | long-term pins -> `pin_user_pages` |
   | `send_sig_info` / `dma_*_attrs` / `init_MUTEX` | 63 | 26 | assorted |

   Order that actually pays off (first pixel first): **pwrap+PMIC -> clk/pinctrl ->
   SMI/IOMMU -> cmdq + DRM + DSI panel -> Mali DDK (r32p0 or newer supports 5.15; the in-tree
   r19p0-era DDK does not) -> input/touch -> charging/battery -> ASoC -> connac wifi/bt ->
   CCCI modem -> mtkcam** (the 6-month item; consider dropping camera or moving to a
   libcamera/ISP-less pipeline instead of transplanting 3.4 M lines of `drivers/gpu`+mtkcam).
4. **Device tree port**: re-express 404 compatibles (MTK 4.19 `mediatek,mt6765-*` strings bind
   to no 5.15 driver), plus the OPlus `oplus6769_2*` board trees, LK/UEFI bootconfig, DTBO
   layout, AVB signing, and the `disp_pwr`/`vdu3x`/`od`/`pvl` MDP extensions mainline never saw.
5. **KernelSU**: don't port `drivers/kernelsu` from 4.19 - on 5.15 use KernelSU >= v0.7
   (GKI-compatible) instead.

Realistic total for a 5.15 kernel that boots this phone with display/audio/touch/charging:
**2-3 engineer-months minimum, 6-9 for feature parity** (camera + modem are the tail).

---

## 6. Device tree, DTBO and flash images (the round after the C-level port)

The C port produced a kernel that compiles; a *phone* kernel additionally needs the board's
device tree, the vendor image packaging and the partition geometry.  Measured results:

| item | result |
|---|---|
| `even` base DTB | `arch/arm64/boot/dts/mediatek/mt6768.dts` - from `even_defconfig:463` `CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE=y` + `..._NAMES="mediatek/mt6768"` |
| DTBO set | `/plugin/` overlays `oplus6769_2167A`, `oplus6769_216AF`, `oplus6768_20761`, `oplus6769_226AF`, `oplus6769_226BE` (`CONFIG_MTK_DTBO_FEATURE=y`) |
| closure | 55 files: 49 absent from 5.15 (transplanted), 6 colliding with mainline files, 0 missing dt-binding headers, 1 kbuild-generated include |
| fixes required to compile | dtc `-I` paths (`arch/$(SRCARCH)/boot/dts{,/include}`, `$(objtree)/include`) + `DTS_CPPFLAGS` hook; shadow copy `mt6358-mt6768.dtsi` (mainline's `mt6358.dtsi` lacks the regulator labels the board references, and 3 other boards include it); 6 vendor `CONFIG_*` DT guards re-materialized as `-D` from `even_defconfig` |
| built | `mt6768.dtb` 122 474 B (629 nodes, 2 538 properties, 413 `compatible`), 5 `dtbo` images, `dtbo.img` 371 235 B via the vendor's own `scripts/mkdtboimg.py` (page 4096, ids 0-4) |
| boot image | `Image.gz-dtb` 10 696 897 B -> `boot.img` 10 823 680 B, header v2, page 2048, kernel @ page 1, dtb section @ page 5225, fits 32 MiB (32 %); round-trip verified by `mkbootimg.py verify` |
| driver reality check | 34 of 417 compatibles bind to a 5.15 driver; 383 orphan (`report/dtsport.json`) - hence the ranked driver list in `MATURITY.md` |
| audit | 68 subsystems measured in `report/subsystem-audit.md`; 15 847 `.c/.h` files sit in subsystems with zero ported content (Mali DDK 3 328, connectivity 2 411, imgsensor 1 198, MSDK video 1 066, OPLUS charging 381, pmic 231, eccci 177, cmdq 112, m4u 75, pmic_wrap 7) |

Two upstream facts decided the approach, and both are measurement rather than opinion: no repo of
`Badmaneers` carries a 5.x base for this device (`apex-v2` and `saturn@rui4-main` are both
4.19.325-cip135-st19), so their value here is the *stock DTB/boot layout and device configs*, not a
5.15 kernel to adopt; and MT8365 (Genio 350) is not this SoC - its `mt8365.dtsi` is A53-only and
5.15 has no MT8365 clock/pinctrl/sound driver at all (`report/soccompare.json`).

## 7. Files in this directory

```
README.md                     how to reproduce every number here
MIGRATION-5.15.md             this report
MATURITY.md                   source-complete / build-complete / flash-ready / boot / function
KNOWN-ISSUES.md               hard limits, dropped content, flash-image caveats
FEATURE-PARITY.md             per-subsystem "what even needs vs what 5.15 has"
dev/even.fragment             product kconfig fragment: appended DTB + DTBO packaging
bin/portclassify.py           delta extraction, hunk classification, apply, verify
bin/dtsport.py                device tree closure transplant + dt-binding/driver audit
bin/bootpack.py               port the vendor Image.gz-dtb / dtbo.img kbuild machinery
bin/mkbootimg.py              Android boot image pack / unpack / verify (header v0-v3)
bin/subsysaudit.py            per-subsystem audit of the port against the working 4.19 tree
bin/buildreport.py            turns a make log into report/build.json (counts, sizes, sha)
bin/mkreport.py               renders report/tables.md from the artifacts
bin/apiaudit.py               hazard census over the vendor-new file set
bin/portedcheck.py            API-regression + header-resolution gate for the ported diff
bin/soccompare.py             MT8365/MT6769 IP-overlap measurement
bin/mkcommits.sh              grouped commit series + format-patch
bin/mkreport.py               renders report/tables.md from the artifacts
patch-series/                 commit series + cover letter, `git format-patch` output; apply
                              on v5.15.220 (`0[0-9][0-9][0-9]-*.eml` - the 4-digit glob matters)
report/tables.md              all tables, machine-generated
report/ledger.csv             per-file classification (5,823 rows)
report/summary.json           subsystem rollup
report/verify.json            post-apply verification + flagged hunks
report/portedcheck.json       applied-subset API audit
report/hazard.json            vendor transplant hazard census
report/soccompare.json        SoC overlap measurement
report/subsystem-audit.md     68 subsystems measured (generated, not hand-written)
report/dtsport.json           device tree closure, reconcile decisions, 417-compat binding audit
report/bootpack-check.json    packaging-port anchor check (dry run)
report/build.json             build gate: rc per target, error counts, Image size/sha, .ko count
report/build-evidence.md      the build narrative, including the fix rounds
report/vendor-new-stats.txt   vendor-new files/lines per top dir
report/deleted-in-vendor.txt  95 files the vendor tree dropped
```
