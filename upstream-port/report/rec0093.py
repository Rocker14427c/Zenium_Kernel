#!/usr/bin/env python3
"""rec0093.py - the records for patch 0093 (colour trio + one record entry point, 57 -> 49 open names).

Same discipline as rec0090.py / rec0091.py / rec0092.py: every edit asserts its anchor by exact count, both
JSON files round-trip through the repo's own serialization, and no number is written that a gate log did not
print. The two logs this round draws on are in the repo (report/logs/) precisely because the volatile
workspace has been wiped twice: slice0092-gate-20260906T111233Z.log (the cold re-verification of 0092,
876 s) and slice0093-gate-20260906T113559Z.log (this slice, 69 s), plus sweep-0093.log.
"""
import json, os, sys

R = "/home/user/Zenium_Kernel/upstream-port"
GATE = "slice0093-gate-20260906T113559Z.log"
GATE0 = "slice0093-gate-20260906T113357Z.log"
GATE92RV = "slice0092-gate-20260906T111233Z.log"


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
append("report/l2-slice-0093-before-after.md", """
## Measured on the landed tree - gate `l2_disp_record_publish51`

`bash /home/user/portwork/slice0093-gate.sh`, log `portwork/logs/%s` (mirrored to
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

* The first run (`%s`, 73 s) printed `in-trio:0`, `defined:0` for the new entry point and "new global
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
""" % (GATE, GATE0))

# ---------- 2. KNOWN-ISSUES: a new numbered entry ----------
sub("KNOWN-ISSUES.md",
"""One smaller recorded non-issue from the same round: the vendor passes `ccflags-y +=
-DDEFAULT_MMP_ENABLE`""",
"""## 16. The display queue is now a header problem, not a file problem (measured at 0093)

0093 landed the colour trio (`common/color20/ddp_color.c`, `common/corr10/ddp_dither.c`,
`common/corr10/ddp_gamma.c`, verbatim, 19 gated objects in `video/mt6768/dispsys/`) with one new record
entry point, and took the open-name count from 57 to 49 with nothing opened. Before choosing it, the
eleven candidate files still standing were priced one at a time on that tree by
`tools/portwork/sweep-0093.sh` (log `report/logs/sweep-0093.log`), each row an apply / whole-tree ON link
with `-k` / restore against `report/l2-open-names-at-0092.txt`. Three findings come out of that sweep, and
they are the reason later rounds should not re-run it blindly.

1. **Ten of eleven candidates never reach a link, and five headers are why.** `ddp_dsi.c:35` and
   `ddp_pwm.c:31` stop at `disp_dts_gpio.h`; `ddp_disp_bdg.c:12` at `ddp_reg_disp_bdg.h`; `ddp_aal.c:23` at
   `mtk_leds_drv.h`; `videox/debug.c:34` at `mtk_disp_mgr.h`; `disp_recovery.c:20`, `disp_lowpower.c:21`,
   `mtkfb.c:31` and `primary_display.c:24` at `ion_drv.h` / `mtk_ion.h`, which is a policy refusal rather
   than a missing file (see 15.3); `fbconfig_kdebug.c` fails on two implicit declarations. The rig prints
   `distinct open names after: 0` with its own "the link never ran, ignore the deltas" warning for those
   rows, which is why the sweep is reported as *blocked*, not as -57.
2. **The one candidate that does link costs more than it pays.** `videox/disp_cust.c` compiles clean
   (object 57,056 B) and is the only candidate in the queue that touches the panel group at all - it closes
   `set_lcm` and `read_lcm` - but it opens seven names (`DSI_dcs_read_lcm_reg_v4`,
   `DSI_dcs_set_lcm_reg_v4`, `_is_power_on_status`, `_primary_path_switch_dst_lock`,
   `_primary_path_switch_dst_unlock`, `primary_display_manual_lock`, `primary_display_manual_unlock`), so
   the ON link would have gone 57 -> 62. It is refused on that number, and the seven names are the panel
   handover's, not this file's.
3. **`disp_dts_gpio.h` is the one that should stay closed.** Two files want it, and it is the header that
   reads pinmux/GPIO configuration out of the device tree. Landing it means either landing DT fragments
   this device's vendor tree does not have or inventing them, which is the boundary this port has held since
   0087 (no DT invented, no binding fabricated). So the "cheap" unblocking of `ddp_dsi.c` and `ddp_pwm.c`
   is not cheap; it is the same device question the panel handover is.

The third thing this round records is about the rig, not the vendor: `nm` does not read an object file from
a pipe. `cat foo.o | nm --defined-only -g` prints nothing (measured: 0 symbols, against 4 for `nm foo.o`),
so every census line written that way - one gate script and `probe-slice.sh`'s "globals defined by the new
objects", which had printed 0 for every candidate ever run - was vacuous. Both now pass the objects as
arguments, and 0093's census is the first measurement of that column: the colour trio defines 32 global
symbols, 8 of which are names this tree had open, with 0 collisions against the rest of the tree.

One smaller recorded non-issue from the same round: the vendor passes `ccflags-y +=
-DDEFAULT_MMP_ENABLE`""", 1)

