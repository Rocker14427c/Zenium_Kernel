# Display bring-up: minimum complete chain to a real panel (planning gate)

Status of this document: **scoping + environment record**; layer L0 (panel/DT identification) is
closed by `report/panel-identification.md` and `report/panel-path-analysis.md` (init sequences, gate IC,
the LK name handover, minimum-path sizing). L1-L5 are scoped on paper but still gated on a
toolchain. No display code was ported in this
round, because the build/link gate the plan requires cannot be run in this sandbox any more
(section 5). Everything measured below is grep/wc output from the 4.19 vendor tree in this
repository (`/home/user/Zenium_Kernel`), with `file:line` for each hardware fact.

## 1. What the board's own DT says (facts, not inference)

| fact | value | source |
|---|---|---|
| dispsys node | `compatible = "mediatek,dispsys"`, `mediatek,larb = <&smi_larb0>` | `arch/arm64/boot/dts/mediatek/mt6768.dts:3125-3127` |
| dispsys clocks | `<&scpsys SCP_SYS_DIS>`, `<&mmsys_config CLK_MM_SMI_COMMON/CLK_MM_SMI_LARB0/CLK_MM_SMI_COMM0/CLK_MM_SMI_COMM1>` | `mt6768.dts:3128-3132` |
| legacy fb node | `compatible = "mediatek,mtkfb"` (no `reg`) | `mt6768.dts:3122` |
| LCM selection | **by name at runtime, not by DT**: `# CONFIG_MTK_LCM_DEVICE_TREE_SUPPORT is not set` (even_defconfig:1715) leaves `disp_lcm.c`'s `LCM_DTS`/`lcm_params-*` parser out of the build, and `CONFIG_MTK_LCM_DEVICE_TREE_SUPPORT_PASCAL_E=y` (:1716, `lcm/Kconfig:27-35` inside `#ifdef OPLUS_BUG_STABILITY`) only changes signatures/tables - `lcm_common.h:27` pointer arg for `lcm_common_get_params()`, `lcm_define.h:13` LCM_FUNC_GPIO/I2C/UTIL/CMD tables, `lcm_i2c.c:65-116` gate-IC client on bus 0 @0x3E "GATE_SM5109_OCP2130" with of_match "default". The selector is `mtkfb_lcm_name[256]` (`videox/mtkfb.c:182`, LK-filled, bounds-checked at :2311) | `report/panel-identification.md` 2 |
| display stack config | `CONFIG_MACH_MT6768=y` `:302`, `MTK_LCM=y` `:1713`, `MTK_FB=y` `:1719`, `MTK_M4U=y` `:1740`, `MTK_CMDQ_V3=y` `:1804`, `MTK_CMDQ=y` `:1805`, `MTK_CMDQ_MBOX=y` `:4452`, `MTK_SMI_EXT=y` `:1810`, `MTK_SMI=y` `:4621`, `MTK_CMDQ_TAB` off `:1806`, `MTK_CMDQ_MBOX_EXT` off `:1807` | `even_defconfig` (line numbers given) |
| panel identity | **resolved in `report/panel-identification.md`** (sections 1-2): this board's kernel compiles SIX LCM dirs (`CONFIG_CUSTOM_KERNEL_LCM`, even_defconfig:1714) and the three that apply are 720x1600 DSI video-mode panels - `ilt9882n_truly_even_hdp_dsi_vdo_lcm` (its readme: project S98670AA1, panel ili9881h+truly), `nt36525b_hlt_even_boe_hdp_dsi_vdo_lcm` (S91369AA1), `ilt7807s_hlt_even_hdp_dsi_vdo_lcm` (S91537AA1). The choice is made at runtime by the LK-supplied `mtkfb_lcm_name`, NOT by the device tree: `MTK_LCM_DEVICE_TREE_SUPPORT` is unset (:1715) so the `lcm_params-*` parser in `disp_lcm.c` is not compiled, and no DTS in the vendor tree carries those properties (measured negative). `lcm/Makefile:41-44` is what maps the defconfig string to the -D<PANEL> macros that gate `mt65xx_lcm_list.c`'s driver list | see `report/panel-identification.md` |

The four `CLK_MM_SMI_*` cells and `SCP_SYS_DIS` are already served by the ported clock provider:
`report/clkaudit.json` reports 234 refs / 234 registered / 0 unresolved on the packaged DTB, and
those cells resolve through `clk-mt6768-pg.c` (`KNOWN-ISSUES.md` 8.7) - so the dispsys core will
not be blocked by clocks, only by IP that is not in the tree yet.

## 2. Cost of each layer, measured

| layer | vendor content | LOC | verdict for "minimum complete" |
|---|---|---|---|
| dispsys core | `video/mt6768/dispsys/` | 34,419 | needed: `ddp_drv.c`, `ddp_base.c`, `ddp_disp_bdg.c`, `ddp_irq.c`, `ddp_pm.c`, the component set the board's path uses (`ddp_ovl`, `ddp_color`, `ddp_aal`, `ddp_gamma`, `ddp_ccorr`, `ddp_dither`, `ddp_merge`, `ddp_ufo`, `ddp_postalign`, `ddp_rd`, `ddp_dsi`), `ddp_info.c`, `ddp_reg.h` |
| shared IP | `video/common/` | 10,328 | only the blocks the dispsys path instantiates; `mtkfb_dummy.o` is excluded by `common/Makefile:103` under `MTK_FB=y` and `mtdummy/` by `video/Makefile:32` under `MTK_LCM=y`, so neither dummy fbdev is in scope |
| CMDQ v3 | `drivers/misc/mediatek/cmdq/v3/` | 29,317 total | **subset**: `cmdq_driver.c` 1,418 + `cmdq_device.c` + `cmdq_core.h`/`cmdq_def.h` + `cmdq_helper_ext.c` 5,610 (the gop/pkt API dispsys calls). `cmdq_test.c` 8,189 and `cmdq_mdp_common.c` 3,988 (MDP/corruption) are out; `cmdq_record.c` 4,140 and `cmdq_prof.c` are trace-side - same treatment as mmprofile in 0080 (compile out, do not fake) |
| LCM/panel | `drivers/misc/mediatek/lcm/` - six dirs compiled for even (`CONFIG_CUSTOM_KERNEL_LCM`, even_defconfig:1714); the three that apply to this board are 797 + 704 + 896 lines, the FHD trio (961 + 1,099 + 1,338) serves sibling variants | 5,796 total, 2,398 applicable | port the common layer (`mt65xx_lcm_list.o lcm_common.o lcm_gpio.o lcm_i2c.o lcm_pmic.o lcm_util.o`, `lcm/Makefile:20-24`) plus the three HDP dirs and the name-selection path - one panel only would build for one unit and fail on another |
| tracing/debug | `display_recorder.c` 1,657, `ddp_dump.c` 1,643, `ddp_debug.c` 964 | 4,264 | deferred with the port-local `ddp_log.h` (0081, `KNOWN-ISSUES.md` 12.6) - re-add only when a device actually needs the dprec mirror |
| DPM / PPBM / MML | `drivers/misc/mediatek/dpm*`, `ppbm` | TBD | MT6768's `even_defconfig` does not enable DPM for this path (`# CONFIG_MTK_CMDQ_TAB is not set`); verify per-file before assuming |

Already in the tree and to be preserved, not re-touched: SMI substrate (0078/0079), M4U v2.0 (0080),
display M4U client glue (0081). The chain is built bottom-up so each layer's binding can be verified
before the next one is added.

## 3. Layer order and the gate for each (nothing ships without its gate)

1. **L0 census/panel identification** - **done** (`report/panel-identification.md` + this document's
   section 1). Gate met: every layer's file list and every panel fact is derived from grep/wc over the
   vendor tree with `file:line`, nothing inferred from directory names.
2. **L1 CMDQ v3 subset** (`CONFIG_MTK_CMDQ_V3`, its own DT node `mediatek,cmdq` + mailbox
   clients). Gate: builds/links; `nm vmlinux | grep -c ' T cmdq_'` > 0; bind audit shows
   `mediatek,cmdq` ENABLED (it is `NO_DRIVER` today); no register behaviour claimed.
3. **L2 dispsys skeleton**: `ddp_base.c`, `ddp_info.c`, `ddp_reg.h`, `ddp_irq.c`, `ddp_pm.c` +
   `ddp_drv.c` probe that binds `mediatek,dispsys`, with everything PQ/OD/merge behind the vendor's
   own `#ifdef`s, and 0081's `ddp_m4u.c` switched back onto the real `ddp_reg.h` LARB path only if
   the ownership question in `KNOWN-ISSUES.md` 12.2 is settled in favour of dispsys. Gate: probe
   compiles, `mediatek,dispsys` ENABLED, `disp_m4u_init()` ordering preserved, host harness still
   43/43.
4. **L3 components + path**: `ddp_ovl/color/aal/gamma/ccorr/dither/rd/dsi` + `ddp_disp_bdg.c` path
   table. Gate: link + `ddp_modules[]` census vs the vendor table + clkaudit unchanged.
5. **L4 LCM common layer + the three HDP panel dirs** (and the `-D<PANEL>` macro plumbing that `lcm/Makefile:41-44` derives from `CONFIG_CUSTOM_KERNEL_LCM`). Gate: all three `LCM_DRIVER` structs link, `lcm_driver_list[]` compiles to six entries as on stock, and the reset-line owner is decided in writing - MMSYS `DISP_REG_CONFIG_MMSYS_LCM_RST_B` (stock `ddp_dsi.c:4959-4969`) vs `disp_dts_gpio_select_state()`, whose `dts_gpio_state` comes from LK. Panel I2C (gate/bias IC) inherits the adapter gap in `KNOWN-ISSUES.md` 8.4 and stays out until a panel file is shown to call `lcm_i2c_*`. Touch stays at the client stage, and it is SPI (`&spi2`, 9.6 MHz, reset `&pio 23`, irq `&pio 1`), not I2C.
   panel resolves, backlight GPIO/PWM bindings cited from the board DT. I2C stays out (touch is the
   client stage that needs adapters, `KNOWN-ISSUES.md` 8.4).
6. **L5 first-frame enablement**: the `atag,videolfb` handover (0 `atag,videolfb-*` props exist in
   the packaged DTB, so LK must supply them - `report/display-m4u-client.md` section 7).

Each layer keeps the invariant that the published `.eml` series reproduces the built tree
byte-for-byte (MANIFEST `verify:` line), and the readiness line is only advanced for the level the
gate actually reached. **No layer may be called functional until it is exercised on the device**;
until then the maximum honest claim is "builds, links, binds, and the traced call sequence
executes on the host".

## 4. What is preserved from the M4U/SMI path

0080/0081 stay as they are: the client's five M4U references resolve into the driver objects, its
`USE_M4U` sequencing finding is recorded, and the LARB register ownership question is documented
rather than "fixed" by a client poking `SMI_LARB0_NON_SEC_CON`. L2 is the first layer where that
decision can be revisited, because that is when the code that legitimately owns those registers
exists in the tree.

## 5. Environment record - why this round has no build result

The sandbox working area was reset: `/home/user/portwork` (the 5.15.220 build tree, the series
worktree, `out/` artifacts, `configs/apply.sh`, `runNN.sh`, the host tools in `tools/bin64`, and
the clang/lld toolchain) no longer exists, and `/tmp` scratch is gone with it. Recovered: the git
repository and every commit I had pushed - `git reset --hard 0fdb893a5` restored
`upstream-port/` (81 `.eml` + cover + MANIFEST, all reports, `tests/`, `bin/`), tree clean, and
the `.eml` count assert (81 non-cover) passes. The ported *sources* survived precisely because the
series is the source of truth: a fresh worktree at `v5.15.220` plus `git am` of the 81 patches
regenerates the audited tree byte-for-byte (`d24f24ea02f61b648cb4a62d2fab497a15eb5e7d`).

Not recoverable here: any compiler for arm64 and the DT tooling. Measured - `clang`, `ld.lld`,
`aarch64-linux-gnu-gcc`, `bc`, `bison`, `flex`, `gperf`, `rsync`, `cpio`, `dtc` are all absent, only
`gcc-12` (host) and `python3` are present, `/etc/apt/sources.list` is empty (so
`apt-get install gcc-aarch64-linux-gnu` cannot be made to work), and package/source egress is
blocked: `HEAD https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.220.tar.xz` -> `HTTP/2 403`,
`https://github.com/torvalds/linux/info/refs` -> no response. Consequences for the gates above:

- `make` of an arm64 `Image`/`Image.gz-dtb`: impossible until a toolchain exists.
- `scripts/dtc/dtc` (the DTB tool of record here, since the LineageOS host tools carry no `dtc`):
  cannot be rebuilt without bison+flex, so `.dtb`-level re-verification (hwenable/clkaudit against
  the packaged DTB) is also blocked; those audits stay at their build-37 results.
- Still runnable: pure static analysis of the vendor 4.19 tree in this repository (that is how
  sections 1-2 were produced - grep/wc only), and reading the committed `.eml` set.

**Corrected in this same round, after the claim above was written:** the `git am` reproduction gate
and the host harness are *also* blocked, and the reason is more basic than a missing compiler. This
repository is a shallow clone of the 4.19 line (`cat-file --batch-all-objects` counts 27 commits,
`.git/shallow` has 2 graft points, and no commit is subject "Linux 5.15.220"), so v5.15.220 does
not exist anywhere in this sandbox - the 5.15 base lived only in `/home/user/portwork/ref/linux/.git`
and is gone with the rest of `portwork/`. Without that base tree the 81 patches have nothing to
apply onto, and `tests/run-disp-m4u-host-test.sh` has no ported tree to compile (it takes the
ported tree as `$1`), even though `gcc-12` is present. `bin/dupdef.py`-style tools that walk the
ported tree are blocked for the same reason. What is *not* lost is the port content itself: the
`.eml` series carries all 81 commits, and each report in `upstream-port/report/` records the hashes
that build-37 measured, so a restored environment can re-derive the tree and re-run every gate.

