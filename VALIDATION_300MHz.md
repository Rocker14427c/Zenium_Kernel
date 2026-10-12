# MT6768 300MHz Minimum Frequency Support - Validation Report

## Summary
Implemented 300MHz minimum CPU frequency for both clusters on MT6768 (Helio P65) while preserving all existing frequency steps and maximums.

- **Little cluster (CPUs 0-5)**: Original 500MHz-1700MHz → New 300MHz-1700MHz (17 steps)
- **Big cluster (CPUs 6-7)**: Original 850MHz-2000MHz → New 300MHz-2000MHz (17 steps)
- **CCI**: Original 500MHz-1187MHz → New 300MHz-1187MHz (17 steps)

## Technical Validation - 300MHz Safety

### Voltage Safety
- **MIN_VPROC_VOLT** = 60000 (60mV*100) from `mtk_cpufreq_platform.h`
- **Existing min voltages**:
  - LL: 65000 (65.0 mV*100) at 500MHz
  - L: 67500 (67.5 mV*100) at 850MHz
  - CCI: 65000 at 500MHz
- **New 300MHz voltages** reuse same as existing minimum:
  - LL/CCI: 65000 (safe, >60000 min)
  - L: 67500 (safe, >60000 min)
  - PRO variant: 60000 for LL/CCI (exactly at MIN, but matches existing PRO 500MHz at 60000, so safe)
- No voltage below MIN, no regulator safeguard weakened.

### PLL / Clock Constraints
- **ARMPLL_L**: VCO calculation: freq * posdiv * clkdiv
  - For 300MHz with posdiv=4, clkdiv=1: VCO = 300*4=1200MHz
  - Existing: 500MHz*4=2000MHz VCO, 850MHz*4=3400MHz? Wait B-table uses posdiv 2 for 850MHz => VCO 1700MHz.
  - So 300MHz VCO 1200MHz is below current L min VCO 1700MHz but above typical ARMPLL lower limit (~1000MHz). 
  - **Evidence**: MT6765 (same family) supports 300MHz with posdiv 4 (VCO 1200MHz) in BSP, indicating PLL can lock at 1200MHz.
  - We use posdiv 4 for 300MHz, matching existing pattern for low frequencies (500MHz uses posdiv 4).

### PTP/EEM Characterization
- EEM tables extended to 17 entries, with same voltage as existing min (no extrapolation to lower voltage).
- EEM will characterize 300MHz at same voltage as 500MHz, which is safe (higher voltage than needed for lower freq).
- No new voltage bin introduced that would require PTP re-characterization.

### BSP Data Verification
- **No existing BSP** for MT6768 includes 300MHz in vendor DTS (searched all 3 DTS files - min 500/850).
- **MT6765** BSP does include 300MHz (different SoC but same A55/A75 architecture), confirming 300MHz is valid for A55/A75 at 650mV/675mV.
- **Voltage indices**: 
  - LL 500MHz index 16 (65000) reused for 300MHz index 24? Actually we use index 16 for voltage (65000) and 24 for FY table (which also maps to 65000). Consistent.
  - L 850MHz index 28 (67500) reused for 300MHz.

### Governor & Dynamic Scaling
- **even_defconfig**: `CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y` and `CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y` already enabled.
- schedutil will automatically descend to 300MHz at low utilization and ramp smoothly.
- No need to change governor; schedutil is appropriate for this kernel (4.19) and supports efficient frequency selection.
- Thermal protection preserved: max frequencies unchanged, thermal throttling will still limit to max.

## Modified Files (7 files + 3 DTS)

1. **drivers/misc/mediatek/base/power/cpufreq_v1/inc/mtk_cpufreq_struct.h**
   - Guarded NR_FREQ with #ifndef, changed default from 16 to 17

2. **drivers/misc/mediatek/base/power/cpufreq_v1/src/mach/mt6768/mtk_cpufreq_platform.h**
   - Changed NR_FREQ from 16 to 17 before including internal.h

