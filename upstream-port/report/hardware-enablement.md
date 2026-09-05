# Device hardware enablement, derived from the built `mt6768.dtb`

Source of truth: `dtc -I dtb -O dts` of the image this device would boot, then 5.15's
`of_device_id` tables and the Makefile line that builds each matching driver. A row is
*ENABLED* only if the Kconfig that builds that driver is `y`/`m` in the build config.

```
dtb_nodes_with_compatible          413
distinct_comptibles_in_built_dtb   339
bound_by_5_15_driver               19
enabled_in_this_build              13
disabled_but_enableable            4
no_driver_in_5_15                  320
```

| compatible | nodes | 5.15 driver | Kconfig | state | class |
|---|--:|---|---|---|---|
| `arm,armv8-pmuv3` | 1 | arch/arm64/kernel/perf_event.c | CONFIG_HW_PERF_EVENTS | y | ENABLED |
| `arm,armv8-timer` | 1 | drivers/clocksource/arm_arch_timer.c | CONFIG_ARM_ARCH_TIMER | y | ENABLED |
| `arm,idle-state` | 7 | drivers/cpuidle/cpuidle-arm.c | CONFIG_ARM_CPUIDLE | y | ENABLED |
| `arm,psci-1.0` | 1 | drivers/cpuidle/cpuidle-psci-domain.c | CONFIG_ARM_PSCI_CPUIDLE_DOMAIN | y | ENABLED |
| `fixed-clock` | 3 | drivers/clk/clk-fixed-rate.c | CONFIG_COMMON_CLK | y | ENABLED |
| `mediatek,generic-tphy-v1` | 1 | drivers/phy/mediatek/phy-mtk-tphy.c | CONFIG_PHY_MTK_TPHY | y | ENABLED |
| `mediatek,mt6358-pmic` | 1 | drivers/mfd/mt6397-core.c | CONFIG_MFD_MT6397 | y | ENABLED |
| `mediatek,mt6358-rtc` | 1 | drivers/rtc/rtc-mt6397.c | CONFIG_RTC_DRV_MT6397 | y | ENABLED |
| `mediatek,mt6577-uart` | 2 | drivers/tty/serial/8250/8250_mtk.c | CONFIG_SERIAL_8250_MT6577 | y | ENABLED |
| `mediatek,mt6768-pinctrl` | 1 | drivers/pinctrl/mediatek/pinctrl-mt6768.c | CONFIG_PINCTRL_MT6768 | y | ENABLED |
| `mediatek,mt6768-pwrap` | 1 | drivers/soc/mediatek/mtk-pmic-wrap.c | CONFIG_MTK_PMIC_WRAP | y | ENABLED |
| `simple-bus` | 1 | drivers/bus/simple-pm-bus.c | CONFIG_OF | y | ENABLED |
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
| `mediatek,apmixed\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,atf_logger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,audio\0syscon` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,camsys\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ccci_ccif` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ccci_cldma` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ccu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,charger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,chipid` | 1 | - | - | - | NO_DRIVER |
| `mediatek,chn_emi` | 1 | - | - | - | NO_DRIVER |
| `mediatek,cmdq-bdg-test` | 1 | - | - | - | NO_DRIVER |
| `mediatek,common-infracfg_ao\0mediatek,infracfg_ao\0syscon` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,gce\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,ged` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gic500` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gic_cpu` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gpio\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,gpio_usage_mapping` | 1 | - | - | - | NO_DRIVER |
| `mediatek,hacc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,hw_dbg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,i2c` | 9 | - | - | - | NO_DRIVER |
| `mediatek,i2c_common` | 1 | - | - | - | NO_DRIVER |
| `mediatek,imgsys\0syscon` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,m4u` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mailbox-gce-bdg` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mailbox-gce-svp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mali\0arm,mali-valhall` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,mddriver\0mediatek,mddriver-mt6768` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_ccorr0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_rdma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_rsz0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_rsz1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_tdshp0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_wdma0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mdp_wrot0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,memory-ssmr-features` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mfgcfg\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi0a\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi0b\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi1a\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi1b\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi2a\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_rx_ana_csi2b\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mipi_tx0` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mm_mutex` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mmdvfs_pmqos` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mmsys_config\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,modem_temp_share` | 1 | - | - | - | NO_DRIVER |
| `mediatek,msdc` | 2 | - | - | - | NO_DRIVER |
| `mediatek,msdc0_top` | 1 | - | - | - | NO_DRIVER |
| `mediatek,msdc1_top` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-charger` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-cpufreq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-cqdma-v1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt-pmic` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6358-auxadc` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,mt6765-spi` | 6 | drivers/spi/spi-mt65xx.c | CONFIG_SPI_MT65XX | - | DISABLED |
| `mediatek,mt6768-auxadc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-camsys\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-consys` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-devapc` | 1 | drivers/soc/mediatek/devapc/devapc-mt6768.c | CONFIG_DEVAPC_MT6768 | - | DISABLED |
| `mediatek,mt6768-dvfsp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-gce` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-gpufreq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-imgsys\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-mcdi` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-mmc` | 2 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-mt6358-sound` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-sound` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-timer\0mediatek,mt6765-timer\0mediatek,sys_timer` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-usb20` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-vcodec-dec` | 1 | drivers/media/platform/mtk-vcodec/mtk_vcodec_dec_drv.c | - | - | UNKNOWN |
| `mediatek,mt6768-vcodec-enc\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,mt6768-wdt\0mediatek,mt6589-wdt\0mediatek,toprgu\0syscon\0simple-mfd` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,pericfg\0syscon` | 1 | - | - | - | NO_DRIVER |
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
| `mediatek,scpsys\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,security_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf2` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf3` | 1 | - | - | - | NO_DRIVER |
| `mediatek,seninf4` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sleep` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sleep_reg_md` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_common` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb0\0mediatek,smi_larb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb1\0mediatek,smi_larb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb2\0mediatek,smi_larb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb3\0mediatek,smi_larb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,smi_larb4\0mediatek,smi_larb` | 1 | - | - | - | NO_DRIVER |
| `mediatek,snd_scp_spk` | 1 | - | - | - | NO_DRIVER |
| `mediatek,speaker_amp` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sramrom` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sspm` | 1 | - | - | - | NO_DRIVER |
| `mediatek,sys_cirq` | 1 | - | - | - | NO_DRIVER |
| `mediatek,tee_sanity` | 1 | - | - | - | NO_DRIVER |
| `mediatek,therm_ctrl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,topckgen\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,topckgen_ao` | 1 | - | - | - | NO_DRIVER |
| `mediatek,topmisc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trng` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trusted_mem` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trusty-gz` | 1 | - | - | - | NO_DRIVER |
| `mediatek,trusty-mtee-v1` | 1 | - | - | - | NO_DRIVER |
| `mediatek,usb1p_sif` | 1 | - | - | - | NO_DRIVER |
| `mediatek,vdec` | 1 | - | - | - | NO_DRIVER |
| `mediatek,vdec_gcon\0syscon` | 1 | - | - | - | NO_DRIVER |
| `mediatek,vdec_mbist_ctrl` | 1 | - | - | - | NO_DRIVER |
| `mediatek,venc` | 1 | - | - | - | NO_DRIVER |
| `mediatek,venc_gcon\0syscon` | 1 | - | - | - | NO_DRIVER |
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

