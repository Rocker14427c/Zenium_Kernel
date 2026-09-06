#!/usr/bin/env python3
"""rec0092.py - the records for patch 0092 (ddp_mmp.c landed, 62 -> 57 open names).

Same discipline as rec0090.py / rec0091.py: every edit asserts its anchor by exact count, both JSON
files round-trip through the repo's own serialization, and no number is written that the gate did not
print (gate log slice0092-gate-20260906T073711Z.log, 66 s, every expectation met).
"""
import json, os, sys

R = "/home/user/Zenium_Kernel/upstream-port"
GATE = "slice0092-gate-20260906T073711Z.log"


def sub(path, old, new, count=1):
    p = os.path.join(R, path)
    s = open(p).read()
    n = s.count(old)
    if n != count:
        sys.exit("ANCHOR %s: expected %d occurrence(s), found %d in %s" % (repr(old[:52]), count, n, path))
    open(p, "w").write(s.replace(old, new, count))
    print("edited %s" % path)


def append(path, text):
    p = os.path.join(R, path)
    s = open(p).read()
    if not s.endswith("\n"):
        s += "\n"
    open(p, "w").write(s + text)
    print("appended to %s" % path)


def jsave(p, obj):
    out = json.dumps(obj, indent=1) + "\n"
    open(p, "w").write(out)
    assert open(p).read() == out, "serialization of %s is not the repo's" % p
    print("wrote %s" % p)


# ---------- 1. the before/after report: predictions are now measurements ----------
sub("report/l2-slice-0092-before-after.md",
"""`init_ddp_mmp_events()` only calls `mmprofile_register_event()` (`:131`, also a dummy). Passing the
define would therefore add one log line and no behaviour, at the cost of making this object the only
one in the directory compiled with a flag the other 15 do not get. Recorded instead of silently
applied; if the port ever lands `drivers/misc/mediatek/mmp/` for real, the define comes back with it.""",
"""`init_ddp_mmp_events()` only calls `mmprofile_register_event()` (`:131`, also a dummy). Passing the
define would therefore add one log line and no behaviour, at the cost of making this object the only
one in the directory compiled with a flag the other 15 do not get. Recorded instead of silently
applied; if the port ever lands `drivers/misc/mediatek/mmp/` for real, the define comes back with it.

## Measured on the landed tree - gate `l2_disp_record_publish50`

`bash /home/user/portwork/slice0092-gate.sh`, log `portwork/logs/%s`, 66 s, on series commit
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
panel names, and the `ddp_mmp_*`-adjacent debug globals.""" % GATE)