While the environment is missing, the only work that can be done honestly is layer L0: identifying
the panel and pinning the DT facts from the vendor tree (section 1's open row), which needs no
compiler and no 5.15 tree. That is the next commit's content, not this one's.

## 6. Resized minimum path after the panel analysis (supersedes the sizing in section 2)

Numbers are in `report/panel-path-analysis.md` section 5; the planning consequences are:

- **L1 CMDQ is a delta, not a transplant - to be confirmed on the first build round.** dispsys calls
  14 cmdq entry points (48 callsites) and the vendor declares them at the mainline header path
  `include/linux/soc/mediatek/mtk-cmdq.h`; `cmdq/v3/` has no `cmdq_core.c`. So the first action with a
  5.15 tree is `grep -c cmdq_pkt_ include/linux/soc/mediatek/mtk-cmdq.h` plus checking
  `cmdq_pkt_sleep_by_poll`, `cmdq_pkt_wait_no_clear`, `cmdq_dev_get_event`, and only the missing
  pieces get ported. L1 still blocks L2: `ddp_dsi.c` needs `cmdq_pkt_write`, the panels'
  `set_backlight_cmdq`/`init_power` need it too, and the truly panel's `dynamic_switch_mipi = 1`
  needs the poll/sleep helpers.
- **L2 is ~35k lines, not "34k minus PQ".** MT6768's dispsys has no AAL/gamma/ccorr/merge/dither
  files to exclude and `ddp_dpi.o` is commented out at `dispsys/Makefile:83`, so the built set is 21
  objects = 32,454 .c + 2,687 .h. `ddp_m4u.o` is among them and already landed (0081), so L2 is a
  continuation of that object list rather than a restart.
- **L3 has two explicit shapes.** Stock-shaped (`mtkfb.c` 3,134 + `primary_display.c` 10,857 +
  `disp_lcm.c` 2,143 = 16,134, keeping the `/chosen` handover and ESD/PM behaviour as measured) or
  thin (a few hundred lines parsing `atag,videolfb-*`, resolving the LCM by name, then calling
  `ddp_dsi`/`ddp_ovl`/`lcm_*`). Thin forfeits logo-handover fidelity; stock-shaped drags
  `disp_dts_gpio`, `ddp_pm`, the dprec log layer and cmdq-using ESD. Decide at the L2 link gate.
- **L4 must include the I2C file the panels never call.** `lcm_i2c.c` (382 lines) supplies
  `display_bias_setting()`, called by all three panels; the gate IC (SM5109 mask 0x03 / OCP2130 mask
  0x33) is named by the kernel command line via `early_param("lcdgateic", parse_lcdBias)`
  (`lcm_i2c.c:261,279`), which also installs the bias driver's compatible over the PASCAL_E
  placeholder `"default"`. That puts an I2C adapter on the panel critical path - and this board's
  touch is SPI, so `KNOWN-ISSUES.md` 8.4's adapter gap now limits the panel, not only the client
  stage. Stock tolerates the failure (log and continue), so bias may be sequenced after first frame,
  recorded as unfinished rather than dropped.
- **Panel selection stays the LK name handover.** `atag,videolfb-lcmname` in `/chosen` ->
  `mtkfb_lcm_name` -> `mtkfb_find_lcm_driver()` against `lcm_driver_list[]` `.name`. No DT-based
  panel binding is to be introduced: LK authors that property per boot, the packaged DTB has no
  `atag,videolfb` properties by design, and pinning one of three modules would break the other two.
  The port must still decide, in writing, what it does when the property is missing.

## 7. GPIO-state and handover findings folded in (`disp-gpio-pinctrl-and-atag-producer.md`)

- **Reset/TE/bias are mainline pinctrl states, not vendor GPIO plumbing.** `videox/disp_dts_gpio.c`
  (109 lines, built via `videox/Makefile:40`) is only `devm_pinctrl_get()` +
  `pinctrl_lookup_state()`/`pinctrl_select_state()`, keyed by `this_state_name[]`
  (`mode_te_gpio`, `mode_te_te`, `mode_te1_te`, `lcm_rst_out0/1_gpio`, `lcm1_rst_out0/1_gpio`, and
  under `OPLUS_BUG_STABILITY` - defined at `Makefile:657-660` - `lcd_bias_enp0/1_gpio`,
  `lcd_bias_enn0/1_gpio`, plus `tp_rst_out0/1_gpio`). `disp_dts_gpio_init_repo()` is a macro
  (`disp_dts_gpio.h:71-75`). So the 5.15 port reuses `pinctrl-names`/`pinctrl-N` on its mtkfb node
  with those state names; the vendor's other branch, `DSI_OUTREG32(NULL,
  DISP_REG_CONFIG_MMSYS_LCM_RST_B, v)` (`ddp_dsi.c:4959-4969`), needs no DT change.
  `lcm_vddio18_enable()` is `#if 0` and DSI0's `set_te_pin` is NULL, so VDDIO18 must not be invented
  and dsi0 TE is `dsi0_te_enable` + the `mode_te_*` states. Which branch stock takes here depends on
  `devm_pinctrl_get()` for a node with no `pinctrl-names` (the board DT's mtkfb node,
  `mt6768.dts:3120-3122`, has none); that is a written fork for L2/L4, with the log lines named as
  the device-side tie-breaker, and the DT-touching option stays blocked under the current rule.
- **Handover stays as it is, plus one new requirement.** The kernel only consumes
  `atag,videolfb-{fb_base_h,fb_base_l,islcmfound,islcm_inited,fps,vramSize,lcmname}` from `/chosen`
  (plus the legacy `atag,videolfb`/`atag,ext_videolfb` blob), never writes them, and LK is not in
  this repo; `k65v1_64_bsp.dts:20-27` is the in-tree witness of the shape (`"_drv"`-suffixed names,
  DT spelling `-islcm_inited`). `mtkfb_find_lcm_driver()` merely returns the string; the string is
  classified by `disp_lcm.c`'s `strstr`/`strncmp` ladder into `lcm_panel_temp` + `setLcmPanel_ID(0/1)`.
  So L5 must reproduce that ladder, and `load_lcm_resources_from_DT()` is compiled out
  (`#if MTK_LCM_DEVICE_TREE_SUPPORT`, `disp_lcm.c:186`) - no DT-based model is warranted.

## 8. Frozen implementation requirements (from the measured stock behaviour)

These are the parts of the stock tree that the port must reproduce *as they are*, because they were
verified by reading the vendor source rather than inferred. Each is written with the check that
decides whether it was met, so "preserved" is falsifiable and not a mood.

| # | requirement | why it is the requirement | check |
|---|---|---|---|
| R1 | Panel selection stays the **LK name handover**: read the string from `/chosen`'s `atag,videolfb-lcmname`, single-shot, `/chosen@0` fallback, no invented default panel when absent. | `mtkfb.c:2295-2320` + `_parse_tag_videolfb()` (`video/include/mtkfb.h:410`); the kernel never writes these (`of_add_property` absent under `video/`); packaged `mt6768.dtb` has 0 of them, so they exist only at runtime. | `grep -c "atag,videolfb-lcmname" <port>/...` = 1 and the missing-property path returns an error, not a fallback panel name |
| R2 | Reproduce the **`_drv`-suffix naming** and the classification ladder's observable outputs (`setLcmPanel_ID(0/1)`, `Lcm_name1`) or record the deliberate drop of per-supplier variant switching. | `disp_lcm.c` ~:1060-1130 (`strstr` + `strncmp` against `_hlt_hdp_dsi_vdo_lcm_drv` etc.); `k65v1_64_bsp.dts:20-27` shows the same suffix convention in MTK's own fallback name. | port keeps a name -> variant table; `nm vmlinux \| grep setLcmPanel_ID` or the equivalent symbol exists |
| R3 | No **DT-based panel model**. `MTK_LCM_DEVICE_TREE_SUPPORT` stays off and `load_lcm_resources_from_DT()` stays uncompiled. | vendor `even_defconfig:1713-1716` (unset), `disp_lcm.c:186` guard, zero `lcm_params-` nodes in any DTS, zero `lcm\|panel\|dsi` hits in `mt6768.dts`. | `grep -c "MTK_LCM_DEVICE_TREE_SUPPORT=.y" portwork/series/.config` = 0 |
| R4 | Reset / TE / bias go through **named pinctrl states on the mtkfb device**, using stock's state strings (`mode_te_gpio`, `mode_te_te`, `mode_te1_te`, `lcm_rst_out0_gpio`, `lcm_rst_out1_gpio`, `lcd_bias_enp0/1_gpio`, `lcd_bias_enn0/1_gpio`), with the MMSYS `DISP_REG_CONFIG_MMSYS_LCM_RST_B` write as the handle-unavailable branch. | `disp_dts_gpio.c` (109 lines: `devm_pinctrl_get` + `pinctrl_lookup_state` + `pinctrl_select_state`, table at `:17-48`); `ddp_dsi.c:4959-4969` picks between the two on `dts_gpio_state`. | the port's state names are byte-identical to that table; `grep -c gpio_set_value` in the ported dispsys files = 0 |
| R5 | **VDDIO18 stays a no-op** (log line only) and DSI0 keeps `set_te_pin = NULL`; TE is `dsi0_te_enable` + the `mode_te_*` states. | `lcm_vddio18_enable()` body is `#if 0` with `[lcm]no need set vddio18`; DSI0 util assignment at `ddp_dsi.c:5218-5250`. | port does not add a VDDIO18 GPIO; `grep -c "vddio18"` matches the log-only form |
| R6 | Init tables are copied **row-for-row with their delay placement**: 225 / 109 / 319 rows for ilt9882n-truly / nt36525b-hlt-boe / ilt7807s-hlt, no delay fields inside rows, `MDELAY(1,3,2,2,2,3,5,2...)` around the pushes, `0x11`+`0x29` tails, and hex row-lengths accepted (`0xNN`). | `report/panel-path-analysis.md` section 1 (two regexes, decimal-only parsing returns 0 rows for nt36525b). | row count per table and the delay-argument sequence compared against the vendor file, not against a summary |
| R7 | Backlight is **DCS 0x51 via CMDQ**, not PWM; brightness scaling stays in `oplus_private_set_backlight()`. | `bl_level` = one `0x51` row `(0x00,0xFF)` in all three panels; `lcm_setbacklight_cmdq()` path; PWM states exist but are unused here. | no PWM-family call in the ported panel path |
| R8 | The gate/bias I2C client is **on the panel path but non-fatal**: callers log failure and continue, so first frame must not depend on it. | `display_bias_setting()` at `lcm_i2c.c:223` called by all three panels (`:603`, `:467`, `:714`); failure returns -2/-3 and callers only print; identity comes from `early_param("lcdgateic")` (`:279`). | `MTK_DISP_M4U`-style independence: the panel probe succeeds with the i2c adapter absent (`KNOWN-ISSUES.md` 8.4) and logs it |
| R9 | CMDQ is a **delta over mainline**, sized by the L1 gate before L2 opens. | `report/panel-path-analysis.md` section 5: 14 entry points / 48 callsites in `dispsys/*.c`, full vendor engine 29,317 lines. | `portwork/l1-gate.sh` prints the missing-symbol list; L2 does not start while it is non-empty |

R1-R3 are the "preserve stock LK panel selection" instruction; R4-R8 are the "preserve pinctrl and
panel behaviour" instruction. None of them is a licence to touch the device tree ahead of the build
environment: R4's state names become a DT edit, so the DT work is still gated by R9 and by the
`make prepare`/`dtbs_check` gates below it.

## 9. Environment restored, and what the L1 gate actually printed (measured 2026-09-05)

`portwork/` was rebuilt inside this sandbox from the only egress that answers here - GitHub repo
tarballs via codeload and PyPI; `cdn.kernel.org`, `deb.debian.org`, `ftp.debian.org`,
`archive.ubuntu.com`, `snapshot.debian.org` all time out, and GitHub *release assets* are
unreachable because they 302 to `objects.githubusercontent.com` (000). So no apt package was ever
installed and no clang was needed: `report/build.json`'s toolchain record shows the earlier builds
ran with clang-14 marked unusable and a GCC wrapper, and that is exactly what was reproduced.

| piece | source | measured state |
|---|---|---|
| base tree | `git clone --depth 1 --branch v5.15.220 https://github.com/gregkh/linux` (stable tags are not in `torvalds/linux`) | `0996e0926`, `git describe` = `v5.15.220`, 1.4 GB, `VERSION = 5` |
| series | `git am $(ls patch-series/*.eml \| grep -v cover \| sort)` (81 files) | HEAD `e6ba9917b`, **tree `d24f24ea02f61b648cb4a62d2fab497a15eb5e7d`** = the tree recorded in `gates.am_reproduce_build37`, `855 files changed, 91713 insertions(+), 2394 deletions(-)`, dirty 0 |
| cross cc | `LineageOS/android_prebuilts_gcc_linux-x86_aarch64_aarch64-linux-gnu-9.3` @ lineage-23.2 (94 MB) | `aarch64-buildroot-linux-gnu-gcc.br_real (Buildroot 2020.08) 9.3.0`, ld 2.33.1; a `-c` compile yields ELF64 / Machine AArch64 |
| host tools | `LineageOS/android_prebuilts_build-tools` @ lineage-21.0 (368 MB tarball) | bison 3.8.2, flex 2.6.4, m4 1.4.19, `bc` -> gavinhoward-bc 6.5.0, make 4.3 |
| dtc | built from the tree (`scripts/dtc`) | `DTC 1.6.0-g183df9e9`, `scripts/dtc/dtc` present; `mkimage` absent (not needed: `dtbo.img` comes from `bin/mkdtboimg.py`) |
| configure | `make ARCH=arm64 defconfig` + `portwork/configs/apply.sh` | all 15 real recorded symbols present, `BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES="mediatek/mt6768"` |
| prepare | `make -j2 prepare` | **exit 0** (vdso, modpost, kconfig, dtc built); `genksyms` not built because MODVERSIONS is off |

These scripts are now versioned under `upstream-port/tools/portwork/` (`restore.sh`,
`configs/apply.sh`, `l1-gate.sh`, `build0.sh`) because `portwork/` has already been wiped twice by
sandbox resets and the recipe is the only durable copy.

### Config deviations, each with its causal chain

None of these is a display-layer choice, and all three exist because this sandbox has no OpenSSL
development headers and no way to obtain them:

1. `CONFIG_MODULE_SIG*` off and `SYSTEM_TRUSTED_KEYS`/`MODULE_SIG_KEY` emptied: `MODULE_SIG_ALL`
   would run `genkey`+openssl to make `certs/signing_key.pem`.
2. `CONFIG_CFG80211`/`MAC80211` off. This is the one that is not obvious:
   `scripts/Makefile:15` puts `extract-cert` in `hostprogs-always-$(CONFIG_SYSTEM_TRUSTED_KEYRING)`,
   `SYSTEM_TRUSTED_KEYRING` is selected by `SYSTEM_DATA_VERIFICATION` (`init/Kconfig:2076-2078`),
   which is selected by `CFG80211_REQUIRE_SIGNED_REGDB` (`net/wireless/Kconfig:92-95`) - a symbol
   that is hidden-but-`default y` while `CONFIG_CFG80211` is on, so `scripts/config --disable`
   cannot clear it. Order matters: cut cfg80211 first, then `SYSTEM_TRUSTED_KEYRING` becomes
   clearable; otherwise `make prepare` dies on `openssl/bio.h` forever.
3. `CONFIG_MAILBOX` + `CONFIG_MTK_CMDQ_MBOX` on (the correct 5.15 name is `MTK_CMDQ_MBOX`, not
   `MTK_CMDQ_MAILBOX`, and `apply.sh`/`l1-gate.sh` were fixed to say so).

Consequence to hold onto: **`Image`/`Image.gz-dtb` sizes from this environment are not comparable to
build-37's** until libssl headers exist, because `certs/` content changed. Any display-layer gate
(L1/L2/L3) is unaffected, since none of them involves the module-signing or wifi paths. The vendor
`even_defconfig` does set `MODULE_SIG=y`/`FORCE=y`/`ALL=y` and `CFG80211_CRDA_SUPPORT=y`
(`arch/arm64/configs/even_defconfig:683-691,1387`), which is a reminder that the final board config
will need those back - with a real toolchain - before any image is called flashable.

### L1's answer, and it is not the answer the plan assumed