320 compatibles in this board's DTB have **no driver in 5.15 at all** - these are the
driver transplants, not fragment edits. First 60:

* `android,nebula-gz-log-v1` (1 node)
* `android,nebula-irq-v1` (1 node)
* `android,nebula-smc-v1` (1 node)
* `android,nebula-virtio-v1` (1 node)
* `android,trusty-gz-log-v1` (1 node)
* `android,trusty-irq-v1` (1 node)
* `android,trusty-smc-v1` (1 node)
* `android,trusty-virtio-v1` (1 node)
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
* `mediatek,bat_gm30` (1 node)
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

## Fragment written

`None` - 4 symbols:

```
CONFIG_ARM_DSU_PMU=y
CONFIG_DEVAPC_MT6768=y
CONFIG_MTK_UART_APDMA=y
CONFIG_SPI_MT65XX=y
```

## PMIC: pwrap + MT6358 (enabled this round)

### What the board's DTB actually says

    pwrap@1000d000 {
            compatible = "mediatek,mt6768-pwrap";
            reg = <0 0x1000d000 0 0x1000>;  reg-names = "pwrap";
            interrupts = <0 0xc2 4>;         /* SPI 194 */
            clocks = <&clk32k>, <&clk26m>;   clock-names = "spi", "wrap";
            mt6358-pmic { compatible = "mediatek,mt6358-pmic";  /* 145-irq controller */
                          mt-pmic, mt6358-auxadc, mtk_ts_pmic, mt6358-regulator,
                          mt6358-rtc, mt6358-misc } }