# ---------- 2. KNOWN-ISSUES: a new numbered entry ----------
sub("KNOWN-ISSUES.md",
"""channel - at which point the prefetch question and the `#if !defined(CONFIG_MTK_CMDQ_MBOX_DRV)` binding of
the header (the eight header warnings this file inherits, including `mtk-cmdq-mailbox.h:91`'s
`struct mbox_chan` scope wart, which pre-dates 0091 and affects every includer) become live engineering
questions rather than documented omissions.""",
"""channel - at which point the prefetch question and the `#if !defined(CONFIG_MTK_CMDQ_MBOX_DRV)` binding of
the header (the eight header warnings this file inherits, including `mtk-cmdq-mailbox.h:91`'s
`struct mbox_chan` scope wart, which pre-dates 0091 and affects every includer) become live engineering
questions rather than documented omissions.

## 15. Why the engine files are not landed yet, and which two files must never be (measured at 0092)

0092 was queued as `ddp_rdma_ex.c` + `ddp_wdma_ex.c` + `ddp_matrix_para.h`. It is not landed, because
pricing that set against the tree of record showed it costs more names than it pays: it compiles clean
and closes 10 open names while opening 21, so the whole-tree link would have gone 62 -> 73 open names
instead of 62 -> 57. Every number is in `report/l2-slice-0092-before-after.md`; the three findings that
decide it are here, so that no later round re-derives them.

1. **13 of the 21 opened names are the record lifecycle, and in the vendor they are not encoders.**
   `cmdqRecCreate`, `cmdqRecDestroy`, `cmdqRecReset`, `cmdqRecFlush`, `cmdqRecFlushAsync`, `cmdqRecWait`,
   `cmdqRecPoll`, `cmdqRecWriteSecure`, `cmdqRecWriteSecureMetaData`, `cmdqRecSetSecure`,
   `cmdqRecSecureEnableDAPC`, `cmdqRecSecureEnablePortSecurity` and `cmdqRecBackupUpdateSlot` are each a
   3-4 line trampoline in `cmdq/v3/cmdq_record.c` (lines 3808-4098) into `cmdq_task_*` / `cmdq_op_*`:
   per-subsys session pools, the `gce_plat` lock, mailbox submission. That is the engine this port
   refuses to land - the reason 0082 exists as a revert. Answering them means either growing the
   adapter into a session model (an architectural change, not a slice) or landing v3 (dead on
   measurement). The other 8 opened names are `videox` debug state (`dbg_urg_low`, `dbg_urg_high`,
   `dbg_ultlow`, `dbg_ulthigh`, `dbg_prehigh`, `_cmdq_insert_wait_frame_done_token_mira` in
   `mt6768/videox/debug.c`), `set_rdma_width_height` (`videox/disp_lowpower.c`) and
   `primary_display_is_decouple_mode` (`videox/primary_display.c`) - i.e. the panel-handover side of the
   cut. `ddp_ovl.c` is the same story at smaller scale: it compiles (with the platform
   `dramc/mt6768/mtk_dramc.h`, 195 ln, landed for it) and closes 6 names but opens 10, for a net +4.
2. **`common/rdma20/ddp_rdma.c` and `common/wdma20/ddp_wdma.c` must not be landed at all.** They look
   like the natural companion to the platform files, but `video/common/Makefile:70-78` descends into
   those two directories only for `CONFIG_MACH_MT6799` (and into `rdma10`/`wdma10` for
   MT6757/KIBOPLUS/MT6797/MT6795/MT8167), so mt6768's vendor build never compiled them. That is also why
   `DDP_REG_BASE_DISP_RDMA0`, which `ddp_rdma.c:25` returns, is defined nowhere in the whole vendor tree
   (grep over `drivers/` and `include/` finds only that use): it is MT6799 code sitting in a shared
   directory, in the same class as the `cmdq/v3/*.c` files this port carries as headers only. The
   mt6768 providers of `rdma_get_address`, `rdma_dump_reg`, `wdma_dump_reg` and friends are the platform
   `ddp_rdma_ex.c` / `ddp_wdma_ex.c`.
3. **`ddp_wdma_ex.c:19`'s `#include <ion_sec_heap.h>` needs the one-line comment-out, and the reason is
   measurable.** This port carries the ION *types* (`drivers/staging/android/mtk_ion/ion.h`, whose line 31
   is `#define ion_phys_addr_t unsigned long`) and not the ION driver, which is the boundary 0080 drew;
   the vendor header the file asks for lives under `mtk_ion/mtk/` and includes `ion_drv.h`, i.e. landing it
   means landing ION. In this file the include contributes nothing that `ion.h` does not: its only type use
   is the `ion_phys_addr_t sec_hdl = -1;` declaration at line 1260, and the only call that needs the
   header, `ion_hdl2sec_type()` at line 1262, is inside `#ifdef CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM`
   (`=y` at `even_defconfig:1977`, absent from this port's config of record). So the fix when RDMA/WDMA
   land is the pattern already at `ddp_drv.c:36` (`/* #include <linux/ion.h> */`) - one commented line,
   `diff`-verifiable against the vendor file, behaviour-preserving in this configuration, and it must be
   re-enabled together with an ION driver if `CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM` is ever set.

One smaller recorded non-issue from the same round: the vendor passes `ccflags-y +=
-DDEFAULT_MMP_ENABLE` when `CONFIG_MMPROFILE=y` (`dispsys/Makefile:109-111`;
`even_defconfig:1711-1712` sets both MMPROFILE symbols), and `ddp_mmp.c`'s `ddp_mmp_init()` body is
inside that define. 0092 lands the file without the define, because the port's dispsys Makefile carries
no `-D` flags at all since 0085's filtered generation and because the guarded body is one `DDPMSG`
plus `mmprofile_enable(1)` / `init_ddp_mmp_events()` / `mmprofile_start(1)`, whose first and third are
static-inline no-ops in the landed `mmp/mmprofile.h:212/216` (that header's `#else` branch of
`#ifdef CONFIG_MMPROFILE`, matching this config) and whose middle only registers event names through the
`mmprofile_register_event()` dummy at `:131`. If the port ever lands `drivers/misc/mediatek/mmp/` as a
driver rather than a header, the define and the real mmprofile behaviour come back together.""")

