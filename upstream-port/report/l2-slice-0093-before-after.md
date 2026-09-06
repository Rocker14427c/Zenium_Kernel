# Slice 0093 - predicted before/after, written before the landing

Everything under "predicted" was measured by replaying the landing against the tree of record
(`bash /home/user/portwork/probe-slice.sh "ddp_color.c ddp_dither.c ddp_gamma.c"`, log
`portwork/logs/probe-ddp_color_c_ddp_dither_c_ddp_gamma_c.log`, on the 92-patch tip
`b5d70973e7f154d47f556bd7abac4aeca4d4176c`, dirty 0) and then restoring that tree. The one part the
probe could not measure is the adapter entry point, because at probe time it did not exist yet: the
probe therefore *opened* one name (`cmdqRecReadToDataRegister`) that this patch closes. That
difference - 8 closed and 1 opened there, 8 closed and 0 opened here - is the whole content of the
slice, so it is the thing the gate is written to confirm rather than assume.

## What the slice is

Five files, three of them vendor code copied verbatim into the port's `dispsys/` directory exactly as
0092 copied `ddp_mmp.c`:

| file | lines | sha256[:12] | destination |
|---|---|---|---|
| `video/common/color20/ddp_color.c` | 4,099 | `b81b1f10ff22` | `video/mt6768/dispsys/ddp_color.c` |
| `video/common/corr10/ddp_dither.c` | 409 | `e2f9ffffc06b` | `video/mt6768/dispsys/ddp_dither.c` |
| `video/common/corr10/ddp_gamma.c` | 1,574 | `d1efbeec6173` | `video/mt6768/dispsys/ddp_gamma.c` |

plus three `obj-$(CONFIG_MTK_DISP_BRINGUP)` lines in the port's `dispsys/Makefile` (16 gated lines to
19), plus one function appended to `drivers/soc/mediatek/mtk-cmdq-disp-record.c` (440 to 491 lines).

No header lands: the three files include `ddp_color.h`, `ddp_dither.h` and `ddp_gamma.h`, and the port
already carries all three in `video/include/` from 0085 (measured: `drivers/misc/mediatek/video/`
under the port tree holds each; the vendor has no same-basename header next to the `.c`). No Device
Tree change, no new Kconfig symbol, no mailbox ABI change, nothing under `include/`.

Outside the series, in this repo: `tests/mtk_disp_record_host_check.c` gains a
read-to-data-register section (design and evidence in
`report/l2-record-adapter-read-to-data-register.md`).

## Why these three, and not the bigger providers

`report/l2-open-names-at-0092.txt` has 57 distinct undefined names with the display switch ON. The
screen of every vendor display `.c` the port has not landed (`tools/portwork/screen-0093.py`, 35
files) says 18 of them could close at least one name and 17 could close none. Of the 18, this trio is
the only candidate whose *entire* unmet dependency is a single record entry point - and that entry
point is one delegation to a mainline helper, which is why the round is worth spending on it rather
than on the DSI/OVL paths, which need panel handover machinery the port does not have. Measured prices
against the same 57-name baseline, whole-tree ON link, same method:

| candidate | net | note |
|---|---|---|
| colour trio + the one entry point | **-8** | this slice |
| colour trio alone (probe, adapter not yet extended) | -7 | closes 8, opens `cmdqRecReadToDataRegister` |
| `ddp_ovl.c` | +4 | needs `mtk_dramc.h` and opens `cmdqRecPoll`/`SetSecure`/`WriteSecure`/`BackupUpdateSlot` |
| `disp_cust.c` | **+5** | the only one of the eleven that reached a link: obj 57,056 B, 0 errors, closes `set_lcm`/`read_lcm`, opens 7 |
| `ddp_dsi.c`, `ddp_pwm.c`, `ddp_disp_bdg.c`, `ddp_aal.c`, `debug.c`, `disp_recovery.c`, `disp_lowpower.c`, `mtkfb.c`, `primary_display.c`, `fbconfig_kdebug.c` | **not priceable** | each dies on one `#include` before the link: `disp_dts_gpio.h` (dsi, pwm), `ddp_reg_disp_bdg.h`, `mtk_leds_drv.h`, `mtk_disp_mgr.h`, `ion_drv.h`/`mtk_ion.h` (4 files, ION - refused by policy), and one implicit-declaration pair in `fbconfig_kdebug.c`. The rig's own "empty name set = the link never ran" warning is printed for all ten, so their deltas are void rather than -57 |

