#!/usr/bin/env python3
"""rec0090.py - records for patch 0090 (ddp_path.c) landing, gating and publishing.

Every edit asserts its anchor: a replace that would be a no-op aborts the run, because a
silently skipped record edit is how a stale "applied=81" claim once reached a report here.
JSON is written back with the repo's serialization (indent=1 + trailing newline) and the
re-read must be byte-identical to what was dumped, or the file's shape was guessed.
"""
import json, os, sys

R = "/home/user/Zenium_Kernel/upstream-port"
def sub(path, old, new, count=1):
    p = os.path.join(R, path)
    s = open(p).read()
    n = s.count(old)
    if n != count:
        sys.exit("ANCHOR %s: expected %d occurrence(s), found %d in %s" % (repr(old[:48]), count, n, path))
    open(p, "w").write(s.replace(old, new, count))
    print("edited %s" % path)

def jload(p):
    raw = open(p).read()
    return json.loads(raw), raw

def jsave(p, obj):
    out = json.dumps(obj, indent=1) + "\n"
    open(p, "w").write(out)
    assert open(p).read() == out, "serialization of %s is not the repo's" % p
    print("wrote %s" % p)

# ---------- MANIFEST header ----------
sub("patch-series/MANIFEST.txt",
    "# Zenium 4.19.325 -> v5.15.220 port series (89 commits + cover letter)",
    "# Zenium 4.19.325 -> v5.15.220 port series (90 commits + cover letter)")
sub("patch-series/MANIFEST.txt",
    "`ls patch-series/*.eml | grep -v cover | wc -l` must be 89 -",
    "`ls patch-series/*.eml | grep -v cover | wc -l` must be 90 -")
sub("patch-series/MANIFEST.txt",
    """# verify:   git rev-parse HEAD^{tree}  ==  7320325c38fdc188de726f3ba658d0f6b80e7eb6  (0089 tip)
#           published prefixes, re-derived by the same command in the 0089 round, both exact
#           (the older ones below are the 0088 round's measurements, carried forward and not
#           re-run, because 0089 touches no file that any of them contains):
#             0001-0088 -> 1a7cf42b066c5379a93cea37fa22a41a4bd9d4c3""",
    """# verify:   git rev-parse HEAD^{tree}  ==  7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed  (0090 tip)
#           published prefixes, re-derived by the same command in the 0090 round, both exact
#           (the older ones below are the rounds' own measurements named beside them, carried
#           forward and not re-run, because 0090 touches no file that any of them contains):
#             0001-0089 -> 7320325c38fdc188de726f3ba658d0f6b80e7eb6   (0090 round)
#             0001-0088 -> 1a7cf42b066c5379a93cea37fa22a41a4bd9d4c3""")
sub("patch-series/MANIFEST.txt",
    """#            l2_pmic_dsv_publish47, i.e. the 0089 tip; 0088's is l2_slot_pool_publish46) and
#            report/display-bringup-plan.md 11.11 (11.8 is the 0088 round);""",
    """#            l2_path_layer_publish48, i.e. the 0090 tip; 0089's is l2_pmic_dsv_publish47,
#            0088's l2_slot_pool_publish46) and report/display-bringup-plan.md 11.16 (11.11 is the
#            0089 round, 11.8 the 0088 round);""")