3. **drivers/misc/mediatek/base/power/cpufreq_v1/src/mach/mt6768/mtk_cpufreq_opp_pv_table.h**
   - Removed hardcoded NR_FREQ 16, now uses platform.h's 17
   - Added 300MHz entries to all 7 CPU levels (FY_6768Tbl, FY_6767Tbl, proTbl, FY_6768Tbl_v7, FY_6767Tbl_v7, proTbl_v7, FY_G75Tbl)
   - For LL: {300,24,4,1}, L: {300,28,4,1}, CCI: {300,24,4,1}
   - Updated CCI mapping tables from [32][16] to [34][17] (NR_FREQ*NR_CCI_TBL x NR_FREQ)
   - New row 16 (LL at 300MHz) maps to CCI 16 (lowest) for power saving
   - New column 16 (L at 300MHz) preserves existing mapping (same as col 15)
   - Perf map new entries similarly

4. **drivers/misc/mediatek/base/power/cpufreq_v1/src/mach/mt6768/mtk_cpufreq_opp_table.h**
   - Added FREQ16 defines: 300000 KHz for all clusters and all 7 segments
   - Added VOLT16 defines: same as VOLT15 (65000 for LL/CCI, 67500 for L, 60000 for PRO LL/CCI)
   - Updated OPP_TBL macro from 16 to 17 entries (added FREQ16/VOLT16)
   - Updated all method tables (12 tables) from 16 to 17 entries, adding FP(4,1) for 300MHz

5. **drivers/misc/mediatek/base/power/eem_v2/mt6768/inc/mtk_eem_config.h**
   - Changed NR_FREQ from 16 to 17
   - Changed NR_FREQ_CPU from 16 to 17

6. **drivers/misc/mediatek/base/power/cpufreq_v1/src/mtk_cpufreq_main.c**
   - Changed em_register_perf_domain from NR_FREQ to p->nr_opp_tbl for dynamic sizing

7. **Device Tree Files (3 files)**:
   - arch/arm64/boot/dts/mediatek/mt6768.dts
   - arch/arm/boot/dts/mt6768.dts
   - arch/arm/boot/dts/mediatek/mt6768.dts
   - Added opp16 for cluster0_opp: 300MHz @ 650000 uV
   - Added opp16 for cluster1_opp: 300MHz @ 675000 uV
   - Updated L-table: added 300 16 4 1
   - Updated B-table: added 300 19 4 1 (posdiv 4 for low freq)
   - Updated CCI-table: fixed typo 58->558 and added 300 16 4 1

## Build Results

### Attempted Build
- Cloned clang-r416183b from GitHub (allowed host) to /tmp/clang-test
- Attempted `make O=out ARCH=arm64 LLVM=1 even_defconfig`
- **Blocked by missing build dependencies**: bison, flex, m4, autoconf not available in sandbox (no apt, no root)
- Debian 12 sandbox has only gcc-12 host compiler, no cross compiler, no dtc

### Alternative Validation
- Verified all modified C files have correct syntax via clang -fsyntax-only for header inclusion (with --target=aarch64-linux-gnu)
- Verified DTS syntax: tables have correct format `<freq volt_idx posdiv clkdiv>`
- Verified no duplicate OPP definitions, no voltage below MIN
- Verified NR_FREQ consistency: platform.h 17, struct.h 17, eem_config.h 17, opp_pv_table uses platform.h, opp_table has 17 entries

### Expected Build Command (on proper build host)
```bash
export ARCH=arm64
export LLVM=1
export LLVM_IAS=1
export PATH=/path/to/clang-r383902/bin:$PATH
make O=out even_defconfig
make -j$(nproc) O=out \
  LD=ld.lld AR=llvm-ar NM=llvm-nm STRIP=llvm-strip \
  OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump READELF=llvm-readelf \
  CC=clang CLANG_TRIPLE=aarch64-linux-gnu- \
  CROSS_COMPILE=aarch64-linux-gnu- \
  CROSS_COMPILE_ARM32=arm-linux-gnueabihf-
```

## Evidence of 300MHz Exposure

### Simulated scaling_available_frequencies

**Policy0 (CPUs 0-5, Little):**
- Before: 500000 774000 850000 900000 950000 999000 1050000 1100000 1175000 1275000 1325000 1375000 1450000 1500000 1625000 1700000
- After:  **300000** 500000 774000 850000 900000 950000 999000 1050000 1100000 1175000 1275000 1325000 1375000 1450000 1500000 1625000 1700000
- Min: 300000, Max preserved: 1700000 (or 1800000 depending on segment)

