# Panel identification for Realme C25 / Narzo 50A ("even", MT6768) - evidence only

Source: the 4.19.325 vendor tree in this repository, read with grep/awk/sed only (paths and line
numbers given for every claim). No build was run and no display code was ported: the 5.15 build
environment is unavailable in this sandbox (`report/display-bringup-plan.md` section 5). Nothing
here is inferred from directory names or from other boards' panels.

## 1. Verdict

The kernel for this board does not carry one panel. It carries **six LCM drivers, selected by name
at boot from the content LK hands over**, and the three that matter for this device family are
720x1600 video-mode DSI panels from three different suppliers:

| LCM driver dir (`drivers/misc/mediatek/lcm/`) | panel, per its own `readme.txt` | size |
|---|---|---|
| `ilt9882n_truly_even_hdp_dsi_vdo_lcm` | "bringup lcm for project **S98670AA1**, and this panel is **ili9881h+truly**" | 797 lines |
| `nt36525b_hlt_even_boe_hdp_dsi_vdo_lcm` | "bringup lcm for project **S91369AA1**" (Novatek NT36525B source-driver on a BOE HDP module) | 704 lines |
| `ilt7807s_hlt_even_hdp_dsi_vdo_lcm` | "bringup lcm for project **S91537AA1**, and this panel is **ili7807s+hlt**" | 897 lines |

The other three in the same defconfig string are FHD panels for sibling variants and are *not*
used by this board's DT/touch config: `ili7807s_xxx_fhd_dsi_vdo_dphy` (961), `ili7807s_jdi_fhd_dsi_vdo_dphy`
(1,099), `nt36672c_tm_fhd_dsi_vdo_dphy` (1,338). Total LCM panel layer for this board: 5,796 lines.

Which one a given phone uses is answerable from the device, not from the source: the touch config
lists the matching TDDI families side by side (`ilitek,ili9882n` and `novatek,nf_nt36525b`, plus
`focal,ft_spi_ft8006s` / `ilitek-ts-spi` / `NVT-ts-spi` fallbacks) and its
`platform_support_project = <20761 20762 20764 20767 20766 0x2167A ...>` property maps sub-project
ids to behaviour, so C25 (mt6768, project 20761) and the Narzo 50A/50 variants share one kernel and
differ by panel module. Therefore the port must carry the panel layer as a **set** plus the
name-based selection, or it will build for one unit and fail on another.

## 2. The selection chain, as compiled

1. `arch/arm64/configs/even_defconfig:1714` sets
   `CONFIG_CUSTOM_KERNEL_LCM="ili7807s_xxx_fhd_dsi_vdo_dphy ili7807s_jdi_fhd_dsi_vdo_dphy nt36672c_tm_fhd_dsi_vdo_dphy ilt9882n_truly_even_hdp_dsi_vdo_lcm nt36525b_hlt_even_boe_hdp_dsi_vdo_lcm ilt7807s_hlt_even_hdp_dsi_vdo_lcm"`.
2. `drivers/misc/mediatek/lcm/Makefile:24-26` turns that string into the built subdirectories
   (`LCM_LISTS := $(subst ",,$(CONFIG_CUSTOM_KERNEL_LCM))`, `obj-$(CONFIG_MTK_LCM) += $(foreach ...)`),
   and `:41-44` **uppercases the same string into -D macros** (`LCM_DEFINES := $(shell echo ... | tr a-z A-Z)`;
   `ccflags-$(CONFIG_MTK_LCM) += $(addprefix -D, $(DEFINES))`). Each panel dir's own Makefile is just
   `obj-y += <name>.o` (e.g. `ilt9882n_truly_even_hdp_dsi_vdo_lcm/Makefile`, 1 rule), so the *symbol*
   that enables a driver is that uppercase -D, nothing else.
3. `drivers/misc/mediatek/lcm/mt65xx_lcm_list.c` holds `struct LCM_DRIVER *lcm_driver_list[]`, whose
   entries are individually wrapped in `#if defined(<THE_UPPER_NAME>)` - so the list contains exactly
   the six drivers above for this defconfig, in the order written there.