# ---------- 3. the plan: 11.17's queue is superseded, 11.18 is the round ----------
sub("report/display-bringup-plan.md",
"""Queue now: **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` + `ddp_wdma_ex.c` (each blocked by that one
header alone, per the header probe), then the DSI/panel handover names, which are a device question and not a
code question.""",
"""Queue then, as written at 0091: **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` + `ddp_wdma_ex.c` (each
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
the panel handover beyond that is still a device question.""")

# ---------- 4. decisions.json ----------
p = os.path.join(R, "report/decisions.json")
d = json.load(open(p))
assert len(d["decisions"]) == 157, "decisions.json is not at 157: %d" % len(d["decisions"])
d["decisions"].append({
 "id": 158,
 "date": "2026-09-06",
 "title": "0092 prices the queued engine files first, lands the one that subtracts open names instead of adding them, and records RDMA/WDMA as gated on a record-layer decision rather than on missing display code",
 "context": "157 published 0091 and named the next round as ddp_matrix_para.h + ddp_rdma_ex.c + ddp_wdma_ex.c, on the reasoning that each of those two files is blocked by that one header alone. The standing rule since 0089 is that a slice must not enlarge the tree's link gap, and this round that rule was applied before landing rather than after: the candidates were priced by replaying each landing against the 91-patch tree (tree 3483759c24eb..., dirty 0), building the WHOLE tree with the switch ON and -k so every gap is reported, and diffing ld's distinct open-name set against report/l2-open-names-at-0091.txt. RDMA/WDMA compiled clean and closed 10 names but opened 21, i.e. 62 -> 73. 13 of the 21 are the record lifecycle, and reading the vendor showed why they are not cheap: cmdqRecCreate/Destroy/Reset/Flush/FlushAsync/Wait/Poll/WriteSecure/WriteSecureMetaData/SetSecure/SecureEnableDAPC/SecureEnablePortSecurity/BackupUpdateSlot are 3-4 line trampolines in v3/cmdq_record.c:3808-4098 into the cmdq_task_*/cmdq_op_* session engine (per-subsys pools, gce_plat lock, mailbox submission) - the engine 0082 reverted. The other 8 are videox debug state, set_rdma_width_height and primary_display_is_decouple_mode, i.e. the panel side of the cut. ddp_ovl.c + the platform mtk_dramc.h is net +4; ddp_color.c + ddp_dither.c + ddp_gamma.c is net -7 with one open name (cmdqRecReadToDataRegister), which is a fourth adapter entry point plus the register-typed-operand rule 0091 declined; ddp_dump.c is already landed; ddp_ccorr.c does not exist; ddp_aal.c, ddp_pwm.c, videox/debug.c and videox/disp_lowpower.c each fail on one unlanded header. A second finding struck two files from the queue permanently: common/rdma20/ddp_rdma.c and common/wdma20/ddp_wdma.c are built only for CONFIG_MACH_MT6799 (video/common/Makefile:70-78) and reference DDP_REG_BASE_DISP_RDMA0, which is defined nowhere in the vendor tree - they are foreign-platform code in a shared directory, like the cmdq/v3 .c files this port carries as headers only.",
 "decision": "Land the file that subtracts: video/mt6768/dispsys/ddp_mmp.c (934 ln, verbatim, sha256 f0a113c93138) plus one obj-$(CONFIG_MTK_DISP_BRINGUP) line, and nothing else - no adapter growth, no Kconfig symbol, no DT change, no edit to any landed file. Chosen because it is the largest measured reduction of the open-name set available inside the existing contract: 62 -> 57, five names closed (ddp_mmp_init, ddp_mmp_get_events, ddp_mmp_ovl_layer, ddp_mmp_rdma_layer, ddp_mmp_wdma_layer), zero opened, 6 new globals with 0 collisions, 0 diagnostics attributed to the file, object 85,592 B rebuilt from scratch. It is also a real dependency rather than a convenient one: the five names are referenced by ddp_drv.c and display_recorder.c through SUPPORT_MMPROFILE (videox/disp_drv_platform.h:37, landed verbatim), and the ovl/rdma/wdma engine files priced above call ddp_mmp_* themselves, so landing it now removes one term from each of their future deltas. RDMA/WDMA are recorded as deferred pending a decision about the record adapter, not as unfinished code - KNOWN-ISSUES.md 15 carries the three measurements that show it, including the ion_sec_heap.h analysis (the include is redundant in this configuration: its only type use is covered by mtk_ion/ion.h:31 and its only call is inside #ifdef CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM, absent from this config), so the fix when they land is the one-line comment-out already used at ddp_drv.c:36 and not a new header. The vendor's -DDEFAULT_MMP_ENABLE is deliberately not carried, with the reason measured: the guarded body is one DDPMSG plus three static-inline dummies in mmp/mmprofile.h.",
 "still_open_on_purpose": [
   "RDMA/WDMA (10 names) and the colour trio (8 names) are not landed, because both need the record adapter to grow - 13 lifecycle entries in the first case, cmdqRecReadToDataRegister plus the register-typed-operand rule in the second - and growing it into a session model is the contract 0091 and 0082 drew. Priced, with vendor line numbers, in report/l2-slice-0092-before-after.md and KNOWN-ISSUES.md 15",
   "57 open names remain before the display path links, and none of them changes the maturity level: nothing landed can create a record, nothing has been flashed, no frame has been drawn",
   "CONFIG_MMPROFILE is unset here, so the port runs on mmp/mmprofile.h's dummy branch; landing the mmp driver later reopens both that and the DEFAULT_MMP_ENABLE flag, deliberately not carried now"
 ],
 "consequences": [
   "the tree at be0ef70ed / b5d70973e7f154d47f556bd7abac4aeca4d4176c is published as the 92nd patch, and 0001-0091 still reproduces 3483759c24eb..., so the base did not move (both re-derived by bin/publish.py in the same run)",
   "gate l2_disp_record_publish50 ran 66 s on a warm tree, and every number in the prediction file came true, including the object size 85,592 B and the 160-reference-line count that the prediction could not fix; the gate also compares the landed file's sha256 against the vendor's, which is the first round where 'verbatim' is a printed check rather than a promise",
   "'price the queue before taking from it' is now the standing shape of a round: probe-slice.sh in tools/portwork takes a file list and prints closes/opens/net plus the object diagnostics, and report/l2-slice-0092-before-after.md is the template for writing those numbers down before landing",
   "the next slice is again a dependency-order question rather than a maturity question, and the decision that unblocks the two biggest candidates is one sentence: does the record adapter grow a session/lifecycle layer, or do the engines that need it wait until the panel handover forces the question"
 ],
 "artifacts": [
   "series commit be0ef70ed, tree b5d70973e7f154d47f556bd7abac4aeca4d4176c",
   "drivers/misc/mediatek/video/mt6768/dispsys/ddp_mmp.c (934 ln, f0a113c93138) + one obj- line in that directory's Makefile (0cfe748be2ca)",
   "upstream-port/report/l2-slice-0092-before-after.md (predictions and gate measurements side by side, plus the priced alternatives)",
   "upstream-port/report/l2-open-names-at-0092.txt (57 names, the before-side for the next round)",
   "upstream-port/tools/portwork/slice0092-gate.sh (sha256 c2053c7ee769) plus the pricing rig upstream-port/tools/portwork/{probe-slice.sh,probe-0092b.sh}, log portwork/logs/slice0092-gate-20260906T073711Z.log",
   "portwork/probe-slice.sh + portwork/probe-0092b.sh and their logs (probe-0092b.log, probe-ddp_mmp_c.log, probe-ddp_ovl_c.log, probe-ddp_color_c_ddp_dither_c_ddp_gamma_c.log) - the pricing rig, outside the repo by design"
 ]})
