# Device hardware enablement, derived from the built `mt6768.dtb`

> Tool note: `bin/hwenable.py --out-md` **overwrites** this file (it did, mid-round, and dropped the
> curated sections below; they were restored from git). Curated prose therefore lives here, and each
> regeneration of the tool output must be captured to `hardware-enablement.rows.md` first - the
> per-row table below is the tool's, the sections after it are hand-written and cite their sources.


Source of truth: `dtc -I dtb -O dts` of the image this device would boot, then 5.15's
`of_device_id` tables and the Makefile line that builds each matching driver. A row is
*ENABLED* only if the Kconfig that builds that driver is `y`/`m` in the build config.

```
dtb_nodes_with_compatible          450
distinct_comptibles_in_built_dtb   349
bound_by_5_15_driver               34
enabled_in_this_build              25
disabled_but_enableable            5
no_driver_in_5_15                  315
```

| compatible | nodes | 5.15 driver | Kconfig | state | class |
|---|--:|---|---|---|---|
| `arm,armv8-pmuv3` | 1 | arch/arm64/kernel/perf_event.c | CONFIG_HW_PERF_EVENTS | y | ENABLED |
| `arm,armv8-timer` | 1 | drivers/clocksource/arm_arch_timer.c | CONFIG_ARM_ARCH_TIMER | y | ENABLED |
| `arm,idle-state` | 7 | drivers/cpuidle/cpuidle-arm.c | CONFIG_ARM_CPUIDLE | y | ENABLED |
| `arm,psci-1.0` | 1 | drivers/cpuidle/cpuidle-psci-domain.c | CONFIG_ARM_PSCI_CPUIDLE_DOMAIN | y | ENABLED |
| `fixed-clock` | 3 | drivers/clk/clk-fixed-rate.c | CONFIG_COMMON_CLK | y | ENABLED |
| `mediatek,apmixed` | 1 | drivers/clk/mediatek/clk-mt6768.c | CONFIG_COMMON_CLK_MT6768 | y | ENABLED |
| `mediatek,audio` | 1 | drivers/clk/mediatek/clk-mt6768.c | CONFIG_COMMON_CLK_MT6768 | y | ENABLED |
| `mediatek,generic-tphy-v1` | 1 | drivers/phy/mediatek/phy-mtk-tphy.c | CONFIG_PHY_MTK_TPHY | y | ENABLED |
| `mediatek,infracfg_ao` | 1 | drivers/clk/mediatek/clk-mt6768.c | CONFIG_COMMON_CLK_MT6768 | y | ENABLED |
| `mediatek,m4u` | 1 | drivers/misc/mediatek/m4u/2.0/m4u.c | CONFIG_MTK_M4U | y | ENABLED |
| `mediatek,mt6358-auxadc` | 1 | drivers/iio/adc/mt635x-auxadc_v1.c | CONFIG_MT635X_AUXADC | y | ENABLED |
| `mediatek,mt6358-pmic` | 1 | drivers/mfd/mt6397-core.c | CONFIG_MFD_MT6397 | y | ENABLED |
| `mediatek,mt6358-rtc` | 1 | drivers/rtc/rtc-mt6397.c | CONFIG_RTC_DRV_MT6397 | y | ENABLED |
| `mediatek,mt6577-uart` | 2 | drivers/tty/serial/8250/8250_mtk.c | CONFIG_SERIAL_8250_MT6577 | y | ENABLED |
| `mediatek,mt6768-auxadc` | 1 | drivers/iio/adc/mt6577_auxadc.c | CONFIG_MEDIATEK_MT6577_AUXADC | y | ENABLED |
| `mediatek,mt6768-pinctrl` | 1 | drivers/pinctrl/mediatek/pinctrl-mt6768.c | CONFIG_PINCTRL_MT6768 | y | ENABLED |
| `mediatek,mt6768-pwrap` | 1 | drivers/soc/mediatek/mtk-pmic-wrap.c | CONFIG_MTK_PMIC_WRAP | y | ENABLED |
| `mediatek,pericfg` | 1 | drivers/clk/mediatek/clk-mt6768.c | CONFIG_COMMON_CLK_MT6768 | y | ENABLED |
| `mediatek,smi_common` | 1 | drivers/memory/mtk-smi-mt6768.c | CONFIG_MTK_SMI_EXT | y | ENABLED |
| `mediatek,smi_larb` | 5 | drivers/memory/mtk-smi-mt6768.c | CONFIG_MTK_SMI_EXT | y | ENABLED |
| `mediatek,topckgen` | 1 | drivers/clk/mediatek/clk-mt6768.c | CONFIG_COMMON_CLK_MT6768 | y | ENABLED |
| `simple-bus` | 1 | drivers/bus/simple-pm-bus.c | CONFIG_OF | y | ENABLED |
| `simple-mfd` | 1 | drivers/bus/simple-pm-bus.c | CONFIG_OF | y | ENABLED |
| `syscon` | 24 | drivers/hwspinlock/qcom_hwspinlock.c | CONFIG_HWSPINLOCK_QCOM | y | ENABLED |
| `syscon-reboot-mode` | 1 | drivers/power/reset/syscon-reboot-mode.c | CONFIG_SYSCON_REBOOT_MODE | y | ENABLED |
| `android,nebula-gz-log-v1` | 1 | - | - | - | NO_DRIVER |
| `android,nebula-irq-v1` | 1 | - | - | - | NO_DRIVER |
| `android,nebula-smc-v1` | 1 | - | - | - | NO_DRIVER |
| `android,nebula-virtio-v1` | 1 | - | - | - | NO_DRIVER |
| `android,trusty-gz-log-v1` | 1 | - | - | - | NO_DRIVER |
| `android,trusty-irq-v1` | 1 | - | - | - | NO_DRIVER |
| `android,trusty-smc-v1` | 1 | - | - | - | NO_DRIVER |
| `android,trusty-virtio-v1` | 1 | - | - | - | NO_DRIVER |
| `arm,cortex-a55` | 6 | - | - | - | NO_DRIVER |
| `arm,cortex-a75` | 2 | - | - | - | NO_DRIVER |
| `arm,dsu-pmu` | 1 | drivers/perf/arm_dsu_pmu.c | CONFIG_ARM_DSU_PMU | - | DISABLED |
| `arm,gic-v3` | 1 | - | - | - | NO_DRIVER |
| `arm,mali-valhall` | 1 | - | - | - | NO_DRIVER |
| `fpc,fpc_irq` | 1 | - | - | - | NO_DRIVER |
| `goodix,goodix_fp` | 1 | - | - | - | NO_DRIVER |
| `goodix,touch` | 1 | - | - | - | NO_DRIVER |
| `jiiov,fingerprint` | 1 | - | - | - | NO_DRIVER |
| `mediatek, dsi_te-eint` | 1 | - | - | - | NO_DRIVER |
| `mediatek, mrdump_ext_rst-eint` | 1 | - | - | - | NO_DRIVER |
| `mediatek,MT6768` | 1 | - | - | - | NO_DRIVER |
| `mediatek,aes_top0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,amms` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ap_ccif0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ap_ccif1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ap_ccif2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ap_ccif3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ap_dma` | 1 | - | - | - | NO_DRIVER |
| `mediatek,apcldmain` | 2 | - | - | - | NO_DRIVER |
| `mediatek,apcldmain_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,apcldmamisc` | 2 | - | - | - | NO_DRIVER |
| `mediatek,apcldmamisc_ao` | 2 | - | - | - | NO_DRIVER |
| `mediatek,apcldmaout` | 2 | - | - | - | NO_DRIVER |
| `mediatek,apcldmaout_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,atf_logger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,audio_sram` | 1 | - | - | - | NO_DRIVER |
| `mediatek,bat_gm30` | 1 | - | - | - | NO_DRIVER |
| `mediatek,bpi_bsi_slv0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,bpi_bsi_slv1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,bpi_bsi_slv2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,btif` | 1 | - | - | - | NO_DRIVER |
| `mediatek,bus_dbg-v2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cam1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cam2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cam3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cam_clear` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cam_inner` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cam_set` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cama_clear` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cama_ext` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cama_inner` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cama_set` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camb_clear` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camb_ext` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camb_inner` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camb_set` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camera_af_lens` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camera_hw` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camsv1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camsv2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camsv3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camsv4` | 1 | - | - | - | NO_DRIVER |
| `mediatek,camsys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ccci_ccif` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ccci_cldma` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ccu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,charger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,chipid` | 1 | - | - | - | NO_DRIVER |
| `mediatek,chn_emi` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cmdq-bdg-test` | 1 | - | - | - | NO_DRIVER |
| `mediatek,common-infracfg_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,consys-reserve-memory` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dbg_apmcu_mp0` | 17 | - | - | - | NO_DRIVER |
| `mediatek,dbg_apmcu_mp1` | 17 | - | - | - | NO_DRIVER |
| `mediatek,dbg_cti` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dbg_dem` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dbg_etr` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dbg_funnel` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dbg_mdsys1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dcm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ddrphy` | 1 | - | - | - | NO_DRIVER |
| `mediatek,devinfo` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dfd` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dfd_cache` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dip1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_aal0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_ccorr0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_color0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_dither0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_gamma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_mutex0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_ovl0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_ovl0_2l` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_pwm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_rdma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_rsz0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,disp_wdma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dispsys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dpe` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dramc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,drcc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dsi0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dvfsp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dvfsrc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,dxcc_sec` | 1 | - | - | - | NO_DRIVER |
| `mediatek,eem_fsm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,efuse_dbg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,efusec` | 1 | - | - | - | NO_DRIVER |
| `mediatek,eint` | 1 | - | - | - | NO_DRIVER |
| `mediatek,emi` | 1 | - | - | - | NO_DRIVER |
| `mediatek,emi_mpu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,extcon-usb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,fdvt` | 1 | - | - | - | NO_DRIVER |
| `mediatek,fhctl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,finger-fp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,fingerprint` | 1 | - | - | - | NO_DRIVER |
| `mediatek,flashlight_core` | 1 | - | - | - | NO_DRIVER |
| `mediatek,flashlights_even` | 1 | - | - | - | NO_DRIVER |
| `mediatek,flashlights_miami` | 1 | - | - | - | NO_DRIVER |
| `mediatek,flashlights_mt6370` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gauge_timer_service` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gce` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ged` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gic500` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gic_cpu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gpio` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gpio_usage_mapping` | 1 | - | - | - | NO_DRIVER |
| `mediatek,hacc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,hw_dbg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,i2c` | 9 | - | - | - | NO_DRIVER |
| `mediatek,i2c_common` | 1 | - | - | - | NO_DRIVER |
| `mediatek,imgsys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,imp_iic` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu4` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu5` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu6` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_dbgsystop_cpu7` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infra_mbist` | 1 | - | - | - | NO_DRIVER |
| `mediatek,infracfg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_bl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_lb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_lm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_lt` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_rb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_rm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_rt` | 1 | - | - | - | NO_DRIVER |
| `mediatek,io_cfg_tl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,iocfg_0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,iocfg_1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,iocfg_2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,iocfg_3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,iocfg_4` | 1 | - | - | - | NO_DRIVER |
| `mediatek,iocfg_5` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ion-carveout-heap` | 1 | - | - | - | NO_DRIVER |
| `mediatek,irq_nfc-eint` | 1 | - | - | - | NO_DRIVER |
| `mediatek,irtx-pwm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,kp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ktf-cmdq-test` | 1 | - | - | - | NO_DRIVER |
| `mediatek,lastbus-v1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,lk_charger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mailbox-gce-bdg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mailbox-gce-svp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mali` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mbist` | 4 | - | - | - | NO_DRIVER |
| `mediatek,mbist_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcucfg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcucfg_mp0_counter` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcupm_reg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcupm_sram0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcupm_sram1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcupm_sram2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mcupm_sram3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,md_auxadc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,md_ccif0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,md_ccif1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,md_ccif2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,md_ccif3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdcldmain` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdcldmain_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdcldmamisc` | 2 | - | - | - | NO_DRIVER |
| `mediatek,mdcldmamisc_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdcldmaout` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdcldmaout_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mddriver` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mddriver-mt6768` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_ccorr0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_rdma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_rsz0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_rsz1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_tdshp0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_wdma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_wrot0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,memory-ssmr-features` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mfgcfg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi0a` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi0b` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi1a` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi1b` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi2a` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi2b` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_tx0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mm_mutex` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mmdvfs_pmqos` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mmsys_config` | 1 | - | - | - | NO_DRIVER |
| `mediatek,modem_temp_share` | 1 | - | - | - | NO_DRIVER |
| `mediatek,msdc` | 2 | - | - | - | NO_DRIVER |
| `mediatek,msdc0_top` | 1 | - | - | - | NO_DRIVER |
| `mediatek,msdc1_top` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-charger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-cpufreq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-cqdma-v1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-pmic` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6358-misc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6358-regulator` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6358-sound` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6358_gauge` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_bled` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_charger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_core` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_dsv` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_fled1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_fled2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_ldo` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6370_pmu_rgbled` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6577-sysirq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6577-uart-dma` | 1 | drivers/dma/mediatek/mtk-uart-apdma.c | CONFIG_MTK_UART_APDMA | - | DISABLED |
| `mediatek,mt6589-wdt` | 1 | drivers/watchdog/mtk_wdt.c | CONFIG_MEDIATEK_WATCHDOG | - | DISABLED |
| `mediatek,mt6765-spi` | 6 | drivers/spi/spi-mt65xx.c | CONFIG_SPI_MT65XX | - | DISABLED |
| `mediatek,mt6765-timer` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-camsys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-consys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-devapc` | 1 | drivers/soc/mediatek/devapc/devapc-mt6768.c | CONFIG_DEVAPC_MT6768 | - | DISABLED |
| `mediatek,mt6768-dvfsp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-gce` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-gpufreq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-imgsys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-mcdi` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-mmc` | 2 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-mt6358-sound` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-sound` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-timer` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-usb20` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-vcodec-dec` | 1 | drivers/media/platform/mtk-vcodec/mtk_vcodec_dec_drv.c | - | - | UNKNOWN |
| `mediatek,mt6768-vcodec-enc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-wdt` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6785-cache-parity` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt67xx-rng` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt_soc_offload_common` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mtboard-thermistor1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mtboard-thermistor2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mtk-btcvsd-snd` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mtk_ts_pmic` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mtkfb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,nfc-gpio-v2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,nfi` | 1 | - | - | - | NO_DRIVER |
| `mediatek,nfiecc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,oplus-fastcharger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pd_adapter` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pmic-accdet` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pmic_clock_buffer` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pwm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pwrap_md32` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pwrap_mpu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pwrap_p2p` | 1 | - | - | - | NO_DRIVER |
| `mediatek,pwraph` | 1 | - | - | - | NO_DRIVER |
| `mediatek,radio_md_cfg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,reserve` | 1 | - | - | - | NO_DRIVER |
| `mediatek,reserve-memory-scp_share` | 1 | - | - | - | NO_DRIVER |
| `mediatek,reserve-memory-sspm_share` | 1 | - | - | - | NO_DRIVER |
| `mediatek,rt-pd-manager` | 1 | - | - | - | NO_DRIVER |
| `mediatek,scp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,scp_dvfs` | 1 | - | - | - | NO_DRIVER |
| `mediatek,scpinfra` | 1 | - | - | - | NO_DRIVER |
| `mediatek,scpsys` | 1 | drivers/clk/mediatek/clk-mt6768-pg.c | - | - | UNKNOWN |
| `mediatek,security_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf4` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sleep` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sleep_reg_md` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb4` | 1 | - | - | - | NO_DRIVER |
| `mediatek,snd_scp_spk` | 1 | - | - | - | NO_DRIVER |
| `mediatek,speaker_amp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sramrom` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sspm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sys_cirq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sys_timer` | 1 | - | - | - | NO_DRIVER |
| `mediatek,tee_sanity` | 1 | - | - | - | NO_DRIVER |
| `mediatek,therm_ctrl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,topckgen_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,topmisc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,toprgu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trng` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trusted_mem` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trusty-gz` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trusty-mtee-v1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,usb1p_sif` | 1 | - | - | - | NO_DRIVER |
| `mediatek,vdec` | 1 | - | - | - | NO_DRIVER |
| `mediatek,vdec_gcon` | 1 | drivers/media/platform/mtk-vcodec/mtk_vcodec_dec_drv.c | - | - | UNKNOWN |
| `mediatek,vdec_mbist_ctrl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,venc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,venc_gcon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,venc_jpg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,wifi` | 1 | - | - | - | NO_DRIVER |
| `mediatek-vcu` | 1 | - | - | - | NO_DRIVER |
| `microtrust,tester-v1` | 1 | - | - | - | NO_DRIVER |
| `microtrust,utos` | 1 | - | - | - | NO_DRIVER |
| `operating-points-v2` | 2 | drivers/of/platform.c | CONFIG_OBJ | - | UNKNOWN |
| `oplus,fp_common` | 1 | - | - | - | NO_DRIVER |
| `oplus,secure_common` | 1 | - | - | - | NO_DRIVER |
| `oplus,shell-temp` | 3 | - | - | - | NO_DRIVER |
| `richtek,rt9465` | 1 | - | - | - | NO_DRIVER |
| `richtek,swchg` | 1 | - | - | - | NO_DRIVER |
| `shared-dma-pool` | 2 | - | - | - | NO_DRIVER |
| `trustonic,mobicore` | 1 | - | - | - | NO_DRIVER |
| `usb-otg-vbus` | 1 | - | - | - | NO_DRIVER |