Against a real v5.15.220 + series tree: `include/linux/soc/mediatek/mtk-cmdq.h` is **283 lines**
(vendor: 434), and of the 19 entry points `dispsys` uses, mainline declares 8
(`cmdq_pkt_write`, `cmdq_pkt_clear_event`, `cmdq_pkt_create`, `cmdq_pkt_destroy`,
`cmdq_pkt_flush_async`, `cmdq_pkt_poll`, `cmdq_mbox_create`, `cmdq_pkt_write_s`) and lacks 11:
`cmdq_pkt_write_masked`, `cmdq_pkt_read`, `cmdq_pkt_sleep`, `cmdq_pkt_sleep_by_poll`,
`cmdq_pkt_wait`, `cmdq_pkt_wait_no_clear`, `cmdq_pkt_event_clear`, `cmdq_dev_get_event`,
`cmdq_pkt_flush`, `cmdq_pkt_flush_threaded`, `cmdq_register_device`. `struct cmdq_pkt` is referenced
19 times in the mainline header against 58 in the vendor one, and the vendor signatures pass a
`struct cmdq_base *clt_base` that mainline's client model does not have. `drivers/soc/mediatek/cmdq.c`
does not exist in 5.15; the engine lives in `drivers/mailbox/mtk-cmdq-mailbox.c` (1,145 lines).

So "port only the missing delta" does not mean eleven stubs: the delta is entangled with the vendor's
packet/client layout, and the two real options are (a) port the vendor CMDQ v2 core
(`drivers/misc/mediatek/cmdq/v2/*.c` = 13,136 lines) beside mainline's and let `dispsys` use the
vendor one, or (b) rewrite the 48 dispsys callsites onto mainline's API and port only the semantics
mainline lacks (`sleep_by_poll`, `wait_no_clear`, `dev_get_event`, `register_device`). A hook for (a)
is already reserved by the series - `drivers/mailbox/Makefile:4` carries
`ccflags-$(CONFIG_MTK_CMDQ_MBOX_EXT) += -I$(srctree)/drivers/misc/mediatek/cmdq/mailbox` - but
`find drivers/misc/mediatek/cmdq` under the series tree returns **0 files**, i.e. the include slot
exists with nothing in it and no patch subject mentions cmdq: L1 is genuinely unwritten, and the
dangling `MTK_CMDQ_MBOX_EXT` symbol is where its Makefile wiring is meant to hang.

First build probe of the mainline driver, `make drivers/mailbox/mtk-cmdq-mailbox.o` with
`CONFIG_MTK_CMDQ_MBOX=y`, currently fails. Captured compiler lines:
    (no error line captured)
Correction to what this section first said, because the probe result was more informative than the
plan's assumption. The object does not fail to compile because of gcc or `-Werror`: enabling
`CONFIG_MTK_CMDQ_MBOX` exposes that **the series has already converted mainline's CMDQ mailbox
driver to the vendor engine interface, without carrying the engine**. Measured errors in
`drivers/mailbox/mtk-cmdq-mailbox.c` (with the toolchain genuinely on PATH, i.e. not the
`scripts/Kconfig.include:39 compiler not found` artifact of running a probe without sourcing
`tools/env.sh`):

    :113:3  error: implicit declaration of function 'cmdq_err'
    :690:11 error: 'CMDQ_DRIVER_NAME' undeclared here (not in a function)
    :700:2  error: implicit declaration of function 'cmdq_msg'
    :727:11 error: 'struct cmdq' has no member named 'base_pa'; did you mean 'base'?

Those four identifiers belong to the vendor tree under `drivers/misc/mediatek/cmdq/` - which is the
same path the series' own `ccflags-$(CONFIG_MTK_CMDQ_MBOX_EXT) += -I...` line points at, and it
contains 0 files. So L1 is not "unwritten": it is **half-landed and currently incoherent**, the
consumer was rewritten onto an API that is not present. Two consequences, both uncomfortable and
both worth stating: (1) `gates.*` for build-37 report 0 compiler errors, and that remains true -
`CONFIG_MTK_CMDQ_MBOX` was never in the 15-symbol recipe, so mainline's converted driver has never
been compiled by any gate in this series; every later layer inherits an unverified file. (2) The
option (a)/(b) fork above is decided by how much of `drivers/misc/mediatek/cmdq/` is carried, and the
converted driver now *requires* the vendor layout (`struct cmdq.base_pa`, `cmdq_err`,
`CMDQ_DRIVER_NAME`) either way, so option (b) additionally means reverting mainline's driver.

L1 work item zero is therefore: decide the engine shape, land `drivers/misc/mediatek/cmdq/`
accordingly, and only then re-run this object as the gate. `make prepare` staying green means the
environment is sound; it does not mean the tree is self-consistent at CMDQ.

L2 (the 21 built `dispsys` objects, 32,454 .c + 2,687 .h) stays gated exactly as R9 requires: L1's
output is a non-empty list.

## 10. CMDQ coherence: inventory, the decision taken, and the corrected baseline

L2 stays stopped. This section is the resolution of the half-landed state, measured against the
restored tree, and it also corrects two things section 9 asserted.

### What the board actually uses (correcting section 6 and 9)

`arch/arm64/configs/even_defconfig:1804-1807` reads `CONFIG_MTK_CMDQ_V3=y`, `CONFIG_MTK_CMDQ=y`,
`# CONFIG_MTK_CMDQ_TAB is not set`, `# CONFIG_MTK_CMDQ_MBOX_EXT is not set`, and the vendor
`drivers/misc/mediatek/cmdq/Makefile` routes the platform by that symbol:

    ifeq ($(CONFIG_MTK_CMDQ_V3),y)
    ifneq (,$(filter $(CMDQ_PLATFORM), "mt6739" "mt6768" "mt6771" "mt8168" ...))
            obj-y += v3/
    ...
    obj-$(CONFIG_MTK_CMDQ_MBOX_EXT) += mailbox/
    obj-$(CONFIG_MTK_MT6382_BDG) += bridge/
    ifeq (,$(filter $(CMDQ_PLATFORM), "mt6885" "mt6873" "mt6853" "mt6893" "mt6833" "mt6877" "mt6781"))
            obj-y += mdp_sync/

So the applicable engine is **v3, not v2** - `v2/` has no `mt6768` board directory and is only
reached with `MTK_CMDQ_V3=n`, which this board does not use. Sizes, counted from the vendor tree:

| engine | .c lines | .h lines | board dirs | built on even? |
|---|---|---|---|---|
| `cmdq/v3/` | 29,317 | 6,479 | `mt6765 mt6768 mt6779 mt6785 mt6833 mt6885` | **yes** |
| `cmdq/v2/` | 23,828 | 4,258 | none for mt6768 | no |
| `cmdq/mailbox/` (sec, bw-mon, test) | - | - | `mt6781 mt6833 mt6853 mt6873` | no (`MBOX_EXT` off) |
| `cmdq/bridge/` (MT6382) | - | - | - | no (`MTK_MT6382_BDG` off) |
| `cmdq/mdp_sync/` | - | - | - | yes (not in the exclusion filter) |

Correcting section 9: the four unresolved identifiers did **not** come from `cmdq/mailbox/`. That
directory is not built on this board, so the series' `ccflags-$(CONFIG_MTK_CMDQ_MBOX_EXT)` line is
inert (its `-I` is never added), and `include/linux/soc/mediatek/mtk-cmdq.h` was never changed by the
series at all - `git checkout v5.15.220 --` reported it identical to upstream. The incoherence lived
purely in the C files: patch `7836cbd3e drivers-mailbox: carry downstream 4.19.325 vendor delta onto
v5.15.220` added +460 lines to `drivers/mailbox/mtk-cmdq-mailbox.c`, +3 to
`include/linux/mailbox/mtk-cmdq-mailbox.h` and +2 to `drivers/mailbox/Makefile`, which pulled in the
vendor driver's references to `cmdq_err`, `CMDQ_DRIVER_NAME`, `cmdq_msg` and `struct cmdq.base_pa` -
identifiers belonging to engine code the series never carried.

### What was done

Reverted the shared API surface to upstream: the three files above are back at `v5.15.220` state.
`drivers/mailbox/mailbox.c` keeps its +39-line delta because grepping that hunk for `cmdq|gce`
returns nothing - it is a generic mailbox-core carry, not part of CMDQ coherence, and leaving it is
the minimal change. Result, with `CONFIG_MTK_CMDQ_MBOX=y` now set for real (see the fragment note
below): `make drivers/mailbox/ drivers/soc/mediatek/` returns rc=0, producing
`drivers/mailbox/mtk-cmdq-mailbox.o` (123,688 bytes) and
`drivers/soc/mediatek/mtk-cmdq-helper.o` (92,776 bytes); all four errors are gone, and
`make Image` (build-38) was launched against the same tree as the link check.

Also corrected from section 9: mainline's client API is *not* absent - it lives in
`drivers/soc/mediatek/mtk-cmdq-helper.c` (there is no `drivers/soc/mediatek/cmdq.c` in 5.15, which
is what that section grepped for). The gap was therefore re-measured the way linking actually
decides it, `nm` over the two built objects plus `static inline` definitions in the header:

    available for the display path (8): cmdq_mbox_create, cmdq_pkt_clear_event, cmdq_pkt_create, cmdq_pkt_destroy, cmdq_pkt_flush_async, cmdq_pkt_poll, cmdq_pkt_write, cmdq_pkt_write_s
    absent (11):                       cmdq_dev_get_event, cmdq_pkt_event_clear, cmdq_pkt_flush, cmdq_pkt_flush_threaded, cmdq_pkt_read, cmdq_pkt_sleep, cmdq_pkt_sleep_by_poll, cmdq_pkt_wait, cmdq_pkt_wait_no_clear, cmdq_pkt_write_masked, cmdq_register_device

Eight of nineteen, as first counted - but now from the object files rather than from one header, and
with the surprise that `cmdq_pkt_read` and `cmdq_pkt_write_masked` are *not* in 5.15's client API
either (they arrive with later kernels), while `cmdq_pkt_poll` and `cmdq_pkt_write_s` are.

### Decision: revert-and-extend, not carry-v3

The engine question is settled by the two lists above, not by taste:

1. Keep mainline's CMDQ stack as the host (revert already done, build green). It implements the GCE
   semantics the display path needs for 8 of the 19 entry points, and it is what `DRM_MEDIATEK` and
   `mtk-cmdq-helper` already consume through the *same* header, so a second API at that path is not
   possible without a shim.
2. Port only the 11 missing entry points, as vendor semantics in vendor-owned files with the vendor's
   own private include layout (`v3/inc`-style), leaving `include/linux/soc/mediatek/mtk-cmdq.h`
   byte-identical to upstream. This preserves stock CMDQ semantics where dispsys depends on them
   (`sleep_by_poll`, `wait_no_clear`, `dev_get_event`, `register_device` are the ones with no
   mainline equivalent in kind, only in name) and avoids inventing a compat layer.
3. Do **not** carry `cmdq/v3/` (29,317 + 6,479 lines) or `mdp_sync/` on spec. The engine becomes
   in-scope only when a specific dispsys callsite is shown to need v3-only behaviour - secure
   path/GCT prefetch/bw-mon - which the 48-callsite census in section 5 does not currently show.
   If that happens, the port carries v3 wholesale *replacing* mainline's driver for the display
   node, because two drivers cannot both own the GCE mailbox node; that would also mean reverting
   this decision, and it must be recorded as such rather than half-done.
4. `MTK_CMDQ_MBOX` is now part of the device build config in the repo
   (`upstream-port/dev/even-hardware.fragment`), with its `MAILBOX` + `MTK_INFRACFG` dependency
   stated. Before this round it appeared in no fragment, which is precisely why the converted driver
   was never compiled by build-33 through build-37 and the incoherence survived seven builds.

Gate for L2 to resume: the 11 ported entry points compile and link in the same tree, and `nm` shows
each one defined exactly once - then the dispsys census in section 5 can be satisfied by real
symbols instead of assumptions.

### 10.6 stage 2 landed (0083) and stage 3's blocker measured

Stage 2 is published as 0083 and verified in the tree the .eml set reproduces: the four entry points
(`cmdq_dev_get_event`, `cmdq_pkt_wait_no_clear`, `cmdq_pkt_flush`, `cmdq_pkt_flush_threaded`) live in
mainline's own `drivers/soc/mediatek/mtk-cmdq-helper.c`, declared in mainline's
`include/linux/soc/mediatek/mtk-cmdq.h`. `git am` of 0001-0083 onto 0996e0926 gives tree
`1bbd779ea9182f344c9e231621bca0ae8b715dae`, identical to the built tree, and the 0001-0081 prefix
still gives `d24f24ea02f61b648cb4a62d2fab497a15eb5e7d`. In that reproduced tree, with the device
config, `make drivers/mailbox/ drivers/soc/mediatek/` returns rc=0 with zero errors and zero warnings,
`mtk-cmdq-helper.o` is 104,352 B (was 92,776 B), and `nm` shows each new symbol defined exactly once.

