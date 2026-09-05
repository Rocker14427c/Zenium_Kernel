# Panel path analysis: init sequences, gate IC, the LK name handover, minimum path

Evidence-only round (no code ported, nothing built - the 5.15 environment is still absent, see
`display-bringup-plan.md` section 5). Every claim below is grep/wc/regex output from the 4.19 vendor
tree in this repository, with `file:line`. This closes the four open items listed in
`panel-identification.md` section 6 and adds the minimum-path sizing the plan needs.

## 1. Init sequences of the three applicable panels

Each panel drives its DSI init through one table named `init_setting_vdo` (type
`LCM_setting_table_V3[]`) pushed by `push_table_cust()`, plus explicit `MDELAY()` calls around it.

| panel | `init_setting_vdo` rows | rows whose length field is hex | first 5 opcodes | last 5 opcodes | tables in file | row delay fields |
|---|---|---|---|---|---|---|
| `ilt9882n_truly_even_hdp_dsi_vdo_lcm` | **225** | 17 | 0xFF 0x98 0x00 0x01 0x02 | 0x53 0x5E 0x35 0x11 0x29 | 8 | none |
| `nt36525b_hlt_even_boe_hdp_dsi_vdo_lcm` | **109** | 129 | 0xFF 0xFB 0xB0 0x00 0xB1 | 0x53 0x55 0x35 0x29 0x11 | 12 | none |
| `ilt7807s_hlt_even_hdp_dsi_vdo_lcm` | **319** | 20 | 0xFF 0x78 0x11 0xFF 0x78 | 0x51 0x53 0x55 0x29 0x35 | 8 | none |

- The tables are the bulk of each file (225/797, 109/704, 319/896 lines) and they differ in both
  length and *encoding*: the Novatek file writes its per-row parameter counts in hex (129 rows)
  while the two ILI files mostly write decimal - a strict `{cmd, N, {params}}` parse therefore
  reported 109 rows for one panel and **0** for another until the pattern accepted `0xNN`
  (measured in this session; recorded so future tooling does not repeat it).
- Every table opens with a page-select write `0xFF` plus the vendor's page bytes:
  `0x98,0x82,0x01` for the ILI9882x (Truly module), `0x78,0x07,0x00` for the ILI7807S, while the
  NT36525B file starts `0xFF 0xFB 0xB0 0x00 0xB1` (Novatek block style). This is the hardware-family
  identification the previous round said needed a device: it is *inside the driver*, and it agrees
  with the directory names instead of being inferred from them.
- All three end with the standard exit set - `0x11` (sleep out) and `0x29` (display on) - and carry
  `0x35` (TE on), `0x51` (WDB brightness), `0x53`/`0x55` (CABC) in different orders: truly ends
  `0x53 0x5E 0x35 0x11 0x29`, ilt7807s `0x51 0x53 0x55 0x29 0x35`, nt36525b
  `0x53 0x55 0x35 0x29 0x11`. Ordering of the TE-on step matters for the port because TE is also a
  `DTS_GPIO_STATE_TE_MODE_*` decision (section 3).
- **No row carries a delay field** (0 in all three); sleeps are `MDELAY(1) MDELAY(3) MDELAY(2)
  MDELAY(2) MDELAY(2) MDELAY(3) MDELAY(5) MDELAY(2)`-style calls interleaved around the pushes
  inside `lcm_init()`. A port that pushes the whole table as one packet silently drops the panel's
  reset/sleep-out timing.
- Backlight: the `bl_level` table is a single row `0x51` with parameters `(0x00, 0xFF)` in all
  three, scaled in `oplus_private_set_backlight()` and issued via `lcm_setbacklight_cmdq()` - DCS
  over CMDQ, not PWM (`ddp_pwm.c` exists on this chip but these panels do not use it). CABC tables
  are present in all three (e.g. nt36525b `lcm_cabc_enter_setting` = `0x53{0x2c},0x55{0x01}`,
  `lcm_dimming_off_setting` = `0x53{0x24}`), exported as `.set_cabc_mode_cmdq`/`.get_cabc_status`,
  and switched by the mtkfb node's `oplus_display_cabc_cmdq_support` DT bool (section 3).