## What config cannot fix

304 compatibles in this board's DTB have **no driver in 5.15 at all** - these are the
driver transplants, not fragment edits. First 60:

* `arm,cortex-a55` (6 nodes)
* `arm,cortex-a75` (2 nodes)
* `arm,gic-v3` (1 node)
* `fpc,fpc_irq` (1 node)
* `goodix,goodix_fp` (1 node)
* `goodix,touch` (1 node)
* `jiiov,fingerprint` (1 node)
* `mediatek, dsi_te-eint` (1 node)
* `mediatek, mrdump_ext_rst-eint` (1 node)
* `mediatek,MT6768` (1 node)
* `mediatek,aes_top0` (1 node)
* `mediatek,amms` (1 node)
* `mediatek,ap_ccif0` (1 node)
* `mediatek,ap_ccif1` (1 node)
* `mediatek,ap_ccif2` (1 node)
* `mediatek,ap_ccif3` (1 node)
* `mediatek,ap_dma` (1 node)
* `mediatek,apcldmain` (2 nodes)
* `mediatek,apcldmain_ao` (1 node)
* `mediatek,apcldmamisc` (2 nodes)
* `mediatek,apcldmamisc_ao` (2 nodes)
* `mediatek,apcldmaout` (2 nodes)
* `mediatek,apcldmaout_ao` (1 node)
* `mediatek,apmixed\0syscon` (1 node)
* `mediatek,atf_logger` (1 node)
* `mediatek,audio\0syscon` (1 node)
* `mediatek,audio_sram` (1 node)
* `mediatek,bpi_bsi_slv0` (1 node)
* `mediatek,bpi_bsi_slv1` (1 node)
* `mediatek,bpi_bsi_slv2` (1 node)
* `mediatek,btif` (1 node)
* `mediatek,bus_dbg-v2` (1 node)
* `mediatek,cam1` (1 node)
* `mediatek,cam2` (1 node)
* `mediatek,cam3` (1 node)
* `mediatek,cam_clear` (1 node)
* `mediatek,cam_inner` (1 node)
* `mediatek,cam_set` (1 node)
* `mediatek,cama_clear` (1 node)
* `mediatek,cama_ext` (1 node)
* `mediatek,cama_inner` (1 node)
* `mediatek,cama_set` (1 node)
* `mediatek,camb_clear` (1 node)
* `mediatek,camb_ext` (1 node)
* `mediatek,camb_inner` (1 node)
* `mediatek,camb_set` (1 node)
* `mediatek,camera_af_lens` (1 node)
* `mediatek,camera_hw` (1 node)
* `mediatek,camsv1` (1 node)
* `mediatek,camsv2` (1 node)
* `mediatek,camsv3` (1 node)
* `mediatek,camsv4` (1 node)
* `mediatek,camsys\0syscon` (1 node)
* `mediatek,ccci_ccif` (1 node)
* `mediatek,ccci_cldma` (1 node)
* `mediatek,ccu` (1 node)
* `mediatek,charger` (1 node)
* `mediatek,chipid` (1 node)
* `mediatek,chn_emi` (1 node)
* `mediatek,cmdq-bdg-test` (1 node)