jsave(p, d)
print("decisions: %d" % len(d["decisions"]))

# ---------- 5. build.json: the gate record ----------
p = os.path.join(R, "report/build.json")
b = json.load(open(p))
assert "l2_disp_record_publish50" not in b["gates"]
b["gates"]["l2_disp_record_publish50"] = {
 "when": "2026-09-06, on the tree that became patch 0092 (video/mt6768/dispsys/ddp_mmp.c landed verbatim), immediately followed by the publish",
 "command": "bash /home/user/portwork/slice0092-gate.sh; log portwork/logs/slice0092-gate-20260906T073711Z.log; then bin/publish.py (count 1) for the .eml and MANIFEST",
 "tree": "series commit be0ef70ed, HEAD^{tree} b5d70973e7f154d47f556bd7abac4aeca4d4176c, landing tree clean. git am of 0001-0092 reproduces that tree and 0001-0091 reproduces 3483759c24eb022373a5290523933b61bbd7ac62, so publishing this slice did not move the 0091 base",
 "numbers": {
  "elapsed_s": 66,
  "why_so_fast": "the tree was warm from the pricing probes, and the gate still deletes what its claim is about: ddp_mmp.o is removed and rebuilt before its size is read, and all display objects are deleted before the OFF link, which then asserts the 'LD vmlinux' marker rather than trusting a zero error count",
  "verbatim_check": "sha256 of the landed ddp_mmp.c equals the vendor's: f0a113c93138, 934 lines on both sides - printed by the gate, because 'verbatim' should be an observable rather than an adjective",
  "off_link": "make ARCH=arm64 -j2 vmlinux Image.gz-dtb rc=0, LD vmlinux x2, 0 error:, 0 undefined reference, vmlinux 168,340,520 B (unchanged since 0089), System.map 6,911,826 B, Image 34,165,248 B, Image.gz 11,734,752 B, Image.gz-dtb 12,228,269 B, appended DTB payload 493,517 B, mt6768.dtb sha256 prefix 34a7e6b536a3 - the last two unchanged since 0081 because no DT file is touched. Image.gz moved +5 B against 0091 with vmlinux unchanged in size, which is the recorded gzip/git-describe behaviour and why image sha256 is not a cross-round check",
  "off_exclusion": "ddp_mmp.o absent with CONFIG_MTK_DISP_BRINGUP off, 0 gated display objects, and nm finds no ddp_mmp_init / ddp_mmp_get_events / ddp_path_init / cmdqRecWrite / display_bias_regulator_init in that vmlinux",
  "on_object": "single-object make rc=0, ddp_mmp.o 85,592 B exactly as predicted, 0 error: lines, 0 diagnostics attributed to ddp_mmp.c or ddp_mmp.h; the 7 warnings are the landed v3 headers' own (cmdq_record.h:804/833/845/889, cmdq_helper_ext.h:881/988) and are printed with file and line so the count is attributable",
  "on_object_symbols": "6 T symbols defined (the 5 MMP names plus init_ddp_mmp_events); 7 undefined: _printk, __stack_chk_fail, disp_mva_map_kernel, disp_mva_unmap_kernel, m4u_mva_map_kernel, m4u_mva_unmap_kernel, dprec_logger_pr - the last five provided by ddp_m4u.c and display_recorder.c, both landed in 0085, which is why the slice opens nothing",
  "on_link": "make ARCH=arm64 -j2 -k vmlinux rc=2 as intended, 0 error:, 160 ld reference lines, 57 distinct open names (0089 78, 0090 65, 0091 62). The delta against report/l2-open-names-at-0091.txt is computed both ways: exactly the 5 claimed names closed, 0 opened. Each claimed name is open:0 in the link and defined:1 tree-wide by nm census. Must-stay-open held: primary_display_is_video_mode, rdma_dump_reg, ovl_dump_reg, ddp_driver_ovl, disp_pwm_set_backlight all open:1; 0089's 2 bias names, 0090's 15 path names and 0091's 3 record names all 0",
  "census": "6 new globals from ddp_mmp.o, 0 collisions against every other .o in drivers/kernel/lib/mm/fs/net",
  "harnesses": "tests/mtk_disp_record_host_check.c 55 cases / 0 mismatches and tests/mtk_disp_slot_host_check.c 37 / 0, both built with 0 warnings - unchanged because the record adapter is untouched, which the log also proves by hashing the adapter's two files to 0091's values (d09f5a729d99, 2db3ccded27d)",
  "restore": "config back to the board's sha256 prefix 099cdd6421b6, landing tree dirty 0 after the gate, display objects deleted so the next build is honest; open-name set kept at portwork/logs/names-0092.txt and copied to report/l2-open-names-at-0092.txt (57 lines)",
  "pricing_that_shaped_the_round": "this is the first round where the queue was measured before being followed: ddp_rdma_ex.c + ddp_wdma_ex.c + ddp_matrix_para.h compile clean but are net +11 (13 of the 21 opened names are v3 cmdq_task_* record-lifecycle trampolines), ddp_ovl.c + mtk_dramc.h is net +4, ddp_color.c + ddp_dither.c + ddp_gamma.c is net -7 with one open name (cmdqRecReadToDataRegister), common/{rdma20,wdma20}/*.c are MT6799-only in the vendor build and struck from the queue. Logs probe-0092b.log, probe-ddp_ovl_c.log, probe-ddp_color_c_ddp_dither_c_ddp_gamma_c.log; write-up report/l2-slice-0092-before-after.md"
 },
 "verdict": "PASS on every predicted number, including the two the prediction could not fix (160 reference lines, the +5 B Image.gz movement) and the object size to the byte. The patch closes 5 open names and opens 0, does not touch the record adapter, the mailbox ABI, the device tree or any landed file's content, and the gate proves verbatim-ness by hashing against the vendor source."}