## Predicted, for the gate to confirm

Before (0092, `report/l2-open-names-at-0092.txt`): **57 distinct names** undefined with the switch ON,
from 160 ld reference lines.

After: **49 distinct names.**

Closed - exactly these 8, each `open:0` in the link and `defined:1` tree-wide:

```
ddp_driver_ccorr  ddp_driver_color  ddp_driver_dither  ddp_driver_gamma
corr_dbg_en  disp_ccorr_on_end_of_frame  disp_color_dbg_log_level  disp_color_ioctl
```

Each of those was already *referenced* by landed code, which is why it counted as open: the module
table in `ddp_info.c:119/132/158/171` and `ddp_info.h:495-503`, the end-of-frame hook in
`ddp_irq.c:456`, the debugfs hooks in `ddp_debug.c:476/482` and `ddp_manager.c:1584`. So the slice
fills holes in code this tree already runs, rather than adding unused code.

Opened: **0.** The trio's only unmet symbol was `cmdqRecReadToDataRegister`, and the new adapter
function provides it (`defined:1` in `mtk-cmdq-disp-record.o`).

Sizes and shapes the probe already fixed: `ddp_color.o` 272,968 B, `ddp_dither.o` 104,728 B,
`ddp_gamma.o` 139,560 B, all three with 0 `error:`; the 8 predicted names must all appear in the
census of globals defined by the three objects (expect 8 of 8) with 0 collisions against the rest of
the tree; the trio's textually detected non-static globals are 32 names, none of which is defined
anywhere in the port's landed display code (measured before the landing, `grep`-based over
`drivers/misc/mediatek/video`).

The entry point is pinned by the harness rather than by the build: 85 cases, 0 mismatches (up from 55),
of which 12 compare the vendor's and mainline's `READ_S` instruction word for the resolvable addresses,
9 assert that an address no `gce` row covers is refused before any word is built, and 4 assert the
definition's shape (delegates to `cmdq_pkt_read_s()`, returns `-EOPNOTSUPP` at or above
`CMDQ_DATA_REG_JPEG_DST`, is the only place that adds `CMDQ_GPR_V3_OFFSET`, resolves the address before
looking at the destination register).

## Honest limit, stated before the numbers

* Nothing in this slice can create a CMDQ record: `cmdqRecCreate` is still not provided, so no landed
  callsite can run. The gate measures link state, not a frame.
* The refused branch is real: a `dst_data_reg >= CMDQ_DATA_REG_JPEG_DST` read needs the vendor's
  `CMDQ_CODE_READ`/`CMDQ_CODE_WFE`/GPR-mutex detour, mainline 5.15 has no `CMDQ_CODE_READ` enumerator
  at all, and `struct cmdq_instruction` plus `cmdq_pkt_append_command()` are private to
  `drivers/soc/mediatek/mtk-cmdq-helper.c`. The port returns `-EOPNOTSUPP` with a
  `pr_err_once()` instead of inventing an encoding. No landed callsite reaches that path: the colour
  code uses `CMDQ_DATA_REG_PQ_COLOR` (0x04) and `0x00`/`0x10`, all below 0x11 (measured: 3 callsites,
  `ddp_color.c:4028/4038/4044`).
* Landing the three objects makes `ddp_path.c`'s module table complete for colour, dither, gamma and
  ccorr, but the vendor's `common/Makefile` also gates those directories on `CONFIG_MTK_AAL_SUPPORT`
  and friends; this port gates all three on `CONFIG_MTK_DISP_BRINGUP`, so the switch is coarser than
  the vendor's on purpose and the report says so.
* Still blocked on panel/lcm handover, unchanged by this slice: 5 `primary_display_*` (including
  `primary_display_idlemgr_kick`, which `ddp_gamma.c:862` calls), `DSI_dcs_read_lcm_reg_v2`,
  `set_lcm`/`read_lcm`, `do_lcm_vdo_lp_*`, and the whole `lcm/` directory.
* Nothing is flashed, nothing boots, no display is drawn: the maturity statement in `MATURITY.md` is
  "compiles and links" and this slice does not move it.

## Measured on the landed tree - gate `l2_disp_record_publish51`

`bash /home/user/portwork/slice0093-gate.sh`, log `portwork/logs/slice0093-gate-20260906T113559Z.log` (mirrored to
`report/logs/`), 69 s on a warm tree, on series commit `0365f7ba4` / tree
`899e689602bca34b67cedf293bb7df337f5bd609`, landing tree clean.