## Fragment written

`None` - 4 symbols:

```
CONFIG_ARM_DSU_PMU=y
CONFIG_DEVAPC_MT6768=y
CONFIG_MTK_UART_APDMA=y
CONFIG_SPI_MT65XX=y
```

## AUXADC, PMIC supplies, and the eMMC host (series round 0076)

### PMIC + SoC ADC providers

The SoC block needed one line, and the vendor tree supplies the justification rather than
my inference: its own `drivers/iio/adc/mt6577_auxadc.c:560` maps
`"mediatek,mt6768-auxadc"` to `mt6765_compat`, and mainline's `mtk_auxadc_compatible` for
that variant is just two behaviour flags (`sample_data_cali = true`,
`check_global_idle = false`) - consistent with this board's DTB carrying
`mediatek,cali-en-bit/-ge-bit/-oe-bit/-efuse-reg-offset` on the same node. 5.15's list
stopped at mt6765, so the alias is added with that citation. (Contrast with pwrap above:
here the "sibling SoC" assumption *is* what MediaTek does, and the evidence is their driver,
not the family tree.)

The PMIC-side converter is the one the battery feeds come through, and mainline has nothing
for it. Rather than invent a driver, this round transplants the variant **this board's own
4.19 defconfig builds**:

    CONFIG_MEDIATEK_MT635X_AUXADC is not set      <- the other variant
    CONFIG_MT635X_AUXADC=y                        <- drivers/iio/adc/mt635x-auxadc_v1.c

