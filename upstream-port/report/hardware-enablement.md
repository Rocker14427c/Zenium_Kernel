# Device hardware enablement, derived from the built `mt6768.dtb`

Source of truth: `dtc -I dtb -O dts` of the image this device would boot, then 5.15's
`of_device_id` tables and the Makefile line that builds each matching driver. A row is
*ENABLED* only if the Kconfig that builds that driver is `y`/`m` in the build config.

```
dtb_nodes_with_compatible          399
distinct_comptibles_in_built_dtb   325
bound_by_5_15_driver               21
enabled_in_this_build              15
disabled_but_enableable            4
no_driver_in_5_15                  304
```

| compatible | nodes | 5.15 driver | Kconfig | state | class |
|---|--:|---|---|---|---|
| `arm,armv8-pmuv3` | 1 | arch/arm64/kernel/perf_event.c | CONFIG_HW_PERF_EVENTS | y | ENABLED |
| `arm,armv8-timer` | 1 | drivers/clocksource/arm_arch_timer.c | CONFIG_ARM_ARCH_TIMER | y | ENABLED |
| `arm,idle-state` | 7 | drivers/cpuidle/cpuidle-arm.c | CONFIG_ARM_CPUIDLE | y | ENABLED |
| `arm,psci-1.0` | 1 | drivers/cpuidle/cpuidle-psci-domain.c | CONFIG_ARM_PSCI_CPUIDLE_DOMAIN | y | ENABLED |
| `fixed-clock` | 3 | drivers/clk/clk-fixed-rate.c | CONFIG_COMMON_CLK | y | ENABLED |
| `mediatek,generic-tphy-v1` | 1 | drivers/phy/mediatek/phy-mtk-tphy.c | CONFIG_PHY_MTK_TPHY | y | ENABLED |
| `mediatek,mt6358-auxadc` | 1 | drivers/iio/adc/mt635x-auxadc_v1.c | CONFIG_MT635X_AUXADC | y | ENABLED |
| `mediatek,mt6358-pmic` | 1 | drivers/mfd/mt6397-core.c | CONFIG_MFD_MT6397 | y | ENABLED |
| `mediatek,mt6358-rtc` | 1 | drivers/rtc/rtc-mt6397.c | CONFIG_RTC_DRV_MT6397 | y | ENABLED |
| `mediatek,mt6577-uart` | 2 | drivers/tty/serial/8250/8250_mtk.c | CONFIG_SERIAL_8250_MT6577 | y | ENABLED |
| `mediatek,mt6768-auxadc` | 1 | drivers/iio/adc/mt6577_auxadc.c | CONFIG_MEDIATEK_MT6577_AUXADC | y | ENABLED |
| `mediatek,mt6768-pinctrl` | 1 | drivers/pinctrl/mediatek/pinctrl-mt6768.c | CONFIG_PINCTRL_MT6768 | y | ENABLED |
| `mediatek,mt6768-pwrap` | 1 | drivers/soc/mediatek/mtk-pmic-wrap.c | CONFIG_MTK_PMIC_WRAP | y | ENABLED |
| `simple-bus` | 1 | drivers/bus/simple-pm-bus.c | CONFIG_OF | y | ENABLED |
| `syscon-reboot-mode` | 1 | drivers/power/reset/syscon-reboot-mode.c | CONFIG_SYSCON_REBOOT_MODE | y | ENABLED |
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
| `mediatek,mailbox-gce-bdg` | 1 | - | - | - | NO_DRIVER |
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

## AUXADC, PMIC supplies, and the eMMC host (this round)

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