Read out of `dts/mt6768.dts.dump` (the decompiled built DTB), not from a tool's node
table: an earlier summary of mine attributed `mediatek,mt-pmic` to the pwrap node itself,
which is a `dtbnodes.py` regex artifact - `mt-pmic` is a *grandchild*.

### Why 5.15 could not drive it, and what was added

`drivers/soc/mediatek/mtk-pmic-wrap.c` in v5.15.220 matches mt2701/mt6765/mt6779/mt6797/
mt6873/mt7622/mt8135/mt8173/mt8183/mt8195/mt8516 - there is no mt6768 entry - and
`pwrap_probe()` additionally returns `-EINVAL` unless the pwrap node's *first child* is in
`of_slave_match_tbl` (which lists `mediatek,mt6358`, not `mediatek,mt6358-pmic`). So both
tables had to learn this board's strings.

**Register evidence for which mainline description fits.** Compared by offset against the
vendor's own MT6768 PMIC-wrap map (`drivers/misc/mediatek/pmic_wrap/mt6768/pwrap_hal.h`,
257 register defines):

| mainline table | shared names | identical | differing |
|---|---|---|---|
| `mt8183_regs` | 43 | **43** | 0 |
| `mt6765_regs` | 20 | 6 | 14 |
| `mt6779_regs` | 30 | 6 | 24 |
| `mt6797_regs` | 20 | 5 | 15 |
| `mt2701/mt7622/mt8135/mt8173/mt8516_regs` | 48-84 | 4-5 | 43-79 |

`mt6765_regs` is the one a "MT6768 is an MT6765 derivative" guess would have reused, and it
is wrong here: RDDMY 0x14 vs 0x20, HARB_HPRIO 0x5C vs 0x68, MAN_CMD 0x74 vs 0x80,
WACS0_EN 0x80 vs 0x8C, INIT_DONE2 0x94 vs 0xA0, TIMER_EN 0xE4 vs 0xE8, DCM 0x1D0 vs 0x1DC.
Every one of mt8183's 48 offsets also *exists* on MT6768; the five that looked "absent"
(HIPRIO_ARB_EN, INT_EN, INT_FLG, INT_CLR, WDT_SRC_EN) are present under the vendor's names
`HPRIO_ARB_EN`@0x60, `INT0_EN`@0xB0, `INT0_FLG`@0xB8, `INT0_CLR`@0xBC, `WDT_SRC_EN_0`@0xF0.

So `pwrap_mt6768` reuses `.regs = mt8183_regs`, `PWRAP_MT8183` (the enum names the wrapper
generation, not the SoC) and `pwrap_mt8183_init_soc_specific()` - that function only writes
STAUPD_GRPEN 0x34, CRC_EN 0xE0, SIG_ADR 0xD0, EINT_STA0_ADR 0x38 and the P2P/MD32 WACS +
INIT_DONE pair, all verified identical on MT6768, and MT6768 really does have those extra
masters (the DTB carries `pwrap_p2p@1005cb000`, `pwrap_md32@10448000`).

