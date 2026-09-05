# Feature parity map: what `even` needs, and where the 5.15 tree stands

Legend — **built**: compiled in the verification build; **base**: 5.15 code only, vendor delta
held out; **partial**: some vendor content carried, more needed; **missing**: vendor-new code not
in the 5.15 Kbuild at all.

Machine-generated counts for these rows are in `report/subsystem-audit.md`; this table is the
judgement layer (what state means for a device build, and the effort class).

| subsystem (device role) | state | what the tree has | what is still needed | effort |
|---|---|---|---|---|
| SoC clocks MT6765/6768/6779 (`COMMON_CLK_MT67xx=y`) | ✔ for this board | 5.15's own mt6765/mt6779 drivers **plus mt6768**, which mainline 5.15 has no driver for: `clk-mt6768.c` + MTCMOS `clk-mt6768-pg.c` + `clk-mtk-v1` ported from the BSP (patch 0074), enabled by `COMMON_CLK_MT6768` and audited against the board DTB (`report/clkaudit.json`: 234 refs, 234 resolve, 0 unresolved) | `peri_clks[]` is the vendor's "
  1-entry stub (0 refs from this DTB); the 22 refs once listed here as \"pointing at unported "
  subsystems\" (smi/m4u/cmdq) are in fact served - they are `SCP_SYS_*` cells of the MTCMOS "
  provider in `clk-mt6768-pg.c`, see KNOWN-ISSUES 8.7; per-clock *rates* still unverified on "
  hardware | S |
