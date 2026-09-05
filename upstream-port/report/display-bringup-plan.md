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
That failure is L1 work item zero - it must be a green object before either option (a) or (b) is
chosen, because both depend on how mainline's header compiles under this gcc.

L2 (the 21 built `dispsys` objects, 32,454 .c + 2,687 .h) stays gated exactly as R9 requires: L1's
output is a non-empty list.

