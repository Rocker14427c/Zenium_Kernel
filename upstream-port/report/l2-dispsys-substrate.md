# L2 dispsys substrate: what the core layer actually requires (measured 2026-09-05)

This is the L2 opening measurement, taken before any display file was committed. It exists because the
plan's L2 sizing ("21 built objects, 32,454 lines") counted *source* lines and said nothing about the
two things that decide the work: which objects need CMDQ, and what the header substrate drags in. Both
answers changed the landing order. Nothing in this file is a claim about hardware behaviour.

## 1. The 21 built objects and their CMDQ dependency, per file

Counts from `grep -cE` over the vendor files in `drivers/misc/mediatek/video/mt6768/dispsys/`; "built"
follows the vendor Makefile (`obj-y` list plus `obj-y += ddp_disp_bdg.o` under
`ifeq ($(CONFIG_MACH_MT6768),y)`, which is `y` in `arch/arm64/configs/even_defconfig:302`).
`ddp_dbi.c` is the only `.c` in the directory that stock does not build (`ddp_dpi.o` is commented out;
`ddp_mmp.o` is built because `CONFIG_MMPROFILE=y`, even_defconfig:1712).

| object | lines | `cmdq_pkt_*` | `cmdqRec*` | `cmdq_op_*` |
|---|---|---|---|---|
| ddp_ovl.c | 2,823 | 0 | 19 | 0 |
| ddp_rdma_ex.c | 1,649 | 0 | 13 | 0 |
| ddp_wdma_ex.c | 1,330 | 0 | 21 | 0 |
| ddp_dsi.c | 8,377 | 4 | 31 | 0 |
| ddp_disp_bdg.c | 5,263 | 33 | 17 | 0 |
| ddp_path.c | 987 | 0 | 3 | 0 |
| ddp_clkmgr.c | 563 | 0 | 0 | 0 |
| ddp_rsz.c | 507 | 0 | 0 | 0 |
| ddp_drv.c | 705 | 0 | 0 | 0 |
| ddp_mutex.c | 389 | 0 | 0 | 0 |
| ddp_m4u.c | 400 | 0 | 0 | 0 |
| ddp_debug.c | 964 | 0 | 0 | 0 |
| ddp_dump.c | 1,643 | 0 | 0 | 0 |
| ddp_manager.c | 2,170 | 0 | 0 | 0 |
| ddp_irq.c | 571 | 0 | 0 | 0 |
| ddp_info.c | 612 | 0 | 0 | 0 |
| ddp_color_format.c | 326 | 0 | 0 | 0 |
| ddp_pwm_mux.c | 347 | 0 | 0 | 0 |
| ddp_met.c | 237 | 0 | 0 | 0 |
| display_recorder.c | 1,657 | 0 | 0 | 0 |
| ddp_mmp.c | 934 | 0 | 0 | 0 |

15 of 21 objects reference no CMDQ client API at all. The display path's CMDQ usage is *not* dominated
by the `cmdq_pkt_*` functions that patches 0082/0083 dealt with: it is the **v3 record API**
(`cmdqRec*`, 28 distinct names used across `video/mt6768/`), reached through the `void *cmdq`
`cmdqRecStruct` handle that `ddp_dsi.c` and the DMA blocks pass around, plus `cmdq_op_*` wrappers in
`ddp_drv.c`/`ddp_disp_bdg.c`.

## 2. `ddp_disp_bdg.c`: the rewrite is narrower than last round's note, and it is not a link need

`cmdqcensus.py` (strips C comments and strings, then resolves each callsite's `#ifdef` chain against
`even_defconfig`) gives:

| callsite | guards | reachability |
|---|---|---|
| `ddp_drv.c:422` `extern void disp_init_bdg_gce_obj(void);` | `#ifdef CONFIG_MTK_MT6382_BDG` | **dead** |
| `ddp_drv.c:564-565` `bdg_is_bdg_connected()` / `disp_init_bdg_gce_obj()` | `#ifdef CONFIG_MTK_MT6382_BDG` | **dead** |
| `ddp_dsi.c:922,1184,1649,2092,2264,2272,2419,5737,5786,5828,5913,6078,6439,6528` `bdg_is_bdg_connected()` | none | **live, 14 sites** |
| `ddp_dsi.c:6442` `bdg_tx_start(DISP_BDG_DSI0, cmdq)` | none | **live** |
| `ddp_disp_bdg.c:3005-3030` `disp_init_bdg_gce_obj()`, which holds `cmdq_register_device()` | none inside the file, but no live caller | compiled, never called |

So last round's framing - "the `cmdq_register_device` rewrite is 18 lines of ddp_disp_bdg.c and it is a
link requirement" - needs correcting on the second half: the object *is* a link requirement (live
`bdg_is_bdg_connected()` and `bdg_tx_start()` calls), but the function that registers the GCE client is
reached only from code this board compiles out. The 17 `disp_bdg_gce_base` users (`:3099-3165`, 14
`cmdq_pkt_write` + 3 `cmdq_pkt_poll`) are in that never-called region. What to do with them is an L2
decision with two defensible answers, and it must not be made by silently keeping dead code:

1. port `ddp_disp_bdg.c` verbatim and satisfy those 18 lines with the verified 5.15 form
   (`cmdq_dev_get_client_reg()` + `cmdq_pkt_write(pkt, reg.subsys, reg.offset, value)`); or
2. drop `disp_init_bdg_gce_obj()` and its consumers, documenting that stock never calls them on even.

Option 1 preserves stock text and is the one this port will take, because it keeps the file diff
against vendor empty; the DT data it needs is already in our tree (see §4).

## 3. The real L2 blocker is the header substrate, and it reaches the v3 CMDQ headers

Static closure over the local (`#include "..."`) includes of the five simplest CMDQ-free objects
(`ddp_info.c ddp_color_format.c ddp_mutex.c ddp_pwm_mux.c ddp_clkmgr.c`): **35 distinct headers,
10,818 lines**, of which 32 were absent from our tree. `ddp_reg.h` alone pulls 8 block register headers
(`ddp_reg_mmsys/mutex/ovl/pq/dma/dsi/mipi/rsz`, 3,529 lines), and `ddp_info.h` → `disp_session.h` →
`ddp_path.h` pulls the CMDQ v3 *header* set:

```
drivers/misc/mediatek/cmdq/v3/cmdq_record.h            923 ln
drivers/misc/mediatek/cmdq/v3/cmdq_helper_ext.h      1,032 ln
drivers/misc/mediatek/cmdq/v3/cmdq_event_common.h      661 ln
drivers/misc/mediatek/cmdq/v3/cmdq_def.h               560 ln
drivers/misc/mediatek/cmdq/v3/cmdq_core.h                12 ln
drivers/misc/mediatek/cmdq/v3/cmdq_subsys_common.h       72 ln
drivers/misc/mediatek/cmdq/v3/mt6768/cmdq_engine.h         (mt6768-specific)
```

That is the same trap 0082 fell into from the other side: `cmdq_helper_ext.h` declares vendor
`cmdq_pkt_*` prototypes with vendor signatures (`struct cmdq_base *clt_base`, `dma_addr_t addr`) while
mainline's `include/linux/soc/mediatek/mtk-cmdq.h` declares the same names with
(`u8 subsys, u16 offset`). Carrying both headers into one tree means any TU that sees both gets
conflicting declarations, and the resolution has to be a deliberate, documented decision - not an
accident produced by an include-closure loop.

I probed this concretely rather than reasoning about it, with `bin/l2slice.py`: copy the requested
objects verbatim, generate a `dispsys/Makefile` from the *stock* ccflags list filtered to directories
that exist in this tree (14 of 24 stock `-I` paths do not exist here: `video/include`, `video/common*`,
`smi`, `gpu/ged/include`, `staging/android/mtk_ion*`, `dramc/mt6768`, `cmdq/v3`, `lcm/inc`), then let
the compiler name each unresolved include and copy that header, iterating. After 16 iterations - 20
headers copied, the v3 set above among them - the kernel build's first real diagnostic was:

```
./drivers/misc/mediatek/cmdq/v3/cmdq_helper_ext.h:69:17: error: field 'savetv' has incomplete type
```

i.e. the v3 header needs further vendor type definitions, so the substrate keeps growing exactly where
the API collision lives. `ddp_color_format.o` did build in that state (it needs no CMDQ types), which
bounds the problem: the small CMDQ-free objects are close, the v3 header surface is the wall.

**The slice was then reverted instead of committed.** `portwork/series` is back to the published 0083
state: `git status --porcelain` empty, tree `1bbd779ea9182f344c9e231621bca0ae8b715dae`, and
`make drivers/misc/mediatek/video/mt6768/dispsys/ drivers/soc/mediatek/ drivers/mailbox/` rc=0 with 0
errors / 0 warnings (`ddp_m4u.o` 64,968 B). Committing a non-building display slice would recreate the
half-landed CMDQ state that 0082 existed to undo.

Two tool notes from the probe, because both are gates I now depend on:

- The first `l2slice.py` run reported `build rc=0` while building **nothing**: it generated
  `obj-y += foo.c` instead of `foo.o`, kbuild ignored the lines, and `built-in.a` was a 514-byte empty
  archive. The script now only accepts rc=0 when every expected `.o` exists and is non-empty, and it
  prints their sizes. A green build that compiled zero files is a fake green.
- The `-I` list has to be recomputed after each copy, since the closure loop creates the directories it
  copies into (`video/include/` did not exist before the first header landed).

## 4. Consequences for the L2 landing order

1. **L2 must start with a CMDQ-header decision, not with a file.** Options, both defensible: (a) carry
   the v3 header set and *not* `cmdq_helper_ext.h`'s `cmdq_pkt_*` prototypes (trim that one header with a
   documented, line-listed exclusion so mainline's `mtk-cmdq.h` stays the only client API), or (b) port
   `cmdq_record.{c,h}` as the record layer's implementation and adapt the 6 CMDQ-calling objects'
   `cmdq_pkt_*` callsites to mainline's signatures. (a) is smaller and keeps 0082's property - one
   client API in the tree; (b) is what full BDG/record parity needs. This is the question to answer
   first, and it is answerable offline.
2. The record layer is a **live** requirement (`cmdqRec*` in ddp_ovl/ddp_rdma_ex/ddp_wdma_ex/ddp_path/
   ddp_dsi), unlike the sleep family, which stayed dead. So "port v3 only when a live callsite requires
   it" bites here in the other direction: v3 *is* now required, and the requirement is measured at 28
   names + 4 files, not assumed from directory size.
3. `ddp_disp_bdg.c`'s GCE-registration region takes the `cmdq_dev_get_client_reg()` form; our
   transplanted `arch/arm64/boot/dts/mediatek/mt6768.dts` retains the `gce-subsys`/`gce-client-reg`
   properties (3 matching lines, identical count to the vendor file), so the DT data exists.
4. `CONFIG_MTK_MT6382_BDG` stays unset and un-Kconfig'd, matching stock: that is what makes the
   `sleep_by_poll` and `disp_init_bdg_gce_obj` regions dead in our build too, and it is why the panel's
   gate/bias I2C need (`lcm_i2c.c` `display_bias_setting()`) is unaffected by any of this.
5. Panel selection stays exactly as stock: `parse_tag_videolfb()` → `mtkfb_lcm_name[]` →
   `mtkfb_find_lcm_driver()` over `mt65xx_lcm_list.c`, with the `_drv` suffix and `setLcmPanel_ID`
   ladder. Nothing in this measurement gives a reason to convert it to a DT model - the packaged
   `mt6768.dtb` carries no such properties.