| pinctrl MTK | ✔ | common v2 core **plus this board's own tables**: `pinctrl-mt6768.c` + `pinctrl-mtk-mt6768.h` ported behind `MACH_MT6768`, compiles, and its `of_match` string is the transplanted DTB's `mediatek,mt6768-pinctrl` | vendor-only `.race_free_access` and eint `.pm` dropped (RMW-shared semantics not reproduced); no upstream `pinconf` binding checks | S |
| pmic wrap / MT6358-6392 PMIC, `MTK_PMIC_WRAP=y` | **built** | 5.15 `mtk-pmic-wrap` + `mtk-sysirq`/`mtk-eint` compiled | PMIC child regulators + `even` PMIC variant selection | M |
| power domains / SCP | **partial** | `drivers/soc/mediatek/` builds (7 objs), vendor `mtk-scpsys-ext.c` + `scpsys-ext.h` transplanted | scp offflow, DVFSRC, `devapc`/`devmpu` (transplanted, not selected) | M |
| SMI + MTK IOMMU | **built** | `drivers/memory` + `drivers/iommu/` compile; `mtk_smi_larb_probe`, `mtk_iommu_probe` present in `vmlinux` | `mtk-smi-debug`, cross-domain MM/MFC latency tuning | M |
| CMDQ | **partial** | 5.15 `mtk-cmdq-*` mailbox code; vendor `cmdq_pkt_create` shape not carried | 4.19→5.15 `cmdq_pkt` GCE opcode API rework for DSI/DDP | **L** |
| Display: DDP/DSI/panel (the screen) | **base** (held) | upstream `DRM_MEDIATEK=m` builds clean after the whole `drivers/gpu/drm/` cluster was rolled back | the vendor `mtk_panel_ext`/`DDPINFO`/`PLANE_PROP_*` extension set re-expressed on 5.15 DRM, DSI video-mode/burst, `mtk_drm_gem`/plane props, panel + touch IC backlight | **XL** |
| GPU Mali-G52 Bifrost | **missing** | nothing (vendor-new r32p0 DDK, out of tree) | import DDK for 5.15 + `mali_kbase` device nodes/DTS, GPL 5.15 compat | **XL** |
| Input: touchscreen (`FT5x06`/Goodix/atmel-mxt), keys, haptics | **partial** | 5.15 mainline drivers build (`CONFIG_TOUCHSCREEN_GOODIX=m` etc.); vendor `oplus_secure_driver`, `mediatek/tp_tcl` missing | `even` touch IC binding in DTS + vendor `hid_update`/fingerprint glue | M |
| Audio: ASoC machine + AW87519/SIA81xx amps | **partial** | `sound/soc/mediatek/` compiles (mt8183/mt6779-ish machine set); amp dirs absent (`aw87519/` dangling, config-off) | mt6765-mt6359 machine driver for `even`, DLDEQ/HAPE/AGC (vendor-new, needs `proc_ops`, no `set_fs`) | **L** |
| Charging / battery (BQ2597x, FG, `MTK_SGQ`), `drivers/power/charging` | **missing** | not in 5.15 Kbuild (5.15 has `BQ27XXX`-style mainline + `POWER_RESET`) | vendor charging stack transplant onto 5.15 power-supply + `typec` APIs; 567 lines of vendor delta + 967 k lines vendor-new | **L** |
| Wi-Fi/BT (connac2 / `wlan_drv_gen4m`) | **missing** | nothing | vendor connac + cfg80211 5.15 rework (`nl80211` vendor edits were rolled back) | **XL** |
| Modem / CCCI / RIL / T-infra | **missing** | nothing (net-side edits rolled back) | CCCI core on 5.15 `tty`/`skb` APIs, `ccci`/`atf_daemon` glue, 4.19 `set_fs`/`mm_segment_t` removal (1 097 hits) | **XL** |
| Camera (`mtkcam`, IMGTOP, sensor pipeline) | **missing** | `drivers/media` vendor edits rolled back to base (the `VB2_MAX_FRAME != VIDEO_MAX_FRAME` static assert) | 16.7 k-line vendor delta + 10.2 M lines vendor-new; V4L2 5.15 `vb2` rework | **XL** |
| Thermal (held at base) | **base** | 5.15 thermal core + `mtk-soc-thermal` (built) | `notify_mode` plumbing, `mtk_get_therm_zone_device`, boarding-mode policies | M |
| Low-memory killer / ULMK, `REAP_MEMORY_ON_SIGKILL` | **base** (dropped) | 5.15 OOM + `MMAP_MIN_VM`/`mmd`-free | decide: mainline `lmk`/PSI + `zap_pid_not_execute` instead of re-adding 4.19 ULMK hooks | M (or drop) |
| `overlayfs`/`fuse` vendor patches (APEX/odm mounts) | **base** | 5.15 mainline overlayfs + fuse build clean | only needed if the vendor userspace relies on the extra ioctls | S |
| KernelSU (root, `obj-$(CONFIG_KSU)`) | **missing** (dangling glue) | — | KernelSU ≥ v0.7 on GKI-style 5.15 (different hook set than 4.19) | M |
| AEE / kdbg / DPST / raws / sec-boot keymaster glue | **missing** | vendor `aee.h`, `mboot_params.h`, `usb_boost.h` headers transplanted for compile coverage only | decide whether to keep; mostly needs `proc_ops`/`pstore`/`remoteproc` 5.15 rework | L |
| Verified boot, DTBO, vendor_boot | **missing** | out of kernel scope | `mkbootimg`/`fdtoverlay`/`avbtool` flow + `even` `dtbo.img` build | M |
| GKI/`SYSTEM_TRUSTED_KEYS` chain, dm-verity | **partial** | cert machinery intact, empty trusted-key list | real device key + verity root hashes into the DT/`fstab` | S |

## Ordering that actually works

1. **pwrap/PMIC → clk/pinctrl → SMI/IOMMU** (largely already built here) so the kernel probes
   its regulators and clocks on a real board.
2. **cmdq + DRM/DSI + panel** (needs the vendor display extension set re-expressed) so there is a
   screen — until then bring-up is via `earlycon`/`ramoops`.
3. **input + charging** for a usable phone.
4. **Mali DDK**, then **ASoC**, then **connac**, then **CCCI**, then **mtkcam** (each of those is
   itself a multi-week transplant measured in vendor-new lines, not hunks).
