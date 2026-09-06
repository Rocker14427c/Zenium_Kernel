# Design note - growing the record adapter by exactly one entry point, and why that is the smallest option

Written after 0092 (tree `b5d70973e7f1…`, 57 open names) and before 0093, on the user's instruction to
pick the smallest evidence-backed architecture rather than wait for approval on each candidate. The
evidence is three greps, one probe, and the bit layout of two headers; every number below is reproducible
with the tools in `upstream-port/tools/portwork/`.

## 1. What the queue actually costs

`probe-slice.sh` prices a candidate by applying it to the tree of record, linking the whole tree with the
display switch ON and `-k`, and diffing ld's distinct open-name set against
`report/l2-open-names-at-0092.txt` (57 names). Net ≤ 0 means the patch series gets strictly closer to
linking; net > 0 means it buys capability at the cost of a wider gap, which this port has refused since
0089.

| candidate | closed | opened | net |
|---|---|---|---|
| `common/color20/ddp_color.c` + `common/corr10/{ddp_dither.c,ddp_gamma.c}` | 8 | 1 | **-8 +1 = -7** |
| `ddp_mmp.c` (landed as 0092) | 5 | 0 | -5 |
| `ddp_ovl.c` (+ `dramc/mt6768/mtk_dramc.h`) | 6 | 10 | +4 |
| `ddp_rdma_ex.c` + `ddp_wdma_ex.c` + `ddp_matrix_para.h` | 10 | 21 | +11 |

The rest of the queue was then priced on this tree by `tools/portwork/sweep-0093.sh`
(`portwork/logs/sweep-0093.log`, mirrored to `report/logs/sweep-0093.log`), one candidate at a time, each
row an apply-link-restore against the same 57-name baseline. The result is the finding of the round, and
it is not a set of prices: **ten of the eleven candidates never reach a link at all.**

| candidate | result | why |
|---|---|---|
| `ddp_dsi.c` | unpriced, `error:1` | `ddp_dsi.c:35: fatal error: disp_dts_gpio.h` |
| `ddp_pwm.c` | unpriced, `error:1` | same header, `ddp_pwm.c:31` |
| `ddp_disp_bdg.c` | unpriced, `error:1` | `ddp_reg_disp_bdg.h` at `:12` |
| `ddp_aal.c` | unpriced, `error:1` | `mtk_leds_drv.h` at `:23` |
| `disp_recovery.c` | unpriced, `error:1` | `ion_drv.h` at `:20` - ION, refused by policy |
| `disp_lowpower.c` | unpriced, `error:1` | `ion_drv.h` at `:21` |
| `mtkfb.c` | unpriced, `error:1` | `ion_drv.h` at `:31` |
| `primary_display.c` | unpriced, `error:1` | `mtk_ion.h` at `:24` |
| `debug.c` | unpriced, `error:1` | `mtk_disp_mgr.h` at `:34` |
| `fbconfig_kdebug.c` | unpriced, `error:2` | `:831: error: implicit declaration of function 'cmdqRecWrite'`-class, i.e. a header whose prototype set the tree carries is not reachable from it |
| `disp_cust.c` | **+5**, obj 57,056 B, 0 errors | closes 2 (`set_lcm`, `read_lcm` - the only candidate that touches the panel group at all), opens 7: `DSI_dcs_{read,set}_lcm_reg_v4`, `_is_power_on_status`, `_primary_path_switch_dst_{lock,unlock}`, `primary_display_manual_{lock,unlock}` |

Every candidate's `distinct open names after: 0` line for the ten blocked rows is the rig's own signal
that the link never ran, so their deltas are void, not wins - the sweep printed that warning rather than
a number. The reading: the queue is no longer a list of `.c` files to price. Eight of the eleven are held
up by *five* headers (`disp_dts_gpio.h`, `ddp_reg_disp_bdg.h`, `mtk_leds_drv.h`, `mtk_disp_mgr.h`, and the
`ion_*.h` family, the last of which is a policy decision, not a missing file), so the next round's real
decision is whether the DT-parsing headers belong in this port at all - `disp_dts_gpio.h` in particular
is the device-tree pin-configuration reader, which is exactly the surface the port has refused to invent.

The colour trio is the only remaining candidate that both compiles untouched and pays for itself. It is
also a real dependency rather than a convenience: `ddp_driver_color`, `ddp_driver_dither`,
`ddp_driver_gamma`, `ddp_driver_ccorr` are the driver structs `ddp_path.c` (0090) reaches through, and
`disp_color_ioctl` is the ioctl `mtkfb.c` will want.

## 2. The one requirement, and its exact size

Requirement census over the three files (not inferred from a header, read out of the sources):

```
color20/ddp_color.c  (4,099 ln):  3x cmdqRecReadToDataRegister, 2x cmdqRecWrite, 8x struct cmdqRecStruct *,
                                   0x CMDQ_REG(
corr10/ddp_dither.c  (  409 ln):  0 record calls, only #include "cmdq_record.h"
corr10/ddp_gamma.c   (1,574 ln):  0 record calls, 4x struct cmdqRecStruct *, only #include "cmdq_record.h"
```