jsave(p, b)
print("gates: %d" % len(b["gates"]))

# ---------- 6. MANIFEST header ----------
sub("patch-series/MANIFEST.txt",
"# Zenium 4.19.325 -> v5.15.220 port series (91 commits + cover letter)",
"# Zenium 4.19.325 -> v5.15.220 port series (92 commits + cover letter)")
sub("patch-series/MANIFEST.txt",
"`ls patch-series/*.eml | grep -v cover | wc -l` must be 91 -",
"`ls patch-series/*.eml | grep -v cover | wc -l` must be 92 -")
sub("patch-series/MANIFEST.txt",
"""# verify:   git rev-parse HEAD^{tree}  ==  3483759c24eb022373a5290523933b61bbd7ac62  (0091 tip)
#           published prefixes, re-derived by the same command in the 0091 round, both exact""",
"""# verify:   git rev-parse HEAD^{tree}  ==  b5d70973e7f154d47f556bd7abac4aeca4d4176c  (0092 tip)
#           published prefixes, re-derived by the same command in the 0092 round, both exact:
#             0001-0091 -> 3483759c24eb022373a5290523933b61bbd7ac62   (0092 round)""")
sub("patch-series/MANIFEST.txt",
"""#           the current build gate for the display slice is in report/build.json (gate
#            l2_disp_record_publish49, i.e. the 0091 tip; 0090's is l2_path_layer_publish48,""",
"""#           the current build gate for the display slice is in report/build.json (gate
#            l2_disp_record_publish50, i.e. the 0092 tip; 0091's is l2_disp_record_publish49,
#            0090's is l2_path_layer_publish48,""")
sub("patch-series/MANIFEST.txt",
"""#            report/display-bringup-plan.md 11.17 (11.16 is the 0090 round, 11.11 the 0089 round);""",
"""#            report/display-bringup-plan.md 11.18 (11.17 is the 0091 round, 11.16 the 0090 round);""")

