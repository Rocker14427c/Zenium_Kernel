# Feature parity map: what `even` needs, and where the 5.15 tree stands

Legend — **built**: compiled in the verification build; **base**: 5.15 code only, vendor delta
held out; **partial**: some vendor content carried, more needed; **missing**: vendor-new code not
in the 5.15 Kbuild at all.

Machine-generated counts for these rows are in `report/subsystem-audit.md`; this table is the
judgement layer (what state means for a device build, and the effort class).

| subsystem (device role) | state | what the tree has | what is still needed | effort |
|---|---|---|---|---|
| SoC clocks MT6765/6768/6779 (`COMMON_CLK_MT67xx=y`) | ✔ for this board | 5.15's own mt6765/mt6779 drivers **plus mt6768**, which mainline 5.15 has no driver for: `clk-mt6768.c` + MTCMOS `clk-mt6768-pg.c` + `clk-mtk-v1` ported from the BSP (patch 0074), enabled by `COMMON_CLK_MT6768` and audited against the board DTB (`report/clkaudit.json`: 231 refs, 209 resolve) | `peri_clks[]` is the vendor's 1-entry stub (0 refs from this DTB); 22 refs point at subsystems not yet ported (smi/m4u/cmdq); per-clock *rates* still unverified on hardware | S |
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