5. DT/DTBO/AVB packaging in parallel from step 2.

The classification numbers bound the work: of 5 823 files the vendor changed vs vanilla 4.19.325,
9 507 candidate hunks were already upstream (38.6 %), 2 959 were mechanically portable and are
applied, and **4 152 MANUAL + 2 886 NEAR + 1 855 PARTIAL hunks remain for human hands**, plus
339 files with no 5.15 target at all.  Prior estimate stands: 2–3 engineer-months to a device
that boots with display, touch and charging; 6–9 months to functional parity.

| Device tree (`even` board + overlays) | **built** | `mt6768.dtb` 122,474 B (product config, forced rebuild; identical node set to the reference decompile - the 89,053 B figure I previously quoted here was a failed-experiment artifact, see KNOWN-ISSUES 7.1) + 5 `dtbo` overlays compile from the transplanted 55-file closure; binding headers from 5.15 except 3 vendor-only ones | 383 of 417 compatibles have no driver; binding rewrites as drivers land (SMI/CMDQ/GCE/pwrap child nodes) | M |
| Image packaging (`Image.gz-dtb`, `dtbo.img`, `boot.img`) | **built, unflashed** | vendor `scripts/mkdtboimg.py` + `BUILD_ARM64_APPENDED_DTB_IMAGE` machinery ported; `bin/mkbootimg.py` emits header-v2 `boot.img` with the device geometry, round-trip verified | ramdisk, AVB with real keys, dtbo board-id/rev mapping, `super`/`vbmeta` assembly | M |

## Where this table came from

Every "what the tree has" cell was derived from `report/` artifacts (ledger + build log +
dtsport audit) rather than memory, and every "what is still needed" cell names the vendor path
and its 4.19 file count.  The effort classes are engineering estimates for a *single engineer
familiar with MTK BSPs*; they are not measurements.

### PMIC / regulator / RTC (this round)

| function | 4.19 vendor tree | 5.15 port, before | 5.15 port, now |
|---|---|---|---|
| PMIC wrapper | `drivers/misc/mediatek/pmic_wrap/` (`of_find_compatible_node("mediatek,pwraph")`, static base) | no mt6768 entry in `mtk-pmic-wrap.c`; probe needs a matching first child | `pwrap_mt6768` + `mediatek,mt6768-pwrap`; child alias `mediatek,mt6358-pmic` |
| PMIC MFD | `drivers/misc/mediatek/pmic/` `upmu` stack | `mt6397-core.c` present, no match for this DT's PMIC node name | matches `mediatek,mt6358-pmic`, creates the 4 MT6358 cells |
| regulators | `mt6358-regulator` via upmu | `REGULATOR_MT6358` off, nothing to bind to | `=y`, binds through the MFD cell; static register tables (no DT `reg` encoding needed for MT6358) |
| RTC | `mt6358-rtc` | `RTC_DRV_MT6397` unconfigurable (depends on the MFD) | `=y` and matched to `mt6358-rtc` |
| battery/charger ADC | `mt6358-auxadc` + `upmu` | driver absent from the match list | `MEDIATEK_MT6577_AUXADC` compiled but **not bound** (needs mt6768/mt6358 auxadc evidence) |
| PMIC keys | `mt-pmic` + `mtk-pmic-keys` | no `mtk-pmic-keys.c` in 5.15 base | still absent: power/home key unbound |
| touchscreen via PMIC | `mtk_ts_pmic` | no mainline equivalent | unchanged, vendor-only |

Runtime status for every row above is unverified; the port has no board. The honest
parity claim for the PMIC block is "the drivers now exist for this DTB and the build links",
not "power management works".

### Boot-path additions (this round)