# ---------- decisions.json ----------
d, _ = jload(os.path.join(R, "report/decisions.json"))
assert len(d["decisions"]) == 155 and d["decisions"][-1]["id"] == 155
d["decisions"].append({
 "id": 156,
 "date": "2026-09-06",
 "title": "0090 landed ddp_path.c verbatim, passed its gate on every predicted number, and is published as the 90th patch",
 "context": "155 committed to narrow B' in dependency order: 0090 first (the path/scenario layer, which is pure display code and adds two record callsites), record adapter second. The slice was priced before it was written by compile probes rather than by reading - portwork/before-after-0090.sh predicted distinct open names 78 -> 65, undefined-reference lines 486 -> 281, 15 names closed and 2 opened, 0 errors - and the plan of record carried those predictions into 11.15 so the gate could be checked against them instead of being graded afterwards.",
 "decision": "Land v3's ddp_path.c unedited (987 lines, 24,946 B, cmp-identical to the vendor file) with one obj-$(CONFIG_MTK_DISP_BRINGUP) line, no new Kconfig symbol, and no DT edit; then gate and publish. The gate reproduced the predictions exactly: switch OFF whole-tree link rc=0 with two 'LD vmlinux' steps, 0 error:, 0 undefined references, vmlinux 168,340,520 B, appended DTB payload 493,517 B (unchanged since 0081, as it must be with no DT change), ddp_path.o absent with the switch off; switch ON 15 objects, 0 error:, 0 diagnostics attributed to ddp_path.c, 486 -> 281 reference lines and 78 -> 65 distinct open names, all 15 claimed names open:0/defined:1, 20 new global symbols with 0 collisions, 0089's bias names still closed. It opened cmdqRecWaitNoClear and cmdqRecSetEventToken at :908/:910/:927 (cmdqRecWrite was already open from ddp_module.c and ddp_reg.h), which is exactly the surface 0091 answers. Published with bin/publish.py --count 1 --expect-tree 7fbaf8257bfa... --prev-tree 7320325c38fd...: 90 numbered patches, all subjects normalized to /90, 'git am' of 0001-0090 reproduces the landing tree and 0001-0089 still reproduces the previous tip, so the landed base did not regress.",
 "still_open_on_purpose": [
  "the three record names, by design - 0091's gate is the next measurement, and nothing lands that the tree cannot link",
  "primary_display_is_video_mode() at ddp_path.c:907/:924 stays open with the panel handover it belongs to; no stub is inserted to make the count look better",
  "the seven pre-existing 'declared inside parameter list' warnings from the landed cmdq headers (cmdq_record.h:804/833/845/889, cmdq_helper_ext.h:880/881/988), reached via ddp_log.h -> ddp_debug.h -> ddp_dump.h -> ddp_path.h; they belong to the include-closure headers, not to this file, and are left alone rather than silenced",
  "no functional claim: the display path links, and is not exercised on hardware"
 ],
 "consequences": [
  "the queue is now 0091 (record adapter, vendor v3 shape, no mailbox ABI change, no invented binding) then 0092 (ddp_matrix_para.h with ddp_rdma_ex.c/ddp_wdma_ex.c)",
  "bin/publish.py refuses to run on a dirty landing tree, including untracked files: the build's arch/arm64/boot/Image.gz-dtb had to be moved to portwork/ before 0090 could publish. Recorded because 'dirty' here is a *safety* check that a build artifact can trigger, and the fix is to move the artifact, never to add -f or skip the check",
  "publish.py rewrites Subject denominators and appends the MANIFEST block, but it does not rewrite the MANIFEST header prose or MATURITY's counts - those are edited by hand in the same round, which is why this record names each file it touched",
  "0090's gate log is portwork/logs/slice0090-gate-20260906T063720Z.log (861 s) and the script is copied to upstream-port/tools/portwork/slice0090-gate.sh so a sandbox reset does not take the measurement procedure with it"
 ],
 "artifacts": [
  "series commit a2985225f, tree 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed",
  "patch-series/0090-video-mt6768-land-the-display-path-scenario-layer-the-.eml (30,721 B) and the 33-line MANIFEST block for it",
  "report/build.json gates.l2_path_layer_publish48",
  "report/display-bringup-plan.md 11.16",
  "portwork/land0090.sh (the landing script), portwork/msg0090.txt (the commit message), portwork/slice0090-gate.sh",
  "report/l2-open-names-at-0089.txt is now superseded for the open set by the gate's names-0090.txt"
 ]})
jsave(os.path.join(R, "report/decisions.json"), d)