Two corrections that came out of doing it rather than guessing: `cmdq_pkt_wait_no_clear` needs no new
instruction at all - this tree's `CMDQ_WFE_OPTION` is already `CMDQ_WFE_WAIT | CMDQ_WFE_WAIT_VALUE`
and `CMDQ_WFE_UPDATE` is ORed in only when `clear` is true, so `cmdq_pkt_wfe(pkt, ev, false)` is
bit-identical to what 4.19.325 emits (the earlier claim in this effort that mainline "cannot express
wait-no-clear" was wrong and is retracted); and `cmdq_pkt_write_masked` is mainline's
`cmdq_pkt_write_mask` renamed, not a gap.

The sleep pair is the remaining L1 item, and its blocker is now measured instead of assumed: the
opcode enum in `include/linux/mailbox/mtk-cmdq-mailbox.h` has MASK/WRITE/POLL/JUMP/WFE/EOC/READ_S/
WRITE_S/WRITE_S_MASK and **no SLEEP, no LOGIC, no plain READ**, while `cmdq_pkt_sleep` needs
`CMDQ_CODE_SLEEP`-equivalent plus the GPR/TPR encoder (`cmdq_pkt_logic_command`,
`cmdq_pkt_write_indriect`, `cmdq_pkt_poll_gpr_check`, `cmdq_pkt_assign_command`,
`cmdq_pkt_get_pa_by_offset`, `cmdq_pkt_cond_jump_abs`, `cmdq_mbox_get_base_pa()`,
`struct cmdq_operand`, `CMDQ_TPR_ID`, `CMDQ_GPR_CNT_ID`, `CMDQ_CPR_TPR_MASK`, `CMDQ_SPR_FOR_TEMP`,
`CMDQ_TPR_TIMEOUT_EN`, `CMDQ_EVENT_GPR_TIMER`, `CMDQ_THR_SPR_IDX1/3`) and mainline's private `struct
cmdq_instruction` exposes only `arg_c`/`src_reg`/`offset`/`event`/`reg_dst`/`subsys`/`sop` - no
`dest_reg`, `arg_a`, `arg_b`. So stage 3 means transcribing the vendor bit positions and extending
that struct inside the helper .c; nothing will be written from analogy. Until that is landed and
build-verified, `ddp_dsi.c`'s three `cmdq_pkt_sleep_by_poll()` callsites and the one `cmdq_pkt_sleep()`
callsite keep L2 closed, and `ddp_disp_bdg.c:3173`'s `cmdq_register_device()` stays rewritten onto
`cmdq_dev_get_client_reg()` rather than shimmed.

### 10.7 stage 3: the sleep pair is not a requirement, and that is a measurement, not a shortcut

Stage 3 was scoped as "port `cmdq_pkt_sleep` and `cmdq_pkt_sleep_by_poll` with the vendor's exact
encoder semantics, plus the GPR/TPR helpers and `cmdq_mbox_get_base_pa()`". Doing it started with the
callsites, and the callsites do not survive contact with the preprocessor:

| symbol | grep hits in video/mt6768 | live after comment-stripping + guard evaluation |
|---|---|---|
| `cmdq_pkt_sleep` | 1 | **0** - the only occurrence, `ddp_dsi.c:7099`, is inside a `/* */` comment |
| `cmdq_pkt_sleep_by_poll` | 4 | **0** - `ddp_dsi.c:2098/4051/7113` and `primary_display.c:8953` are all inside `#ifdef CONFIG_MTK_MT6382_BDG`, and so is the vendor definition (`mtk-cmdq-helper.c:1329-1372`) and its header declaration (`mtk-cmdq.h:412-414`); even_defconfig has `# CONFIG_MTK_MT6382_BDG is not set` |
| `cmdq_pkt_timer_en` (the other `cmdq_mbox_get_base_pa()` user) | 0 | **0** |
| `cmdq_pkt_poll_gpr_check()` (sleep's GPR bookkeeping) | - | its whole body is inside `#if IS_ENABLED(CONFIG_MACH_MT6885)`; this board is MACH_MT6768, so in stock it appends nothing |

So on this board the sleep family is not compiled, not called, and its bookkeeping helper is empty.
Porting it would add unreachable kernel code whose only evidence of correctness would be that it
resembles the vendor - exactly the speculative shim this port exists to avoid. It is therefore not
ported, `cmdq_mbox_get_base_pa()` is not added (nothing live would call it), and no GPR/TPR encoder
enters the tree. The census tool that produced this is committed as `bin/cmdqcensus.py`: it strips C
comments and string literals before matching, then reports each hits enclosing `#if/#ifdef` chain and
resolves those guards against `even_defconfig`. That distinction (hits vs compiled code) is the whole
reason my earlier "3 sleep_by_poll callsites in the built dispsys objects" figure was wrong, and the
same tool re-checked the four symbols 0083 did ship: 7, 3, 2 and 1 callsites, all live.

The encodings are still recorded, as numbers rather than as dead code. `tests/cmdq_words_host_check.c`
transcribes the vendor's `struct cmdq_instruction` (arg_c:16/arg_b:16/arg_a:16, then s_op:5 +
arg_c_type/arg_b_type/arg_a_type, then op:8) and `cmdq_pkt_instr_encoder()`, and v5.15.220's union
struct, then compares the 64-bit words both produce. Result (`report/cmdq-words-check.txt`): 48
comparisons, 0 mismatches - `cmdq_pkt_wait_no_clear(ev)` and `cmdq_pkt_wfe(ev, false)` agree for every
event 0..0x3fe and both reject 0x3ff and above (identical bounds, 0x3FF in both trees), so 0083's
bit-identity claim is now machine-checked instead of asserted. The same harness prints the sleep-family
words it deliberately did not port (LOGIC SUBTRACT/OR/ADD with `CMDQ_TPR_ID`=56,
`CMDQ_GPR_CNT_ID`=32, `CMDQ_CPR_TPR_MASK`=0x8000, `CMDQ_CPR_SLP_GPR_MAX`=0x8003,
`CMDQ_EVENT_GPR_TIMER`=994, `CMDQ_CODE_LOGIC`=0xa0, `CMDQ_CODE_JUMP_C_ABS`=0xb0,
`CMDQ_US_TO_TICK(t)`=t*26), so if a later round ever enables BDG the transcription is already done and
already reviewed. That supersedes the forward-looking sentence in 0083's commit message and cover
letter about the sleep pair "waiting" to be transcribed; the published .eml files are deliberately not
rewritten, because the .eml set is the build and its code is unaffected.

L1 is now complete for everything the compiled display path needs: all 11 live CMDQ names
(`cmdq_dev_get_event`, `cmdq_pkt_wait_no_clear`, `cmdq_pkt_flush`, `cmdq_pkt_flush_threaded`,
`cmdq_pkt_write`, `cmdq_pkt_clear_event`, `cmdq_pkt_create`, `cmdq_pkt_destroy`,
`cmdq_pkt_flush_async`, `cmdq_pkt_poll`, `cmdq_mbox_create`) are declared in
`include/linux/soc/mediatek/mtk-cmdq.h` or the mailbox header of the ported tree.

`cmdq_register_device` is the one live display symbol 5.15 will never provide, and the rewrite is
bigger than "one callsite", which the earlier note understated: `ddp_disp_bdg.c:3030` assigns
`disp_bdg_gce_base`, and **17 further lines in that file pass it as `clt_base`** to 14
`cmdq_pkt_write()` and 3 `cmdq_pkt_poll()` calls (`:3099-3165`), all to registers in the 0x0002xxxx
window. The vendor function only builds a base-to-id table from DT `gce-subsys`/`#gce-subsys-cells`
plus a `gce-cpr-range`, and `cmdq_pkt_write(pkt, clt_base, addr, value, mask)` uses it to convert
`(0x0002 << 16)` into a subsys id, falling back to raw-address writes when it finds nothing. The
verified 5.15 equivalent is therefore not a drop-in: mainline's `cmdq_pkt_write(pkt, subsys, offset,
value)` wants the subsys id and offset directly, which is what `cmdq_dev_get_client_reg(dev, &reg, i)`
returns from `mediatek,gce-client-reg`. The vendor `mt6768.dts` carries those properties and so does the copy this series transplanted:
`grep -c "gce-client-reg\|gce-subsys" arch/arm64/boot/dts/mediatek/mt6768.dts` returns 3 in the vendor
tree and 3 in `portwork/series`, so the DT data the rewrite needs is already in our tree and the 18
affected lines can go through `cmdq_dev_get_client_reg()` rather than an open-coded subsys id. That is display-side work and it is now unblocked: L1
imposes no further CMDQ engine changes.

## 11. L2 opened: the substrate measurement that sets the landing order

See `l2-dispsys-substrate.md` (measured 2026-09-05, no display file committed). Three results move the plan:
the per-object CMDQ table (15 of the 21 built objects reference no CMDQ client API at all, while the
v3 **record** API accounts for 28 names across 6 files - the record layer, not the sleep pair, is the
live v3 requirement); `disp_init_bdg_gce_obj()`, which holds `cmdq_register_device()`, is reachable only
from `#ifdef CONFIG_MTK_MT6382_BDG` code and so is compiled out exactly like the sleep family, which
narrows the BDG rewrite to a text-preservation choice rather than a link need; and the header closure of
the five simplest CMDQ-free objects is 35 headers / 10,818 lines whose first wall is
`cmdq_helper_ext.h:69: field 'savetv' has incomplete type` - i.e. L2 starts at the same one-client-API
question 0082 settled, so that decision comes before the first display file. A probe slice was built
out to that point and then reverted: `portwork/series` is back at the published 0083 tree
(`1bbd779e...`), dirty=0, and the dispsys/mailbox/soc build is rc=0 with 0 errors and 0 warnings.
Gate: `build.json` `gates.l2_substrate_probe40`; decision 136; tooling `bin/l2slice.py`.
`ddp_color_format.o` compiled clean in the probe, so the small CMDQ-free objects are near-landed; the
v3 header surface is the blocker.

### 11.1 Slice 1 landed (0084), the environment rebuilt a second time, and the gates re-run

0084 landed the CMDQ-free dispsys core: 14 objects (the generated `dispsys/Makefile` is the definition
of that count - the first enumeration of it said 13 and was wrong), 91 files, 27,994 insertions. After
the published series was built, the sandbox was reset again and `/home/user/portwork/` was lost a second
time. Rebuilding it exposed that `tools/env.sh` had never been versioned, and two further environment
defects that only a fresh tree shows; all three are fixed in `upstream-port/tools/portwork/`
(`env.sh` now lives there too, and `restore.sh` proves `bison` before running `make`). Both
reproducibility gates and the full slice gate were then re-run and passed:

    0001-0084 -> tree 3fa1c650082e917773ac00d2190befb35d575572, dirty 0    (== recorded)
    0001-0083 -> tree 1bbd779ea9182f344c9e231621bca0ae8b715dae              (no regression in the prefix)
    defconfig + apply.sh + prepare -> rc 0;  slice build -> rc 0, 0 errors, 14/14 objects, 0 dup defs

The gate is now a script (`portwork/l2-slice-gate.sh` + `bin/undeps.py`) instead of a sequence of
one-liners, and it derives the expected object list from the tree's own `obj-y`. Details, including why
quoted object sizes differ by a few bytes between checkouts, are in `l2-recovery-and-record-probe.md`;
`build.json` gates `l2_recovery_recheck45`, `l2_record_probe45`; decisions 138, 139.

### 11.2 What L2 needs next, measured rather than assumed

Probing `cmdq_record.c` (the one file that defines every `cmdqRec*`/`cmdqBackup*` the display path
calls) at the published tree changed the shape of the question:

* the record layer drags in **2 headers and no engine file at all** - it references 0 globals defined in
  any other v3 `.c`, so the 26,437 lines of v3 engine are *not* required by it (this is what R9's
  "unless a live display callsite proves it required" was waiting for);
* its only wall is the shared CMDQ ABI: 6 `struct cmdq_pkt` members mainline lacks (22 references) and
  13 `enum cmdq_code` opcodes; `include/linux/mailbox/mtk-cmdq-mailbox.h` is 279 vendor lines against
  our 93;
* the demand is 31 entry points / 453 callsites / 12 files, and the secure-path and loop callsites are
  live and unguarded on even, so they cannot be configured away.

Whether to grow mainline's `struct cmdq_pkt`/opcode set and land the vendor record file on top of it, or
to carry the vendor engine (which re-opens the 0082 coherence decision *and* creates a `mediatek,gce`
DT-node double-bind), is an architectural and hardware-risk choice, not a dependency-order one: it is
costed in `report/l2-record-layer-options.md` and held at decision 139 pending the human's call. R9
still gates: nothing display-side beyond that point is ported until it is made.

### 11.3 Gate 1 was run, and it killed option A

Option A ("extend mainline's CMDQ ABI, land `cmdq_record.c`") was chosen by the human with an explicit
fallback rule: if either safety gate fails, stop and report - do not switch to carrying the vendor engine,
do not land a partially-proven layer. Gate 1 failed, for a structural reason rather than a subtle one:
the vendor record layer does not write into *a* buffer, it writes into a **list of chunks** that its own
allocator chains together with physical-address jump instructions, and mainline's `struct cmdq_pkt` has
exactly one buffer to alias. So the choice is one packet-buffer model or the vendor's, and A's cost is the
vendor client+mailbox stack (~4.0k lines in the two files 0082 reverted), not a header extension.
Measured sizes, the three allocator functions, the `pa_base`-in-a-jump-word issue under M4U/SMI, and the
rejected one-chunk variant are written up in `l2-record-gate1-result.md`; decision 140.

Nothing was landed from the probe. Current honest state: 0084's 14-object display core, compile-verified,
not linkable; 70 unresolved names whose providers are not in the tree; ~~`videox/disp_helper.c` still owed
an `obj-y` line~~ *(this clause was wrong - it has had one since 0081; what was actually broken is the
subject of 11.4)*; and the display port held at this substrate until the human decides between option B and
stopping here. R9's "CMDQ must be coherent before display code" is satisfied - and it is also what stops
further display work, because the remaining display layers are all record-API users.

### 11.4 0084 had broken the directory it lived in; 0085 repairs it, and the gate contract changed

Writing 11.3 down forced a check of one of its own sentences - "videox/disp_helper.c has no obj-y line" -
and the sentence was false: `videox/Makefile` has carried `obj-y += disp_helper.o` since 0081. The reason
its three symbols had no provider turned out to be a build failure, not a wiring gap. 0084 replaced
`dispsys/display_recorder.h` with the vendor file, which includes `mmprofile.h` (in
`drivers/misc/mediatek/mmp/`) and, through `ddp_info.h`, `ion.h`; the hand-written 0081 `videox/Makefile`
listed only `include/`, `video/mt6768/` and `video/`. From 0084 on, `make ARCH=arm64
drivers/misc/mediatek/video/` died on `disp_helper.o` with `fatal error: mmprofile.h: No such file or
directory` - while every L2 gate, all of which named `.../dispsys/`, stayed green, because the *generated*
`dispsys/Makefile` does advertise `mmp/`.

So the failure mode to remember is not the missing `-I`, it is the shape of the verification: **a gate that
names a leaf directory certifies that leaf directory and nothing else.** Three changes follow, all landed:

* `l2-slice-gate.sh` builds the **parent** `drivers/misc/mediatek/video/` and derives the expected object
  list from the `obj-y` of *every* landed Makefile in the slice (`SLICE_DIRS`), so a slice can no longer be
  reported green while its own directory's sibling fails to compile. `undeps.py` gained `--objs dir1 dir2`,
  because a symbol satisfied by a sibling directory is not a blocker.
* A rule for the remaining layers: **a patch that replaces a header consumed by another directory must
  re-derive that directory's include set** - include requirements travel with shared headers, not with the
  `.c` file. This binds L3/L4, where more vendor headers are being copied over ported ones.
* Publishing is now a checked script (`upstream-port/bin/publish.py`) rather than a hand edit: it refuses on
  a dirty or mis-hashed tree, renumbers every `Subject:` with a fold-tolerant regex (the stored patches are
  literally folded inside `[PATCH 84` / `/84]`), asserts the file count, and finally `git am`s the whole set
  in a scratch worktree and compares trees - which is how "0085 = 0084 + one file, and the 0084 prefix is
  untouched" became a measurement rather than an assertion. The same pass found, and regenerated away, two
  carried-forward doc defects: the cover letter's verification bullet quoted the 0001-0083 tree as "all 84",
  and its diffstat was still the 0081-era one.

0085 changes one file (`git diff --name-only HEAD~1 HEAD`), and the gate at its tip is green: rc=0, 0
`error:` lines, 15/15 objects, 257 link-visible definitions with 0 duplicates, 87 names without an in-tree
provider (down from 220: the three `disp_helper_*` names resolve now). `disp_helper.c:290
-Wimplicit-fallthrough` is vendor code, newly *seen* rather than caused, and is left alone. What is still
open is unchanged from 11.3 - the record layer, and therefore any further display layer - plus one item
that 11.3 could not know about: **the whole-tree build of 0082-0085 had never been run.** That is now
running as a resumable stage (`report/l2-videox-include-regression.md` 6), and until `vmlinux` links, no
image-level claim is made for 0082 onward.

### 11.5 The whole-tree survey this triggered, and what it found in 0001

