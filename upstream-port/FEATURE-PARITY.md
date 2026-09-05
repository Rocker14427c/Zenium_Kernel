# Feature parity map: what `even` needs, and where the 5.15 tree stands

Legend — **built**: compiled in the verification build; **base**: 5.15 code only, vendor delta
held out; **partial**: some vendor content carried, more needed; **missing**: vendor-new code not
in the 5.15 Kbuild at all.

| subsystem (device role) | state | what the tree has | what is still needed | effort |
|---|---|---|---|---|
| SoC clocks MT6765/6768/6779 (`COMMON_CLK_MT67xx=y`) | **built** | vendor clk drivers carried and compiled; only `clkchk` glue stripped | verify per-clock rates against `even` schematic/DTS | S |
| pinctrl MTK | **built** | 5.15 `pinctrl-mtk-*` + carried vendor pin lists | board pinmux comes with the DTS | S |
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