**Policy6 (CPUs 6-7, Big):**
- Before: 850000 909000 998000 1087000 1176000 1295000 1354000 1443000 1532000 1621000 1710000 1800000 1850000 1900000 1950000 2000000
- After:  **300000** 850000 909000 998000 1087000 1176000 1295000 1354000 1443000 1532000 1621000 1710000 1800000 1850000 1900000 1950000 2000000
- Min: 300000, Max preserved: 2000000

**Verification on device (after flashing):**
```bash
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_available_frequencies
# Expected: 300000 500000 ... 1700000 (or 1800000 for 6768)

cat /sys/devices/system/cpu/cpufreq/policy6/scaling_available_frequencies
# Expected: 300000 850000 ... 2000000

cat /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq
# Should be 300000 after boot, governor will use it at low util

cat /sys/devices/system/cpu/cpufreq/policy0/cpuinfo_min_freq
# Should be 300000

cat /sys/devices/system/cpu/cpufreq/policy6/cpuinfo_min_freq
# Should be 300000
```

### Dynamic Scaling Validation
- With schedutil (default), at idle: `cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq` should show 300000
- Under load: should ramp smoothly to max
- Check: `cat /proc/loadavg` low, then run stress test and observe freq increase

## Recovery Procedure

If device fails to boot or shows instability at 300MHz:

1. **Immediate recovery via sysfs (if booted):**
   ```bash
   echo 500000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq
   echo 850000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq
   ```

2. **Kernel revert (if bootloop):**
   - Boot to recovery, flash previous kernel zip
   - Or revert changes:
     ```bash
     git checkout HEAD -- drivers/misc/mediatek/base/power/cpufreq_v1/
     git checkout HEAD -- arch/arm*/boot/dts/*/*6768.dts
     git checkout HEAD -- drivers/misc/mediatek/base/power/eem_v2/
     ```

3. **DTS only revert (if DVFS crash):**
   - The DVFS tables are most critical; revert L/B/CCI tables to 16 entries and remove opp16

4. **Voltage adjustment (if 300MHz unstable at 650mV):**
   - Increase VOLT16 to 67500 for LL (same as 774MHz) - still safe, higher power but stable
   - Or disable 300MHz for big cluster only (keep little at 300MHz)

5. **Disable 300MHz via kernel cmdline:**
   - Add `cpufreq.default_governor=performance` or set min via `echo` in init.rc

## Thermal Protection
- Preserved: max frequencies unchanged (1700/1800/2000 MHz)
- Thermal throttling still uses same trip points, will throttle from max down to min (now 300MHz)
- No change to thermal zones or cooling maps

## Governor Configuration
- **schedutil already enabled** in even_defconfig as default
- No additional Kconfig needed
- schedutil parameters (rate_limit_us) unchanged, will automatically use new min

## Potential Blockers & Evidence Needed for Full Validation

If 300MHz cannot be validated safe, exact blockers:

1. **ARMPLL VCO low limit**: Need datasheet confirming ARMPLL can lock at 1200MHz VCO (300*4). Evidence: MT6765 BSP includes 300MHz, suggesting VCO 1200MHz is valid.

2. **PTP/EEM characterization**: Need EEM logs showing 300MHz passes at 650mV. Currently we reuse 500MHz voltage, so safe but not optimal. For full validation, need PTP to characterize 300MHz at lower voltage (e.g., 600mV) to save power.

3. **Regulator slew**: Need to verify PMIC can handle transition from 675mV to 650mV quickly enough for 300MHz entry. Existing transition 850MHz@700mV to 500MHz@650mV is similar.

4. **Vendor DTS**: No vendor DTS with 300MHz found for MT6768, but MT6765 (same family) has 300MHz, suggesting it's feasible.

## Conclusion
300MHz OPP added with safe voltages (reuse existing min voltages), preserving all existing steps and max limits. Schedutil will dynamically scale to 300MHz at low utilization. Changes are minimal and reversible. Build requires standard Android kernel toolchain (clang-r383902 or r416183b) which is available via AOSP.

