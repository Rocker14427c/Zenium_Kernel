# Display bring-up: minimum complete chain to a real panel (planning gate)

Status of this document: **scoping + environment record**. No display code was ported in this
round, because the build/link gate the plan requires cannot be run in this sandbox any more
(section 5). Everything measured below is grep/wc output from the 4.19 vendor tree in this
repository (`/home/user/Zenium_Kernel`), with `file:line` for each hardware fact.

## 1. What the board's own DT says (facts, not inference)

| fact | value | source |
|---|---|---|
| dispsys node | `compatible = "mediatek,dispsys"`, `mediatek,larb = <&smi_larb0>` | `arch/arm64/boot/dts/mediatek/mt6768.dts:3125-3127` |
| dispsys clocks | `<&scpsys SCP_SYS_DIS>`, `<&mmsys_config CLK_MM_SMI_COMMON/CLK_MM_SMI_LARB0/CLK_MM_SMI_COMM0/CLK_MM_SMI_COMM1>` | `mt6768.dts:3128-3132` |
| legacy fb node | `compatible = "mediatek,mtkfb"` (no `reg`) | `mt6768.dts:3122` |
| LCM selection style | DT-based, not compile-time: `CONFIG_MTK_LCM_DEVICE_TREE_SUPPORT=y` is *off* but `CONFIG_MTK_LCM_DEVICE_TREE_SUPPORT_PASCAL_E=y` is on, inside `#ifdef OPLUS_BUG_STABILITY` | `arch/arm64/configs/even_defconfig:1715-1716`, `drivers/misc/mediatek/lcm/Kconfig:27-35` |
| display stack config | `CONFIG_MACH_MT6768=y` `:302`, `MTK_LCM=y` `:1713`, `MTK_FB=y` `:1719`, `MTK_M4U=y` `:1740`, `MTK_CMDQ_V3=y` `:1804`, `MTK_CMDQ=y` `:1805`, `MTK_CMDQ_MBOX=y` `:4452`, `MTK_SMI_EXT=y` `:1810`, `MTK_SMI=y` `:4621`, `MTK_CMDQ_TAB` off `:1806`, `MTK_CMDQ_MBOX_EXT` off `:1807` | `even_defconfig` (line numbers given) |
| panel identity | **resolved in `report/panel-identification.md`**: the board builds six LCM drivers, the three that apply to this device are 720x1600 DSI **video-mode** panels - `ilt9882n_truly_even_hdp_dsi_vdo_lcm` (ili9881h+truly), `nt36525b_hlt_even_boe_hdp_dsi_vdo_lcm`, `ilt7807s_hlt_even_hdp_dsi_vdo_lcm` - selected at runtime by the LK-supplied `mtkfb_lcm_name`, with no panel timing in the device tree at all - deliberately left blank. `arch/arm64/boot/dts/oplus6768_20761/cust.dtsi` contains no `lcm`/`panel` string, and `drivers/misc/mediatek/lcm/` holds hundreds of candidate dirs (`hx83102d_txd_jelly_hdp_dsi_vdo_lcm`, `ft8201_wxga_vdo_incell_boe`, `hx83112b_fhdp_dsi_cmd_*`, ...). The answer was neither of the two guesses this row anticipated: `MTK_LCM_DEVICE_TREE_SUPPORT` is off, so `disp_lcm.c`'s DT parser is not compiled, and the choice is made by name from LK - see `report/panel-identification.md` sections 1-2. | measured negative: greps above |