`drivers/misc/mediatek/auxadc/` also ships only `mt6765` + `mt6885` per-SoC data, so the
MT6768 SoC block is MT6658-generation by the vendor's own layout ✓ (auxadc has no per-SoC
register table in mainline's driver; only the two flags above.)

What the transplant involved, and what each piece is justified by:
* `mt635x-auxadc_v1.c` copied verbatim except three mechanical adaptations, all recorded in
  the file: `struct mt6358_chip` -> mainline's `struct mt6397_chip` (same `regmap` member,
  and it is exactly what `mt6358-regulator.c` already does with `dev_get_drvdata(parent)`);
  `#include <linux/mfd/mt6358/core.h>` -> `<linux/mfd/mt6397/core.h>`; and the 20 vendor
  `CONFIG_MTK_PMIC_CHIP_MT6358` guards rebound to the driver's own `CONFIG_MT635X_AUXADC`,
  because that symbol is the vendor's one-PMIC-per-build selector and 5.15 has no equivalent -
  the other PMICs' arms were then dropped from `probe()`'s switch (their tables compile out,
  so referencing them would not build).
* `include/linux/mfd/mt6358/registers.h`: **193 `#define`s appended, each copied verbatim**
  from the vendor's 23,828-line header, selected by the compiler's own
  `use of undeclared identifier` list - no numbering was guessed and nothing else from that
  header was dragged in.
* `drivers/mfd/mt6397-core.c`: a `mt635x-auxadc` cell with
  `.of_compatible = "mediatek,mt6358-auxadc"`, because mainline's `mt6358_devs[]` lists only
  regulator/rtc/sound/keys - without a cell, the DTB's `mt635x-auxadc` subnode never becomes
  a device and no `io-channels` consumer could ever resolve. The driver's own of_match string
  is identical to that node's compatible, so this is not a binding rewrite.
* **Not ported, deliberately:** the probe's `pmic_auxadc_chip_init()` call. In the BSP that
  function is *consumer glue*, not PMIC programming - it registers per-channel
  convert/cali callbacks, efuse calibration init, MDRT debug sampling, `parsing_cust_setting()`,
  and a one-off VBIF28 read whose global nothing here reads. Porting it would mean the vendor's
  whole PMIC helper stack. The cost is stated in the file and here: `IIO_CHAN_INFO_PROCESSED`
  values are still converted from counts using each channel's `r_ratio`/`res`, but
  battery voltage is **uncalibrated** (no `cali_fn`) and **battery temperature is not
  trustworthy** (the `convert_fn` pre/post step around the read is skipped). The vendor's
  registration API (`auxadc_set_convert_fn`/`auxadc_set_cali_fn`, both exported) is left in
  place as the seam where the charging/fuel-gauge port must hook in - "channels present" is
  not "battery readings correct".

### PMIC supply phandles: the fix that matters beyond the ADC

`mt6358-regulator.c` registered every descriptor with `config.regmap` only, never setting
`config.of_node`, so each regulator inherited the MFD cell's node. Consumer `*-supply`
phandles point at the *per-rail children*, so they matched nothing and the consumers deferred
forever (MSDC0's `vmmc-supply = <&ldo_vemc>` being the boot-relevant example). The driver now
runs `of_regulator_match()` over its own `desc.name` strings and passes each child as
`config.of_node`.

Measured against this board's DTB: the PMIC's regulator node (`mt6358regulator`) has **42
children**, and **41 of mainline's 41 descriptor names match one exactly** (`buck_vcore`,
`buck_vdram1`, `buck_vgpu`, `buck_vmodem`, `buck_vpa`, `buck_vproc11/12`, `buck_vs1/s2`,
`ldo_vemc`, ...) - the vendor's DT and mainline's table use the same names, so this is a
lookup the two already agree on. The single unmatched DT child is `ldo_va09`, which mainline's
table has no descriptor for: that rail stays unregistered, so any future consumer of VA09
would defer. `of_regulator_match()` in 5.15 returns a count (it does not fail on absent
children) and also honours `regulator-compatible`, so boards with fewer children simply keep
the previous `of_node = NULL` behaviour - no regression for other MT6358 machines.

### eMMC (MSDC0) - the root device

`mmc@11230000`/`mmc@11240000` are `compatible = "mediatek,mt6768-mmc"`, absent from 5.15's
table. Chosen description: mainline's `mt6779_compat`, justified field-by-field against the
vendor's own `mt6768_compat` (same file, `drivers/mmc/host/mtk-sd.c:498`): `clk_div_bits = 12`,
`hs400_tune = false`, `pad_tune_reg = MSDC_PAD_TUNE0`, `async_fifo`, `data_tune`,
`busy_check`, `stop_clk_fix`, `enhance_rx`, `support_64g` - **every field equal**; the only
field the vendor's struct lacks is `recheck_sdio_irq`, which `mt6779_compat` sets false, i.e.
the vendor's implicit zero. Nothing about MT6768 was assumed.

The node also already satisfies what the driver asks for by name, which is the part that
usually blocks a vendor DTB: `clock-names = "source","hclk","source_cg","crypto_clk"` against
`devm_clk_get("source")`/`("hclk")` + optional `"source_cg"` (the fourth, crypto, is simply
unused), and the driver's second-reg-resource `top_base` mapping is covered by the DT's
`<... 0x11cd0000 0x1000>`. Decoding the DT's clock cells against the ported clock provider:
source = `CLK_TOP_MSDC50_0` (topckgen id 60), hclk = `CLK_IFR_MSDC0` (infracfg id 28),
source_cg = `CLK_IFR_MSDC0_SRC` (id 76) - all three are ids the ported `clk-mt6768.c`
registers, so the previously-noted pericfg-CG gap does not block MSDC, and `pinctrl-names`
includes the `"default"`/`"state_uhs"` states mainline uses ✓.

Config: `MMC_MTK=y` + `MMC_BLOCK=y` (`MMC_CQHCI` selected), and **`MMC_MTK_PRO` is
unavailable by construction** (`depends on !MMC_MTK`) which is what we want: the same DTB
also carries the vendor's *legacy* `msdc@11230000`/`msdc0_top@11cd0000` nodes with
`compatible = "mediatek,msdc"` for the BSP's proprietary host driver, and two host drivers on
one controller would be fatal at runtime - Kconfig's mutual exclusion is the guard, noted so
nobody "helpfully" enables both. CQ mode is not requested: mainline enables it from
`supports-cqe`, which this DTB does not set, and the vendor's `mediatek,cqhci` property is
ignored, so eMMC runs HS200/HS400 without CQ ✓ stated rather than implied.

### I2C: not a missing alias - the DTB's nodes are not adapters

All nine `i2cN@...` nodes are `compatible = "mediatek,i2c"` with vendor-era properties (`id`,
`clock-div`, `scl-gpio-id`, `eh_cfg`, `pu_cfg`, `rsel_cfg`, `aed`, `gpio_start`, `mem_len`)
and **no `#address-cells`/`#size-cells`**, so they are the BSP's legacy hardware description,
not I2C adapter nodes. 5.15's `i2c-mt65xx.c` (mt2712/mt6577/mt6589/mt7622/mt8173/mt8183)
cannot match them, and neither can the *vendor's own* 4.19 `i2c-mt65xx.c` (same six strings,
no `"mediatek,i2c"`) - so how the stock kernel reaches these buses is still unexplained here,
and I am not going to invent an answer: the honest state is that I2C needs a *binding*
decision (which adapter description, which pins, which cell-index convention), not a one-line
alias, and until that is settled touch/eeprom/charger-ADC consumers cannot attach. Left as the
next item with the node text quoted, rather than flipping a CONFIG to make it look enabled.