# ---------- 7. MATURITY ----------
sub("MATURITY.md",
"**91 patches** (`patch-series/0000-cover-letter.eml` + `0001..0091`), base `v5.15.220`, tree **`3483759c24eb022373a5290523933b61bbd7ac62`**. Reproducibility gate re-run on this state twice: by `bin/publish.py --verify-only` (`git worktree add --detach ref/linux v5.15.220` + `git am` of the 4-digit glob -> rc 0, tree byte-identical, and the 0001-0088 and 0001-0087 prefixes reproduce `1a7cf42b066c…` and `deba5bd29ec6…`), and again by accident",
"**92 patches** (`patch-series/0000-cover-letter.eml` + `0001..0092`), base `v5.15.220`, tree **`b5d70973e7f154d47f556bd7abac4aeca4d4176c`**. Reproducibility gate re-run on this state at publish time by `bin/publish.py` itself (`git am` of the 4-digit glob -> rc 0, tree byte-identical, and the 0001-0091 prefix reproduces `3483759c24eb…` exactly), and twice before that by accident")
sub("MATURITY.md",
"""**DONE for the tree any user builds** - at the 0091 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,265 B, the device's own `mt6768.dtb` 122,474 B (sha `34a7e6b536a3…`), 0 `error:` lines and 0 undefined references. Two honest qualifiers: the display objects behind `CONFIG_MTK_DISP_BRINGUP` deliberately do **not** link (211 deferred reference lines / 62 distinct names, §Round 0083-0091), and the 529-DTB / 840-`.ko` figures are `build-37`'s - modules and the DTB sweep have not been re-measured since 0081 | `report/build-evidence.md`, `report/build.json` (gate `l2_disp_record_publish49`), `report/subsystem-audit.md` |""",
"""**DONE for the tree any user builds** - at the 0092 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,269 B, the device's own `mt6768.dtb` 122,474 B (sha `34a7e6b536a3…`), 0 `error:` lines and 0 undefined references. Two honest qualifiers: the display objects behind `CONFIG_MTK_DISP_BRINGUP` deliberately do **not** link (160 deferred reference lines / 57 distinct names, §Round 0082-0092), and the 529-DTB / 840-`.ko` figures are `build-37`'s - modules and the DTB sweep have not been re-measured since 0081 | `report/build-evidence.md`, `report/build.json` (gate `l2_disp_record_publish50`), `report/subsystem-audit.md` |""")