Two things follow from the `0x CMDQ_REG(` line. The first is that this candidate does **not** need the
register-typed-operand rule that 0091 declined to carry: nothing in the trio writes a value that came from
a GPR, so the `-EOPNOTSUPP` in `cmdqRecWrite()` stays as it is. The second is that the three
`cmdqRecReadToDataRegister()` calls are the entire gap - one entry point, not a layer.

They sit in the HIST readback of `ddp_color_get_hist...`, guarded at the callsite by
`if ((module == DISP_MODULE_COLOR0) && (state == CMDQ_AFTER_STREAM_EOF))` (`ddp_color.c:4022`), and on
this board the `#elif defined(CONFIG_MACH_MT6768)` branch is the live one:

```c
ret = cmdqRecReadToDataRegister(cmdq_trigger_handle,
        ddp_get_module_pa(DISP_MODULE_COLOR0) +
        (DISP_COLOR_TWO_D_W1_RESULT - DISPSYS_COLOR0_BASE),
        CMDQ_DATA_REG_PQ_COLOR);                                    /* ddp_color.c:4038-4041 */
```

`CMDQ_DATA_REG_PQ_COLOR = 0x04` (`cmdq/v3/cmdq_def.h:273`) is below `CMDQ_DATA_REG_JPEG_DST = 0x11`
(`:271`), which is the branch test in the vendor:

```c
/* cmdq/v3/cmdq_record.c:1576, cmdq_op_read_to_data_register() */
if (dst_data_reg < CMDQ_DATA_REG_JPEG_DST) {
        op_code = CMDQ_CODE_READ_S;              arg_a_type = 1;   arg_b_type = 0;
        arg_a_i = dst_data_reg + CMDQ_GPR_V3_OFFSET /* 0x20 */;    arg_b_i = hw_addr;
} else {
        op_code = CMDQ_CODE_READ;  /* 0x01 */    ...
}
return cmdq_append_command(handle, op_code, arg_a_i, arg_b_i, arg_a_type, arg_b_type);
```

So this board only ever takes the `CMDQ_CODE_READ_S` path, and the `else` path goes through
`cmdq_append_wpr_command()`, whose unresolvable-address case inserts a `CMDQ_CODE_WFE` on
`CMDQ_SYNC_TOKEN_GPR_SET_4` plus a `CMDQ_CODE_MOVE` into `CMDQ_DATA_REG_DEBUG` - the same GPR detour 0091
documented as declined. The port therefore implements the live branch and refuses the other one
loudly, which is the shape 0091 already established.

## 3. Why it can be a delegation, with the bits written out

`include/linux/soc/mediatek/mtk-cmdq-mailbox.h` has no `struct cmdq_instruction`: in 5.15 it is private to
`drivers/soc/mediatek/mtk-cmdq-helper.c`, and so is `cmdq_pkt_append_command()`. That is the hard
constraint on every option below - the adapter cannot emit a hand-built instruction word without either
editing a mainline file (the mistake class 0082 reverted) or landing the vendor engine. What it *can* do
is call the public helpers in `include/linux/soc/mediatek/mtk-cmdq.h`, which is what 0091's three entry
points do. The public set relevant here is:

```c
int cmdq_pkt_read_s(struct cmdq_pkt *pkt, u16 high_addr_reg_idx, u16 addr_low, u16 reg_idx);
int cmdq_pkt_write_s(struct cmdq_pkt *pkt, u16 high_addr_reg_idx, u16 addr_low, u16 src_reg_idx);
int cmdq_pkt_write_s_mask(struct cmdq_pkt *pkt, u16 high_addr_reg_idx, u16 addr_low, u16 src_reg_idx, u32 mask);
```