- No panel file has a `.check_id`/`.compare_id` member (measured across all three `LCM_DRIVER`
  structs), which is the second confirmation that selection is by name, not by ID read in-kernel.

## 2. Gate/bias IC: the panels do reach I2C, just not directly

This corrects `panel-identification.md` section 6 item (ii), which asked whether the panels use
`lcm_i2c_*`: they do not call it, and that question was the wrong one.

- All three call `display_bias_setting(0x14)` in the power-on sequence (`ilt9882n...c:603`,
  `nt36525b...c:467`, `ilt7807s...c:714`); direct `lcm_i2c_read/write` callsites: 0 in each file.
- `display_bias_setting()` is defined in the LCM I2C layer, `drivers/misc/mediatek/lcm/lcm_i2c.c:223`.
  It selects a gate IC by `gateICfalg`: for SM5109 it writes reg `0x03 = 0x43` (bit0/bit1 active
  discharge OUTP/OUTN, bit6 drive capability) and then `0x00`/`0x01 = voltage_value_offset`,
  re-reading the first write to compare against 2; for OCP2130 it writes `0x00`/`0x01` only and
  returns -2 on failure; anything else returns -3 ("no gate ic device matched"). Selection is
  written as `if(!(gateICfalg ^ LCD_GATE_IC_SM5109_MUSK))` - an equality test spelled as
  XOR-negate, with the masks `0x03` (SM5109) and `0x33` (OCP2130) at `lcm_i2c.c:219-220`. A
  "readable" rewrite into `==` changes nothing semantically but any deviation in the mask values
  would silently disable bias programming, so the pair is part of the port contract.
- The identity is a **kernel command line** input: `static int __init parse_lcdBias(char *arg)` at
  `lcm_i2c.c:261`, registered by `early_param("lcdgateic", parse_lcdBias)` at `lcm_i2c.c:279`. It
  `strcmp`s the argument against `"SM5109"` / `"OCP2130"`, sets `gateICfalg`, and rewrites the
  placeholder OF match: `strcpy(_lcm_i2c_of_match->compatible, "LCD_BIAS_SM5109")` - where
  `_lcm_i2c_of_match` is `{ .compatible = "default" }` in the PASCAL_E arm
  (`lcm_i2c.c:100-104`), bus 0 (`:70-77`, bus 3 under `MTK_CUSTOM_LCM_DIFFERENT`), client address
  `0x3E`, name `"GATE_SM5109_OCP2130"`. So the chain is
  `lcdgateic=<tok>` -> mask + compatible -> i2c client lookup -> two register writes.