# ---------- 3. the plan: 11.18's queue is superseded, 11.19 is the round ----------
append("report/display-bringup-plan.md", """
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

Gate `l2_disp_record_publish51` (`slice0093-gate.sh`, `%s`, 69 s) measured the result: **57 -> 49 distinct
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
`slice0092-gate.sh` was re-run cold on that recovered tree (log `%s`, 876 s) and reproduced every claim of
0092's published gate - 57 names, CLOSED 5, OPENED 0, object 85,592 B, 6 new globals, 0 collisions, both
harnesses, the DTB sha and the 493,517 B payload - with the only differences being the `git describe`
width in the two gzipped sizes. That is gate `l2_disp_record_reverify51`, and it is recorded as a gate
because "the recovery works" is otherwise the kind of sentence a port carries untested until the day it
needs it. Every log this round depends on is now mirrored into `upstream-port/report/logs/`, and both the
pricing rig and the durable driver (`run-0093.sh`, resumable at each step) live in `tools/portwork/`.
""" % (GATE, GATE92RV))

# ---------- 4. decisions.json ----------
p = os.path.join(R, "report/decisions.json")
d = json.load(open(p))
assert d["decisions"][-1]["id"] == 158, "decisions.json no longer ends at 158"
d["decisions"].append({
    "id": 159,
    "date": "2026-09-06",
    "title": ("0093 lands the colour trio with the one record read entry point it needs, refuses the "
              "vendor's wpr read branch instead of inventing an encoder, and reports the rest of the "
              "display queue as a header problem rather than a file problem"),
    "context": ("158 published 0092 with the queue priced: the colour trio was measured at net -7 "
                "(closes 8, opens cmdqRecReadToDataRegister), ddp_ovl.c at +4, the rdma/wdma set at +11, "
                "and the remaining candidate files were still only screened, not priced. The standing rule "
                "since 0089 is that a slice must not enlarge the tree's link gap; the question this round "
                "had to answer first was architectural rather than cosmetic, because the trio's single "
                "unmet symbol sits in the one layer - CMDQ record - that 0082 reverted and 0091 deliberately "
                "kept narrow. Two ways to answer it: grow the adapter into a session/GPR engine so the "
                "vendor's whole read path exists, or add exactly one entry point and refuse the branch that "
                "needs machinery 5.15 does not expose. The user's standing instruction for this round was to "
                "finish pricing and design analysis, then choose the smallest evidence-backed architecture "
                "and land one verified slice without waiting, stopping only if the evidence left two "
                "materially different choices."),
    "decision": ("Take the second option, and land it as one slice: (1) ddp_color.c (4,099 ln), "
                 "ddp_dither.c (409 ln) and ddp_gamma.c (1,574 ln) copied verbatim and flat into "
                 "video/mt6768/dispsys/ behind three obj-$(CONFIG_MTK_DISP_BRINGUP) lines, no header landed; "
                 "(2) exactly one new entry point, cmdqRecReadToDataRegister(), in "
                 "drivers/soc/mediatek/mtk-cmdq-disp-record.c, as a resolve-then-call delegation to mainline's "
                 "cmdq_pkt_read_s(), with the at-or-above-CMDQ_DATA_REG_JPEG_DST case returning -EOPNOTSUPP "
                 "behind pr_err_once(); (3) no include/ change, no DT change, no new Kconfig symbol, no "
                 "mailbox ABI change; (4) tests/mtk_disp_record_host_check.c extended to 85 cases so the "
                 "delegation is a measurement (12 vendor-vs-mainline read_s words, 9 refusals for addresses "
                 "no gce row covers, 4 source-shape pins) rather than a reading of a header. The rest of the "
                 "queue was priced in the same round and, where it could not be priced, the reason was "
                 "recorded: of eleven candidates ten die on one #include before the link runs, and the one "
                 "that links (disp_cust.c) is net +5, so it is rejected."),
    "consequences": ("The switch-ON whole-tree link goes 57 -> 49 distinct open names (160 -> 140 reference "
                     "lines), closing exactly ddp_driver_color/dither/gamma/ccorr, corr_dbg_en, "
                     "disp_ccorr_on_end_of_frame, disp_color_dbg_log_level and disp_color_ioctl - all eight "
                     "already referenced by landed code in ddp_info.c, ddp_irq.c, ddp_debug.c and "
                     "ddp_manager.c - and opening nothing; the three objects rebuild at 272,968 / 104,728 / "
                     "139,560 B with 0 error: lines, 0 diagnostics naming them, 32 new globals and 0 "
                     "collisions; the switch-OFF image is unchanged in every number that matters. The price is "
                     "a documented gap: the refused wpr read branch means a future callsite wanting "
                     "CMDQ_DATA_REG_JPEG_DST or the debug registers needs a decision, not a patch, and "
                     "nothing in the tree can create a record yet, so the colour layer is link-required and "
                     "unreachable at runtime. Method consequences were larger than the slice's: nm cannot "
                     "read objects from a pipe, so every census line written that way in every gate and probe "
                     "script was vacuously 0 and is fixed; two set comparisons in the gate fired on correct "
                     "states and now compare sorted sets; and every log a claim rests on is mirrored into "
                     "upstream-port/report/logs/ because the volatile workspace has now been wiped twice "
                     "mid-round, once with the fix to this rig uncommitted in it."),
    "alternatives": ("(a) Grow the adapter into the vendor's session model (cmdqRecCreate/Destroy/Reset/Flush "
                     "and the GPR mutex tokens) so the read path is complete: measured as the reason rdma/wdma "
                     "were rejected in 158, and it is the layer 0082 reverted - refused. (b) Land the trio "
                     "without the entry point (net -7, one new open name): refused by the rule since 0089, and "
                     "pointless once (c) costs one function. (c) Do disp_cust.c or the DSI provider first, "
                     "since disp_cust closes set_lcm/read_lcm: measured +5, refused. (d) Land the five missing "
                     "headers to unblock ten files at once: disp_dts_gpio.h is the device-tree pin reader, "
                     "mtk_disp_mgr.h/ddp_reg_disp_bdg.h/mtk_leds_drv.h belong to subsystems this port has not "
                     "taken (display manager, bdg registers, LED driver) and the ion_*.h family is a policy "
                     "refusal - refused, and recorded in KNOWN-ISSUES 16 as the actual next decision. (e) Land "
                     "nothing until the design doc had been reviewed: superseded by the user's instruction "
                     "this round to proceed on the smallest evidence-backed choice."),
    "verification": ("gate l2_disp_record_publish51 (report/logs/slice0093-gate-20260906T113559Z.log, 69 s, "
                     "every expectation met including the 8-name closed-set identity and the 8/8 census) plus "
                     "the discarded first run (%s, 73 s) whose three vacuous lines are what led to the nm fix; "
                     "bin/publish.py re-derived both directions (0001-0093 -> "
                     "899e689602bca34b67cedf293bb7df337f5bd609, 0001-0092 -> "
                     "b5d70973e7f154d47f556bd7abac4aeca4d4176c, 93 .eml files); the record harness reads 85 "
                     "cases / 0 mismatches and the slot harness 37 / 0; and the same round re-verified 0092's "
                     "gate cold on a tree rebuilt from the .eml set alone (l2_disp_record_reverify51, 876 s) "
                     "so that the recovery path is a tested path." % GATE0),
})
jsave(p, d)

