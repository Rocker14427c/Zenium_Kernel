# Slice 0092 - predicted before/after, written before the landing

Everything under "predicted" was measured by replaying the landing against the tree of record
(`bash /home/user/portwork/probe-0092b.sh`, `bash /home/user/portwork/probe-slice.sh "ddp_mmp.c"`,
logs `portwork/logs/probe-0092b.log`, `portwork/logs/probe-ddp_mmp_c.log`, both on
`3483759c24eb022373a5290523933b61bbd7ac62` = the 91-patch tip, dirty 0) and then restoring that tree
(config back to `099cdd6421b6`, `git status --porcelain` back to 0). No number below is a guess about
the future build; each is a measurement of the same edit applied once already.

## What the slice is

One vendor file, verbatim, plus one Makefile line:

| file | lines | sha256[:12] | destination |
|---|---|---|---|
| `drivers/misc/mediatek/video/mt6768/dispsys/ddp_mmp.c` | 934 | `f0a113c93138` | same path in the port |

plus `obj-$(CONFIG_MTK_DISP_BRINGUP) += ddp_mmp.o` appended to the port's `dispsys/Makefile`, which
goes from 15 gated `obj-$(CONFIG_MTK_DISP_BRINGUP)` lines to 16.

`ddp_mmp.h` is already in the port (4,435 B), `ddp_reg.h`, `ddp_log.h`, `ddp_m4u.h` and
`drivers/misc/mediatek/mmp/mmprofile.h` are already in the port, and every `-I` the file needs is
already in the Makefile - so the patch touches exactly two files.

Why this file, when the obvious candidates were RDMA and WDMA: it is the largest measured *reduction*
of the open-name set available without growing the record adapter (see "priced alternatives").

## Predicted, for the gate to confirm

Before (0091, `report/l2-open-names-at-0091.txt`): **62 distinct names** undefined with the display
switch ON, from 211 ld reference lines.

After: **57 distinct names.**

Closed - exactly these 5, each `open:0` in the link and `defined:1` tree-wide:

```
ddp_mmp_get_events   ddp_mmp_init   ddp_mmp_ovl_layer   ddp_mmp_rdma_layer   ddp_mmp_wdma_layer
```

Opened: **0.** `ddp_mmp.o` introduces no name that was not already open, because everything it calls
that the port lacks sits behind the landed `#ifdef CONFIG_MTK_M4U` (line 655) or the landed
`#ifdef CONFIG_MTK_HDMI_SUPPORT` (line 205), and the three `mmprofile_*` calls are static-inline no-ops
in the port's `mmp/mmprofile.h:131/212/216` (that header is the `#else` branch of
`#ifdef CONFIG_MMPROFILE`, and the port's config of record does not set that symbol).

| measurement | predicted |
|---|---|
| `ddp_mmp.o` size, built from scratch with the switch ON | 85,592 B |
| `error:` / `warning:` lines attributed to `ddp_mmp.c` | 0 / 0 |
| `error:` in the whole ON log (compile stage) | 0 |
| global `T` symbols the object adds | 6 (the 5 above plus `init_ddp_mmp_events`) |
| collisions of those globals with the rest of the tree | 0 |
| `mt6768.dtb` | 122,474 B, sha `34a7e6b536a3` |
| appended DTB payload in `Image.gz-dtb` | 493,517 B, unchanged since 0081 |
| OFF-state `vmlinux` | 168,340,520 B, links, 0 `error:` |
| host harnesses | record 55 cases / 0 mismatches, slot 37 / 0 - neither is touched by this slice |
| config after the gate | `099cdd6421b6` |

The record adapter (`drivers/soc/mediatek/mtk-cmdq-disp-record.c`, `include/linux/soc/mediatek/`)
is deliberately **not** extended by this patch: no name this slice lands needs a record entry point,
and the standing rule is that the adapter grows only where a landed callsite proves the requirement.

`Image.gz-dtb` total size is not predicted: it moved 12,228,271 -> 12,228,265 -> 12,228,264 B across
0089/0090/0091 while `vmlinux` and the appended DTB payload were byte-identical, because gzip output and
the embedded `git describe` string both change with the commit. Sizes and payload are the cross-round
checks; the image sha256 is not.

## Priced alternatives (measured, same method, same tree)

These are the numbers behind the shape of this slice. All were probed by applying the landing and
linking the whole tree with the switch ON.

