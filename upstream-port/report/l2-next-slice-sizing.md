# Next-slice sizing, measured: why DSI/LCM cannot land yet, and what can

Follows the human decision recorded as 148 ("keep deferring the record-write half; the next work is the
DSI/LCM layer that would actually need it", chosen 2026-09-05 after 0088). This round sized that
instruction against the tree instead of starting it, because the sizing changes what the slice has to be.
Everything below is measured; no file was copied into the landing tree and nothing was published.

## 1. Every remaining vendor `dispsys` file is blocked, individually

`l2slice.py`'s gate left seven of stock's twenty built objects unlanded (stock's own
`video/mt6768/dispsys/Makefile:79-107` - `ddp_dpi` is `#obj-y` and `ddp_dbi` is absent, so neither is in
scope). Each was compiled **in isolation** against the landed include set in the scratch tree
(`portwork/buildfull` at the published tip `1a7cf42b066c…`, primed to 15/15 objects with 0 errors first),
one at a time, with the object line gated on `CONFIG_MTK_DISP_BRINGUP`:

| file | lines | builds? | first hard error (verbatim cause) |
|---|---|---|---|
| `ddp_ovl.c` | 2823 | no | fatal error: `mtk_dramc.h`: No such file |
| `ddp_path.c` | 987 | no | fatal error: `ddp_ovl.h`: No such file (via `ddp_info.h:15`) |
| `ddp_rdma_ex.c` | 1649 | no | same, via `ddp_info.h:15` |
| `ddp_wdma_ex.c` | 1330 | no | same |
| `ddp_mmp.c` | 934 | no | same |
| `ddp_disp_bdg.c` | 5263 | no | same |
| `ddp_dsi.c` | 8377 | no | fatal error: `ddp_mmp.h`: No such file (via `ddp_debug.h:10`); earlier probe also shows `disp_dts_gpio.h` missing at `ddp_dsi.c:35` |

The include chain is not the only gate. `grep -c "cmdqRec" drivers/misc/mediatek/video/mt6768/dispsys/ddp_ovl.c`
= **35 record-API references**, including `cmdqRecWriteSecure` (`:678`, `:710`), `cmdqRecWriteSecureMetaData`
(`:684`, `:716`) and `cmdqRecSetSecure` (`:977`) - the *secure* record path, which 0083 never provided (it
landed four entry points, `cmdqRecWrite` among them, and explicitly not the secure ones). So even with the
headers landed, the component layer would add a second, larger deferral-shaped gap.

Method note: the first pass of this probe produced nonsense ("0 distinct unresolved names", an
`mtk_ion.h` failure from a *landed* file) because the scratch tree had untracked vendor copies of
`ddp_m4u.h` and friends left in `dispsys/` by earlier rounds. `git clean -fq` on the two slice directories
plus a re-primed 15/15 build was required before the numbers above became trustworthy. A scratch tree is
not a baseline until it reproduces the published gate.

## 2. The LCM half lands on a different trap: the bias glue is a config-selected *behaviour*

The landed display core's remaining references into the panel side are exactly two names, both from
`ddp_drv.o` (`nm -u`, cross-checked against `undeps.py`'s provider census):

```
disp_late_bias_enable      PROVIDER NOT LANDED   drivers/misc/mediatek/lcm/lcm_pmic.c    ddp_drv.o
display_bias_regulator_init PROVIDER NOT LANDED  drivers/misc/mediatek/lcm/lcm_pmic.c    ddp_drv.o
```

`lcm_pmic.c` is 149 lines, so it looks like the cheapest slice in the project. It is not: the whole file is

```c
#if defined(CONFIG_RT5081_PMU_DSV) || defined(CONFIG_MT6370_PMU_DSV)
        /* regulator_get(NULL, "dsv_pos"/"dsv_neg"), regulator_set_voltage(5.4 V), regulator_enable() */
#else
        int display_bias_regulator_init(void) { return 0; }
        int display_bias_enable(void)         { return 0; }
        int disp_late_bias_enable(void)       { return 0; }
        int display_bias_disable(void)        { return 0; }
#endif
```

and this board's own config selects the **first** branch: `arch/arm64/configs/even_defconfig:1693`
`CONFIG_MT6370_PMU_DSV=y` (the second, `RT5081_PMU_DSV`, is not set). `CONFIG_MT6370_PMU_DSV` does not
exist in 5.15, so landing the file as-is would compile the `#else`: the link references would be
"closed" by replacing two regulator enables with `return 0`. That is the same failure mode this project
has already rejected twice (the CPU-substitute for `ddp_reg.h`, the silent-drop `cmdqRecWrite` shim) - a
symbol that exists so the link succeeds while the hardware action disappears. `display_bias_setting()` in
`lcm_i2c.c` is not an escape either: nothing in the landed tree references it (`grep -c` over the provider
census = 0), and `lcm_i2c.c` includes `platform/upmu_common.h`, `mach/mt_pm_ldo.h`, `cust_i2c.h` - the
unported 4.19 platform-header set.

## 3. What actually unblocks the bias path, sized

`regulator_get(NULL, "dsv_pos")` needs a provider. In the vendor tree that is the MT6370 PMU:
`drivers/misc/mediatek/pmic/mt6370/` = 13 `.c` files / **15,200 lines**, with `MT6370_PMU_DSV` defined at
`drivers/misc/mediatek/pmic/mt6370/Kconfig:71` as `depends on REGULATOR && MFD_MT6370_PMU` and building
`mt6370_pmu_dsv.o mt6370_pmu_dsv_debugfs.o` (`Makefile:16`). The useful slice is smaller than the
directory: MFD core + regmap/i2c + the DSV cell, i.e. `mt6370_pmu_core.c`, `mt6370_pmu_i2c.c`,
`mt6370_pmu_reg.c`, `mt6370_pmu_irq.c` as needed and `mt6370_pmu_dsv.c` (584 lines) - and it is the same
shape of work as 0075 (pwrap + MT6358 node-name alias), including the `regulator_get(NULL, name)` alias
question that 0075 already had to answer for the MT6358 supplies.

Good news from the DT side, measured rather than hoped: 0070's transplant **already landed**
`arch/arm64/boot/dts/mediatek/mt6370.dtsi` and `mt6370_pd.dtsi`, and the landed `mt6768.dts` references the
sub-PMIC (`flashlights_mt6370` at `:3710`, `charger = <&mt6370_chg>` at `:3989`, `subpmic_pmu_eint` at
`:4002`), so the node the DSV cells would hang off exists in the audited tree. Whether it carries the
`dsv-pos`/`dsv-neg` regulator children is the first thing to measure when this slice starts; if it does
not, that is a DT change (a deviation from stock) and another human decision, not a licence to invent.

## 4. Ranking of candidate next slices, by what they close and what they cost

| # | slice | closes | new gaps it opens | honest? |
|---|---|---|---|---|
| 1 | **MT6370 PMU DSV provider (+ `lcm_pmic.c`)** | 2 refs from `ddp_drv.o`, and the bias/power-on sequence becomes real | MFD + regmap + i2c porting work; possibly a DT child node | yes - it is the only route where the landed caller does what stock does |
| 2 | Component header closure (`ddp_ovl.h`, `ddp_mmp.h`, `mtk_dramc.h`, `disp_dts_gpio`) | 0 (headers only) | carries dead weight if no object lands with it | weak on its own, needed by #3 |
| 3 | Component layer (`ddp_ovl.c` + `ddp_path.c`) after the record half | ~10s of refs | needs `cmdqRecWriteSecure`/`_MetaData`/`SetSecure` - a *second*, bigger deferral | only after the record decision changes |
| 4 | `lcm_pmic.c` alone, `#else` branch | 2 refs, cosmetically | none - and that is the problem | **no**: substitutes stock's regulator enables with `return 0` |

Recommendation: #1. #3 is gated on the choice made in 148, and #4 would violate it indirectly.