# ---------- build.json ----------
b, _ = jload(os.path.join(R, "report/build.json"))
g = b["gates"]
assert "l2_path_layer_publish48" not in g
g["l2_path_layer_publish48"] = {
 "when": "2026-09-06, on the tree that became patch 0090 (ddp_path.c, the display path/scenario layer)",
 "command": "TREE=/home/user/portwork/series EXPECT_TREE=7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed bash /home/user/portwork/slice0090-gate.sh; log portwork/logs/slice0090-gate-20260906T063720Z.log; then bin/publish.py (count 1) for the .eml and MANIFEST",
 "tree": "series commit a2985225f, HEAD^{tree} 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed, landing tree clean (tracked modifications 0). git am of 0001-0090 reproduces that tree; 0001-0089 reproduces 7320325c38fdc188de726f3ba658d0f6b80e7eb6, so the published base did not move under the new patch",
 "numbers": {
  "elapsed_s": 861,
  "off_link": "make ARCH=arm64 -j2 vmlinux Image.gz-dtb rc=0, 'LD vmlinux' x2, 0 error:, 0 undefined reference, vmlinux 168,340,520 B, System.map 6,911,826 B, Image 34,165,248 B, Image.gz 11,734,748 B, Image.gz-dtb 12,228,265 B, appended DTB payload 493,517 B, mt6768.dtb unchanged (no DT file touched by this patch)",
  "off_exclusion": "ddp_path.o absent with CONFIG_MTK_DISP_BRINGUP off, 0 gated display objects, and nm finds none of ddp_path_init / ddp_connect_path / module_list_scenario / display_bias_regulator_init in vmlinux",
  "on_objects": "15 display objects (the 14 from 0084-0089 plus ddp_path.o at 162,296 B), and drivers/misc/mediatek/video/mt6768/videox/disp_helper.o built in the same whole-tree pass - the check that a directory-scoped make used to fake",
  "on_link": "make -k vmlinux rc=2 (the known deferred gaps), 0 error:, 0 warning: lines in the ON pass, 0 diagnostics attributed to ddp_path.c, 281 'undefined reference to' lines (486 at 0089 in the same measurement)",
  "open_names": "65 distinct open names, from 78 at 0089 - the prediction in report/l2-slice-0090-before-after.md was 65 and it held",
  "closed": "all 15 names the patch claims: ddp_path_init, ddp_connect_path, ddp_disconnect_path, ddp_check_path, ddp_is_module_in_scenario, ddp_get_dst_module, ddp_set_dst_module, ddp_get_module_num, ddp_get_module_num_l, ddp_get_scenario_list, ddp_get_scenario_name, ddp_get_mode_name, ddp_path_top_clock_on, ddp_path_top_clock_off, module_list_scenario - each open:0 in the link and ' T' once in the object",
  "opened": "cmdqRecWaitNoClear (ddp_path.c:908, :910), cmdqRecSetEventToken (:927); cmdqRecWrite was already open from ddp_module.c and the DISP_REG_SET macro in ddp_reg.h:266-280. primary_display_is_video_mode stays open with the panel handover",
  "census": "20 new global text/data symbols from ddp_path.o, 0 collisions against the rest of the tree; 0089's bias names stay closed",
  "config": "sha256 prefix 099cdd6421b6 at gate start and at gate end (apply.sh restores it after the ON experiment)"
 },
 "verdict": "0090 is compile- and link-verified only. The path layer's own code is the vendor's verbatim, its symbols resolve, and the record-mode names it opens are answered by 0091. No device is flashed, no frame is drawn, and the display path still cannot be exercised: the gated tree links 65 names short and the record layer is link-required rather than reachable."
}
jsave(os.path.join(R, "report/build.json"), b)

# ---------- plan section ----------
plan = os.path.join(R, "report/display-bringup-plan.md")
s = open(plan).read()
assert "### 11.16" not in s
section = """
### 11.16 - Round 0090: the path/scenario layer, landed and published with its predictions intact

`ddp_path.c` was the largest of the display objects still in the vendor tree and the one every caller in
`ddp_manager.c` had been waiting for: `ddp_path_init()`, `ddp_connect_path()`, `ddp_disconnect_path()` and
`ddp_check_path()` are how a scenario is wired, and 0084/0085 had landed the callers with those symbols
unresolved. It landed verbatim (987 lines, 24,946 B, `cmp`-identical to `4.19.325`'s file) with one
`obj-$(CONFIG_MTK_DISP_BRINGUP)` line, no new Kconfig symbol, and no device-tree edit.

What makes this round different from the earlier ones is that the numbers were written down *before* the
landing (`report/l2-slice-0090-before-after.md`, 11.15) and the gate was then read against them:

| measured | predicted at 11.15 | gate |
|---|---|---|
| distinct open names | 78 -> 65 | 65 |
| `undefined reference` lines | 486 -> 281 | 281 |
| names closed / opened | 15 closed, 2 opened | 15 closed, 2 opened (`cmdqRecWrite` was already open) |
| compile errors in the file | 0 | 0, and 0 diagnostics attributed to it |
| appended DTB payload | 493,517 B unchanged | 493,517 B |
| vmlinux | 168,340,520 B | 168,340,520 B |

Gate `l2_path_layer_publish48`; published as `0090-video-mt6768-land-the-display-path-scenario-layer-the-.eml`
with `bin/publish.py`, which re-verified that 0001-0089 still reproduces the previous tip before and after.
Two workflow facts came out of the publish step and are recorded in decision 156: `publish.py` refuses a dirty
landing tree, and a build artifact (`arch/arm64/boot/Image.gz-dtb`) is enough to make it dirty - move the
artifact, never override the check; and neither the MANIFEST header nor MATURITY's counts are rewritten by the
tool, so those are edited by hand in the same round.

Queue now: **0091** the record adapter (`drivers/soc/mediatek/mtk-cmdq-disp-record.c`, vendor v3 semantics,
no mailbox ABI change, no invented binding) then **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` +
`ddp_wdma_ex.c`.
"""
open(plan, "w").write(s.rstrip("\n") + "\n" + section)
print("appended plan 11.16")