| function | 4.19 vendor tree | 5.15 port, before | 5.15 port, now |
|---|---|---|---|
| SoC AUXADC (IIO) | `drivers/iio/adc/mt6577_auxadc.c` with an mt6768 entry | 5.15's list stops at mt6765 -> no bind | aliased to `mt6765_compat` (vendor's own choice); `MEDIATEK_MT6577_AUXADC=y` |
| PMIC AUXADC (batadc/bat_temp/chip_temp/vcdt) | `CONFIG_MT635X_AUXADC=y` -> `mt635x-auxadc_v1.c` | nothing in mainline matches `mediatek,mt6358-auxadc`; no MFD cell | vendor's v1 driver transplanted + `mt635x-auxadc` cell added; channels exposed, calibration hooks not installed (KNOWN-ISSUES 8.2) |
| PMIC supply phandles (`vmmc-supply` etc.) | regulator driver reads its own DT children | `mt6358-regulator.c` never set `config.of_node` -> every consumer deferring | `of_regulator_match()` over the driver's own names; 41/42 children match |
| eMMC (root device) | vendor `MMC_MTK_PRO` on `msdc@` nodes | no mt6768 entry in `mtk-sd.c` | `mediatek,mt6768-mmc` -> `mt6779_compat` (fields equal to vendor's); `MMC_MTK=y`, CQ off (no `supports-cqe`), clocks/pinctrl verified against the node |
| I2C | legacy `mediatek,i2c` nodes | - | **unchanged**: the DTB's nodes are not adapters, so this is a binding decision (KNOWN-ISSUES 8.4), not a driver alias |
| display / touch / audio / connectivity / charging | MSDK, `mtk_ts_pmic`, ASoC machine, connac, `drivers/power/mediatek` | untouched | untouched - still the per-subsystem transplants in report/subsystem-audit.md |

Parity is still "source + build" only. A flash-ready claim additionally requires the DTB
packaging defect (KNOWN-ISSUES 8.1) to be resolved, because the appended DTB is currently not
the DTB `make dtbs` produces.

## Boot path this round (0076-0077)

| Item | Vendor 4.19.325 | This 5.15 port | Evidence / gap |
|---|---|---|---|
| SoC AUXADC | `mt6577_auxadc.c` with mt6768 alias | alias added to the same driver | DT `auxadc@11001000` `"mediatek,mt6768-auxadc"`; built into `mt6577_auxadc.o` (`strings`) |
| PMIC ADC (Vbat/BAT_TEMP/VCDT/chip temp) | `pmic/mt6358/v1/pmic_auxadc.c` + `mt635x-auxadc_v1.c` | BSP driver variant imported, MFD cell added, `pmic_auxadc_chip_init()` deliberately not ported | channels expose mV; **Vbat uncalibrated, BAT_TEMP untrustworthy** until a charger registers `auxadc_set_{convert,cali}_fn()` (KNOWN-ISSUES 8.2) |
| PMIC regulators | same driver + vendor of_node use | `of_regulator_match()` added so `*-supply` phandles resolve | 41 of 42 DT children match a descriptor; `ldo_va09` has none (8.3) |
| eMMC (root device) | `MMC_MTK_PRO` proprietary host on `msdc@` | mainline `mtk-sd` host on `mmc@`, `MMC_MTK_PRO` excluded by Kconfig | HS200/HS400 capable per DT; **no CQ** - mainline wants `supports-cqe`, absent here (8.5) |
| I2C | vendor `i2c-mt65xx` + BSP-extended binding | **not enabled** | board DT `i2cN` nodes are legacy hardware descriptions, not adapters (8.4); needs a binding decision |
| Device tree in the image | built once, per-board flags always in scope | `DTS_CPPFLAGS` now shared by both build paths | packaged DTB byte-identical to `make dtbs` output, 413 compatible nodes; audits read that file (8.1 resolved) |

## Display/video round: SMI substrate (0078)

| item | 4.19.325 vendor tree (stock `even`) | 5.15 port after 0078 | parity |
|---|---|---|---|
| SMI device model | `drivers/memory/mtk-smi.c` under `CONFIG_MTK_SMI_EXT=y` (`even_defconfig:1810`), 6 devices from `mediatek,smi-id` | `drivers/memory/mtk-smi-mt6768.c`, `CONFIG_MTK_SMI_MT6768=y`, same six DT nodes | parity for clock/keep semantics |
| clock API | `mtk_smi_clk_enable/disable()`, `mtk_smi_dev_get()`, `mtk_smi_conf_set()` exported (GPL) | same four names and signatures, exported, `struct mtk_smi_dev` field-for-field | parity |
| client wrapper | `smi_bus_prepare_enable()/smi_bus_disable_unprepare()/smi_get_dev_num()` from `drivers/misc/mediatek/smi/smi_drv.c` | same three, MT6885 sub-common expansion and `smi_clk_record()` tracing omitted | parity for MT6768's path |
| BWC / scenarios / mmdvfs-PMQOS / emi-BWL / sysram / mmprofile / sspm / debugfs | present in `smi_drv.c` (1,548 lines) and `mt6768/smi_conf.h` (230 lines) | not ported; `mtk_smi_conf_set()` inert by construction | **gap, written up (KNOWN-ISSUES 9.1)** |
| init-time enable + `pg_callbacks` re-enable | `smi_register()` (smi_drv.c:1330-1393) | not ported; impossible against this DT without adding the `mmsys_config` phandle property | **gap, written up (KNOWN-ISSUES 9.2, 9.3)** |
| M4U / `mediatek,m4u` binding | `MTK_M4U=y` (`even_defconfig:1740`) with `IOMMU_IOVA=y` (`:4462`) | landed in 0080, see the M4U section below; `mediatek,m4u` is `ENABLED` in the bind audit | parity for the engine, gaps in tracing/compat |
| mainline alternatives | n/a | `CONFIG_MTK_SMI` (mainline mtk-smi.c) and `CONFIG_MTK_IOMMU` are compiled in this tree but bind zero nodes of this DTB | deliberately not used: would need DT surgery |

Also new in this round, in the tooling column rather than the feature column: `bin/hwenable.py`
now splits DTB `compatible` properties on NUL, which is how the kernel matches them. That raised
the audit's counted bindings from 22 to 33 with the DTB unchanged, and it is the reason the SMI
larbs could be shown as bound rather than driverless.

### M4U <-> ION decision (audit, before porting)

| question | measured answer | source |
|---|---|---|
| Does vendor M4U itself need `MTK_ION`? | No. Its only ION code is `m4u_test_ion()` under `#ifdef CONFIG_M4U_TEST_ION`; that symbol exists in no Kconfig and in no defconfig, so stock builds M4U with zero ION code. `mt6768/` has 0 ion/dma_buf references | `m4u/2.0/m4u_debug.c:335-402`, `even_defconfig` |
| Can M4U work with an allocator at all removed? | It already is allocator-agnostic: `m4u_alloc_mva(client, port, va, sg_table, size, prot, flags, *pMva)` takes a VA (M4U builds the sgt with `vmalloc_to_page`/`follow_pte`) or the caller's `sg_table` (`M4U_FLAGS_SG_READY`). No fd, no `ion_handle` | `m4u/2.0/m4u.c:694,603,721` |
| Can 5.15 dma-buf/heaps serve the clients? | Yes for allocation + mapping: `dma_buf_get/attach/map_attachment` yields exactly the `sg_table` M4U wants, and `dma_buf_vmap` replaces `ion_map_kernel`. No for MTK heap extensions (`ION_CMD_MULTIMEDIA` booking, `ion_mm_data`, LOG/DECOUPLE/GAINCONTROL) and no for the `/dev/ion` ABI | `report/m4u-ion-audit.md` sections 3-4 |
| Chosen path | Port M4U verbatim minus ION (its own `#ifdef` does the excluding), `MTK_M4U` depending on `MTK_SMI_EXT` instead of `MTK_ION`; no ION transplant, no speculative `CONFIG_DMABUF_HEAPS` | `report/m4u-ion-audit.md` section 5 |
| Consequence the SMI port had to absorb | `CONFIG_MTK_SMI_MT6768` renamed to `CONFIG_MTK_SMI_EXT`, because M4U's clock keeps are `#ifdef CONFIG_MTK_SMI_EXT` and `smi_public.h`'s `#else` turns `smi_bus_prepare_enable()` into `((void)0)` - a wrong symbol name would compile an M4U with no clock handling, silently | `m4u_hw.c:19,1109,1124`, `smi/smi_public.h:31` |
## Display/video round: M4U v2.0 (0080, build-36)

| item | 4.19.325 vendor tree (stock `even`) | 5.15 port after 0080 | parity |
|---|---|---|---|
| driver body | `drivers/misc/mediatek/m4u/{2.0,mt6768}`, `MTK_M4U=y` | same 16 files / 10,896 lines, built `obj-y`; six 5.15 API adaptations annotated in-file | parity |
| allocator-facing API | `m4u_alloc_mva(client, port, va, sg_table, size, prot, flags, *pMva)` | identical, still allocator-agnostic (`M4U_FLAGS_SG_READY` path intact, `m4u.c:721`) | parity |
| larb clock keeps | `smi_bus_prepare_enable/disable_unprepare` under `CONFIG_MTK_SMI_EXT` | same calls into `drivers/memory/mtk-smi-mt6768.c`; symbols verified in `vmlinux` | parity |
| DT binding | `mediatek,m4u` plus `m4u_reg_init()`'s own `smi_common`/`smi_larb0..4` lookups | same strings, all present in the packaged `.dtb`; bind audit 33->34 bound, 24->25 enabled, `mediatek,m4u` `NO_DRIVER`->`ENABLED` | parity, DT untouched |
| `/proc/m4u`, 9 `/proc/m4u_dbg/*` nodes, debugfs `m4u` tree | `file_operations` | same nodes and ioctls through `struct proc_ops` (11.1) | parity |
| suspend/resume | platform `.suspend/.resume` plus `dev_pm_ops` | `dev_pm_ops` path only (the platform fields are gone in 5.15); same `m4u_reg_backup`/`m4u_reg_restore` | parity |
| mmprofile trace events | `CONFIG_MMPROFILE=y` (`:1712`), 6 M4U events emitted | compiled out via the vendor header's `!CONFIG_MMPROFILE` no-ops; no `mmp/src` | **not at parity** (11.2) |
| 32-bit compat ioctls | 4 commands translated with `compat_alloc_user_space()` | `NULL` handler: this base has no `fs/compat.c` | **not at parity** (11.3) |
| TEE / secure video+camera path, L2 | behind `M4U_TEE_SERVICE_ENABLE` (Trustonic + `MTK_TEE_GP_SUPPORT` + SEC_VIDEO_PATH/CAM_SECURITY) | not built, as in any config without those symbols | not attempted |
| ION bridge / multimedia heaps | `MTK_ION=y` (`:4363`) with MTK's extended ION for the clients | not ported: M4U needs no ION (audit), no client asks yet; `# CONFIG_DMABUF_HEAPS is not set` | documented, deferred (10, 11.7) |
| user-PTE dump in two error paths | arm64 `show_pte()` | failing level reported by `m4u_user_v2p()`, raw pte value not | minor gap (11.4) |
| `m4u_hw.c:1723` port-attribute test | `&&` where a bit test was meant, warning included | carried verbatim, deliberately not fixed | parity by design (11.5) |

Measured: `objects 7372 -> 7377`, `Image 26,966,024 -> 27,035,656` (+69,632 B), `Image.gz-dtb
11,141,946`, 0 errors and no new warning other than the inherited vendor line, `mt6768.dtb` sha
`34a7e6b5...85a11cd` unchanged, `boot.img` repacked at 11,268,096 B with its dtb section byte-identical
to the build. Flash/boot/function stay no: nothing on the device opens M4U yet.