# ---------- 5. build.json: the gate record, and the re-verification of 0092 ----------
p = os.path.join(R, "report/build.json")
b = json.load(open(p))
assert "l2_disp_record_publish50" in b["gates"], "0092's gate missing from build.json"
b["gates"]["l2_disp_record_reverify51"] = {
    "when": "2026-09-06, re-running patch 0092's gate on a workspace rebuilt from the published .eml files after the second sandbox reset of this round",
    "command": "bash /home/user/portwork/restore.sh && bash /home/user/portwork/build0.sh; then bash /home/user/portwork/slice0092-gate.sh (driven by tools/portwork/run-0093.sh, which resumes at the step whose artefact is missing)",
    "tree": "series tree b5d70973e7f154d47f556bd7abac4aeca4d4176c reproduced exactly; dirty 0",
    "result": ("cold, 876 s, every published claim of 0092 reproduced: ddp_mmp.c sha f0a113c93138 with 934 "
               "lines on both sides, 16 gated obj- lines, switch-OFF link clean (LD vmlinux 2, 0 error:, 0 "
               "undefined, 0 gated display objects, no ddp_mmp/ddp_path/cmdqRecWrite/bias symbol in vmlinux), "
               "payload 493,517 B, mt6768.dtb 34a7e6b536a3, object 85,592 B matching its published size, "
               "switch ON 57 distinct names with CLOSED 5 / OPENED 0, 0 collisions, record harness 55 cases / "
               "0 mismatches, slot harness 37 / 0, config back to 099cdd6421b6, dirty 0"),
    "difference_from_original": ("Image.gz 11,734,750 B and Image.gz-dtb 12,228,267 B against 11,734,752 / "
                                "12,228,269 in the published gate, with vmlinux, System.map and the "
                                "uncompressed Image identical in size - the recovered tree is a replay, so its "
                                "git describe string is one commit-hash width different. This is the recorded "
                                "gzip/`git describe` behaviour and the reason image sha256 is not a cross-round "
                                "check while sizes and the appended payload are."),
    "log": "report/logs/slice0092-gate-20260906T111233Z.log",
}
b["gates"]["l2_disp_record_publish51"] = {
    "when": "2026-09-06, on the tree that became patch 0093 (the colour trio ddp_color.c/ddp_dither.c/ddp_gamma.c landed verbatim plus cmdqRecReadToDataRegister() in the record adapter), immediately followed by the publish",
    "command": "bash /home/user/portwork/land0093.sh; git commit; bash /home/user/portwork/slice0093-gate.sh (twice - the first run exposed vacuous nm census lines in the gate itself); then bin/publish.py (count 1) for the .eml and MANIFEST block",
    "tree": "series commit 0365f7ba4, HEAD^{tree} 899e689602bca34b67cedf293bb7df337f5bd609, landing tree clean",
    "result": ("switch ON: 49 distinct undefined names from 140 reference lines (was 57/160 at 0092; 78 at "
               "0089, 65 at 0090, 62 at 0091), CLOSED is exactly the eight predicted names "
               "(ddp_driver_ccorr/color/dither/gamma, corr_dbg_en, disp_ccorr_on_end_of_frame, "
               "disp_color_dbg_log_level, disp_color_ioctl) each open:0 / defined-tree-wide:1 / in-trio:1, "
               "OPENED 0, and cmdqRecReadToDataRegister open:0 / defined:1 from the adapter object; single-"
               "object rebuild of all four objects: 0 error:, 29 warnings all from the landed v3 headers plus "
               "one from mtk-cmdq-mailbox.h:91, 0 diagnostics naming the landed files, sizes 272,968 / "
               "104,728 / 139,560 B (matching the pricing probe exactly) and adapter 105,000 B; census 32 new "
               "global symbols, 8 of 8 predicted names present, 0 collisions; switch OFF unchanged: vmlinux "
               "168,340,520 B, System.map 6,911,826 B, Image 34,165,248 B, Image.gz-dtb 12,228,266 B, payload "
               "493,517 B, mt6768.dtb 34a7e6b536a3, trio and record objects absent, none of 11 probed symbols "
               "in vmlinux; harnesses record 85 cases / 0 mismatches (12 read_s words, 9 refusal cases) and "
               "slot 37 / 0, both with 0 build warnings; verbatim-ness by sha256 against the vendor files "
               "(b81b1f10ff22, e2f9ffffc06b, d1efbeec6173); gate 69 s warm, config restored to 099cdd6421b6, "
               "dirty 0, open-name set written to report/l2-open-names-at-0093.txt"),
    "artifacts": "portwork/artifact-0093-gate-Image.gz-dtb (sha256 prefix 6d3f94eb207d), gate + sweep logs in report/logs/",
    "log": "report/logs/slice0093-gate-20260906T113559Z.log",
}
jsave(p, b)
print("rec0093.py done: before/after, KNOWN-ISSUES 16, plan 11.19, decision 159, two gates")