# ---------- MATURITY ----------
sub("MATURITY.md",
    "**89 patches** (`patch-series/0000-cover-letter.eml` + `0001..0089`), base `v5.15.220`, tree **`7320325c38fdc188de726f3ba658d0f6b80e7eb6`**.",
    "**90 patches** (`patch-series/0000-cover-letter.eml` + `0001..0090`), base `v5.15.220`, tree **`7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed`**.")
sub("MATURITY.md",
    "`patch-series/` (89 `.eml`), `report/ledger.csv`",
    "`patch-series/` (90 `.eml`), `report/ledger.csv`")
sub("MATURITY.md",
    "- at the 0089 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,271 B,",
    "- at the 0090 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,265 B,")
sub("MATURITY.md",
    "deliberately do **not** link (499 deferred references, \u00a7Round 0083-0089)",
    "deliberately do **not** link (281 deferred reference lines / 65 distinct names, \u00a7Round 0083-0090)")
sub("MATURITY.md",
    "`report/build.json` (gate `l2_pmic_dsv_publish47`), `report/subsystem-audit.md`",
    "`report/build.json` (gate `l2_path_layer_publish48`), `report/subsystem-audit.md`")
# ---------- FEATURE-PARITY ----------
sub("FEATURE-PARITY.md",
    "## Round 0082-0089: display core, gate, slot pool, panel bias (supersedes the rows above where they conflict)",
    "## Round 0082-0090: display core, gate, slot pool, panel bias, path layer (supersedes the rows above where they conflict)")
sub("FEATURE-PARITY.md",
    "**split deliberately**: the four entry points and the 222-line backup-slot pool landed (0083, 0088, host-checked 37/0), `cmdqRecWrite` and the record layer stay out (decision 148) because a provider would need a GCE mailbox binding the board DT does not expose in 5.15 | M for what landed; L for what is deferred |",
    "**split deliberately, then narrowed by measurement**: the four entry points and the 222-line backup-slot pool landed (0083, 0088, host-checked 37/0); `cmdqRecWrite` stayed out under decision 148 until 155 un-deferred a narrow B\u2032 - a record adapter that delegates to this tree\u2019s own `cmdq_pkt_*` helpers, changes no mailbox ABI and invents no binding, verified against the vendor source by `tests/mtk_disp_record_host_check.c` (0091) | M for what landed; the adapter is link-required, not reachable (no landed `cmdqRecCreate` caller) |")
sub("FEATURE-PARITY.md",
    "| MT6370 sub-PMIC reachability |",
    """| display path/scenario layer | `video/mt6768/dispsys/ddp_path.c` (987 ln), reached from `ddp_manager.c` and `ddp_ddp.c` | **landed verbatim (0090)**, `cmp`-identical to the vendor file, one `obj-$(CONFIG_MTK_DISP_BRINGUP)` line, no Kconfig symbol of its own; closes 15 link symbols and opens the three record names | S |
| MT6370 sub-PMIC reachability |""")
sub("FEATURE-PARITY.md",
    """Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,271 B) and *partial* for the gated one by design (499 deferred references); DT-binding
verification yes in the negative sense - `mt6768.dtb` is byte-identical across 0088 and 0089 (122,474 B,
sha `34a7e6b536a3…`) because no DT was edited; runtime evidence none (host-side checks only); flash no,
boot no, function no. `report/display-bringup-plan.md` 11.6-11.12 and `report/build.json`'s gates
`l2_wholetree_survey45` .. `l2_pmic_dsv_publish47`.""",
    """Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,265 B at the 0090 tip) and *partial* for the gated one by design (281 deferred reference lines,
65 distinct names); DT-binding verification yes in the negative sense - `mt6768.dtb` is byte-identical across
0088, 0089 and 0090 (122,474 B, sha `34a7e6b536a3…`) because no DT was edited; runtime evidence none
(host-side checks only); flash no, boot no, function no. `report/display-bringup-plan.md` 11.6-11.16 and
`report/build.json`'s gates `l2_wholetree_survey45` .. `l2_path_layer_publish48`.""")
print("done")