| prediction | gate |
|---|---|
| 57 -> 49 distinct open names | **49**, and the delta both ways is exactly the claim: 8 closed, 0 opened (160 -> 140 ld reference lines) |
| the closed set is the eight predicted names | "the closed set is exactly the eight predicted names: yes", and each one reads `open:0 defined-tree-wide:1 in-trio:1` |
| `cmdqRecReadToDataRegister` closes the trio's one gap | `open:0 defined:1`, and the three callsites at `ddp_color.c:4028/4038/4044` are printed from the landed file |
| objects 272,968 / 104,728 / 139,560 B | all three, rebuilt from scratch after deleting them; the adapter object is 105,000 B with `cmdqRecReadToDataRegister` among its four `T` entry points |
| 0 `error:` lines in the ON build | 0 in the single-object build and 0 in the whole-tree `-k` link; the 29 warnings in the single-object build are the landed v3 headers' own - `cmdq_record.h:804/833/845/889` and `cmdq_helper_ext.h:880/881/988`, four of each for four translation units, plus `mtk-cmdq-mailbox.h:91` once - and 0 diagnostics name the three landed files |
| 32 new globals, 0 collisions | 32 globals defined by the three objects, all 8 predicted names inside that census, 0 collisions with the rest of the tree |
| verbatim | three sha256 matches against the vendor files: `b81b1f10ff22`, `e2f9ffffc06b`, `d1efbeec6173` |
| OFF state unchanged by this slice | rc 0 with `LD vmlinux` twice, 0 `error:`, 0 undefined, `vmlinux` 168,340,520 B, `System.map` 6,911,826 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,266 B, payload 493,517 B, `mt6768.dtb` `34a7e6b536a3`; no landed symbol in that `vmlinux` (11 names probed, all 0), no record object, 0 gated display objects |
| prior rounds keep their closures | 0089's bias names, 0090's 15 path names, 0091's 3 record names, 0092's 5 mmp names: all 0 in the open set |
| harnesses carry the new proof | record **85 cases / 0 mismatches** (12 `read_s` words compared, 9 refusal cases), slot 37 / 0, both with 0 build warnings |
| tree usable afterwards | config back to `099cdd6421b6`, dirty 0 |

Two rig findings from the same two runs, recorded because they changed what the numbers mean:

* The first run (`slice0093-gate-20260906T113357Z.log`, 73 s) printed `in-trio:0`, `defined:0` for the new entry point and "new global
  symbols from the three objects: 0". Those were the gate's own bugs, not the tree's: `nm` reading an
  object from a pipe prints nothing at all (`cat x.o | nm --defined-only -g` -> 0 symbols, `nm x.o` -> 4,
  measured on the adapter object), and every census line that piped was therefore vacuously zero. The
  fixed gate re-ran and printed the numbers in the table above. The same bug in
  `tools/portwork/probe-slice.sh` is why every earlier sweep row read "globals defined by the new
  objects: 0" - that column had never measured anything, and it is fixed here rather than back-filled,
  because no past conclusion rested on it (each of those rounds used the whole-tree link, not the census).
* The `CLOSED` set comparison fired ("closed set differs from the prediction") on a correct state, because
  it compared `comm`'s sort order against prose order. Set comparisons now sort both sides. A gate check
  that fails on a good tree is worse than no check, which is also why the HEAD-is-0093 check stopped
  grepping for a filename the subject never uses.

The gate's ON-state warning total is not comparable across its two runs (121 warnings in the first, 113 in
the second): warnings are emitted per compilation and a warm re-run recompiles fewer files. Only the
single-object count, 29, is a statement about this slice's four translation units, and it is the number
quoted above.

Post-slice open set, 49 names, kept as `report/l2-open-names-at-0093.txt` (written by the gate) for the
next round's before-side. What is left is a different kind of list: 10 `ddp_driver_*`-adjacent engine
structs minus the four this slice closed, the DSI/LCM group, and the dump/debug globals - and per
`report/logs/sweep-0093.log`, ten of the eleven remaining candidate files cannot even be priced until five
headers are settled, four of which (`disp_dts_gpio.h`, `ddp_reg_disp_bdg.h`, `mtk_leds_drv.h`,
`mtk_disp_mgr.h`) are board-config or DT-reader headers and one of which is ION.