### Verification (build-32) and the packaging defect found on the way

`make Image.gz-dtb modules`: 0 compiler errors, 0 make failures; `Image` 26,966,024 B (grew by
2,048 this time), `Image.gz-dtb` 11,063,228 B, 7,371 objects, 840 `.ko` (all new drivers
built-in), vmlinux carries 80 auxadc/regulator/msdc symbols and **zero** references to
`pmic_auxadc_chip_init` ✓. `strings` on the built objects: `mt6577_auxadc.o` has
`mediatek,mt6768-auxadc`, `mt635x-auxadc_v1.o` has `mediatek,mt6358-auxadc`+`mt635x-auxadc`,
`mtk-sd.o` has `mediatek,mt6768-mmc`, `mt6397-core.o` has the auxadc cell ✓. `hwenable.py`'s
per-compatible rows resolve `mt6768-auxadc -> mt6577_auxadc.c` and
`mt6358-auxadc -> mt635x-auxadc_v1.c` ✓ (its `mt6768-mmc` row still says "NO DRIVER" - that
row is resolved by a grep that this run did not credit for the added table entry; the object
and the string checks above are the authority for that one, and the tool's aggregate row is
recorded as unreliable here rather than patched mid-round).

**The important finding is a defect in what we package, not in a driver.** The same tree
builds two different `mt6768.dtb` depending on the target: `make dtbs` applies the board
Makefile's `DTS_CPPFLAGS` (`arch/arm64/boot/dts/mediatek/Makefile:37`,
`-DCONFIG_MTK_GAUGE_VERSION=30`, `-DCONFIG_MTK_M4U=1`, `-DCONFIG_MTK_SEC_VIDEO_PATH_SUPPORT=1`,
`-DCONFIG_CHARGER_RT9471=1`, `-DCONFIG_TCPC_RT1711H=1`, `-DCONFIG_MTK_ENABLE_GENIEZONE=1`) -
`.mt6768.dtb.cmd` records those 6 flags, the preprocessed intermediate is 163,417 bytes and
the DTB is 122,474 with 413 compatible-bearing nodes. `make Image.gz-dtb modules` builds the
same `.dtb` through `arch/arm64/boot/Makefile`'s `DTB_OBJS` prerequisite, where that
directory-local variable is out of scope: its `.cmd` records **0** `-DCONFIG` flags, the
intermediate is 118,235 bytes, the DTB is **89,053**, 399 compatible nodes, and the M4U/IOMMU
references disappear. Since `arch/arm64/boot/Makefile:47` packs `$(DTB_OBJS)` into
`Image.gz-dtb`, **the DTB in our boot.img is the node-poorer one** - which also finally
explains the 89,053/122,474 oscillation that produced two wrong explanations earlier in this
port (see KNOWN-ISSUES 7.1 and 8.1). Not fixed in this commit: the fix needs a decision about
which DTB shape this port ships (and the +14 nodes describe vendor-only blocks), so it is
recorded as the top boot-critical item with the measurements that pin it down.
## Series round 0077: DTB packaging made consistent, and the audits moved onto the shipped file

The previous section's verification exposed a defect in what the *image* carries, not in the
drivers, and this round closes it (series commit 0077). `make Image.gz-dtb` and `make dtbs` were
building two different `mt6768.dtb` from the same source, because `scripts/Makefile.lib:355`'s
`%.dtb` rule appends the directory-local `$(DTS_CPPFLAGS)` - in scope only when kbuild runs inside
the board directory. The packaging path (`arch/arm64/boot/Makefile`'s `DTB_OBJS` prerequisites)
therefore preprocessed the board DTS with none of the six `-DCONFIG_*` flags the board Makefile
sets, silently dropping every `#if defined(CONFIG_MTK_*)` block from the DTB that gets appended to
the kernel image - including all M4U/IOMMU content and the `CONFIG_MTK_GAUGE_VERSION == 30`
battery/charger properties.

Consequences worth stating plainly:

* 399 vs 413 compatible-bearing nodes, i.e. every bind audit run against the packaging-path DTB was
  looking at a *different device tree* than `make dtbs` produced; and because the two `cmd_dtc`
  strings differ, `if_changed` could never settle, so the file oscillated between builds (this is
  what produced two wrong explanations in earlier rounds - see KNOWN-ISSUES 7.1 / 8.1).
* The previous `boot.img` contained **two different device trees**: its kernel section
  (`Image.gz-dtb`) carried the 89,053-byte build while its dtb section carried the 122,474-byte
  one.

Fix and re-verification (all measured, no board):

* One shared fragment, `arch/arm64/boot/dts/mediatek/dts-cppflags.mk`, included by the board Makefile
  and (under `CONFIG_ARCH_MEDIATEK`) by `arch/arm64/boot/Makefile`. `dtbs` -> `.dtb` ->
  `Image.gz-dtb` -> `dtbs` now leave one stable 122,474-byte file (6 flags in `.mt6768.dtb.cmd`,
  md5 `a2522a615fd6`), and the DTB inside `Image.gz-dtb` is byte-identical to it at offset
  10,603,132, followed by the 5 overlays (6 FDT blobs). `Image` is unchanged (26,966,024 B);
  `Image.gz-dtb` grows to 11,096,649 B.
* `dtc -I dtb -O dts | dtc -I dts -O dtb` on the packaged DTB round-trips to byte-identical
  122,474 B with 413 `compatible` properties, `mediatek,m4u` present and 66 gauge/battery lines -
  the content that used to vanish.
* Both audits were then regenerated *from the packaged DTB*, so `report/clkaudit.json`
  (passes `--require-fresh`) and `report/hardware-enablement.json` describe the image we ship:
  **413 compatible-bearing nodes / 339 distinct / 21 bound / 15 enabled / 4 enableable /
  318 driverless**. Two rows changed since the 89,053-shape measurement and three are new bindings
  from this round's drivers (`mt6768-auxadc`, `mt6358-auxadc`, plus `mt6768-pwrap`/`mt6768-pmic`
  from the previous one). `mediatek,mt6768-mmc` still prints NO DRIVER there - `strings`/`nm` on
  `mtk-sd.o` remain the authority for aliases added to an existing table (KNOWN-ISSUES 8.6).
* Artifact repack (`report/artifacts.json`, build-33): `boot.img` 11,223,040 B with `--boot-id`
  pinned, `mkbootimg.py verify` re-pack byte-identical, `dtbo.img` repacked from the 5 overlays with
  the same header, `SHA256SUMS.txt` regenerated. Still not flash-ready, and `artifacts.json` now
  lists the three external facts that would be needed to say otherwise.

## I2C: how the stock kernel drives those buses (investigation round - closes 8.4)

Requested explicitly as "establish the stock path before deciding", so this section is evidence,
not a config change. Two of my earlier statements here were wrong and are corrected below.

**The driver is `i2c-mtk.c`, not `i2c-mt65xx.c`.** The board's own `even_defconfig` line 2822 is
`CONFIG_I2C_MTK=y`, and `CONFIG_I2C_MT65XX` is absent from it. `drivers/i2c/busses/i2c-mtk.c:1641`
matches `.compatible = "mediatek,i2c"` with `.data = &i2c_common_compat` - the exact string this
board's DT uses - and registers each bus with `i2c_add_numbered_adapter()` (`:1835`, with
`i2c_add_adapter()` commented out at `:1834`). Its `Kconfig` entry has no `depends on` and no
`select` (`:714-725`).
*Correction:* 8.4 previously said "neither 5.15's nor the *vendor's own* `i2c-mt65xx.c` matches
`mediatek,i2c`", which was true of the file I looked at and false as a conclusion: the vendor tree
has a second, different MediaTek I2C host driver that does match it.