Three fields are **not** MT8183's, because MT6768's BSP says otherwise: `arb_en_all`
`0x3fa65` (vendor `pwrap_hal.c:901`; MT8183 uses `0x3fa75` - bit 4 differs, i.e. a
different set of bus masters may touch the PMIC), `int1_en_all` `0xffffffff` (MT8183 masks
to `0xeef7ffff`); `int_en_all` `0xffffffff` happens to agree. Left clear on purpose:
`PWRAP_CAP_DCM` - MT6768 has DCM_EN/DCM_DBC_PRD at 0x1D0/0x1D8, which `mt8183_regs` does not
describe, so enabling the generic DCM path would have pointed it at offset 0. Cost: the
debounce-counter diagnostic stays off (as on every MT8183-class board mainline supports).
No register is written at a wrong address either way.

### Dependency chain now enabled

`MEDIATEK_MT6577_AUXADC` is compiled but does **not** bind: 5.15's `mt6577_auxadc.c` lists
mt2701/mt2712/mt6765/mt7622/mt8173-auxadc only, while this board has `mediatek,mt6768-auxadc`
and `mediatek,mt6358-auxadc`. That alias needs its own register evidence and is left open -
it is what the charger/battery temperature and Ra measurements go through, so it gates the
OPLUS charging round.

Regulators: mainline `drivers/regulator/mt6358-regulator.c` builds all
`MT6358_MAX_REGULATOR` descriptors from static tables (`MT6358_BUCK("buck_vdram1", VDRAM1,
...)`, offsets from `include/linux/mfd/mt6358/registers.h`) and has no `of_match_table` -
it binds as the MFD cell `mt6358-regulator` that `mt6397-core.c` creates, and its
per-regulator DT child names (`buck_vdram1`, ...) are the same names this DTB uses.
**This retracts my earlier statement that "regulators will not bind from the vendor DT
because it lacks mainline's `reg = <shift width mask>` encoding"**: that encoding belongs to
mt6323/mt6397, not mt6358.

RTC: `RTC_DRV_MT6397` *depends on MFD_MT6397*, so before this round it could not be enabled
at all - `scripts/config --enable` was silently reverted by olddefconfig, which is why an
earlier note of mine recorded it as "already enabled, blocked at probe". It is now `=y`,
which is the accurate story: enabling the MFD is what makes an existing driver usable.

Still vendor-only after this round: `mediatek,mt-pmic` (no `drivers/input/misc/
mtk-pmic-keys.c` in this base at all, so power-key/home-key stay unbound), `mtk_ts_pmic`,
`mt6358-misc`, `mt6358-sound` (cell exists, no 5.15 machine driver for this board),
`mediatek,pwraph`/`pwrap_p2p`/`pwrap_md32`/`pwrap_mpu`.

### Verification performed (and not)

* both `.o` files carry the new strings: `strings mtk-pmic-wrap.o | grep -E
  'mt6768-pwrap|mt6358-pmic'` -> 2 hits; `mt6397-core.o` -> 1.
* `nm vmlinux | grep pwrap_mt6768` -> `ffff8000098fceb8 d pwrap_mt6768`; 38 pwrap symbols total.
* `make Image.gz-dtb modules`: 0 compiler errors, 0 make failures; `Image.gz-dtb`
  11,061,273 B (+1,937 over build-30); `modules_ko` unchanged at 840 (all five new drivers
  are built-in). `Image` itself stayed at 26,963,976 B = 6586 pages - page-count-granular,
  so *do not* read "same Image size" as "nothing added"; the gz+DTB number is the sensitive one.
* `bin/hwenable.py` per-compatible rows now resolve: `mediatek,mt6768-pwrap` ->
  `drivers/soc/mediatek/mtk-pmic-wrap.c`, `mediatek,mt6358-pmic` ->
  `drivers/mfd/mt6397-core.c`, `mediatek,mt6358-rtc` -> `drivers/rtc/rtc-mt6397.c`.
* **Not verified: anything runtime.** No board, so no claim that the wrapper actually talks
  to the PMIC, that the watchdog source mask is right, or that PMIC EINT delivery works. The
  offset comparison is the strongest evidence obtainable here; it is not a boot test.