| candidate | compiles? | closes | opens | net |
|---|---|---|---|---|
| `ddp_mmp.c` (this slice) | yes, 85,592 B | 5 | 0 | **-5** |
| `ddp_color.c` (4,099 ln) + `ddp_dither.c` (409 ln) + `ddp_gamma.c` (1,574 ln) from `common/{color20,corr10}` | yes: 272,968 / 104,728 / 139,560 B, 0 diags | 8 | 1 - `cmdqRecReadToDataRegister` | **-7** |
| `ddp_rdma_ex.c` (1,649 ln) + `ddp_wdma_ex.c` (1,330 ln) + `ddp_matrix_para.h` (131 ln) | yes (wdma with one documented include deviation, see below) | 10 | 21 | **+11** |
| `ddp_ovl.c` (4,527 ln) + `dramc/mt6768/mtk_dramc.h` (195 ln) + one `-I` | yes, 496,168 B, 0 diags | 6 | 10 | **+4** |
| `ddp_dump.c` | already landed, so a no-op | 0 | 0 | 0 |
| `ddp_ccorr.c`, `ddp_aal.c` (as `common/aal20`), `ddp_pwm.c` | no - `ddp_ccorr.c` does not exist (ccorr lives inside `ddp_color.c`), aal needs `mtk_leds_drv.h`, pwm needs `disp_dts_gpio.h` | - | - | not priceable |
| `videox/debug.c`, `videox/disp_lowpower.c` | no - `debug.c` needs `mtk_disp_mgr.h`, `disp_lowpower.c` needs `ion_drv.h` | - | - | not priceable |
| `common/rdma20/ddp_rdma.c`, `common/wdma20/ddp_wdma.c` | **must not be landed** | - | - | foreign to this board |

The last row is worth spelling out, because those two files looked like the natural 0092 and are not:
`drivers/misc/mediatek/video/common/Makefile:70-78` descends into `rdma20/`/`wdma20/` only for
`CONFIG_MACH_MT6799` (and into `rdma10/`/`wdma10/` for MT6757/KIBOPLUS/MT6797/MT6795/MT8167). mt6768
takes neither branch, so the vendor's mt6768 build never compiled them - which is also why
`DDP_REG_BASE_DISP_RDMA0`, which `ddp_rdma.c:25` returns, is defined nowhere in the vendor tree
(grep over `drivers/` + `include/` finds only that one use). They are MT6799 code kept in a shared
directory, in the same class as the `cmdq/v3/*.c` files that are headers-only in this port. The
mt6768 providers of `rdma_get_address`, `rdma_dump_reg`, `wdma_dump_reg` etc. are the platform
`ddp_rdma_ex.c` / `ddp_wdma_ex.c`, which is what the +11 row measured.

The one deviation the RDMA/WDMA row needed to compile at all: `ddp_wdma_ex.c:19` has
`#include <ion_sec_heap.h>`, and this port carries no such header - the vendor's lives under
`drivers/staging/android/mtk_ion/mtk/`, which 0080 landed as headers-only for the type closure
(`drivers/staging/android/mtk_ion/ion.h`, whose line 31 is `#define ion_phys_addr_t unsigned long`).
Landing `ion_sec_heap.h` itself would drag in `ion_drv.h` and the ION driver it describes, which is
the boundary 0080 drew. In this file the include provides nothing that `ion.h` does not already
provide: its only type use is the `ion_phys_addr_t sec_hdl = -1;` declaration at line 1260, and the
only call that would need the header, `ion_hdl2sec_type()` at line 1262, is inside
`#ifdef CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM` - `=y` in `even_defconfig:1977`, absent from this port's
config of record. So the comment-out is behaviour-preserving here and follows the pattern already in
`ddp_drv.c:36` (`/* #include <linux/ion.h> */`). It is recorded and not applied, because this slice
does not land RDMA/WDMA.

## Why RDMA/WDMA are deferred rather than forced