**The missing `#address-cells`/`#size-cells` are therefore deliberate, not damage.** Because the
BSP numbers its adapters and its clients call them by bus number, the nine `i2cN@` nodes are pure
hardware descriptions; `i2c-mtk.c:1541-1555` reads `clock-div`, `scl-gpio-id`, `sda-gpio-id`,
`gpio_start`, `mem_len`, `eh_cfg`, `pu_cfg`, `rsel_cfg`, `aed`, `id`, `clk_sta_offset`, `cg_bit`
straight off the node. The pads come from those `*_cfg` ioconfig writes, not from pinctrl: the
board DT contains **no i2c pin groups at all** (21 `i2c` mentions in the whole dump, all of them
the host nodes plus unrelated `smi`/`cam` uses), which is why nothing was "forgotten" there.

**The IP is register-compatible with mainline's driver.** Comparing the two register descriptions
directly: mainline 5.15's `i2c-mt65xx.c` `mt_i2c_regs_v1[]` (`:111` onward: DATA_PORT 0x0,
SLAVE_ADDR 0x4, INTR_MASK 0x8, INTR_STAT 0xc, CONTROL 0x10, TRANSFER_LEN 0x14, TRANSAC_LEN 0x18,
DELAY_LEN 0x1c, TIMING 0x20, START 0x24, EXT_CONF 0x28, FIFO_STAT 0x30, ...) and the vendor's
`i2c-mtk.h` `enum I2C_REGS_OFFSET` (`:43` onward, same list, same values, plus LTIMING 0x2c)
agree offset for offset; the DMA block agrees too (mainline `:86-96` INT_FLAG 0x0, INT_EN 0x4, EN
0x8, RST 0xc, CON 0x18, TX/RX_MEM_ADDR 0x1c/0x20, TX/RX_LEN 0x24/0x28 vs the vendor's
`enum DMA_REGS_OFFSET` `:145` with the same numbers plus STOP 0x10, FLUSH 0x14, INT_BUF_SIZE 0x38).
Mainline models the extra 0x2c as the `ltiming` flag in `mt2712_compat`, which is the variant
closest to this SoC.
*Correction:* the earlier note "would create a probe-able, useless adapter" was about aliasing
`"mediatek,i2c"` blindly, and it still stands as a warning about *clients*, but the register
concern it implied (wrong IP generation) does not hold.

**What mainline needs from this DT, measured node by node** (`i2c0@11007000`, dump `:2672`):
`clocks = <&infracfg_ao 11 &infracfg_ao 38>` with `clock-names = "main","dma"` - and 5.15's
mandatory gets are exactly `"main"` and `"dma"` (`i2c-mt65xx.c:1255,1261`), while `"arb"` is
optional (`:1267-1269` sets it to `NULL` on failure) and `"pmic"` only applies when
`have_pmic` - so the clocks are already right; `reg` has a second range (`0x11000080/0x80`, the
CG/ioconfig window the vendor uses) which mainline ignores because it takes
`IORESOURCE_MEM 0`; `interrupts` is present; and 5.15's driver requires **no** pinctrl states
(`state_high`/`state_slow` arrived in later kernels - `grep pinctrl_lookup_state` on 5.15's file
returns nothing). The only structural gap is adapter-ness: `#address-cells = <1>` /
`#size-cells = <0>` per bus, without which `of_i2c_register_devices()` finds no clients.

**Conclusion.** Two coherent routes, neither of them free:
1. *Additive DT edits, mainline host.* Nine nodes gain two cells each; alias
   `"mediatek,i2c"` to `mt2712_compat` in the ported `i2c-mt65xx.c` (justified by the offset tables
   above). Gives real DT adapters that mainline touch/sensor/charger drivers can use - the shape
   this port wants. Needs the pad pull-up story to come from pinctrl instead of `pu_cfg`/`rsel_cfg`,
   so the i2c pin groups have to be *added* too (they do not exist in this DT), and the vendor
   host must stay off (`CONFIG_I2C_MTK` unset in our config, which it already is).
2. *Vendor host verbatim.* Port `i2c-mtk.c` + `i2c-mtk.h` (+ `i2c-mtk_debug.c`) with the DT
   untouched; matches this hardware exactly, including ioconfig - but clients then only appear via
   the BSP's `i2c_new_device()` call sites in vendor touch/sensor/charger drivers, i.e. it is
   useless until those are ported too, and it does not give mainline drivers a bus.
Recommendation: (1), but folded into the round that ports the first real I2C client (touch),
because the pin groups and the client arrive together; standalone it buys an empty bus.
No config was changed and no DT was edited for this section.

## SMI / M4U: feasibility measured before any code (target chosen for the next round)

The starting condition is a consequence of commit 0077: `m4u@10205000` and the SMI clock cells exist
**only** in the DTB that `make dtbs` builds - the packaging path used to strip the `MTK_M4U` block,
so the DTB our image carried had *no M4U node at all*. Regenerating the reference dump from the
packaged DTB (`dts/mt6768.packaged.dts.dump`, 4,546 lines vs the old 4,288) is what made the
subsystem describable: `grep -c mediatek,m4u` -> 0 in the old dump, 1 in the new one.

Inventory from the packaged DTB (verbatim, not inferred):

    smi_common@14002000  compatible "mediatek,smi_common"        reg 0x14002000/0x1000  smi-id <5>
    smi_larb0@14003000   "mediatek,smi_larb0\0mediatek,smi_larb"  smi-id <0>  clocks = <&scpsys ..> <&mmsys_config ..>
    smi_larb1@16010000   "mediatek,smi_larb1\0.."                smi-id <1>  + <&vdec_gcon ..>
    smi_larb2@15021000   "mediatek,smi_larb2\0.."                smi-id <2>  + <&syscon@15020000 (imgsys) ..>
    smi_larb3@1a002000   "mediatek,smi_larb3\0.."                smi-id <3>  + <&camsys ..>
    smi_larb4@17010000   "mediatek,smi_larb4\0.."                smi-id <4>  + <&venc_gcon ..> x2
    m4u@10205000         "mediatek,m4u"  cell-index <0>  interrupts <0 0xae 8>  clocks = <&syscon@15020000 1>
    (larb clock-names are consumer-shaped, e.g. larb2: "scp-isp", "mm-img", "img-larb2")

Three facts decide the shape of the work - the first of which I had backwards, so it is corrected
here rather than quietly rewritten:

1. **The clock cells are already served.** Counting `clocks` references per provider node in the
   packaged DTB gives `mmsys_config@14000000` 37, `scpsys@10001000` 23, `camsys@1a000000` 8,
   `syscon@15020000` 5, `venc_gcon@17000000` 4, `vdec_gcon@16000000` 2, and `report/clkaudit.json`
   had been reporting `unresolved_provider: 22` against them. That count was an artifact of the
   audit, not a gap in the port: the five `mmsys_config`/`camsys`/`imgsys`/`*_gcon` compatibles are
   all in `clk-mt6768.c`'s own `of_match` table (so those refs resolve), and `mediatek,scpsys` is
   bound by the MTCMOS driver ported in 0074 - `drivers/clk/mediatek/clk-mt6768-pg.c:3764` - whose
   probe (`:3576-3614`) allocates `SCP_NR_SYSS` (=13, `include/dt-bindings/clock/mt6768-clk.h:411`),
   registers `scp_clks[]`'s 13 power-gate clocks via `init_clk_scpsys()` and publishes them with
   `of_clk_add_provider(node, of_clk_src_onecell_get, clk_data)`. The cells the DT asks for -
   1, 3, 4, 5, 7, 8, 9, 10, 11, 12 - are `SCP_SYS_CONN/DIS/MFG/ISP/MFG_CORE0/MFG_CORE1/MFG_ASYNC/
   CAM/VENC/VDEC`, all in range with no holes, and they match their consumers semantically
   (`smi_larb1` -> VDEC, `smi_larb2` -> ISP, `smi_larb3` -> CAM, `smi_larb4` -> VENC,
   `smi_larb0`/`smi_common`/`dispsys`/`gce`/`imgsys_config` -> DIS, `gpufreq` -> the three MFG
   entries, `consys` -> CONN, `vcodec_dec` -> {DIS, VDEC}, `vcodec_enc` -> {DIS, VENC},
   `ccu`/`kd_camera_hw1` -> CAM), which is the cross-check that the BSP means this provider for
   exactly those references. `scpsys@10001000` shares its first `reg` range with
   `infracfg_ao@10001000`, but they are distinct nodes with distinct id spaces - `SCP_SYS_*` cells
   must not be compared against `CLK_IFR_*` indices. Audit fixed (second id family, `scp_clks[]`,
   the `mediatek,scpsys` provider, multi-file `--driver`, and per-row `unresolved_refs` output);
   no kernel source needed to change, and the numbers are now **234 refs / 234 registered /
   0 unresolved / 0 foreign / 0 collisions**.
2. **The DT has no IOMMU consumers.** `grep -c 'iommus = '` on the packaged DTB: **0**. The BSP's
   media/display clients reach the IOMMU through the vendor SMI/M4U APIs plus `mediatek,smi-id`,
   not through `iommus` phandles - so a mainline `mtk_iommu` binding, even with per-MT6768 data
   written from the BSP, would register an IOMMU that nothing references; wiring `iommus` into the
   display/camera/video nodes is DT surgery across dozens of nodes.
3. **Both mainline halves exist in 5.15 but want a different tree shape.** `drivers/memory/mtk-smi.c`
   matches `mediatek,{mt2701,mt2712,mt6779,mt8167,mt8173,mt8183,mt8192}-smi-{common,larb}`, requires
   per-larb clocks named `"apb"`/`"smi"` (`:332-336`) and a `mediatek,smi` phandle to the common node
   (`:350`); `drivers/iommu/mtk_iommu.c` builds its larb set from the m4u node's `mediatek,LARB`
   phandle list (`:876-881`). This DT has flat sibling larbs with vendor compatibles and
   `mediatek,smi-id`, no `mediatek,smi`/`mediatek,LARB` links, and clock names the vendor driver
   chose instead (`"scp-isp"`, `"mm-img"`, `"img-larb2"`). MT6768 is in no mainline table, and the
   closest one, `mt6779_data` (`:1049`), is not a drop-in: its `.larbid_remap` covers 8 groups up to
   larb 10 against MT6768's five larbs (`smi-id` 0..4), with
   `.flags = HAS_SUB_COMM | OUT_ORDER_WR_EN | WR_THROT_EN` and `REG_MMU_INV_SEL_GEN2` each needing
   verification against the BSP's mt6768 M4U. Neither `CONFIG_MEDIATEK_SMI` nor `CONFIG_MTK_IOMMU` is
   enabled in our config.

What that means for the work, after the "measure before deciding" instruction:

- **S1: closed as an audit correction, not a driver change.** See fact 1. The gate moved the way
  gates should: `bin/clkaudit.py` reports `unresolved_provider: 0` because the tool can now see the
  provider that was always there, and the same run confirms nothing else was missing
  (234/234). Because no source file changed, build-33 remains the reference build and the flash set
  is unchanged.
- **The BSP's own SMI/M4U matches this DT exactly, which is the strongest argument for the vendor
  route.** `even_defconfig` sets `CONFIG_MTK_M4U=y` (`:1740`), `CONFIG_MTK_SMI=y` (`:4621`),
  `CONFIG_MTK_SMI_EXT=y` (`:1810`) and `CONFIG_IOMMU_IOVA=y` (`:4462`): the stock device runs
  `drivers/misc/mediatek/m4u/mt6768/` (3,074 lines in `m4u_hw.c` alone) plus
  `drivers/misc/mediatek/smi/`, and the BSP's SMI looks clocks up *by name*
  (`mmdvfs_mgr_v3.c:813 of_clk_get_by_name()`, `mtk-smi-dbg.c:691 devm_clk_get(node->dev, name)`),
  which is precisely what those per-larb names are for. A vendor-stack port therefore needs **zero**
  DT edits, including for the clock cells S1 just confirmed are provided by our own pg driver.
- **The mainline route costs DT surgery in three places and buys an unused IOMMU.** Per-larb
  clock-names + `mediatek,smi`, an `mediatek,LARB` list on the m4u node, and `iommus` on every
  client - while the only clients in this tree are the BSP's (`drivers/misc/mediatek/video/mt6768`
  references m4u in 16 files, `ccu/src` in 31) and they call the vendor API, not the generic IOMMU
  bindings.
- **Recommendation, per the instruction to defer the architecture decision:** sequence SMI+M4U
  (vendor route, no DT changes) *inside* the display/video round, so the infrastructure lands with
  its callers, and keep the mainline `mtk_iommu` option open as a display-architecture question
  rather than an SMI one. No `iommus`/`#dma-cells` properties were added and no `CONFIG_MTK_*` IOMMU
  symbol was enabled for this round; I2C likewise stays as documented above (investigation only,
  enablement folded into the touch round).

## SMI substrate landed: patch 0078, measured on build-34

The plan recorded in the section above ("SMI / M4U: feasibility measured before any code")
was executed as proposed: the vendor MT6768 SMI substrate is in the tree, and the DT was not
touched to get it there.

**What landed** (`drivers/memory/mtk-smi-mt6768.c`, `include/soc/mediatek/smi-mt6768.h`,
`CONFIG_MTK_SMI_MT6768`): the `CONFIG_MTK_SMI_EXT` half of the BSP's `drivers/memory/mtk-smi.c`
(clock enable/disable, `mtk_smi_dev_get()`, `mtk_smi_conf_set()`, `mtk_smi_clks_get()`,
`mtk_smi_dev_probe()` with the optional power-reset/common-reset/common-clamp cells, the
larb/common probes, both `of_device_id` tables, both `platform_driver` objects) plus the two
wrappers the BSP exposes for clients, `smi_bus_prepare_enable()` / `smi_bus_disable_unprepare()`
and `smi_get_dev_num()`, taken from `drivers/misc/mediatek/smi/smi_drv.c` with its MT6885-only
sub-common expansion and `smi_clk_record()` tracing left out.

**Why the vendor driver and not mainline's.** This tree already builds mainline's
`drivers/memory/mtk-smi.c` (`CONFIG_MTK_SMI=y`) and `drivers/iommu/mtk_iommu.c`
(`CONFIG_MTK_IOMMU=y`), and neither can bind this board's DT: mainline's SMI asks for per-larb
clock-names `apb`/`smi`(`gals`) and finds its common device through a `mediatek,smi` phandle,
while this DT carries flat sibling nodes with BSP clock-names (`scp-isp`, `mm-img`,
`img-larb2`, ...) and a `mediatek,smi-id` index; mainline's `mt6779_data` also maps up to
larb 10 where MT6768 has five. Using them would mean rewriting the DT, which is what the
round's rule forbids. The ported code needs nothing from the DT that isn't already there.