4. The name actually in use at runtime is `mtkfb_lcm_name[256]` (`video/mt6768/videox/mtkfb.c:182`),
   filled from the LK boot info (`mtkfb.c:2311` bounds the copy against `sizeof(mtkfb_lcm_name)`;
   `ddp_dsi.h:166` declares it "defined in mtkfb.c" and `ddp_dsi.h:167` declares `dts_gpio_state`,
   the companion LK-supplied value). `disp_lcm.c`'s DT-driven `LCM_DTS` machinery - and with it
   `parse_lcm_params_dt_node()` and all 292 `lcm_params-*` property reads - sits inside
   `#if defined(MTK_LCM_DEVICE_TREE_SUPPORT)` (`videox/disp_lcm.c:186-1030`, also `:1053`, `:1131`,
   `:1230`), and **that symbol is not set** (`even_defconfig:1715`), while only the OPLUS-specific
   `CONFIG_MTK_LCM_DEVICE_TREE_SUPPORT_PASCAL_E=y` is (`:1716`). Consequence, stated precisely: no
   panel timing on this board is read from the device tree; it is compiled into the panel driver and
   selected by name. (Verified negative: `grep -rl "lcm_params-" arch/arm64/boot/dts/` returns
   nothing, i.e. no DTS in this tree carries those properties.)
5. What PASCAL_E does change is small and specific: `lcm/Kconfig:27-35` (`#ifdef OPLUS_BUG_STABILITY`),
   `lcm/Makefile:48` (`-DMTK_LCM_DEVICE_TREE_SUPPORT_PASCAL_E`), and inside the drivers
   (a) `lcm/inc/lcm_common.h:15` and `lcm_define.h:13` pull in the common-LCM tables,
   (b) `lcm_common.h:27` changes `lcm_common_get_params()` to take `struct LCM_PARAMS *` instead of
   the by-value argument, and (c) `lcm/lcm_i2c.c:65-116` replaces the `mediatek,I2C_LCD_BIAS`
   of_match with `{ .compatible = "default" }`, uses bus 0 (bus 3 when `MTK_CUSTOM_LCM_DIFFERENT`),
   address 0x3E, client name "GATE_SM5109_OCP2130", and makes `_lcm_i2c_client` non-static so panel
   files can share it. So `lcm_get_params(struct LCM_PARAMS *params)` in each of the three even
   panels is the PASCAL_E form (`ilt9882n_truly_even_hdp_dsi_vdo_lcm.c:476`), not the vendor-mainline
   by-value form - a port must reproduce the pointer signature or the common layer's calls will not
   match.

## 3. DSI parameters (measured from the three even panel files)