Landing the two platform engine files would open 21 names while closing 10. 13 of the 21 are the
record lifecycle, and in the vendor they are not encoders at all: `cmdqRecCreate`, `cmdqRecDestroy`,
`cmdqRecReset`, `cmdqRecFlush`, `cmdqRecFlushAsync`, `cmdqRecWait`, `cmdqRecPoll`, `cmdqRecWriteSecure`,
`cmdqRecWriteSecureMetaData`, `cmdqRecSetSecure`, `cmdqRecSecureEnableDAPC`,
`cmdqRecSecureEnablePortSecurity`, `cmdqRecBackupUpdateSlot` are each a 3-4 line trampoline in
`cmdq/v3/cmdq_record.c` (lines 3808-4098) into the `cmdq_task_*` / `cmdq_op_*` session engine - the
part of v3 with per-subsys session pools, the `gce_plat` lock and the mailbox submission path, i.e. the
engine this port refuses to land (0082's revert is the reason). The remaining 8 are `videox` debug
knobs (`dbg_urg_low`, `dbg_urg_high`, `dbg_ultlow`, `dbg_ulthigh`, `dbg_prehigh`, defined in
`mt6768/videox/debug.c`, plus `_cmdq_insert_wait_frame_done_token_mira` there), `set_rdma_width_height`
(`videox/disp_lowpower.c`) and `primary_display_is_decouple_mode` (`videox/primary_display.c`) - all
three of those files are on the panel-handover side of the cut, not this side.

So RDMA/WDMA are gated on a decision about the record layer, not on missing display code. That is
recorded as an open decision in `KNOWN-ISSUES.md`, and the `cmdqRecReadToDataRegister` requirement in
the colour row is the same class of question one size smaller: the vendor's
`cmdq_op_read_to_data_register()` (`cmdq/v3/cmdq_record.c:1576`) is a pure encoder for the
`dst_data_reg < CMDQ_DATA_REG_JPEG_DST` case (`ddp_color.c:4040` passes `CMDQ_DATA_REG_PQ_COLOR` = 0x04,
`cmdq_def.h:273`, so this board takes that branch) and its other case goes through
`cmdq_append_wpr_command()`, whose special-address handling is the GPR-mutex/`MOVE` detour 0091
declined to carry. Both are one adapter entry away, and both would need the same host-check
transcription proof as 0091 before landing - which makes them a decision, not a slice.

## Honest limit

Nothing here draws a frame. `ddp_mmp.o` closes five link names that `ddp_drv.c` and
`display_recorder.c` have been referencing since 0085; the state of the port after this slice is
"compiles and links with fewer unresolved names". The one `#ifdef DEFAULT_MMP_ENABLE` block in the
file (`ddp_mmp_init()`, lines 927-934) is compiled out here, because the port's `dispsys/Makefile`
carries no `-D` flags at all (0085's filtered generation) while the vendor adds
`ccflags-y += -DDEFAULT_MMP_ENABLE` when `CONFIG_MMPROFILE=y` (`dispsys/Makefile:109-111`;
`even_defconfig:1712` sets it). That is a measured no-op rather than an omission: with the define the
body is `DDPMSG(...)`, `mmprofile_enable(1)`, `init_ddp_mmp_events()`, `mmprofile_start(1)` - and
`mmprofile_enable`/`mmprofile_start` are the static-inline dummies at `mmp/mmprofile.h:212/216`, while
`init_ddp_mmp_events()` only calls `mmprofile_register_event()` (`:131`, also a dummy). Passing the
define would therefore add one log line and no behaviour, at the cost of making this object the only
one in the directory compiled with a flag the other 15 do not get. Recorded instead of silently
applied; if the port ever lands `drivers/misc/mediatek/mmp/` for real, the define comes back with it.

## Measured on the landed tree - gate `l2_disp_record_publish50`

`bash /home/user/portwork/slice0092-gate.sh`, log `portwork/logs/slice0092-gate-20260906T073711Z.log`, 66 s, on series commit
`be0ef70ed` / tree `b5d70973e7f154d47f556bd7abac4aeca4d4176c`, landing tree clean.

| prediction | gate |
|---|---|
| 62 -> 57 distinct open names | **57**, and the delta both ways is exactly the claim: 5 closed, 0 opened (211 -> 160 ld reference lines) |
| the 5 MMP names, `open:0` / `defined:1` | all five `open:0 defined-tree-wide:1 in-object:1` |
| `ddp_mmp.o` 85,592 B | 85,592 B, rebuilt from scratch after deleting it |
| 0 diagnostics in the file | 0 `error:` in the single-object build and 0 in the whole-tree build; the 7 warnings are the landed v3 headers' own (`cmdq_record.h:804/833/845/889`, `cmdq_helper_ext.h:881/988`), printed with file and line so the count is attributable |
| 6 new globals, 0 collisions | 6 `T` symbols (`ddp_mmp_get_events`, `ddp_mmp_init`, `ddp_mmp_ovl_layer`, `ddp_mmp_rdma_layer`, `ddp_mmp_wdma_layer`, `init_ddp_mmp_events`), 0 collisions |
| verbatim | `sha256` of the landed file equals the vendor's: `f0a113c93138`, 934 lines on both sides |
| OFF state unchanged | rc 0 with `LD vmlinux` twice, 0 `error:`, 0 undefined, `vmlinux` 168,340,520 B, `System.map` 6,911,826 B, `Image` 34,165,248 B, `Image.gz` 11,734,752 B, `Image.gz-dtb` 12,228,269 B, payload 493,517 B, `mt6768.dtb` `34a7e6b536a3`; no `ddp_mmp` symbol in that `vmlinux` and 0 gated display objects |
| prior rounds keep their closures | 0089's 2 bias names, 0090's 15 path names, 0091's 3 record names: all 0 in the open set |
| harnesses unaffected | record 55 cases / 0 mismatches, slot 37 / 0, both with 0 build warnings; the adapter's two files still hash to `d09f5a729d99` and `2db3ccded27d`, i.e. 0091's bytes |
| tree usable afterwards | config back to `099cdd6421b6`, dirty 0 |

Two numbers the prediction could not fix in advance, recorded because the log has them: the `ld`
reference-line count fell 211 -> 160 (not a gate criterion, since lines are not names), and
`Image.gz`/`Image.gz-dtb` moved +5 B against 0091 with `vmlinux` and the appended DTB payload
unchanged - the gzip and `git describe` behaviour already documented, which is why image sha256 is
not a cross-round check.

The object's own 7 undefined symbols are worth listing, because "0 opened" is a claim about them:
`_printk` and `__stack_chk_fail` are core, and `disp_mva_map_kernel`, `disp_mva_unmap_kernel`,
`m4u_mva_map_kernel`, `m4u_mva_unmap_kernel` and `dprec_logger_pr` are already provided by
`ddp_m4u.c` and `display_recorder.c`, both landed in 0085. The gate prints that list; `nm -u` has no
type column, so the provider check is the `defined:1 tree-wide` census above rather than a guess from
the name.

Post-slice open set, 57 names, kept as `report/l2-open-names-at-0092.txt` for the next round's
before-side. The largest still-open provider is unchanged: 6 `ddp_driver_*` structs plus their engine
files (ovl, rdma, wdma, dsi0, pwm, aal, ccorr, color, dither, gamma), 5 `primary_display_*`, 4
`ovl_*`, 6 `rdma_*`/`wdma_*` dump and colour-transform names, 3 `do_lcm_vdo_lp_*`/`read_lcm`/`set_lcm`
panel names, and the `ddp_mmp_*`-adjacent debug globals.

## Re-verified after the second sandbox reset of this round - gate `l2_disp_record_reverify51`

The sandbox wiped `/home/user/portwork` (build tree, toolchain, and the log directory) a second time
during this round, so the gate was re-run from nothing on a recovered tree rather than cited from the
log above: `restore.sh` replayed the 92 `.eml` files, `build0.sh` rebuilt the toolchain hooks, and
`slice0092-gate.sh` ran cold. Every claim in the table above reproduced:

| claim | re-verified |
|---|---|
| landed file is the vendor's | `f0a113c93138`, 934 lines, both sides |
| 16 gated `obj-` lines | 16 |
| OFF link clean | rc 0, `LD vmlinux` 2, 0 `error:`, 0 undefined, 0 gated display objects, no `ddp_mmp_init`/`ddp_path_init`/`cmdqRecWrite`/`display_bias_regulator_init` in `vmlinux` |
| ON name state | 57 distinct names, CLOSED 5, OPENED 0, name-count expectation met |
| object | `ddp_mmp.o` 85,592 B, size matches the prediction |
| census | 0 collisions |
| harnesses | record 55 cases / 0 mismatches, slot 37 / 0 |
| adapter untouched | `mtk-cmdq-disp-record.c` `d09f5a729d99`, its header `2db3ccded27d` - 0091's bytes |
| tree left usable | config `099cdd6421b6`, dirty 0 |
| appended DTB | 493,517 B payload, `mt6768.dtb` `34a7e6b536a3` |

Two OFF-state sizes differ from the table above and the reason is the one already documented: `Image.gz`
11,734,750 B and `Image.gz-dtb` 12,228,267 B here against 11,734,752 B and 12,228,269 B there, while
`vmlinux` (168,340,520 B), `System.map` (6,911,826 B) and the uncompressed `Image` (34,165,248 B) are
identical. The recovered tree is a *replay* of the same patches, so its `git describe` string is one
commit-hash width different and gzip shows those two bytes. This is exactly why image sizes and the
payload size are the cross-round checks and image sha256 is not. Gate wall time 876 s cold, on 2 CPUs.

The value of running it again is not the confirmation itself: it is that a recovery path which
reproduces a published gate, bit for bit in the numbers that matter, is a recovery path that can be
trusted for the next slice.