# ---------- 8. FEATURE-PARITY ----------
sub("FEATURE-PARITY.md",
"## Round 0082-0091: display core, gate, slot pool, panel bias, path layer, record adapter (supersedes the rows above where they conflict)",
"## Round 0082-0092: display core, gate, slot pool, panel bias, path layer, record adapter, MMP layer (supersedes the rows above where they conflict)")
sub("FEATURE-PARITY.md",
"""| dispsys core | `video/mt6768/dispsys/`, 21 files | **14 objects + `disp_helper.c` landed under `CONFIG_MTK_DISP_BRINGUP` (default n)**; the seven that remain need the record API (`ddp_ovl.c`: 35 `cmdqRec*` references incl. the secure trio 0083 never provided) or the unported `ddp_mmp`/`disp_dts_gpio` chains | M |""",
"""| dispsys core | `video/mt6768/dispsys/`, 21 files | **15 objects + `disp_helper.c` landed under `CONFIG_MTK_DISP_BRINGUP` (default n)**, `ddp_mmp.c` included verbatim in 0092 (934 ln, closes its 5 names, opens 0); what remains needs the record API beyond what 0091 carries (`ddp_ovl.c`: 35 `cmdqRec*` references incl. the secure trio 0083 never provided; measured net +4 with `mtk_dramc.h` landed) or an unported chain (`disp_dts_gpio.h` for `ddp_pwm.c`, `ion_drv.h` for `videox/disp_lowpower.c`) | M |
| MMP layer (layer protection / mmprofile events) | `video/mt6768/dispsys/ddp_mmp.c` (934 ln) + `mmp/mmprofile.{h,c}`, built by the vendor when `CONFIG_MMPROFILE=y` (`even_defconfig:1712`) | **the display half landed verbatim (0092)** - one file, one `obj-$(CONFIG_MTK_DISP_BRINGUP)` line, 5 names closed, 0 opened; it compiles against `mmp/mmprofile.h`'s `#else`-of-`CONFIG_MMPROFILE` static-inline dummies (`:131/:212/:216`), and the vendor's `-DDEFAULT_MMP_ENABLE` is recorded as not carried because with it the guarded body is one `DDPMSG` plus three of those same dummies. `ddp_mmp.c`'s own unmet calls sit in the `CONFIG_MTK_HDMI_SUPPORT` (`:205`) and `CONFIG_MTK_M4U` (`:655`) blocks | S |""")
sub("FEATURE-PARITY.md",
"""| display path/scenario layer | `video/mt6768/dispsys/ddp_path.c` (987 ln), reached from `ddp_manager.c` and `ddp_ddp.c` | **landed verbatim (0090)**, `cmp`-identical to the vendor file, one `obj-$(CONFIG_MTK_DISP_BRINGUP)` line, no Kconfig symbol of its own; closes 15 link symbols and opens the three record names | S |""",
"""| display path/scenario layer | `video/mt6768/dispsys/ddp_path.c` (987 ln), reached from `ddp_manager.c` and `ddp_ddp.c` | **landed verbatim (0090)**, `cmp`-identical to the vendor file, one `obj-$(CONFIG_MTK_DISP_BRINGUP)` line, no Kconfig symbol of its own; closes 15 link symbols and opens the three record names | S |
| engine files priced but not landed (rdma/wdma/ovl/colour) | `ddp_rdma_ex.c` (1,649 ln), `ddp_wdma_ex.c` (1,330 ln), `ddp_matrix_para.h` (131 ln), `ddp_ovl.c` (4,527 ln), `common/{color20,corr10}` trio (6,082 ln) | **all five sets compile in this tree** (wdma with one documented `#include <ion_sec_heap.h>` comment-out) and were priced by whole-tree ON link rather than guessed: -7 for the colour trio, +4 for ovl, +11 for rdma/wdma - the two positive ones are gated on the record adapter, the colour trio on a fourth entry point plus the register-typed-operand rule 0091 declined. `common/{rdma20,wdma20}/*.c` are MT6799-only in the vendor's build and permanently out | - (measurement: report/l2-slice-0092-before-after.md) |""")