- Port consequence: this needs a live I2C adapter plus a bound bias driver whose compatible matches
  what `parse_lcdBias` installs. The adapter is exactly what `KNOWN-ISSUES.md` 8.4 says this board's
  DT does not describe, so the gate IC sits on the **panel** critical path (not the touch stage:
  this board's touch is SPI, `cust_mt6768_touch_720x1600.dtsi`). Mitigating fact, also measured: the
  callers treat failure as non-fatal (they log and continue), so bias can be sequenced after
  first-frame work without hiding a hard error - and it must be recorded as unfinished, not skipped.

## 3. `dts_gpio_state`: who writes it, what it gates, what is still open

- Defined in the mtkfb instance for this chip: `video/mt6768/videox/mtkfb.c:97`
  (`long dts_gpio_state;`), externed for dispsys at `dispsys/ddp_dsi.h:167`.
- Written exactly once, in mtkfb's probe, just before the framebuffer is allocated:
  `mtkfb.c:2629  dts_gpio_state = disp_dts_gpio_init_repo(pdev);` then
  `:2630 if (dts_gpio_state != 0) DISPMSG("retrieve GPIO DTS failed.");`. The identical pair appears
  per chip (`mt6765:2487`, `mt6779:2612`, `mt6785:2431`, `mt6833:2579`, `mt6853:2558`), so it is an
  MTK convention rather than an OPLUS patch, and the polarity is inverted relative to the naive
  reading: **non-zero means "no repo", which is the fallback branch**.
- Contract and vocabulary live in `video/mt6768/videox/disp_dts_gpio.h`: "This module helps you to
  set GPIO pin according to linux device tree (DTS). To use this module, you MUST init this module
  once before any operation." Its `enum DTS_GPIO_STATE` = `TE_MODE_GPIO` (mode_te_gpio),
  `TE_MODE_TE`, `TE1_MODE_TE`, `LCM_RST_OUT0`, `LCM_RST_OUT1`, `LCM1_RST_OUT0`, `LCM1_RST_OUT1`,
  then under `#ifdef OPLUS_BUG_STABILITY` the four `LCD_BIAS_ENP0/ENP1/ENN0/ENN1` (plus MT6382
  entries under `CONFIG_MTK_MT6382_BDG`).
- Consumers: `dispsys/ddp_dsi.c:4959-4969` `lcm_set_reset_pin()` - when `dts_gpio_state != 0` it
  writes `DISP_REG_CONFIG_MMSYS_LCM_RST_B`, otherwise it calls
  `disp_dts_gpio_select_state(DTS_GPIO_STATE_LCM_RST_OUT1/OUT0)`; `ddp_dsi.c:4971` `lcm_bias_vsp()`
  (the VSP/VSN lines the panels reach through `lcm_util.set_gpio_lcd_enp_bias/enn_bias`);
  `video/common/pwm10/ddp_pwm.c:402,412` for the PWM-transparent/GPIO-low states. So the LCM reset
  line is either an MMSYS config bit or a DT-described GPIO selected through that state table - never
  a GPIO number inside the panel driver.
- Same probe block also reads the only panel-adjacent DT knob on that node:
  `oplus_display_cabc_cmdq_support = of_property_read_bool(pdev->dev.of_node,
  "oplus_display_cabc_cmdq_support")`, logged as "read bool oplus_display_cabc_cmdq_support failed."
  when absent - i.e. CABC-over-CMDQ is an mtkfb-node option on this board, not an LCM property.
- **Still open, deliberately not guessed:** the definition of `disp_dts_gpio_init_repo()` (and of
  `disp_dts_gpio_select_state()`). The greps run here found call sites plus the header, and the
  `disp_dts_gpio.h` file that exists per chip carries the enum/prototypes; settling this needs
  `grep -rn 'disp_dts_gpio_init_repo' --include='*.c' drivers/ | grep -v '='` (and then whether the
  table comes from the mtkfb node, `/chosen`, or an LK-provided DTS blob), which decides whether the
  5.15 port drives the MMSYS `LCM_RST_B` bit (no DT change) or must add GPIO state properties (a
  binding change - which needs a device to check, per the standing rule).

## 4. How the stock `mtkfb_lcm_name` handover is populated

Not a config value, not a board-DT constant: it is read from **`/chosen` at runtime**, from
properties LK creates for that boot. Chain, measured in `video/mt6768/videox/mtkfb.c`:

1. `parse_tag_videolfb()`: `chosen_node = of_find_node_by_path("/chosen")`, falling back to
   `/chosen@0`; returns early if `is_videofb_parse_done` (single-shot); tries
   `__parse_tag_videolfb(chosen_node)` then `__parse_tag_videolfb_extra(chosen_node)`; with no
   chosen node it logs `"[DT][videolfb] of_chosen not found"` and returns -1.
2. `__parse_tag_videolfb()`: `atag,videolfb-vramSize` and `atag,videolfb-fb_base_l` each via
   `of_get_property` + `of_read_number`, and a missing property is a hard `-1`; then
   `prop = of_get_property(node, "atag,videolfb-lcmname", (int *)&size)`, `if (size >=
   sizeof(mtkfb_lcm_name))` -> `DISPCHECK("%s: error to get lcmname size=%ld\n")` and `-1`, else
   `memset(mtkfb_lcm_name, 0, sizeof(...)); strncpy(mtkfb_lcm_name, prop, sizeof(...));
   mtkfb_lcm_name[size] = '\0';`. The buffer is `mtkfb.c:182` (`char mtkfb_lcm_name[256] = { 0 }`).
   `islcmconnected`, `is_lcm_inited` and `fps` are read from the same tag family and logged at the
   `found:` label.
3. Consumption: `primary_display_init(mtkfb_find_lcm_driver(), lcd_fps, is_lcm_inited)` in the same
   probe, where `mtkfb_find_lcm_driver()` resolves the string against the compiled
   `lcm_driver_list[]` by matching each `struct LCM_DRIVER .name` - e.g.
   `ilt9882n_truly_even_hdp_dsi_vdo_lcm.c:777-778`
   `.name = "ilt9882n_truly_even_hdp_dsi_vdo_lcm"` - and `disp_lcm.c`'s DT-based `LCM_DTS` parser is
   not compiled on this board at all (`#if defined(MTK_LCM_DEVICE_TREE_SUPPORT)`, which
   `even_defconfig:1715` leaves unset).

Consequences, including the answer to the standing question about DT-based selection:

- The authoritative choice is made by **LK per unit** (LK probes/identifies, then writes the name
  into `/chosen`); the kernel holds a registry of six candidates and picks by string. The DT is the
  carrier, not the decider.
- `atag,videolfb-*` properties are absent from the DTB this project packages (measured last round:
  0 such properties in `mt6768.dtb`) - expected, since LK adds them at boot. A port must therefore
  read them at runtime, handle absence the way stock does (return -1, fall through), and choose its
  fallback in writing.
- **Do not convert panel selection to a DT binding.** The handover evidence shows a per-boot,
  per-unit value; freezing one of the three modules into the ported DT would contradict stock's
  mechanism and break the other two. The port keeps the same shape: name registry + `/chosen`
  reader + explicit absent-property behaviour.

## 5. Minimum common LCM + CMDQ + DSI + panel path (sized)

Sized from the vendor Makefiles and call-site censuses, not from directory sizes.

| layer | what is actually compiled/called on this board | LOC | notes |
|---|---|---|---|
| L1 CMDQ client | 14 entry points, 48 callsites in `video/mt6768/dispsys/*.c`: `cmdq_pkt_write` 15, `cmdq_dev_get_event` 7, `cmdq_pkt_clear_event` 4, `cmdq_pkt_wait_no_clear` 3, `cmdq_pkt_sleep_by_poll` 3, `cmdq_pkt_destroy` 3, `cmdq_pkt_poll` 2, `cmdq_pkt_flush` 2, `cmdq_pkt_create` 2, `cmdq_register_device` 1, `cmdq_pkt_sleep` 1, `cmdq_pkt_flush_threaded` 1, `cmdq_pkt_flush_async` 1, `cmdq_mbox_create` 1 | TBD (delta) | the vendor declares these at the *mainline* header path - `include/linux/soc/mediatek/mtk-cmdq.h` (`:279 cmdq_pkt_write`, `:318 cmdq_pkt_poll`, `:383 cmdq_pkt_flush_async`, `:388 cmdq_pkt_flush_threaded`) - and `cmdq/v3/` has no `cmdq_core.c` at all, while the full engine is 29,317 lines (`v2/cmdq_core.c` 10,185, `v3/cmdq_helper_ext.c` 5,610, `v3/cmdq_record.c` 4,140, `v3/cmdq_mdp_common.c` 3,988, `v3/cmdq_test.c` 8,189, `bridge/cmdq-bdg-mailbox.c` 1,120, `mailbox/*` ~4,474). Strongly suggests 5.15's mainline mailbox cmdq already provides create/destroy/write/flush* and only the poll/event helpers are BSP-side. **Unverified here** (no 5.15 tree); it is L1's first gate, not an assumption |
| L2 dispsys core | 21 objects, `video/mt6768/dispsys/Makefile:79-100`: `ddp_ovl ddp_rdma_ex ddp_wdma_ex ddp_dsi ddp_clkmgr ddp_rsz ddp_drv ddp_path ddp_mutex ddp_m4u ddp_debug ddp_dump ddp_manager ddp_irq ddp_info ddp_color_format ddp_pwm_mux ddp_disp_bdg`(MT6768-only)`...` | **32,454 .c + 2,687 .h** | correction to this plan's earlier model: MT6768 has no separate `ddp_aal.c`/`ddp_gamma.c`/`ddp_ccorr.c`/`ddp_merge.c`/`ddp_dither.c` to leave out (dir total .c is 34,419, so the built set is ~94% of it), and `ddp_dpi.o` is commented out at `Makefile:83`. `ddp_m4u.o` is one of the 21 and already landed (0081), so L2 continues rather than restarts |
| L3 fb + panel manager | `mtkfb.c` 3,134 + `primary_display.c` 10,857 + `disp_lcm.c` 2,143 (+ `disp_helper.c` 453, ported) | 16,134 | two shapes, decision deferred to the L2 link gate: (a) stock-shaped, so the `/chosen` handover, `mtkfb_find_lcm_driver()`, ESD worker and `ddp_pm` behave as measured; (b) thin - a small client that parses `atag,videolfb-*`, resolves the name, and calls `ddp_dsi`/`ddp_ovl`/`lcm_*` directly (hundreds of lines). (b) forfeits logo-handover fidelity; (a) drags `disp_dts_gpio`, `ddp_pm`, the dprec log layer and cmdq-using ESD |
| L4 LCM layer | common `mt65xx_lcm_list.c` 1,654 + `lcm_common.c` 1,477 + `lcm_gpio.c` 326 + `lcm_i2c.c` 382 + `lcm_pmic.c` 149 + `lcm_util.c` 257 = 4,245; headers `lcm/inc/*.h` 1,401; panels 797 + 704 + 896 = **2,395** | 8,041 | `lcm_i2c.c` is required for `display_bias_setting()` (section 2); the `-D<PANEL>` macro plumbing (`lcm/Makefile:41-44`) must be reproduced or `lcm_driver_list[]` compiles to zero entries; the FHD trio (961+1,099+1,338) stays out because this board's DT/touch config does not name those controllers |
| L5 handover + board glue | `atag,videolfb-{vramSize,fb_base_l,lcmname}` reader (the `__parse_tag_videolfb` shape, ~120 lines), `oplus_display_cabc_cmdq_support` bool, gate IC over I2C (blocked on 8.4), `dts_gpio_state` owner decision | ~0.2k | plus the `lcdgateic=` token: stock expects it on the kernel command line, and the port has to state what happens without it (bias returns -3, panels continue) |

Minimum to "a panel is initialised and shows something", with L3 taken as (b): roughly
**43k lines** of vendor source to adjudicate - 35k (L2) + 8k (L4) + the L1 delta + ~0.2k of glue -
containing 653 init rows across three panels. That is the honest size of "minimum complete" for
MT6768; a smaller number would mean inventing an interface rather than porting one.

## 6. Still unmeasured, with the command that settles each

1. `disp_dts_gpio_init_repo()` / `disp_dts_gpio_select_state()` definitions and their data source:
   `grep -rn 'disp_dts_gpio_init_repo' --include='*.c' drivers/ | grep -v '='`.
2. Whether more of `dispsys/Makefile` gates objects by CONFIG beyond `MTK_FB`/`MACH_MT6768`
   (`sed -n '100,170p' drivers/misc/mediatek/video/mt6768/dispsys/Makefile`), which decides whether
   `ddp_debug.o`/`ddp_dump.o` can be trimmed.
3. The 5.15 cmdq surface (L1 row).
4. Exact `MDELAY()` placement per panel around the pushes
   (`awk '/static void lcm_init/,/^}/' <panel>.c`), needed to reproduce init timing rather than
   approximate it.

Settled this round and removed from the list: the init-table row counts and encodings (section 1),
whether the panels use the LCM I2C path (section 2 - yes, through `display_bias_setting()`, fed by
`early_param("lcdgateic", ...)`), and what writes `dts_gpio_state` (section 3).

Nothing here was compiled, linked, or checked against a built DTB. This document constrains what a
port must contain; it makes no claim about 5.15 behaviour or about any device.