Common to all three: `params->type = LCM_TYPE_DSI`; `LCM_DSI_CMD_MODE 0` (`:79`/`:82`) so
`dsi.mode = SYNC_PULSE_VDO_MODE` with `dsi.switch_mode = CMD_MODE` but `switch_mode_enable = 0` -
**DSI video mode, no dynamic video/command switching**; `LANE_NUM = LCM_THREE_LANE`;
`data_format` RGB / MSB-first / pad-LSB / `RGB888`, `PS = LCM_PACKED_PS_24BIT_RGB888`;
`packet_size = 256`; geometry `FRAME_WIDTH (720)`, `FRAME_HEIGHT (1600)`,
`LCM_PHYSICAL_WIDTH (67930)` um and `LCM_PHYSICAL_HEIGHT (150960)` um (6.5", 120 Hz class HDP).

| item | ilt9882n_truly | nt36525b_hlt_boe | ilt7807s_hlt |
|---|---|---|---|
| vertical sync/back/front porch | 2 / 16 / 240 | (2 / 16 / **10**) | (2 / 16 / **32**) |
| horizontal sync/back/front porch | 8 / 26 / 27 | same shape, `vfp` differs | same shape |
| `dsi.PLL_CLOCK` | 360 | 360-class (same table note) | 360-class |
| `dsi.data_rate` | 735 | - | - |
| dynamic DSI clock | `dynamic_switch_mipi = 1`, `horizontal_sync_active_dyn = 8`, `horizontal_backporch_dyn = 11`, `data_rate_dyn = 720` | not present | not present |
| ESD | `esd_check_enable = 0`, `customization_esd_check_enable = 0`, table `{cmd 0x0A, count 1, para[0] 0x9C}` | same pattern | same pattern |
| misc | `lcd_serial_number = 1`, `CLK_HS_PRPR = 7`, `ssc_disable = 1`, `pll_div1/div2 = 0`, `fbk_div = 0x1` | | |

The init sequences are pushed through `dsi_set_cmdq*`/`push_table_cust` style helpers with
`LCM_setting_table` arrays (the truly file's `lcm_init()` is at `:610`, `lcm_get_params` at `:476`,
the `LCM_DRIVER` struct at `:777` with `.init_power/.resume_power/.suspend_power`,
`.shutdown_power` under `OPLUS_BUG_STABILITY`, `.esd_recover`, `.set_backlight_cmdq`,
`.set_cabc_mode_cmdq`, `.get_cabc_status`). All three therefore need the CMDQ-backed
`set_backlight_cmdq`/`init_power` path, not just the DSI packet writer.

## 4. Reset, TE, bias, backlight - where the numbers really live

- Panel files never name a GPIO number. They use `lcm_util` hooks: `SET_RESET_PIN(v) =
  lcm_util.set_reset_pin(v)` (`ilt9882n...c:41`, `nt36525b...c:41`, `ilt7807s...c:45`),
  `SET_LCM_VDD18_PIN = set_gpio_lcm_vddio_ctl` (`:42`), `SET_LCM_VSP_PIN =
  set_gpio_lcd_enp_bias` (`:43`), `SET_LCM_VSN_PIN = set_gpio_lcd_enn_bias` (`:44`), plus
  `display_bias_setting(0x14)` before reset toggling (`:603`, `:467`, `:714`).
- On the dispsys side those hooks resolve to **MMSYS register writes or an LK-supplied GPIO state**,
  not to pinctrl: `video/mt6768/dispsys/ddp_dsi.c:4959-4969` `lcm_set_reset_pin()` does
  `DSI_OUTREG32(NULL, DISP_REG_CONFIG_MMSYS_LCM_RST_B, value)` when `dts_gpio_state != 0`, else
  `disp_dts_gpio_select_state(DTS_GPIO_STATE_LCM_RST_OUT1/OUT0)`; `lcm_bias_vsp()` starts at `:4971`.
  `PM_lcm_utils_dsi0` (`ddp_dsi.c:7489-7495`) is the whole util set the panels get: `.set_reset_pin`,
  `.udelay`, `.mdelay`, `.dsi_set_cmdq = DSI_set_cmdq_wrapper_DSI0`,
  `.dsi_set_cmdq_V2 = DSI_set_cmdq_V2_Wrapper_DSI0` - five members, no regulator get/put, no
  `gpio_set_value`. TE is a DSI-side flag, not a GPIO irq: `PanelMaster_get_TE_status()`
  (`ddp_dsi.c:7499-7506`) returns `dsi0_te_enable` and ignores dsi1 on this chip.
  Consequence for the port: the panel's reset line is driven through the SoC's MMSYS
  `LCM_RST_B` config bit or through the LK GPIO-state table, so a 5.15 port cannot substitute
  `gpio_set_value(C, n)` without first deciding which of the two paths the board actually uses -
  and `dts_gpio_state` (declared `ddp_dsi.h:167`) is set from LK-provided DT content, i.e. it is a
  boot-time fact this sandbox cannot observe.
- Backlight is a `level -> DSI write` translation with an HW-check log line, per panel:
  `oplus_private_set_backlight(level)` (`:658`, `:618`, `:768`) called from
  `lcm_setbacklight_cmdq()` (`:685`, `:645`, `:795`), which logs
  `"[ HW check backlight ili9882n+truly]level=%d, para_list[0]=%x, para_list[1]=%x"` etc. - i.e.
  the PWM is not in the panel driver at all; brightness travels as DSI packets issued through CMDQ.
  CABC goes the same way (`.set_cabc_mode_cmdq`, `.get_cabc_status`).

## 5. The touch/client stage: this board's touch is on SPI, not I2C

The one DTS in this tree that names the panel controllers is the *touch* config for the
720x1600 mt6768 board: `arch/arm64/boot/dts/mediatek/cust_mt6768_touch_720x1600.dtsi`, included by
`arch/arm64/boot/dts/mediatek/oplus6768_20761.dts` (the only mt6768 board dts that includes it;
`oplus6769_2167A.dts` and `oplus6769_216AF.dts` include the mt6769 720x1600 twin). Its content:
`&spi2 { touch_ts@0 { reg = <0>; compatible = "oppo,tp_noflash","ilitek,ili9882n",
"ilitek,ilitek-ts-spi","novatek,NVT-ts-spi","novatek,nf_nt36525b","focal,ft_spi_ft8006s";
spi-max-frequency = <9600000>; chip_name_ilitek = "NF_ILI9881H"; chip_name_ilitek_9882n =
"NF_ILI9882N"; chip_name_novatek = "NF_NT36525B"; chip_name_himax = "NF_HX83102D";
chip_name_focal = "NF_FT8006S"; reset-gpio = <&pio 23 0x00>; irq-gpio = <&pio 1 0x2002>;
interrupts = <1 IRQ_TYPE_EDGE_FALLING 1 0>; touchpanel,max-num-support = <10>;
touchpanel,tx-rx-num = <18 32>; touchpanel,panel-coords = <720 1600>; touchpanel,display-coords
= <720 1600>; ...}` - plus `incell_screen`, `charger_pump_support`, `black_gesture_support` and the
`platform_support_project`/`platform_support_project_dir` id maps. So:
(a) the touch is an **incell/TDDI device on SPI bus 2 at 9.6 MHz**, sharing the panel's reset pin
    (`&pio 23`) and using `&pio 1` as interrupt - it is the SPI touch core (`mtk_ts_spi` family),
    not the I2C one;
(b) I2C does appear on the display path, but only for the **gate/bias IC** through `lcm_i2c.c`
    (bus 0, 0x3E, "GATE_SM5109_OCP2130"), and only for panels that call `lcm_i2c_read/write` - a
    per-panel question that the three even dirs answer "yes/no" to by inspection when L4 is ported;
(c) correcting the plan's earlier wording: "keep I2C integration for the touch/client stage" should
    read "keep the SPI touch path in scope for the client stage; I2C is needed for the bias/gate IC
    and it inherits the same adapter gap as `KNOWN-ISSUES.md` 8.4".

## 6. What this changes in the bring-up plan

- L4 is not "one panel driver": it is the common LCM layer (`mt65xx_lcm_list.o`, `lcm_common.o`,
  `lcm_gpio.o`, `lcm_i2c.o`, `lcm_pmic.o`, `lcm_util.o` per `lcm/Makefile:20-24`), the PASCAL_E
  signature change, and **three** HDP panel dirs (2,398 lines), selected by the LK-passed name.
- The reset/bias/TE path must be ported as a decision, not as code: MMSYS `LCM_RST_B` bit vs the
  `disp_dts_gpio_select_state()` table (section 4). Under 5.15 the honest options are to drive the
  same MMSYS bit from the dispsys/DSI port (it is a SoC register, no pinctrl needed) and to document
  the LK GPIO-state path as unavailable, or to add real `pinctrl-0` handles in the ported DT - the
  latter edits a binding, so it needs the usual "no DT edit without a device to check it on" rule.
- `dynamic_switch_mipi = 1` on the truly panel makes CMDQ part of the *panel* path, not merely an
  optimisation: L1 (CMDQ) is a hard prerequisite for that panel's timing behaviour.
- Still unmeasured, with the command that settles each:
  (i) the init-sequence lengths and content per panel: `awk '/LCM_setting_table|lcm_init_sequence/,/};/'`
      over each dir;
  (ii) whether any of the three even panels calls `lcm_i2c_*` at all: `grep -n "lcm_i2c_" <dir>/*.c`;
  (iii) the consumer of `LCD_HW_ID_STATUS_*` (declared in `mt65xx_lcm_list.c:19-22`, not found in
      `lcm_gpio.c`/`lcm_util.c`/`videox/*.c`): `grep -rn "LCD_HW_ID_STATUS" drivers/ | grep -v lcm_list`;
  (iv) `dts_gpio_state`'s writer and the GPIO-state table it selects from:
      `grep -rn "dts_gpio_state\|disp_dts_gpio_select_state\|DTS_GPIO_STATE" drivers/misc/mediatek/video | head`.
  None of these is needed to size the layers; all four are needed before L4 is written.

## 7. Claim ceiling

This is a source-level identification. It says what the vendor kernel compiles and how it chooses;
it does not say what a particular unit's panel is (that needs `mtkfb_lcm_name` from a running
device or LK), it does not verify any timing against a datasheet, and it establishes nothing about
5.15 behaviour - no compile, no link, no DTB re-audit was possible this round
(`report/display-bringup-plan.md` section 5).
