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
| panel identity | **not yet resolved** - deliberately left blank. `arch/arm64/boot/dts/oplus6768_20761/cust.dtsi` contains no `lcm`/`panel` string, and `drivers/misc/mediatek/lcm/` holds hundreds of candidate dirs (`hx83102d_txd_jelly_hdp_dsi_vdo_lcm`, `ft8201_wxga_vdo_incell_boe`, `hx83112b_fhdp_dsi_cmd_*`, ...). First task of the next round is to find the node `MTK_LCM_DEVICE_TREE_SUPPORT_PASCAL_E` actually reads (`grep -rn "of_getprop.*lcm\|lcm-name\|mediatek,lcm" drivers/video/mediatek drivers/misc/mediatek/lcm`, then match the value against the `compatible`/dir names) and to confirm the panel from the *device's* own `mtkfb`/`disp_lcm` DT output if a board is ever reachable. No panel name is asserted here. | measured negative: greps above |

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
| LCM/panel | `drivers/misc/mediatek/lcm/*` | per-panel dir, TBD | needed once the panel is identified; DT-based selection means the panel dir's `Kconfig`/`Makefile` is chosen by `MTK_LCM_DEVICE_TREE_SUPPORT*`, so the port must carry both the DT lookup and one panel driver |
| tracing/debug | `display_recorder.c` 1,657, `ddp_dump.c` 1,643, `ddp_debug.c` 964 | 4,264 | deferred with the port-local `ddp_log.h` (0081, `KNOWN-ISSUES.md` 12.6) - re-add only when a device actually needs the dprec mirror |
| DPM / PPBM / MML | `drivers/misc/mediatek/dpm*`, `ppbm` | TBD | MT6768's `even_defconfig` does not enable DPM for this path (`# CONFIG_MTK_CMDQ_TAB is not set`); verify per-file before assuming |

Already in the tree and to be preserved, not re-touched: SMI substrate (0078/0079), M4U v2.0 (0080),
display M4U client glue (0081). The chain is built bottom-up so each layer's binding can be verified
before the next one is added.

## 3. Layer order and the gate for each (nothing ships without its gate)

1. **L0 census/panel identification** (this document + the open item in section 1). Gate: every
   layer's file list derived from `#include` edges, no guess.
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
5. **L4 LCM + one panel driver** + `MTK_LCM_DEVICE_TREE_SUPPORT` lookup. Gate: DT child for the
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