Expanding mainline's private struct - `{{value|mask|{arg_c,src_reg}}, {offset|event|reg_dst}, {subsys|
sop:5,arg_c_t:1,src_t:1,dst_t:1}, op}` packed little-endian into 64 bits - gives `arg_a` =
`[15:0] offset|reg_dst | [20:16] sop | [21] arg_c_t | [22] src_t | [23] dst_t | [31:24] op` and
`arg_b` = `[15:0] arg_c | [31:16] src_reg`. Laid against the vendor's rules from
`cmdq_append_rw_s_command()` (v3/cmdq_record.c:941-951), the read-to-GPR case:

| field | vendor (read_s, dst `<` JPEG_DST) | mainline `cmdq_pkt_read_s(pkt, subsys, addr_low, reg_idx)` |
|---|---|---|
| `arg_a[15:0]` | `dst_data_reg + 0x20` (`CMDQ_GPR_V3_OFFSET`) | `reg_dst` = the 4th argument, verbatim |
| `arg_a[20:16]` | `subsys & 0x1f` (`subsys_bit` = 16 on mt6768) | `sop`, a 5-bit field |
| `arg_a[23:21]` | `arg_type = (arg_value_type<<2)\|(arg_addr_type<<1)` = `1<<2` ⇒ bit 23 | `dst_t = CMDQ_REG_TYPE` ⇒ bit 23 |
| `arg_a[31:24]` | `CMDQ_CODE_READ_S` = 0x80 | `inst.op = CMDQ_CODE_READ_S` = 0x80 |
| `arg_b[31:16]` | `(hw_addr & 0xffff)` | `src_reg = addr_low` |
| `arg_b[15:0]` | 0 | 0 (`arg_c` untouched) |

Every row is the same field, at the same bit position, with the same value - so the delegation is exact for
this board's one live shape, and the only transcription is that the port must add `CMDQ_GPR_V3_OFFSET`
itself where the vendor added it inside `cmdq_op_read_to_data_register()`. The subsys resolution is 0091's
already-proven `mtk_disp_rec_resolve_subsys()`, and the address must be the *physical* address the
callsite computes (`ddp_get_module_pa(...) + offset`), which is the rule 0091 pinned for
`cmdqRecWrite`: an address no `gce` row covers returns `-EINVAL` rather than going through
`CMDQ_CODE_LOGIC`/`CMDQ_SPR_FOR_TEMP`, because 5 of the 99 the vendor's `CMDQ_SPECIAL_SUBSYS_ADDR` uses do
not fit a 5-bit field.

Two candidate alternatives were considered and rejected on measurement, not preference:

- **Refuse `cmdqRecReadToDataRegister` with a stub** (return `-EOPNOTSUPP` unconditionally). It links, so
  it is tempting, and 0091's refusal of register-typed operands proves the port will use a refusal when it
  is honest. Here it would not be: the live branch is a four-instruction-word encoder whose every field is
  already available, so a stub would be a *silent capability loss in code that can be written*, and the
  HIST readback is exactly the kind of path a first frame will hit. The refusal stays where it belongs -
  the `else` branch, which this board does not reach and whose encoding needs the declined detour.
- **Grow the adapter into the `cmdq_task_*` session layer** (what RDMA/WDMA want: `cmdqRecCreate/Destroy/
  Reset/Flush/FlushAsync/Wait/Poll` + the five secure ops). Rejected twice over: those 13 vendor functions
  are 3-4 line trampolines into per-subsys session pools with a `gce_plat` lock and mailbox submission,
  and there is no public primitive to build their instruction words with either. That is a rewrite of the
  v3 record engine inside `drivers/soc/`, in a tree whose display code is still 49-57 names from linking -
  and the 0082 revert is the standing evidence for what happens when vendor GCE session state is
  reintroduced here.

## 4. The slice this leads to

1. `drivers/soc/mediatek/mtk-cmdq-disp-record.c`: one entry point, `cmdqRecReadToDataRegister()`, using
   the guards 0091 already has (`mtk_disp_rec_pkt()` for the handle/pkt/finalized checks,
   `mtk_disp_rec_resolve_subsys()` for the address), the `-EOPNOTSUPP` for the `>= JPEG_DST` branch, and a
   pr_err_once on the refusal so it cannot fail quietly. Its declaration goes into
   `include/linux/soc/mediatek/mtk-cmdq-disp-record.h` next to the other three.
2. `upstream-port/tests/mtk_disp_record_host_check.c`: extend the existing 55 cases with a read_s section -
   the same 7 addresses the write cases use, `CMDQ_DATA_REG_PQ_COLOR` and the neighbours on both sides of
   the `0x11` boundary, and for each case compare the word the vendor's rules produce against the word
   mainline's field layout produces, so the `+0x20`, the 5-bit `sop` and bit 23 are all pinned by
   comparison rather than by prose. The `>= 0x11` refusal is asserted to refuse, not silently skipped.
3. `ddp_color.c`, `ddp_dither.c`, `ddp_gamma.c` landed verbatim (4,099 + 409 + 1,574 lines) with three
   `obj-$(CONFIG_MTK_DISP_BRINGUP)` lines, no `-D` flags, no Kconfig symbol, no DT edit.

Predicted effect, from the probe: `ddp_color.o` 272,968 B, `ddp_dither.o` 104,728 B, `ddp_gamma.o`
139,560 B, 0 diagnostics attributed to any of the three; 8 names closed
(`ddp_driver_color`, `ddp_driver_dither`, `ddp_driver_gamma`, `ddp_driver_ccorr`, `corr_dbg_en`,
`disp_color_dbg_log_level`, `disp_color_ioctl`, `disp_ccorr_on_end_of_frame`); **0** opened, because
`cmdqRecReadToDataRegister` is defined by the same patch that lands the caller; 57 → **49** distinct open
names. The census check stays what it has been: each closed name `open:0` in the link and `defined:1`
tree-wide, 0 collisions against the rest of the tree, and 0092's 5 MMP names, 0090's 15 path names, 0091's
3 record names and 0089's 2 bias names all still closed.