# ---------- 9. cover letter ----------
sub("patch-series/0000-cover-letter.eml",
"""that answers the three names it opens (0091) - a narrow vendor-shaped delegation with its instruction
encoding compared word by word against the 4.19 source in `tests/mtk_disp_record_host_check.c`.""",
"""that answers the three names it opens (0091) - a narrow vendor-shaped delegation with its instruction
encoding compared word by word against the 4.19 source in `tests/mtk_disp_record_host_check.c` - and the
MMP layer the display code has been calling since 0085, `ddp_mmp.c` landed verbatim (0092), chosen over the
rdma/wdma pair that was queued because pricing both showed the pair opens 21 names to close 10.""")
sub("patch-series/0000-cover-letter.eml",
"""    Published prefix trees are re-derived every round, because adding a patch must not move them: the 0091
    round measured 0001-0090 -> 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed and 0001-0089 ->""",
"""    Published prefix trees are re-derived every round, because adding a patch must not move them: the 0092
    round measured 0001-0091 -> 3483759c24eb022373a5290523933b61bbd7ac62, and the 0091 round measured
    0001-0090 -> 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed and 0001-0089 ->""")
sub("patch-series/0000-cover-letter.eml",
"""    mailbox header and the sha256 pins of the one transcription it relies on.""",
"""    mailbox header and the sha256 pins of the one transcription it relies on.
  - gate for 0092 (`slice0092-gate.sh`, log slice0092-gate-20260906T073711Z.log, 66 s) is the round where the
    queue was measured before being followed: ddp_mmp.c landed, switch OFF image unchanged in size (payload
    still 493,517 B, mt6768.dtb 34a7e6b536a3) with no ddp_mmp symbol in vmlinux, switch ON closes exactly the
    5 names it claims and opens 0 (62 -> 57 distinct names, 211 -> 160 reference lines), object 85,592 B
    rebuilt from scratch with 0 diagnostics attributed to the file, 6 new globals and 0 collisions, and
    verbatim-ness printed as a sha256 match against the vendor file. The record adapter is untouched, which
    the log also proves by hashing its two files to 0091's values.""")
print("rec0092 done")