**Verified, per dependency:**

| dependency | how it was verified | result |
|---|---|---|
| compiles | `make ... drivers/memory/mtk-smi-mt6768.o`, then full `Image.gz-dtb modules` (build-34) | 0 errors, 0 new warnings; objects 7,371 -> 7,372; `Image.gz-dtb` 11,096,649 -> 11,099,339 B |
| links / is in the image | `nm vmlinux` | the 7 API symbols are `T` (mainline's static `t mtk_smi_clk_enable` coexists), 7 `__ksymtab_*` entries; `strings Image` finds the driver's own messages |
| DT binding, compatibles | `bin/hwenable.py` on the built `mt6768.dtb` | `mediatek,smi_common` nodes=1 and `mediatek,smi_larb` nodes=5 -> `class=ENABLED`, `driver=drivers/memory/mtk-smi-mt6768.c`, `CONFIG_MTK_SMI_MT6768=y`; `mediatek,m4u` nodes=1 still `NO_DRIVER` at that point (flipped to `ENABLED` by 0080, see the M4U section below) |
| DT binding, ids | `mediatek,smi-id` read from the DTB | larb0..4 = 0..4, `smi_common@14002000` = 5, matching the BSP's `mt6768/smi_port.h` (`SMI_LARB_NUM` 5, `SMI_DEV_NUM` 6) |
| clocks | `bin/clkaudit.py --require-fresh` on the packaged DTB | totals unchanged: 234 refs / 234 registered / 0 unresolved provider / 0 collisions; the rows that cover these nodes are `CLK_MM` 37/37 and `SCP_SYS` 23/23, so every cell the six SMI nodes reference is already registered by 0074's `clk-mt6768.c` + `clk-mt6768-pg.c`. Each larb's `clks[0]` is that `scp-*` MTCMOS cell, which `mtk_smi_clk_enable()` deliberately skips and `smi_unit_prepare_enable()` enables - so SMI needed no new clock work |
| DT untouched | `sha256sum arch/arm64/boot/dts/mediatek/mt6768.dtb` | `34a7e6b536a3a34e...`, identical to build-33 |
| series reproducibility | `git worktree` at v5.15.220 + `git am` of all 78 `.eml` | rc=0, `HEAD^{tree}` = `1ce51ae42f7ea320beb23a202db77ec38c249b68`, equal to the built tree |

**The audit had to be fixed first.** `bin/hwenable.py` indexed each DTB `compatible` property as
a single string. The kernel's `of_match_node()` tests every NUL-separated entry, and this BSP's
DT stores several compatibles per blob (`"mediatek,smi_larb0\0mediatek,smi_larb"`,
`"mediatek,scpsys\0syscon"`), so any driver binding on a non-first entry was invisible - the
five SMI larbs would have been reported driverless while their driver matches them. The rows in
`report/hardware-enablement.rows.md` / `.json` are regenerated with that fix: 413 nodes with a
compatible / 450 compatible entries / 349 distinct / 33 bound / 24 enabled / 5 enableable / 316
driverless. The numbers quoted earlier in this file (339 distinct / 21 bound / 15 enabled / 4
enableable / 318 driverless) came from the pre-fix tool and are superseded; `report/decisions.json`
(`hwenable-nul-compatible-split`) records why they moved.

**Not ported, with the cost stated** (full text in the file header): BWC tables, mmdvfs/PMQOS,
emi/BWL, sysram, mmprofile, sspm, debugfs, `smi_clk_record()` per-user clock counters, and the
BSP's `smi_register()`. `smi_register()` cannot run against this DT at all: it does
`of_parse_phandle(<common node>, "mmsys_config", 0)` and returns `-ENOMEM` when that property is
missing, and this board's `smi_common@14002000` has only `compatible`/`reg`/`mediatek,smi-id`.
Consequences: the larbs are enabled per client call rather than pre-enabled at init;
`mtk_smi_conf_set()` is inert (its `conf_pairs`/`scen_pairs` stay empty, so it writes nothing
instead of a partial set); and the MTCMOS `after_on`/`before_off` re-enable hook is absent, so a
clock lost across a subsystem power cycle is not restored by this file. All three are tracked in
`KNOWN-ISSUES.md`.

## M4U v2.0 landed: patch 0080, measured on build-36

The row `mediatek,m4u` carried above as `NO_DRIVER` since the DTS transplant is now `ENABLED`:
driver `drivers/misc/mediatek/m4u/2.0/m4u.c`, `CONFIG_MTK_M4U=y`. That is the only row the commit
moved, and the aggregate block above was refreshed from the tool at the same time (it had been stale
since build-32 - the `--out-md` hazard noted at the top of this file):

```
                       build-35 (0079)          build-36 (0080)
bound_by_5_15_driver            33      ->             34
enabled_in_this_build           24      ->             25
no_driver_in_5_15              316      ->            315
```

M4U is unusual among the ported drivers in that it does not rely only on its own `of_match_table`;
`m4u_reg_init()` (`mt6768/m4u_hw.c:2802-2831`) does its own `of_find_compatible_node()` +
`of_iomap()` for the SMI blocks. Each string was checked against the shipped `.dtb` with
`dtc -I dtb -O dts`, not against DTS source:

| M4U looks up | source of the string | entries in `mt6768.dtb` | node it resolves to |
|---|---|--:|---|
| `mediatek,m4u` (`of_match`, `iommu_of_ids`, `m4u.c:2339`) | static string | 1 | `m4u@10205000` |
| `mediatek,smi_common` | only under `M4U_MMU_SLAVE_SWITCH`, which MT6768 defines (`m4u_priv.h:103`) | 1 | `smi_common@14002000` |
| `mediatek,smi_larb0..4` | `gM4U_SMILARB[]` (`m4u_platform.h:9`), `SMI_LARB_NR 5` | 1 each | the five `smi_larb@...` nodes |
| `mediatek,pericfg` | inside `#if (TOTAL_M4U_NUM > 1)`; MT6768 is 1 (`m4u_hw.h:11`) | 1 | not referenced at run time |

The larb rows still show `mediatek,smi_larbN` as `NO_DRIVER` while `mediatek,smi_larb` shows
`nodes=5 ENABLED`, and that is correct rather than a gap: the DTB stores both spellings in one
`compatible` property, the SMI driver matches the second entry, and M4U's lookup - which walks every
NUL-separated entry, like `of_property_match_string()` - finds the first. Nothing in the DT was
renamed or converted to make M4U bind, and the `.dtb` is unchanged: `34a7e6b5...85a11cd`, 122,474 B,
byte-identical inside the repacked `boot.img`.

M4U does not request the clock its node carries. `mt6768/m4u_hw.c` has no `clk_get`/
`clk_prepare_enable` at all (it takes larb clocks through the SMI API instead), so
`clocks = <&syscon_15020000 1>` / `clock-names = "ISP_CLK_IMG_DIP"` is left to its owner, exactly as
on stock; `bin/clkaudit.py --require-fresh` on build-36 still reports 234 refs / 234 registered / 0
unresolved, with that cell listed under `m4u@10205000` as registered. `bin/hwenable.py` was re-run
without `--compat-index` here, the same methodology that produced the build-35 numbers, so the
comparison is like for like.
