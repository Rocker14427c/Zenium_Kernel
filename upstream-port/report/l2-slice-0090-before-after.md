# Slice 0090 candidate, measured: `ddp_path.c` priced by a real before/after ON build

Date: 2026-09-06. Tree of record: `/home/user/portwork/series` at tree hash
`7320325c38fdc188de726f3ba658d0f6b80e7eb6` (89 published patches, 0089 tip content). Nothing here is a
claim about the device: no boot, no panel, no first frame. This file exists so the next round can land
the slice without re-deriving the evidence, and so a reviewer can re-run it.

## Why this file and not the others

`report/l2-open-names-at-0089.txt` carries the corrected, definition-based census (78 names, 17 provider
files). A grep can rank candidates but cannot say whether a file compiles against the include set this
port actually carries, so each unlanded `dispsys` provider was built in the real tree with
`CONFIG_MTK_DISP_BRINGUP=y` - one vendor `.c` copied byte-for-byte, one `obj-` line, nothing else:

| file | lines | result | what stopped it |
|---|---:|---|---|
| **`ddp_path.c`** | 987 | **compiles clean**, object 162,296 B, 21 global symbols | nothing |
| `ddp_mmp.c` | 934 | compiles clean, 85,592 B, 7 symbols | declined - see below |
| `ddp_ovl.c` | 2,823 | fails | `ddp_ovl.c:21:10: fatal error: mtk_dramc.h` |
| `ddp_rdma_ex.c` | 1,649 | fails | `:12:10: fatal error: ddp_matrix_para.h` |
| `ddp_wdma_ex.c` | 1,330 | fails | `:11:10: fatal error: ddp_matrix_para.h` |
| `ddp_dsi.c` | 8,377 | fails | `:35:10: fatal error: disp_dts_gpio.h` |
| `ddp_disp_bdg.c` | 5,263 | fails | `:12:10: fatal error: ddp_reg_disp_bdg.h` |

Every one of the five failures is a *single missing header*, which is the same class of step 0085
("repair the dispsys include set") already handled - so the header can be landed together with the file
that needs it, in that order: rdma/wdma share `ddp_matrix_para.h` (10 names between them), then ovl,
then dsi, then bdg (which additionally needs the measured rewrite at `ddp_disp_bdg.c:3030`).

`ddp_mmp.c` is declined even though it compiles: `grep -rl "define DEFAULT_MMP_ENABLE"` over
`drivers/misc/mediatek` and `include/` finds nothing in the vendor tree, so stock's own `ddp_mmp_init()`
body compiles out for every board, and with `CONFIG_MMPROFILE=y` the tracing hooks resolve to
`mmprofile.h`'s no-op arm unless `drivers/misc/mediatek/mmp/` is ported too. It closes 5 instrumentation
names and moves no frame: an artificial slice, by the definition the port has been using.

`ddp_path.c` is the opposite case. It is not an optional layer - five of the names it defines are
referenced by files that are **already landed**, so its gaps were created by this port:

```
ddp_path_init          <- dispsys/ddp_drv.c          ddp_get_scenario_list  <- dispsys/ddp_manager.c
ddp_connect_path       <- dispsys/ddp_manager.c      ddp_get_dst_module     <- dispsys/ddp_manager.c
module_list_scenario   <- dispsys/ddp_mutex.c        ddp_get_module_num_l   <- dispsys/ddp_mutex.c
```

## Before/after, whole-tree ON link

`portwork/before-after-0090.sh` builds `vmlinux` twice with `CONFIG_MTK_DISP_BRINGUP=y` (`make -j2
ARCH=arm64 -k vmlinux`), parses `ld` with the correct pattern (`undefined reference to \`name'` - the
first attempt grepped for quotes and reported 0 names, which is how a harness bug nearly became a
finding), and diffs the distinct-name sets. The tree is left with `MTK_DISP_BRINGUP` disabled, dirty 0,
same tree hash.

| | before | after |
|---|---:|---:|
| compile errors, whole ON build | 0 | 0 |
| warnings attributed to `ddp_path.c` | - | **0** |
| `undefined reference` lines | 486 | 281 |
| **distinct undefined names** | **78** | **65** |
| names closed | - | 15 (all of the census's `ddp_path.c` rows, incl. the `module_list_scenario` array) |
| names opened | - | 2 |

The two it opens are `cmdqRecWaitNoClear` and `cmdqRecSetEventToken` - the deferred record-write family
(decisions 146/148/149), reachable from `ddp_path.c:908/910/927` inside the `#ifdef
CONFIG_MTK_SMI_EXT` region opened at `:881`. That region is live for this board (even_defconfig sets
`CONFIG_MTK_SMI_EXT=y`), i.e. stock compiles it too and resolves it from `cmdq/v2/cmdq_record.c`, which
this port has deliberately not carried. Per the standing rule the names are left undefined and
documented rather than shimmed.

Two numbers in the earlier record get sharpened by this run:

- `disp_helper_get_option`/`disp_helper_get_stage` are **not** open in a real ON build. A single-directory
  probe (`make ... drivers/misc/mediatek/video/mt6768/dispsys/`) makes them look undefined because
  `video/Makefile` descends into `videox/` on `obj-$(CONFIG_MTK_DISP_M4U)` while the objects are keyed on
  `CONFIG_MTK_DISP_BRINGUP`: build one directory and you silently drop the `videox` half of the gated set.
  A full ON build compiles `videox/disp_helper.o` (452 lines, landed non-verbatim - it carries two
  documented `Port:` comments where unported `primary_display.c` calls were removed) and it defines both.
  **Gates and probes must therefore build the whole tree, not a directory.**
- "0 warnings" in 0089's ON phase meant 0 warnings from the objects that run *rebuilt* (9 PMIC objects).
  A full ON recompile is not warning-free: 7 `warning:` lines come from landed headers
  (`cmdq/v3/cmdq_record.h:804/833/845/889`, `cmdq_helper_ext.h:880/881/988` - "declared inside parameter
  list"), reached through `ddp_log.h -> ddp_debug.h -> ddp_dump.h -> ddp_path.h`, and they fire for any file
  that includes that chain, `disp_helper.c` among them. `ddp_path.c` itself contributes none. This is
  pre-existing landed state worth its own small slice (forward-declare the enum/struct, as stock's own
  header ordering does), and it is not a reason to hold the path slice.

## Landing shape for the next round

Copy `drivers/misc/mediatek/video/mt6768/dispsys/ddp_path.c` verbatim into the same relative path, add
one line to that directory's Makefile gated on `CONFIG_MTK_DISP_BRINGUP`, placed to preserve stock's
relative order (stock `dispsys/Makefile` has `obj-y += ddp_path.o` at :88, between `ddp_clkmgr.o` :84 and
`ddp_irq.o` :95). No header, no Kconfig, no code edit. Then the standing gate: whole-tree link with the
switch off (must be `LD vmlinux` clean), ON build asserting 0 errors and the 65-name set, `nm` confirming
the 15 closed names are `T` and that the bias names from 0089 stay closed. Expect the ON distinct-name
count to read 65; if it reads differently, that difference is the finding.