Fixing the videox include set made the next question unavoidable: if a directory-scoped gate could miss
a broken sibling, what else has it been missing? `make ARCH=arm64 vmlinux` at the 0085 tip (config of
record: `defconfig` + the two in-repo fragments, `.config` sha `758ae54339bf…`, `make prepare` rc=0)
died at 1,732 objects on `drivers/acpi/fan.c:273: error: conflicting types for 'show_state'`.

It is not a display defect and not an upstream one: `drivers/acpi/` and `include/linux/sched/debug.h`
are byte-identical to mainline in our tree, and pristine v5.15.220 with the same `.config` compiles
`fan.o` (rc=0, 87,160 B). The cause is a single line **0001** carried from the vendor
`include/linux/wait.h:10` — `#include <linux/sched/debug.h>` — which puts mainline's
`static inline void show_state(void)` into every TU, where 5.15's `DEVICE_ATTR_RW(state)` in `fan.c`
clashes with it. In 4.19 the line was inert (the vendor's `fan.c` has no `show_state`), and the line is
load-bearing here (deleting it fails `make prepare`, because the vendor added `__sched` to
`pagemap.h`/`mm/filemap.c`/`kernel/sched/wait.c` and `__sched` is only defined in `sched/debug.h`).
Blast radius: one file in the whole tree. Fix: `pagemap.h` includes what it uses, `wait.h` goes back to
pristine — committed in the landing tree, **unpublished** until the `-k` whole-tree survey
(`portwork/logs/full-k.summary`) comes back, so no link or image claim is made from it.

Two rules for the rest of the port, both from measurements in `l2-wholetree-survey.md`: every full-build
gate records its `.config` sha256 (build-37's entries do not, which is why its "0 `error:`" can no longer
be reconciled here), and the gate for any patch that touches a *core header* is a whole-tree `-k` pass,
not a directory pass. It also exposed a scope fact worth stating plainly: `make even_defconfig` is not
available in the landing tree at all (`arch/arm64/configs/` holds only `defconfig`), so "the device
config" for the 5.15 port means defconfig + fragments, and a device-defconfig-shaped config is an open
item rather than an existing capability.

### 11.6 The link step the suite was missing, and what it says about 0084

The `-k` survey finished the job a compile gate cannot do: it **linked**. Every built-in object in the
tree compiles at the 0085 tip (0 `error:` lines) once the `wait.h`/`pagemap.h` include defect from 0001 is
fixed - and then `vmlinux` fails with 507 `undefined reference` lines, every one of them from the 15 landed
display objects. In other words 0084 did not land "a slice that is not yet functional"; it landed a slice
that **the tree cannot link**, so no image exists from 0084 on. `undeps.py` had already counted that
boundary (87 names without an in-tree provider); the linker only made it unforgiving.

The vendor tree shows the shape of the fix. Its `video/mt6768/Makefile:20` is

```make
obj-$(CONFIG_MTK_FB) += dispsys/
```

so the directory is only descended when the display stack is *enabled as a whole* - and on this board
`CONFIG_MTK_FB=n`, i.e. stock even does not build the legacy display core either. Our generated Makefiles
use bare `obj-y` (chosen so a sandbox could compile the objects at all), and that is what turns "providers
not landed yet" from a harmless state into a broken build. Measured with both display directories switched
to `obj-$(CONFIG_MTK_DISP_BRINGUP_INCOMPLETE)` and the symbol unset: `LD vmlinux` succeeds (167,987,640 B),
`Image.gz-dtb` is 12,207,264 B with 0 error lines, the appended DTB payload is 493,517 B - byte-equal in
size to the value recorded for build-37 - and `mt6768.dtb` is still `34a7e6b5…`, unchanged since build-33.

Two rules follow, and they bind the rest of this plan: **every slice gate gains a link step** (`make -k
vmlinux` with the slice enabled, not just per-directory compiles), and **no slice is landed that the tree
cannot link** - which for L2 means the display directories stay Kconfig-gated (default `n`) until the patch
that closes the last provider turns them on, at which point the gate must show a linked `vmlinux` in the
same round. Whether to re-gate the already-published 0084/0085 that way, to land the provider closure
first instead, or to unwind the build wiring of 0084 and restart L2 bottom-up is a sequencing decision for
the human (decision 143); it interacts with the still-open record-layer fork (option B vs stopping at this
substrate), because the gate is also what would make "stop here" an ending state that still builds.

### 11.7 Published state after the gate: 0086 + 0087, and what the next slice may not do

The series is 87 patches. 0086 removes the `wait.h` include 0001 carried (the `show_state` collision with
`drivers/acpi/fan.c`) by giving `pagemap.h` the header its own `__sched` annotations need; `wait.h` is now
byte-identical to mainline and the published footprint shrank by a file (the cover's regenerated diffstat
went 943 → 942 files). 0087 gates the landed display objects behind `CONFIG_MTK_DISP_BRINGUP`, **default
`n`** per the human's instruction, mirroring the vendor's `obj-$(CONFIG_MTK_FB) += dispsys/`.

Re-measured from the **published `.eml` set**, not the landing tree (that distinction is the point of the
exercise): a fresh worktree at `v5.15.220`, `git am` of 0001-0087 → `rc=0`, `dirty=0`, tree
`deba5bd29ec656ecb9b542837198cccc76cc5a09`, and `0001-0085` still → `01e8b1eae19a…`. The config of record
now hashes `d780d6d3d391…` where the pre-0087 state was `758ae54339bf…` - a *legitimate* move, because
0087 adds a Kconfig symbol, and precisely the kind of drift the `.config` hash rule exists to catch: it is
recorded rather than explained away, and `CONFIG_MTK_DISP_BRINGUP` reads `n` in it.

The rest of that run, in the same fresh tree: `make prepare` `rc=0` with 0 `error:` lines, which is 0086
being exercised on a tree nobody had built before; the whole-tree **link with the gate off**
`make ARCH=arm64 -j2 vmlinux` → `rc=0`, **0 `error:` lines and 0 `undefined reference` lines** over 3,693
object files, `nm` showing **zero** display symbols and the providers still in (`mtk_iommu_v2_sys` 130, SMI
entry points 5); `Image.gz-dtb` at 12,204,094 B with an appended DTB payload of 493,517 B — the size
recorded in build 37 — and `mt6768.dtb` still `34a7e6b536a3…`, so 0078-0087 touch no DT; then, in that same
tree, `CONFIG_MTK_DISP_BRINGUP=y` → `rc=0`, 0 errors, **15/15** objects, 107 warnings. (`Image`/`Image.gz`
differ by 4 B from the landing-tree measurement because `CONFIG_LOCALVERSION_AUTO` embeds
`5.15.220-g<commit-sha>`; the stable identity checks are the appended-payload size and the dtb hash, and
they match.)

That run also caught two defects in the **gate itself**, which is the part worth writing down:
`l2-slice-gate.sh` derived its expected-object list with a `sed` that matched only the literal `obj-y`, and
0087 had just rewritten every line to the gated form, so the list collapsed to one entry and the existence
check passed on a list that no longer described the slice — it printed `GATE GREEN` while checking 1 of 15
objects. The pattern now matches both shapes and a second, independently grepped count is asserted to
agree with it. The worktree-clean check likewise counted untracked files, so any tree that had been built
failed it; it now fails only on tracked modifications (a build leaves `arch/arm64/boot/Image.gz-dtb`, which
the kernel's `.gitignore` does not name). The lesson for every later round here: **read the counts, not just
the verdict.** Full numbers in `report/build.json` under `l2_published_set_gate45`, raw logs in
`portwork/logs/gate-published-0087.summary` and `logs/gatepub-*.log`.

What the next slice may **not** do, per the same instruction: no expansion of display or CMDQ architecture
until this published-series gate run is clean and the repository state is synchronised. The narrow B′
record-layer direction, now costed against measurements in `l2-record-layer-design-bprime.md`: the 4 entry
points (`cmdqRecWrite` via `ddp_reg.h:205/216/232`, `cmdqBackup{Allocate,Read,Write}Slot` at
`ddp_drv.c:95/98/108`) split into a slot pool that can land alone and a record-write adapter that must wait
for a mailbox provider to bind the `gce` node, because `cmdq_pkt_write_s_value()` needs a `struct cmdq_pkt`
that cannot exist until then. The hardware-only question - the pool's address under M4U/SMI - is left
explicitly inside the design rather than assumed away (decision 146). And 0087's gate is not a
capability: with the switch on the display objects compile, and `vmlinux` still fails on 507
references (502 after 0088, see 11.8). That is the honest boundary of that layer.

### 11.8 0088: the slot-pool half lands, and the record half is measured, not estimated

The directive for this round was to land `cmdqBackup{Allocate,Read,Write}Slot` first, keep
`cmdqRecWrite` deferred until the GCE provider/binding question is answered from stock evidence,
and then reassess the GCE requirement from the actual display callsites. All three are done.

**What landed** (`0088`, tree `1a7cf42b066c5379a93cea37fa22a41a4bd9d4c3`, 4 files / 256 added lines):
`drivers/soc/mediatek/mtk-cmdq-disp-slot.c` (222 ln) + `include/linux/soc/mediatek/mtk-cmdq-disp-slot.h`
(32 ln) + one `Makefile` line + one help-text line in `video/Kconfig`. **No new Kconfig symbol** -
the `obj-` line is keyed directly on `CONFIG_MTK_DISP_BRINGUP`, after three alternatives were measured
(`default MTK_DISP_BRINGUP`: inert against an explicit `is not set` in `.config`; `select`: propagates
but can never force off; `depends on MTK_CMDQ`: dead, because `CONFIG_MTK_CMDQ` is unset in the config
of record and the mainline helper builds via `drivers/soc/mediatek/Makefile:20`'s `MTK_CMDQ_MBOX` line).
The semantics are stock's, defects included: the lookup finds the pool containing `base + idx*4` and
does not clamp `idx` to that pool's `slot_count`, so an out-of-range index aliases into the neighbouring
pool instead of failing; the write path carries no barrier and returns the value (`return value;`,
mirroring `cmdq_helper_ext.c:2202`). Excluded for lack of references: `cmdqBackupFreeSlot`, the
`cmdq_alloc_mem`/`cmdq_cpu_*` layer, per-client pools, and the debug/pid/prefetch/CPR machinery.

**Gate, both directions** (numbers in `report/build.json` under `l2_slot_pool_publish46`): with the
switch off the whole tree still links - `vmlinux` 167,987,640 B, `System.map` 6,878,442 B, 0 undefined
references, 0 `cmdqBackup*` symbols in the image, `Image.gz-dtb` 12,204,087 B with the 493,517 B
appended-DTB payload, `mt6768.dtb` 122,474 B / sha `34a7e6b536a3` unchanged, and `.config` byte-identical
(`d780d6d3d391`) to the 0087 tip. With it on: 15/15 display objects plus the provider (57,256 B, the 3
symbols defined exactly once tree-wide), 0 error lines, 0 warnings from the two new files, and the
whole-tree link goes from 507 to 502 undefined-reference lines - the three slot names, and nothing else.
`undeps.py` confirms the three are gone from the no-provider list (67 names remain at that build state,
over 3,709 objects - the count is per-build-state and is quoted that way in every round from here on).

**Address arithmetic is now tested on the host**, because a kernel build cannot show it:
`tests/mtk_disp_slot_host_check.c` transcribes stock's `cmdqCoreAllocWriteAddress` /
`cmdqCoreReadWriteAddress` / `cmdqCoreWriteWriteAddress` beside the port and runs 37 cases with 0
mismatches (output in `report/mtk-disp-slot-check.txt`). Two of those cases are the aliasing hazard:
past-the-end indexes are silently dropped by both, and with two 16-slot pools allocated contiguously -
as they can be - index 16 of pool 1 writes slot 0 of pool 2 *on both sides*. The one intentional
divergence is documented in the source: stock's `s32 offset` truncates when two pools sit 4 GiB apart
and can alias into a wrong pool, the port's `long` refuses; unreachable here (low DRAM), recorded rather
than hidden. This also caught a methodology bug of mine: the first version of the alias case shared one
arena between the two implementations, so it "agreed" while asserting nothing - a test must assert the
observable it claims to demonstrate.

**The reassessment, from the callsites.** `cmdqRecWrite`'s 29 link-time references come from
`ddp_mutex.o` and `ddp_rsz.o` via the `DISP_REG_*` macros in `ddp_reg.h:115/205/216/232`; 9 of the 11
symbols those objects define are used by `ddp_manager.o`, so the mutex layer is live in the landed set.
But `ddp_manager.c` only forwards the `cmdqhandle` it is *given* (`:49`, `:415`, `:545`), `nm -u` finds
0 references to `cmdqRecCreate`/`cmdqRecDestroy`, and `DISPSYS_SLOT_BASE` is `#define … dispsys_slot`
(`ddp_reg.h:115`) - the global the allocator fills, not a constant base. So the deferred half costs the
tree a link, not the device a behaviour, and the design in `l2-record-layer-design-bprime.md` stands
unchanged: `cmdqRecWrite` lands with whatever slice first creates a record, and the GCE binding answer
has to come from stock evidence about the vendor node. No `#mbox-cells`, no compatible string, no
port-local provider was added. `CONFIG_MTK_DISP_BRINGUP` stays `default n`; nothing here is a functional
claim - the panel is still not enabled by the driver, and nothing is flashed or booted.

### 11.9 The deferred half, from stock evidence (no code this round)

The GCE provider/binding question that keeps `cmdqRecWrite` out is now answered from the vendor tree in
this repository, and the answer is recorded in `report/gce-binding-stock-evidence.md`. In one line: stock
does not put the mailbox role on the `gce` syscon node at all - it has a second node `gce_mbox` with
`"mediatek,mt6768-gce"` and `#mbox-cells = <3>` (`arch/arm/boot/dts/mt6768.dts:1601`), whose provider is
mainline's own `drivers/mailbox/mtk-cmdq-mailbox.c` plus one table entry (`mt6768-gce` ->
`gce_plat_v2`, `.thread_nr = 16`) - and the display engine reaches it through the ordinary
`mbox_request_channel()` in the helper, not through any vendor mailbox extension
(`even_defconfig`: `# CONFIG_MTK_CMDQ_MBOX_EXT is not set`, `CONFIG_MTK_CMDQ_MBOX=y`). Our tree already
builds that provider and that helper (`mtk-cmdq-mailbox.o` 123,568 B, idle; `mtk-cmdq-helper.o` 104,232 B
with `cmdq_pkt_write_s_value` and `cmdq_pkt_write_s_mask_value` defined), so nothing has to be invented.
What has to be *decided* is whether to edit the already-published device tree and mailbox stack to close
the last 29 references - 2 cells instead of stock's 3, or stock's split-node topology - and that is a
human call, so no `#mbox-cells`, compatible string or port-local provider was added and the tree is
unchanged this round. The 0088 tip (`1a7cf42b066c...`) stands as published and gated.

### 11.10 Sizing the DSI/LCM instruction: both halves measured, and neither can land yet

The post-0088 instruction was to keep the record-write half deferred and take the DSI/LCM layer next.
Sizing it against the tree (`report/l2-next-slice-sizing.md`) turned up two gates, both measured this
round in the scratch tree at the published tip. First, all seven remaining vendor `dispsys` objects fail
in isolated compilation - six on the header chain (`ddp_ovl.h` via `ddp_info.h:15`, `ddp_mmp.h`,
`mtk_dramc.h`, `disp_dts_gpio.h`), and `ddp_ovl.c` additionally carries 35 record-API references
including `cmdqRecWriteSecure`/`cmdqRecWriteSecureMetaData`/`cmdqRecSetSecure`, which 0083 never provided.
Second, the panel side's two open references from `ddp_drv.o` (`disp_late_bias_enable`,
`display_bias_regulator_init`) resolve only to `lcm_pmic.c`, a 149-line file whose *real* branch is
`#if defined(CONFIG_RT5081_PMU_DSV) || defined(CONFIG_MT6370_PMU_DSV)` - and this board's own
`even_defconfig:1693` sets `CONFIG_MT6370_PMU_DSV=y`, a symbol 5.15 does not have. Landing that file
alone would compile the vendor's `#else` (`return 0`) and "close" the references by deleting two
`regulator_enable()` calls - the silent-substitution failure mode this project has rejected twice.

So the next honest slice is the provider behind it: the MT6370 PMU DSV regulator cell
(`drivers/misc/mediatek/pmic/mt6370/`, 13 files / 15,200 lines as a directory, of which
`mt6370_pmu_dsv.c` is 584; `MT6370_PMU_DSV depends on REGULATOR && MFD_MT6370_PMU`), the same shape of
work as 0075's pwrap + MT6358 alias, and with 0070's DT transplant already carrying `mt6370.dtsi` /
`mt6370_pd.dtsi` in the audited tree. That is decision 149; no code was written this round, and the
published state is unchanged at 0088 / `1a7cf42b066c…`.

### 11.11 0089: the bias provider lands, and "it links" turns out not to mean "it probes"

One slice, as instructed, with the record-write half still deferred (148/149). 0089 is
`misc: mediatek: give the panel bias rails their MT6370 provider` - 22 files, +4,972 lines, landing
tree `7320325c38fd188de726f3ba658d0f6b80e7eb6`, published as patch 0089 of 89.

**What it carries.** Everything with code in it is verbatim from the vendor tree:
`drivers/misc/mediatek/pmic/mt6370/v1/`'s `mt6370_pmu_{i2c,regmap,irq,subdevs,core,dsv,dsv_debugfs}.c`
(380/391/401/167/281/583/246 = 2,449 lines) with the four `inc/` headers they actually include,
`drivers/misc/mediatek/include/mt-plat/rt-regmap.h` (216) with `drivers/misc/mediatek/rt-regmap/rt-regmap.c`
(1,646), and `drivers/misc/mediatek/lcm/lcm_pmic.c` (149). The only authored content is five
Makefiles/Kconfigs, two wiring lines in `drivers/misc/{Kconfig,Makefile}` and a help-text paragraph.
`v1/` rather than the parent directory because the vendor's own `pmic/mt6370/Makefile:1-4` descends into
`v1/` for `CONFIG_MACH_MT6768=y` - which is a condition this port's config satisfies, since `apply.sh`
enables `MACH_MT6768`. That closes 11.10's dangling note about an "885-line dead variant": the file the
earlier round measured at the top level is simply not the one this SoC builds.

**The measurement that changed the wiring.** The first version keyed all nine objects on
`CONFIG_MTK_DISP_BRINGUP` and added `-DCONFIG_MT6370_PMU_DSV=1` in `lcm/Makefile`. It compiled clean and
closed both bias names. Grepping every `CONFIG_*` token in the ported sources - the check that catches
silent branch loss in a verbatim port - then found `mt6370_pmu_regmap.c` keeping its whole body inside
`#ifdef CONFIG_RT_REGMAP` (lines 12-370). Stock reaches that symbol via `MFD_MT6370_PMU`'s
`select RT_REGMAP`; without it `mt6370_pmu_regmap_register()` is a `return 0` stub, `chip->rd` stays
NULL, and `mt6370_pmu_core.c:166` calls `rt_regmap_cache_reload()` on it. So the final wiring uses
stock's symbols and stock's Kconfig text (2 blocks verbatim, the 5 unported sub-device blocks omitted),
the board fragment enables `CONFIG_MFD_MT6370_PMU`/`CONFIG_MT6370_PMU_DSV` exactly as
`even_defconfig:1687-1693` does, and only `lcm_pmic.c` stays under the display switch - which is also why
the config of record moved for the first time since 0086, from `d780d6d3d391` to `099cdd6421b6`.
Two rejected alternatives, recorded because they were both tempting: a `-D` (the consumer's branch would
depend on a Makefile line that menuconfig cannot see) and `def_bool MTK_DISP_BRINGUP` on the PMIC symbols
(a board PMIC gated by a display switch, and the gate passes the switch on the make command line, which
does not propagate through `default` into `.config` - the 0088 round measured exactly that asymmetry).
The other branch points were checked, not assumed: `mt6370_pmu_i2c.c:177`'s
`!defined(CONFIG_MTK_GPIO) || defined(CONFIG_MTK_GPIOLIB_STAND)` takes the same `of_get_named_gpio()`
path in both trees, and `DEBUG_FS` (y here, not set in `even_defconfig`) is the one place the port exposes
more than stock.

**What the gate caught in itself.** The first clean gate run printed `0 undefined references` in *both*
directions. Both were lies: `rt-regmap/Makefile` was missing the `-I` pair that
`drivers/misc/mediatek/m4u/Makefile:11-13` carries (stock supplies it globally at
`drivers/misc/mediatek/Makefile:3`), the compile died, and a build that dies before the link never runs
the link. `slice0089-gate.sh` now asserts the `LD vmlinux` marker and the object count alongside the error
count, and reads an empty name set as a failure rather than a pass. It also landed the `rt_regmap_cache_reload`
reference the slice had initially *introduced* by pulling in `rt-regmap.c` - a new undefined name is as
much a regression as a stale one.

**Numbers.** Gate off (what any user builds): rc=0, 0 `error:` lines, 0 undefined references, vmlinux
168,340,520 B, Image.gz-dtb 12,228,271 B (0088: 167,987,640 / 12,204,087), `mt6768.dtb` byte-identical
(122,474 B, sha `34a7e6b536a3...`), and `nm vmlinux` shows the intended split - `mt6370_pmu_regmap_register`
and `rt_regmap_device_register` present, `display_bias_regulator_init` absent. Gate on: all 9 objects
rebuilt from scratch, rc=0 with 0 errors and 0 warnings; whole-tree link 502 → 499 undefined lines and
80 → 78 distinct names, the closed pair exactly `disp_late_bias_enable`/`display_bias_regulator_init`,
zero newly introduced; 39 distinct global text symbols, none defined anywhere else in the tree.
No regulator-core change was needed, which 11.10 had left open: 5.15's `regulator_dev_lookup()` already
falls through to `regulator_lookup_by_name()` → `regulator_match()` → `rdev_get_name()`, which prefers
`constraints->name`, and the landed DT sets `regulator-name = "dsv_pos"/"dsv_neg"` - so
`regulator_get(NULL, "dsv_pos")` resolves without porting 0075's `of_regulator_match()` pattern.

**The limit, and it is not a build limit.** Nothing binds this driver yet. The DTB this tree appends
(`CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES="mediatek/mt6768"`, built from `arch/arm64/boot/dts/mediatek/mt6768.dts`)
carries the MT6370 *configuration* node - decompiled: `mt6370_pmu_dts` with `interrupt-controller`,
`#interrupt-cells = <1>`, `mt6370,intr_gpio = <&pio 3 0>` plus the legacy `mt6370,intr_gpio_num = <3>`,
and the `mt6370_dsvp`/`mt6370_dsvn` cells - and it carries `i2c5@11016000` with `compatible =
"mediatek,i2c"`. What it does not carry is the I2C client `subpmic_pmu@34` that the driver's
`of_match_table` would bind (`mediatek,subpmic_pmu`, already listed at `mt6370_pmu_i2c.c:342-347`, so no
driver edit is needed): that node lives in `arch/arm64/boot/dts/oplus6768_20761/cust.dtsi:151`, in a
board directory this tree does not compile - one file, no `.dts`. The landed `i2c5` node also lacks the
`#address-cells`/`#size-cells` a child needs and the bus properties the board file sets
(`clock-frequency = <3400000>`, `mediatek,use-push-pull`). Whether the port should grow the SoC dts or
adopt a board dts as its DT surface of record is the first architectural fork here that measuring the
vendor tree cannot settle, because the vendor tree has both files and this port compiles one; it is
recorded as decision 151 with three costed options and no patch attached. One runtime question that *can*
be answered from source was: `mt6370_pmu_dsv_irq_register()` is `void` and skips any named IRQ resource it
cannot find (`mt6370_pmu_dsv.c:199-222`), so the missing `interrupts` property on the DSV child cannot
fail or crash the probe - the OCP handler just stays unregistered, as it does on any board whose DT omits it.

Next is unchanged by this slice and still blocked on the same thing: the DSI/component half waits on
`cmdqRecWrite` (29 link references) and therefore on the deferred record layer. The bias path is no
longer one of the open gaps, and the display core still cannot be built into a usable kernel.
### 11.12 Two answers, a sizing correction, and a reset that cost nothing

The human answered both open questions the same day 0089 shipped: the DT surface stays as it is (option
c of 151 - no DT change, the sub-PMIC remains linked-but-unbound, the fork stays recorded), and the next
slice is the LCM/panel-record side. Decision 152.

Sizing that second answer immediately falsified its own description, which is why it is written down
before any code exists. The three panel-side names the landed tree still lacks are *not* in
`drivers/misc/mediatek/lcm/`:

| name | real home in the vendor tree | size |
|---|---|---|
| `set_lcm` | `video/mt6768/videox/disp_cust.c` (+`disp_cust.h`) | 49 (+13) ln |
| `do_lcm_vdo_lp_read`, `do_lcm_vdo_lp_write` | `video/mt6768/videox/disp_recovery.c` (+`disp_recovery.h`) | 1,228 (+34) ln |
| `get_lcm` | no definition found under `drivers/misc/mediatek/` at all | - |

So the slice is two `videox` files, and `get_lcm`'s provider has to be found by measuring the landed
tree's references rather than by assuming a signature - the lesson from 143's wrong file, restated in
149's census method.

*(corrected the same evening, 2026-09-06 - see 11.13: measuring it found that `get_lcm` is not a gap at all,
it is absent from both trees, and that `disp_cust.c` only forwards into the unported DSI/primary-display
layer, so this "two videox files" target is blocked by the same deferred half as DSI. The next-slice
sentence above should be read as superseded.)* The `lcm/` directory stays out until a callsite in this tree needs it:
`lcm_common.c` 1,477, `mt65xx_lcm_list.c` 1,654, `lcm_i2c.c` 382, `lcm_gpio.c` 326, `lcm_util.c` 257
(plus the landed `lcm_pmic.c` 149), 8 headers / 1,401 ln and 87 panel subdirs.

Stock's own board selection, measured from `even_defconfig` while sizing this: `CONFIG_MTK_LCM=y` (:1713),
`CONFIG_CUSTOM_KERNEL_LCM` naming **six** panel directories (:1714 - `ili7807s_xxx_fhd_dsi_vdo_dphy`,
`ili7807s_jdi_fhd_dsi_vdo_dphy`, `nt36672c_tm_fhd_dsi_vdo_dphy`, `ilt9882n_truly_even_hdp_dsi_vdo_lcm`,
`nt36525b_hlt_even_boe_hdp_dsi_vdo_lcm`, `ilt7807s_hlt_even_hdp_dsi_vdo_lcm`), `MTK_LCM_PHYSICAL_ROTATION="0"`
(:1721) and `CONFIG_MTK_LCM_DEVICE_TREE_SUPPORT` **not** set - only `..._PASCAL_E=y` (:1716). That is
evidence for the standing instruction to keep LK panel selection: the panel identity reaches the kernel
through the handover, not through DT, and 6 of 87 directories is the set the vendor actually compiles.
One mechanism in that Makefile is flagged rather than copied: `lcm/Makefile:31-34` upper-cases each
`CUSTOM_KERNEL_LCM` name into a `-D` define, which is precisely the Makefile-drives-branch-selection shape
decision 150 rejected for the PMIC. If a panel driver ever lands, that choice gets made explicitly.

**The reset.** At 20:51 UTC the sandbox rolled back: `/home/user/portwork/` (host tools, the gcc 9.3
prebuilt, `ref/linux`, the `series`/`buildfull`/`buildpub` trees, `dl/`, all logs) disappeared and the
local repo lost its commit history, landing at the session base `011d4a1f2` with the later files present
but untracked. Nothing was lost, because everything durable is pushed: `git fetch origin` +
`git reset --hard 11a9ffb4c` brought back the 89-patch series, the gate scripts and the records, and
`cp -a Zenium_Kernel/upstream-port/tools/portwork/. portwork/ && bash portwork/restore.sh && bash
portwork/build0.sh` rebuilds the toolchain, the base tree and the series tree from the repo alone. That is
the second time the decision to version `env.sh`/`apply.sh`/the gate scripts under `tools/portwork/` has
paid for itself, and 0089's gate script was committed hours before this one needed it.

The reset also found a real bug in the recovery tooling, fixed in the same commit as this note:
`restore.sh` sources `tools/env.sh` to get `M4` *before* installing it, and the durable copy in the repo
is flat (`tools/portwork/env.sh`, not `tools/portwork/tools/env.sh`), so the source silently failed,
`M4` was unset, and the whole restore aborted with `bison: m4 subprocess failed` next to a perfectly good
bison. `restore.sh` now installs `tools/env.sh` and `configs/apply.sh` from the durable copies before
anything sources them and exports `M4` defensively; `bison ok: 1270-line parser generated` in
`logs/restore.log` is the assertion that proves it, because that probe is what fails when it does not.

Consequence for cadence: the published set's *build* state is unknown until it is re-measured in the
recreated tree, so the next round re-runs the 0089 gate in both directions first (that becomes a
re-verification entry in `report/build.json`, not new evidence for 0089), and only then starts the
`videox` slice.

### 11.13 Re-verifying 0089 in a recreated environment, and the census that replaced the guess

The reset described in 11.12 left the published state intact but the *build* state unproven, so the first
thing done afterwards was the gate, in the tree `restore.sh` rebuilt from the `.eml` set alone. It took
874 s and every number reproduced (`report/build.json`, gate `l2_pmic_dsv_reverify48`):

- the gate now asserts its own subject: `tree matches the published 0089 tip: yes`, on
  `7320325c38fdc188de726f3ba658d0f6b80e7eb6`, while `git rev-parse HEAD` in that tree reads
  `e1ceeaf8e` - a different commit sha, the same tree. This is the case for keying every claim to the
  tree hash; it also means nothing in the port depends on the local commit ids surviving.
- switch off: `rc=0`, `LD vmlinux` present, 0 `error:` and 0 undefined-reference lines, vmlinux
  168,340,520 B, System.map 6,911,826 B, Image 34,165,248 B, 8 board objects, `lcm_pmic.o` absent, and
  `nm vmlinux` with 0 hits for `display_bias_regulator_init` against 4 for each of
  `mt6370_pmu_regmap_register` and `rt_regmap_device_register`.
- switch on: 9/9 objects rebuilt from scratch, 0 errors, 0 warnings, 499 undefined-reference lines over
  78 distinct names, the two bias names absent from that set, 39 new text symbols, 0 collisions.
- what did *not* reproduce byte-for-byte: four object sizes by -8 B and `Image.gz`/`Image.gz-dtb` by
  -17 B, because the version string embeds `git describe`. The appended-DTB payload (493,517 B) and
  `mt6768.dtb` are byte-stable. A gate that compared image *bytes* would have called this a regression,
  which is why it compares sizes, the DTB payload and symbol sets.
- one recorded number needed sharpening: "29 `cmdqRecWrite` references" is 29 printed lines *plus*
  `ld`'s `more undefined references to cmdqRecWrite follow` truncation notice, so it is a lower bound on
  call sites and an exact count of lines. The name-level counts are the ones gates use.

Then the census that 11.12 should have started with. `report/l2-open-names-at-0089.txt` now holds the 78
names and, per name, the vendor file that would provide it. The shape of the remaining work is not what
152 assumed:

| group | count | what it means |
|---|---|---|
| provided in `video/mt6768/` (dispsys `ddp_*_ex.c`, `videox/disp_*.c`) | 52 | the component + DSI + primary-display half, blocked on the deferred record layer |
| provided in `video/common/` (aal30, corr10, color20, pwm10, rdma20) | 9 | the shared-IP layer, never attempted, each file pulling `ddp_path.h`/`disp_dts_gpio.h`/`primary_display.h` |
| not functions at all (`ddp_driver_*` structs, `g_mobilelog`, `module_list_scenario`) | 14 | data symbols owned by the same blocked files; no header work reaches them |
| `smi_debug_bus_hang_detect` | 1 | an **arm** problem, not a missing layer - see below |
| `cmdqRecWrite` | 1 | the deferred record write, decision 148/149 |

The single-name case is the interesting one and it is a small mirror of 0089: `drivers/misc/mediatek/smi/`
in this tree holds only `smi_public.h`, whose `#else` (line 32) turns `smi_debug_bus_hang_detect()` into
`((void)0)` and whose `#if` (lines 23-27) declares it. This tree has `CONFIG_MTK_SMI_EXT=y` (apply.sh's
own symbol list) and the caller `ddp_dump.c:886` is landed, so the declaration arm is live and the
provider - the vendor's `smi_drv.c`, which 0078 deliberately replaced with mainline's `mtk-smi` driver -
is not in the tree. Three honest answers exist (keep this tree on the vendor's no-op arm by making the
guard false here; add wrappers over mainline's PM/larb APIs, which the live callsite would justify under
the no-speculative-shim rule; or port the vendor debug path alongside mainline's driver) and the choice
is decision material for the next round, recorded as decision 153, not a patch slipped in tonight.

Sizing that also reclassified the panel side. `pwm10/ddp_pwm.c` - the backlight layer, 1,052 lines, only
one `cmdqRec` reference - looked like the cheapest entry into shared IP until its include list was read:
`ddp_path.h`, `disp_dts_gpio.h`, `mtk_leds_drv.h`, `mtk_leds_sw.h`, `primary_display.h`. And
`disp_cust.c`, the provider of `set_lcm`/`read_lcm`, turned out to be nothing but forwards into
`primary_display_manual_lock()`, `primary_display_idlemgr_kick()`, `_is_power_on_status()` and
`DSI_dcs_{set,read}_lcm_reg_v4()`. So the panel-record half and the DSI half are the same blocker wearing
different hats, and the next slice is either the SMI arm decision or a shared-IP directory landed with
the vendor's own `#else` arms - not `lcm/`, and not `videox/` alone.


### 11.14 Pricing the next slice with the compiler instead of with grep

The census in 11.13 said which vendor file *mentions* each open name. That is not the same question as
which file *provides* it, and the difference mattered: `_get_dst_module_by_lcm` was listed against
`ddp_clkmgr.c:320`, which is a call from a file this port already landed, while the definition is
`videox/primary_display.c:1211`; `ovl_to_index` was listed against `ddp_irq.c:243` (a call) with the
definition in `ddp_ovl.c:138`. Re-derived from definition-shaped lines only, 70 of the 78 names resolve
to 17 provider `.c` files, and the remaining 14 - `ddp_driver_ovl`, `ddp_driver_color`, `aal_dbg_en`,
`module_list_scenario`, `g_mobilelog` and friends - are data symbols owned by those same files, with
callers already landed in `ddp_info.c`'s module table (`:69-213`), `ddp_debug.c` and `ddp_mutex.c`. Two
conclusions follow straight from that: no header work could ever have closed those 14, and the port's own
earlier slices are what created several of the gaps.

The other hope died in the same pass. If a name were open only because an `#if` arm in an *already
landed* file excluded its definition, a config-fidelity fix would be the cheapest slice in the port. So
every landed `.c` was searched for a definition of each of the 78, printing the enclosing `#if` stack for
any hit: there are none. Fifteen names have a *prototype* in a landed header (`ovl_base_addr` in
`ddp_ovl.h:70`, `DSI_set_cmdq_V2` in `ddp_dsi.h:200`, `set_lcm` in `videox/disp_cust.h:8`) which is
precisely what an undefined reference is - declared, never defined here - and one of those arms is itself
config-gated (`disp_bls_set_backlight` under `#ifdef CONFIG_MTK_FB_DUMMY`, absent in stock and in ours).

Ranking by names-per-line then leaves a short list, and reading include lists to pick between them is
still guessing about the compiler. So each unlanded `dispsys` provider was copied verbatim into the tree
of record, given one gated `obj-` line, and *built* with `CONFIG_MTK_DISP_BRINGUP=y`
(`portwork/probe-file.sh`, log `portwork/logs/probes-0090.log`):

| file | lines | build result |
|---|---:|---|
| **`ddp_path.c`** | 987 | **clean** - object 162,296 B, 21 global symbols, 0 errors, 0 warnings of its own |
| `ddp_mmp.c` | 934 | clean - 85,592 B, 7 symbols, 5 names |
| `ddp_ovl.c` | 2,823 | `fatal error: mtk_dramc.h` (line 21) |
| `ddp_rdma_ex.c` | 1,649 | `fatal error: ddp_matrix_para.h` (line 12) |
| `ddp_wdma_ex.c` | 1,330 | `fatal error: ddp_matrix_para.h` (line 11) |
| `ddp_dsi.c` | 8,377 | `fatal error: disp_dts_gpio.h` (line 35) |
| `ddp_disp_bdg.c` | 5,263 | `fatal error: ddp_reg_disp_bdg.h` (line 12) |

Five files each miss exactly one header, which is the same kind of step 0085 was, so the queue after the
path slice is set by that header rather than by taste: `ddp_matrix_para.h` unlocks rdma and wdma together,
then `mtk_dramc.h` for ovl, `disp_dts_gpio.h` for dsi, and `ddp_reg_disp_bdg.h` plus the measured rewrite
at `ddp_disp_bdg.c:3030` for bdg.

`ddp_mmp.c` was declined although it compiles. `grep -rl "define DEFAULT_MMP_ENABLE"` over
`drivers/misc/mediatek` and `include/` returns nothing, so stock's own `ddp_mmp_init()` body compiles out
on every board in this tree, and with `CONFIG_MMPROFILE=y` the hooks only mean something if
`drivers/misc/mediatek/mmp/` comes with them. Landing it would close five instrumentation names and move
no frame: the artificial slice this plan keeps refusing.

`ddp_path.c` was kept, and then priced properly - not by what one object needs, but by linking the whole
tree with and without it (`portwork/before-after-0090.sh`, logs `on-before.log`/`on-after.log`):

| whole-tree ON link | before | after |
|---|---:|---:|
| compile errors | 0 | 0 |
| warnings attributed to `ddp_path.c` | - | **0** |
| `undefined reference` lines | 486 | 281 |
| **distinct undefined names** | **78** | **65** |
| names closed / opened | - | 15 / 2 |

The 15 include `ddp_path_init`, `ddp_connect_path`, `ddp_get_scenario_list`, `ddp_get_dst_module` and
`module_list_scenario`, each of them referenced by a landed file (`ddp_drv.c`, `ddp_manager.c`,
`ddp_mutex.c`), which is the test this port uses for "meaningful": the slice removes gaps the port made.
The 2 it opens - `cmdqRecWaitNoClear`, `cmdqRecSetEventToken` - come from the `#ifdef
CONFIG_MTK_SMI_EXT` region at `:881-:933` (live for this board, since `even_defconfig` sets
`CONFIG_MTK_SMI_EXT=y`) and join `cmdqRecWrite` in the deferred record family, decision 148. They are
left undefined and documented rather than shimmed, and the landing shape does not depend on how that
decision is eventually revisited: either way the record layer closes them, not us.

The run also corrected two things this plan had written down. A directory-scoped `make` is not a
measurement of the ON state: `video/Makefile` descends into `videox/` on `obj-$(CONFIG_MTK_DISP_M4U)`
while the objects inside are keyed on `CONFIG_MTK_DISP_BRINGUP`, so building only `dispsys/` drops the
`videox` half of the gated set and reported `disp_helper_get_option`/`disp_helper_get_stage` as new gaps
- a full ON build compiles `videox/disp_helper.o` (452 lines, landed with two documented `Port:` comments
where calls into unported `primary_display.c` were removed) and it defines both. And "0 warnings" in the
0089 gate means 0 warnings from the 9 objects that run *rebuilt*: a full ON recompile emits 7
`warning:` lines from landed headers (`cmdq/v3/cmdq_record.h:804,833,845,889`,
`cmdq_helper_ext.h:880,881,988`, "declared inside parameter list", reached through `ddp_log.h ->
ddp_debug.h -> ddp_dump.h -> ddp_path.h`) for every file that includes that chain. Tidying those headers is
its own small, honest slice; it is not a reason to hold the path slice. Finally, the same unchanged tree
printed 486 reference lines here and 499 there, ld truncating per object, while both read 78 distinct
names - which is why the gate keys on names and never on line counts.

### 11.15 The record layer is un-deferred, and stock evidence shrinks it before a line is written

Asked and answered the same day: of four costed options for the deferred `cmdqRecWrite` half, the user
chose **un-defer narrow B′** (port-local record provider), which the question framed as reopening the
"DT surface of record stays as-is" constraint. Measuring that constraint before acting on it turned it off:
the port's `arch/arm64/boot/dts/mediatek/mt6768.dts` already contains stock's mailbox provider node
*verbatim* - `gce_mbox@10238000` at :1614, `compatible = "mediatek,mt6768-gce"`, `reg`, `interrupts`,
`default_tokens`, `clocks`/`clock-names = "gce", "gce-timer"`, `#mbox-cells = <3>`, `#gce-event-cells`,
`#gce-subsys-cells` - and `diff` against the vendor file at the same lines reports them identical, because
the DT slice copied the node whole rather than the subset the syscon consumer needed. **So B′ as chosen
requires no DT edit**, and the earlier "leave the DT alone" instruction stands unchanged.

The provider's identity also needed correcting, against my own question. The option text named
`cmdq/v2/cmdq_record.c` (2,352 lines) because that is what the census's grep printed first. The vendor
`cmdq/Makefile:22` decides otherwise:

    ifeq ($(CONFIG_MTK_CMDQ_V3),y)
    ifneq (,$(filter $(CMDQ_PLATFORM), "mt6739" "mt6768" "mt6771" "mt8168" "mt6785" "mt6761" "mt6765" "mt6779"))
            obj-y += v3/
    endif
    else ifneq (,$(filter $(CMDQ_PLATFORM), "mt8167" "mt6761" "mt6765" "mt6779"))
            obj-y += v2/
    endif

with `even_defconfig:1804` setting `CONFIG_MTK_CMDQ_V3=y`. For mt6768 stock builds **v3** - 4,140 lines of
`cmdq_record.c` alone, 16 objects in `cmdq/v3/` - and mt6768 is *not* in the v2 fallback list, so without
V3 this board would get no engine at all. v2 is not this board's provider and will not be ported as a
stand-in for it. `CONFIG_MTK_CMDQ_MBOX=y` (`even_defconfig:4452`) is the other half of the picture: stock
takes its mailbox provider from `drivers/mailbox/mtk-cmdq-mailbox.c`, which in the 4.19 tree carries
`.compatible = "mediatek,mt6768-gce"`, `.data = &gce_plat_v2` (`:2053`) - the same file mainline has, evolved.

That comparison is what the next round has to price, and both sides are now read, not assumed:

| | vendor 4.19 `drivers/mailbox/mtk-cmdq-mailbox.c` | mainline 5.15.220 in our tree |
|---|---|---|
| mt6768 in the match table | yes, `gce_plat_v2` (`:2053`) | no (`:673-678` = mt8173/mt8183/mt6779/mt8192/mt8195) |
| `cmdq_xlate` cells | 3: `args[0]` thread, `args[1]` timeout (`0` → `CMDQ_TIMEOUT_DEFAULT`), `args[2]` priority | 2: `args[0]` thread, `args[1]` **priority**; `args[2]` never read, no `args_count` check |
| thread count | `gce_plat_v2.thread_nr = 16`, `shift = 0` | per-SoC `gce_plat`, v2 same shape |

Reading the vendor's secure-side xlate (`cmdq/mailbox/cmdq-sec-mailbox.c:1637-1653`) gives the same three
cells in the same order, which is what you would expect if 3 cells are this family's shape rather than an
mt6768 quirk. The consequence for the two candidate shapes: dropping an mt6768 match into mainline's driver
means either reading `args[2]` in a shared xlate (silently redefining the binding for every other SoC
mainline serves, where the binding document describes 2 cells) or branching the xlate per-SoC - and the
standing instruction is to keep mainline's CMDQ stack coherent and carry vendor semantics only where a live
callsite demands them. A port-local provider avoids touching mainline at the cost of owning a second
controller, and it is the shape the design doc's `#6.3` already recommended for the adapter: a new file
(`drivers/soc/mediatek/mtk-cmdq-disp-record.c`), the object gated so it can be switched off, mainline's
`mtk-cmdq-helper.c` untouched.

Two facts keep this honest whatever shape wins. Nothing in the landed set calls `cmdqRecCreate`/
`cmdqRecDestroy`, so the macros take their `handle == NULL` CPU branch and the record path is unreachable at
runtime: the layer is required at link time, which is why it is being landed, and it cannot be exercised
without a device, which is why landing it will not raise the maturity level past "compiles and links". And
the adapter must fail loudly when it has no channel - a silent drop would be the CPU-substitute fabrication
this port has already rejected twice, in 11.5 and in the 0088 sizing.

Queue as it now stands: **0090** `ddp_path.c` (measured 78 → 65) → **0091** the record layer in whichever
of the two shapes above the next round commits to → **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` +
`ddp_wdma_ex.c`, which the header probe says are each blocked by that one header alone.

### 11.16 - Round 0090: the path/scenario layer, landed and published with its predictions intact

`ddp_path.c` was the largest of the display objects still in the vendor tree and the one every caller in
`ddp_manager.c` had been waiting for: `ddp_path_init()`, `ddp_connect_path()`, `ddp_disconnect_path()` and
`ddp_check_path()` are how a scenario is wired, and 0084/0085 had landed the callers with those symbols
unresolved. It landed verbatim (987 lines, 24,946 B, `cmp`-identical to `4.19.325`'s file) with one
`obj-$(CONFIG_MTK_DISP_BRINGUP)` line, no new Kconfig symbol, and no device-tree edit.

What makes this round different from the earlier ones is that the numbers were written down *before* the
landing (`report/l2-slice-0090-before-after.md`, 11.15) and the gate was then read against them:

| measured | predicted at 11.15 | gate |
|---|---|---|
| distinct open names | 78 -> 65 | 65 |
| `undefined reference` lines | 486 -> 281 | 281 |
| names closed / opened | 15 closed, 2 opened | 15 closed, 2 opened (`cmdqRecWrite` was already open) |
| compile errors in the file | 0 | 0, and 0 diagnostics attributed to it |
| appended DTB payload | 493,517 B unchanged | 493,517 B |
| vmlinux | 168,340,520 B | 168,340,520 B |

Gate `l2_path_layer_publish48`; published as `0090-video-mt6768-land-the-display-path-scenario-layer-the-.eml`
with `bin/publish.py`, which re-verified that 0001-0089 still reproduces the previous tip before and after.
Two workflow facts came out of the publish step and are recorded in decision 156: `publish.py` refuses a dirty
landing tree, and a build artifact (`arch/arm64/boot/Image.gz-dtb`) is enough to make it dirty - move the
artifact, never override the check; and neither the MANIFEST header nor MATURITY's counts are rewritten by the
tool, so those are edited by hand in the same round.

Queue now: **0091** the record adapter (`drivers/soc/mediatek/mtk-cmdq-disp-record.c`, vendor v3 semantics,
no mailbox ABI change, no invented binding) then **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` +
`ddp_wdma_ex.c`.

### 11.17 - Round 0091: the record adapter, landed as vendor-shaped delegation with the encoding measured

The queue's gate node is passed: `cmdqRecWrite`, `cmdqRecWaitNoClear` and `cmdqRecSetEventToken` now have a
provider, the whole-tree open-name count is 62, and no file under `drivers/mailbox/` or
`include/linux/mailbox/` was edited, no compatible or `#cells` was added, and no property was invented. The
shape is what 11.13->11.15 argued for and what the user fixed as the instruction: the narrow MT6768/v3
adapter, not the engine.

Three things the reading settled that the design doc had only inferred, now in the records because each one
changes what the code does:

  * the two event entry points are delegations in the vendor itself (`:1510` and `:1532` call
    `cmdq_pkt_wait_no_clear()` / `cmdq_pkt_set_event()`), so this port delegating is not a weakening;
  * the vendor's masked write starts with `CMDQ_CODE_MOVE` and mainline's with `CMDQ_CODE_MASK`, and the two
    headers give those names the *same number* (0x02), as they do for `WRITE_S_W_MASK` / `WRITE_S_MASK`
    (0x91) - so the delegated write is the same instruction stream, which is a claim the harness now checks
    instead of a claim this document makes;
  * SW sync tokens need no device tree at all (their default id is their own index, per
    `cmdq_core_init_dts_data()`), while `CMDQ_EVENT_MUTEX0_STREAM_EOF` takes `stream_done_0 = <130>` from the
    board's `gce` node - present, so `ddp_path.c:908` resolves exactly as stock's does on this board.

Gate `l2_disp_record_publish49` (62 distinct names, 3 symbols defined once tree-wide, 0 collisions, 0
diagnostics in either new file) and harness 55/0; published as the 91st patch with `0001-0090` still
reproducing the 0090 tip. KNOWN-ISSUES 14 records the three vendor behaviours deliberately not carried
(prefetch insert pairs, the SPR/`CMDQ_CODE_LOGIC` detour, register-typed operands) and why each fails loudly
rather than quietly.

Queue then, as written at 0091: **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` + `ddp_wdma_ex.c` (each
blocked by that one header alone, per the header probe), then the DSI/panel handover names, which are a
device question and not a code question. **0092 measured that queue and did not follow it**, because pricing
it showed the pair opens 21 names while closing 10 (11.18); the slice that is now landed is `ddp_mmp.c`.

### 11.18 - Round 0092: pricing the engines before landing them, and taking the file that subtracts

The queue said RDMA and WDMA. The measurement said those two files are net +11 on the open-name set, so
this round landed the largest measured *reduction* instead - `video/mt6768/dispsys/ddp_mmp.c`, 934 lines
verbatim (`sha256` `f0a113c93138`, gate-compared against the vendor file rather than asserted in prose),
one `obj-$(CONFIG_MTK_DISP_BRINGUP)` line, nothing else: 15 gated objects to 16.

Why the file the port was already calling into is the one to land: `ddp_drv.c` and `display_recorder.c`
have referenced `ddp_mmp_init`, `ddp_mmp_get_events`, `ddp_mmp_ovl_layer`, `ddp_mmp_rdma_layer` and
`ddp_mmp_wdma_layer` with no provider since 0085, and those references are live not because of a Kconfig
symbol but because of `SUPPORT_MMPROFILE`, defined in the landed `video/mt6768/videox/disp_drv_platform.h:37`
and tested at `display_recorder.c:221/1139`. The gate measured the consequence: **62 -> 57 distinct open
names** (211 -> 160 ld reference lines), the five names `open:0`/`defined:1 tree-wide`, **0 names opened**,
`ddp_mmp.o` 85,592 B rebuilt from scratch, 0 diagnostics in the file, 6 new global `T` symbols with 0
collisions, `primary_display_is_video_mode`/`rdma_dump_reg`/`ovl_dump_reg`/`ddp_driver_ovl`/
`disp_pwm_set_backlight` all still `open:1`, and 0089's two bias names, 0090's 15 path names and 0091's 3
record names still closed. Zero new open names is the property that makes this slice routine, and the reason
it holds is that every call this file makes that the port lacks is inside a guard the port already satisfies -
the `CONFIG_MTK_HDMI_SUPPORT` block at `:205`, the `CONFIG_MTK_M4U` block at `:655`, and the three
`mmprofile_*` calls that resolve to the static-inline dummies in the landed `mmp/mmprofile.h` (`:131`,
`:212`, `:216`). `ddp_mmp.o`'s 7 undefined symbols are `_printk`, `__stack_chk_fail` and the five
MVA-mapping/dprec names that `ddp_m4u.c` and `display_recorder.c` already provide.

What the pricing bought, beyond the shape of this round: `ddp_color.c` + `ddp_dither.c` + `ddp_gamma.c`
(4,099 + 409 + 1,574 ln, from `common/color20` and `common/corr10`, all three unconditionally built for this
platform by `video/common/Makefile:55-57`) compile clean and are net **-7** (8 closed, 1 opened), with the
one open name being `cmdqRecReadToDataRegister`; `ddp_ovl.c` + `dramc/mt6768/mtk_dramc.h` is net **+4**;
`ddp_rdma_ex.c` + `ddp_wdma_ex.c` + `ddp_matrix_para.h` is net **+11**; `ddp_dump.c` is a no-op because it
is already landed; `ddp_ccorr.c` does not exist (ccorr is implemented inside `ddp_color.c`), `ddp_aal.c`
needs `mtk_leds_drv.h` and `ddp_pwm.c` needs `disp_dts_gpio.h`, and `videox/debug.c` /
`videox/disp_lowpower.c` need `mtk_disp_mgr.h` / `ion_drv.h` respectively. `common/rdma20` and
`common/wdma20` turned out to be MT6799-only in the vendor's own build and are struck from the queue
entirely. All of it, with the line numbers, is in `report/l2-slice-0092-before-after.md`, and the three
consequences for how the record layer may be grown are in `KNOWN-ISSUES.md` 15.

Two decisions the pricing makes explicit rather than implicit. (a) Both net-negative candidates beyond this
round want something from the record adapter that 0091's narrow shape does not carry: the colour trio wants
a fourth entry point (`cmdqRecReadToDataRegister`, whose live branch here is the pure
`CMDQ_CODE_READ_S` encoder at `v3/cmdq_record.c:1576` - `ddp_color.c:4040` passes `CMDQ_DATA_REG_PQ_COLOR`
= 0x04, below `CMDQ_DATA_REG_JPEG_DST` = 0x11 at `cmdq_def.h:271/273`, so this board takes that branch - while
its other branch goes through `cmdq_append_wpr_command()`, whose GPR-mutex/`MOVE` detour 0091 declined), and
RDMA/WDMA want the 13-entry session/lifecycle layer that is the v3 task engine. (b) Landing either is a
choice about the adapter's contract, so it is recorded as a decision to be made, not a dependency to be
satisfied quietly, and the port's maturity statement is unchanged: gate `l2_disp_record_publish50` shows
the switch OFF image byte-for-byte in its recorded sizes (payload still 493,517 B, `mt6768.dtb`
`34a7e6b536a3`) and the switch ON link still failing on 57 names. 57 to go before the display path links;
the panel handover beyond that is still a device question.

### 11.19 - Round 0093: the queue stops being a list of files, and the last free slice is taken

0092 ended with the queue priced and one candidate left that subtracts open names: the colour trio, blocked
by exactly one record op. This round took that slice and, in the same pass, priced everything else, which
turned out to be the more durable result.

The landing is five files. `common/color20/ddp_color.c` (4,099 ln), `common/corr10/ddp_dither.c` (409) and
`common/corr10/ddp_gamma.c` (1,574) go into `video/mt6768/dispsys/` verbatim behind three
`obj-$(CONFIG_MTK_DISP_BRINGUP)` lines (16 gated objects to 19), with no header landed - the
`ddp_{color,dither,gamma}.h` they include are in `video/include/` since 0085 and the vendor's `color20/`
and `corr10/` hold no same-basename header, which is the kind of thing worth measuring rather than assuming
because 0092's `ddp_mmp.h` did have to come along. The fifth file is the port's own: one function appended
to `drivers/soc/mediatek/mtk-cmdq-disp-record.c` (440 to 491 ln), `cmdqRecReadToDataRegister()`, which
resolves the address against the `gce` subsys table and calls mainline's `cmdq_pkt_read_s()`, and returns
`-EOPNOTSUPP` behind a `pr_err_once()` at or above `CMDQ_DATA_REG_JPEG_DST`.

That delegation is the whole design question and it was written up before landing
(`report/l2-record-adapter-read-to-data-register.md`), because the alternative - growing the adapter into a
GPR/wpr engine so the refused branch works too - is the same architectural step 0082 reverted and 0091
declined. The evidence for "delegation is enough" is that the vendor's live branch on this board is one
instruction and mainline's `cmdq_pkt_read_s()` fills the same four fields of the same 64-bit word:
`CMDQ_CODE_READ_S` into `arg_a[31:24]`, `reg + CMDQ_GPR_V3_OFFSET` into `arg_a[15:0]`, the 5-bit subsys
index into `arg_a[20:16]`, the destination tag into `arg_a[23]`, and `hw_addr & 0xffff` into
`arg_b[31:16]`. `tests/mtk_disp_record_host_check.c` now says so with numbers: 12 `read_s` words compared
against the vendor's model for every address this tree can produce, 9 refusal cases for the addresses no
`gce` row covers, 4 source-shape cases pinning that the definition delegates rather than hand-builds a word
and that only it adds `CMDQ_GPR_V3_OFFSET`. 85 cases, 0 mismatches (was 55).

Gate `l2_disp_record_publish51` (`slice0093-gate.sh`, `slice0093-gate-20260906T113559Z.log`, 69 s) measured the result: **57 -> 49 distinct
open names** with the switch ON (160 -> 140 reference lines), 8 closed, 0 opened, each closed name
`open:0` in the link and `defined:1` tree-wide and `in-trio:1`; objects 272,968 / 104,728 / 139,560 B
rebuilt from scratch; 0 `error:` lines in the ON build and 0 diagnostics naming the landed files, with the
29 single-object warnings all attributable to the landed v3 headers and `mtk-cmdq-mailbox.h:91`; 32 new
global symbols with 0 collisions; switch OFF unchanged (`vmlinux` 168,340,520 B, payload 493,517 B,
`mt6768.dtb` `34a7e6b536a3`, none of the 11 probed symbols in that `vmlinux`). Published as patch 0093 of 93
by `bin/publish.py`, which re-verified both directions: 0001-0093 reproduces
`899e689602bca34b67cedf293bb7df337f5bd609` and 0001-0092 still reproduces
`b5d70973e7f154d47f556bd7abac4aeca4d4176c`.

Two rig repairs came out of the same two gate runs, and both matter more than the slice. `nm` cannot read
an object from a pipe (`cat x.o | nm --defined-only -g` -> 0 symbols, `nm x.o` -> 4), which had silently
emptied every census line in every gate and probe script that used it - including
`probe-slice.sh`'s "globals defined by the new objects", a column that had reported 0 for every candidate
ever priced; and two set comparisons fired on correct states because they compared sorted output with prose
order or grepped a subject line for a filename the subject does not contain. All three are fixed in
`tools/portwork/`, and the honest framing is in `report/l2-slice-0093-before-after.md`: the first run of
this gate printed `defined:0` for the very symbol the patch adds, and a reader who trusted that line would
have rejected a correct slice.

The pricing half of the round is `report/logs/sweep-0093.log`, and its headline is negative: ten of the
eleven unlanded candidate files never reach a link at all. `ddp_dsi.c` and `ddp_pwm.c` stop at
`disp_dts_gpio.h`, `ddp_disp_bdg.c` at `ddp_reg_disp_bdg.h`, `ddp_aal.c` at `mtk_leds_drv.h`,
`videox/debug.c` at `mtk_disp_mgr.h`, and `disp_recovery.c`, `disp_lowpower.c`, `mtkfb.c`,
`primary_display.c` at the ION headers this port refuses by policy; `fbconfig_kdebug.c` fails on an implicit
declaration. The one file that does link, `disp_cust.c`, closes `set_lcm` and `read_lcm` - the only
candidate in the queue that touches the panel group - and opens seven panel-handover names, so it is +5 and
was rejected. So the next decision in this port is not "which `.c` file next" but "does a
device-tree-reading header belong in a port that has refused to invent device tree content", because that
is what stands between this tree and the DSI and PWM providers. 49 names remain, and the first-frame
estimate is unchanged at roughly 43k vendor lines.

The round also spent its remaining time on the recovery path, because the sandbox wiped the workspace
again mid-round: `restore.sh` replayed the 92 `.eml` files, `build0.sh` rebuilt the toolchain hooks, and
`slice0092-gate.sh` was re-run cold on that recovered tree (log `slice0092-gate-20260906T111233Z.log`, 876 s) and reproduced every claim of
0092's published gate - 57 names, CLOSED 5, OPENED 0, object 85,592 B, 6 new globals, 0 collisions, both
harnesses, the DTB sha and the 493,517 B payload - with the only differences being the `git describe`
width in the two gzipped sizes. That is gate `l2_disp_record_reverify51`, and it is recorded as a gate
because "the recovery works" is otherwise the kind of sentence a port carries untested until the day it
needs it. Every log this round depends on is now mirrored into `upstream-port/report/logs/`, and both the
pricing rig and the durable driver (`run-0093.sh`, resumable at each step) live in `tools/portwork/`.
