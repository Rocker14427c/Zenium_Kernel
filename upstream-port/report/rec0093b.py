#!/usr/bin/env python3
"""rec0093b.py - the documents that state the CURRENT tip, updated for patch 0093.

rec0093.py took the round's own records (before/after report, KNOWN-ISSUES, plan, decisions, gates). This one
carries the numbers into the four places a reader looks at first - the MANIFEST header, MATURITY's
build-complete row, FEATURE-PARITY's round block - plus the cover letter's round paragraphs, and fixes the
one stale echo in the recovery script that a reset exposed. Same rule as everywhere else here: anchors are
asserted by exact count, and a number is only written because a log printed it.
"""
import os, sys

R = "/home/user/Zenium_Kernel/upstream-port"


def sub(path, old, new, count=1):
    """Replace, or skip if this edit is already present. The first run of this script stopped halfway (an
    anchor read "0083 carries" where the file says "0091 carries"), so re-runnability is now a property of
    the tool rather than of my memory about which edits landed."""
    p = os.path.join(R, path)
    s = open(p).read()
    if new in s:
        print("already applied in %s: %s" % (path, repr(old[:40])))
        return
    n = s.count(old)
    if n != count:
        sys.exit("ANCHOR %s: expected %d occurrence(s), found %d in %s" % (repr(old[:52]), count, n, path))
    open(p, "w").write(s.replace(old, new, count))
    print("edited %s" % path)


# ---------- 1. MANIFEST header: count, tip, prefix, gate, plan section ----------
sub("patch-series/MANIFEST.txt",
"# Zenium 4.19.325 -> v5.15.220 port series (92 commits + cover letter)",
"# Zenium 4.19.325 -> v5.15.220 port series (93 commits + cover letter)")
sub("patch-series/MANIFEST.txt",
"#           (assert the count first: `ls patch-series/*.eml | grep -v cover | wc -l` must be 92 -",
"#           (assert the count first: `ls patch-series/*.eml | grep -v cover | wc -l` must be 93 -")
sub("patch-series/MANIFEST.txt",
"""# verify:   git rev-parse HEAD^{tree}  ==  b5d70973e7f154d47f556bd7abac4aeca4d4176c  (0092 tip)
#           published prefixes, re-derived by the same command in the 0092 round, both exact:
#             0001-0091 -> 3483759c24eb022373a5290523933b61bbd7ac62   (0092 round)
#           (the older ones below are the rounds' own measurements named beside them, carried
#           forward and not re-run, because 0092 touches no file that any of them contains):""",
"""# verify:   git rev-parse HEAD^{tree}  ==  899e689602bca34b67cedf293bb7df337f5bd609  (0093 tip)
#           published prefixes, re-derived by the same command in the 0093 round, both exact:
#             0001-0092 -> b5d70973e7f154d47f556bd7abac4aeca4d4176c   (0093 round)
#           (the older ones below are the rounds' own measurements named beside them, carried
#           forward and not re-run, because 0093 touches no file that any of them contains - it
#           adds three files under video/mt6768/dispsys/, three obj- lines there, and appends one
#           function to drivers/soc/mediatek/mtk-cmdq-disp-record.c, whose 0091 hashes were
#           therefore re-checked in the gate log rather than assumed):""")
sub("patch-series/MANIFEST.txt",
"""#            l2_disp_record_publish50, i.e. the 0092 tip; 0091's is l2_disp_record_publish49,""",
"""#            l2_disp_record_publish51, i.e. the 0093 tip; 0092's is l2_disp_record_publish50,
#            0091's is l2_disp_record_publish49,""")
sub("patch-series/MANIFEST.txt",
"""#            report/display-bringup-plan.md 11.18 (11.17 is the 0091 round, 11.16 the 0090 round);""",
"""#            report/display-bringup-plan.md 11.19 (11.18 is the 0092 round, 11.17 the 0091 round);""")
sub("patch-series/MANIFEST.txt",
"""#            (0089's gate was re-run after a sandbox reset in a tree rebuilt from these .eml files
#             alone - gate l2_pmic_dsv_reverify48 - and reproduced 499/78 and the 39-symbol census,
#             with the only byte differences coming from git-describe in the version string)""",
"""#            (0089's and 0092's gates were each re-run after a sandbox reset in a tree rebuilt from these
#             .eml files alone - gates l2_pmic_dsv_reverify48 and l2_disp_record_reverify51 - reproducing
#             499/78 with its 39-symbol census and 57/CLOSED 5/OPENED 0 with its 6-symbol census; the only
#             differences in either case came from git-describe in the version string, which is also why
#             restore.sh's "N published patches" line now counts the .eml files instead of naming them)""")

# ---------- 2. MATURITY ----------
sub("MATURITY.md",
"""**92 patches** (`patch-series/0000-cover-letter.eml` + `0001..0092`), base `v5.15.220`, tree **`b5d70973e7f154d47f556bd7abac4aeca4d4176c`**. Reproducibility gate re-run on this state at publish time by `bin/publish.py` itself (`git am` of the 4-digit glob -> rc 0, tree byte-identical, and the 0001-0091 prefix reproduces `3483759c24eb…` exactly), and twice before that by accident - a sandbox reset on 2026-09-06 wiped the build workspace and `restore.sh` rebuilt the same tree from the `.eml` set alone.""",
"""**93 patches** (`patch-series/0000-cover-letter.eml` + `0001..0093`), base `v5.15.220`, tree **`899e689602bca34b67cedf293bb7df337f5bd609`**. Reproducibility gate re-run on this state at publish time by `bin/publish.py` itself (`git am` of the 4-digit glob -> rc 0, tree byte-identical, and the 0001-0092 prefix reproduces `b5d70973e7f1…` exactly), and three times before that by accident - sandbox resets on 2026-09-06 wiped the build workspace, `restore.sh` rebuilt the same tree from the `.eml` set alone both times, and the second time the rebuilt tree was put through patch 0092's own gate, which reproduced it in full (gate `l2_disp_record_reverify51`).""")
sub("MATURITY.md",
"""**DONE for the tree any user builds** - at the 0092 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,269 B, the device's own `mt6768.dtb` 122,474 B (sha `34a7e6b536a3…`), 0 `error:` lines and 0 undefined references. Two honest qualifiers: the display objects behind `CONFIG_MTK_DISP_BRINGUP` deliberately do **not** link (160 deferred reference lines / 57 distinct names, §Round 0082-0092), and the 529-DTB / 840-`.ko` figures are `build-37`'s - modules and the DTB sweep have not been re-measured since 0081 | `report/build-evidence.md`, `report/build.json` (gate `l2_disp_record_publish50`), `report/subsystem-audit.md` |""",
"""**DONE for the tree any user builds** - at the 0093 tip, config of record: `vmlinux` 168,340,520 B, `Image` 34,165,248 B, `Image.gz-dtb` 12,228,266 B, the device's own `mt6768.dtb` 122,474 B (sha `34a7e6b536a3…`), 0 `error:` lines and 0 undefined references. Two honest qualifiers: the display objects behind `CONFIG_MTK_DISP_BRINGUP` deliberately do **not** link (140 deferred reference lines / 49 distinct names, §Round 0082-0093 - the 19 landed gated display objects compile with 0 errors and the gap is now entirely other layers' providers), and the 529-DTB / 840-`.ko` figures are `build-37`'s - modules and the DTB sweep have not been re-measured since 0081 | `report/build-evidence.md`, `report/build.json` (gate `l2_disp_record_publish51`), `report/subsystem-audit.md` |""")

# ---------- 3. FEATURE-PARITY: heading, the two rows the slice changes, the readiness paragraph ----------
sub("FEATURE-PARITY.md",
"## Round 0082-0092: display core, gate, slot pool, panel bias, path layer, record adapter, MMP layer (supersedes the rows above where they conflict)",
"## Round 0082-0093: display core, gate, slot pool, panel bias, path layer, record adapter, MMP layer, colour trio (supersedes the rows above where they conflict)")
sub("FEATURE-PARITY.md",
"""| dispsys core | `video/mt6768/dispsys/`, 21 files | **15 objects + `disp_helper.c` landed under `CONFIG_MTK_DISP_BRINGUP` (default n)**, `ddp_mmp.c` included verbatim in 0092 (934 ln, closes its 5 names, opens 0); what remains needs the record API beyond what 0091 carries (`ddp_ovl.c`: 35 `cmdqRec*` references incl. the secure trio 0083 never provided; measured net +4 with `mtk_dramc.h` landed) or an unported chain (`disp_dts_gpio.h` for `ddp_pwm.c`, `ion_drv.h` for `videox/disp_lowpower.c`) | M |""",
"""| dispsys core | `video/mt6768/dispsys/`, 21 files | **19 objects + `disp_helper.c` landed under `CONFIG_MTK_DISP_BRINGUP` (default n)**, `ddp_mmp.c` verbatim in 0092 (934 ln, 5 names closed, 0 opened) and the colour trio in 0093 (`color20/ddp_color.c` 4,099 + `corr10/ddp_dither.c` 409 + `corr10/ddp_gamma.c` 1,574, verbatim, 8 names closed, 0 opened, with one new record entry point `cmdqRecReadToDataRegister()` added for them); what remains needs the record API beyond what 0083/0091 carry (`ddp_ovl.c`: 35 `cmdqRec*` references incl. the secure trio 0083 never provided; measured net +4 with `mtk_dramc.h` landed) or a header this port has not taken (`disp_dts_gpio.h` for `ddp_pwm.c` and `ddp_dsi.c`, `ddp_reg_disp_bdg.h`, `mtk_leds_drv.h`, `mtk_disp_mgr.h`; `ion_drv.h` for `videox/disp_lowpower.c`, `mtkfb.c`, `disp_recovery.c`) | M |""")
sub("FEATURE-PARITY.md",
"""| engine files priced but not landed (rdma/wdma/ovl/colour) | `ddp_rdma_ex.c` (1,649 ln), `ddp_wdma_ex.c` (1,330 ln), `ddp_matrix_para.h` (131 ln), `ddp_ovl.c` (4,527 ln), `common/{color20,corr10}` trio (6,082 ln) | **all five sets compile in this tree** (wdma with one documented `#include <ion_sec_heap.h>` comment-out) and were priced by whole-tree ON link rather than guessed: -7 for the colour trio, +4 for ovl, +11 for rdma/wdma - the two positive ones are gated on the record adapter, the colour trio on a fourth entry point plus the register-typed-operand rule 0091 declined. `common/{rdma20,wdma20}/*.c` are MT6799-only in the vendor's build and permanently out | - (measurement: report/l2-slice-0092-before-after.md) |""",
"""| engine files priced but not landed (rdma/wdma/ovl) | `ddp_rdma_ex.c` (1,649 ln), `ddp_wdma_ex.c` (1,330 ln), `ddp_matrix_para.h` (131 ln), `ddp_ovl.c` (4,527 ln) | **all four compile in this tree** (wdma with one documented `#include <ion_sec_heap.h>` comment-out) and were priced by whole-tree ON link rather than guessed: +4 for ovl, +11 for rdma/wdma - both gated on the record adapter, which is a decision and not a missing file. The colour trio that shared this row until 0093 was priced at -7 without an adapter change and landed at -8 with one (`report/l2-slice-0093-before-after.md`). `common/{rdma20,wdma20}/*.c` are MT6799-only in the vendor's build and permanently out | - (measurements: report/l2-slice-0092-before-after.md, report/l2-slice-0093-before-after.md) |
| the rest of the unlanded display queue | 11 candidate files under `video/mt6768/` | **priced in one sweep and ten of eleven cannot be priced at all**: `ddp_dsi.c`, `ddp_pwm.c`, `ddp_disp_bdg.c`, `ddp_aal.c`, `videox/debug.c`, `disp_recovery.c`, `disp_lowpower.c`, `mtkfb.c`, `primary_display.c` each stop at a single missing `#include` before the link runs, and `fbconfig_kdebug.c` fails on two implicit declarations; the one file that links, `disp_cust.c`, is net +5 and was refused. The queue is therefore a header decision (`disp_dts_gpio.h` is a device-tree pin reader, the `ion_*.h` family is a policy refusal) rather than a work queue | - (measurement: report/logs/sweep-0093.log, KNOWN-ISSUES.md 16) |""")
sub("FEATURE-PARITY.md",
"""Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,269 B at the 0092 tip - `vmlinux` unchanged in size at 168,340,520 B, the 5 B moving in the
gzipped image being the recorded gzip/`git describe` behaviour rather than code) and *partial* for the gated
one by design (160 deferred reference lines, 57 distinct names, down from 211/62 at 0091 and 486/78 at 0089);
DT-binding verification yes in the negative sense - `mt6768.dtb`'s size and sha are unchanged across 0088,
0089, 0090, 0091 and 0092 (122,474 B, sha `34a7e6b536a3…`) and the appended DTB payload has been 493,517 B
since 0081, because no DT was edited and no binding was invented; the 0091 harness additionally proves the
gce subsys triples the record adapter reads are the vendor board's own, and 0092 re-hashes that harness's two
subjects to 0091's values to prove the adapter was not touched. 0092's own proof is the sha256 match between
the landed `ddp_mmp.c` and the vendor file, plus the 0-names-opened census; runtime evidence none (host-side
checks only, 55 cases / 0 mismatches on the encoding, 37 / 0 on the slot pool); flash no, boot no, function
no. `report/display-bringup-plan.md` 11.6-11.18 and `report/build.json`'s gates `l2_wholetree_survey45` ..
`l2_disp_record_publish50`.""",
"""Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,266 B at the 0093 tip - `vmlinux` unchanged in size at 168,340,520 B, the small movements in
the gzipped image being the recorded gzip/`git describe` behaviour rather than code) and *partial* for the
gated one by design (140 deferred reference lines, 49 distinct names, down from 160/57 at 0092, 211/62 at
0091 and 486/78 at 0089); DT-binding verification yes in the negative sense - `mt6768.dtb`'s size and sha are
unchanged across 0088 through 0093 (122,474 B, sha `34a7e6b536a3…`) and the appended DTB payload has been
493,517 B since 0081, because no DT was edited and no binding was invented; the 0091 harness additionally
proves the gce subsys triples the record adapter reads are the vendor board's own, 0092 re-hashes that
harness's two subjects to 0091's values to prove the adapter was not touched, and 0093 extends that same
harness to 85 cases so that the one function it adds to the adapter is pinned by 12 word-for-word
instruction comparisons, 9 refusal cases and 4 source-shape checks rather than by prose. 0093's proof for
the vendor side is again the sha256 match on all three landed files plus the 0-names-opened census (32 new
globals, 8 of them names this tree had open, 0 collisions); runtime evidence none (host-side checks only, 85
cases / 0 mismatches on the encoding, 37 / 0 on the slot pool); flash no, boot no, function no.
`report/display-bringup-plan.md` 11.6-11.19 and `report/build.json`'s gates `l2_wholetree_survey45` ..
`l2_disp_record_publish51`.""")

# ---------- 4. cover letter: the round paragraph and the gate bullets ----------
sub("patch-series/0000-cover-letter.eml",
"""MMP layer the display code has been calling since 0085, `ddp_mmp.c` landed verbatim (0092), chosen over the
rdma/wdma pair that was queued because pricing both showed the pair opens 21 names to close 10.""",
"""MMP layer the display code has been calling since 0085, `ddp_mmp.c` landed verbatim (0092), chosen over the
rdma/wdma pair that was queued because pricing both showed the pair opens 21 names to close 10, and the
colour trio `ddp_color.c` + `ddp_dither.c` + `ddp_gamma.c` landed verbatim with the single record read entry
point they need (0093), which is the first slice in this series to answer an open name with a mainline
delegation instead of with vendor code.""")
sub("patch-series/0000-cover-letter.eml",
"""  - Image/vmlinux sha256 is still not a cross-round check: the version string embeds `git describe`,
    so the same code from a different commit differs in those bytes; sizes and the 493,517 B appended
    DTB payload are the stable observables.""",
"""  - gate for 0093 (`slice0093-gate.sh`, log slice0093-gate-20260906T113559Z.log, 69 s) is the round where
    the queue was found to be a header problem: switch ON 57 -> 49 distinct names (160 -> 140 reference
    lines), 8 closed and 0 opened, the closed set compared as a set against the eight predicted names; the
    three objects rebuilt from scratch at 272,968 / 104,728 / 139,560 B with 0 error: lines and 0 diagnostics
    naming the landed files (29 warnings, all from the landed v3 headers and mtk-cmdq-mailbox.h:91); census 32
    new globals with 0 collisions; `cmdqRecReadToDataRegister` open:0 and defined:1 in the adapter object;
    switch OFF unchanged (payload 493,517 B, mt6768.dtb 34a7e6b536a3, no landed symbol in vmlinux); harnesses
    85 cases / 0 mismatches and 37 / 0. The same round priced the eleven remaining candidates
    (sweep-0093.log) and reported ten as blocked before the link rather than as cheap, and the one that
    links as net +5.
  - two rig repairs came out of those runs and both are recorded rather than quietly applied: `nm` reads
    nothing from an object piped to it, so every "census" line written that way in a gate or probe script had
    been printing 0 since it was first written, and two gate comparisons fired on correct states (a
    sorted-versus-prose set compare, and a subject-line grep for a filename the subject never uses). The
    first run of this gate therefore printed `defined:0` for the very symbol the patch adds; the fixed run
    is the one quoted above.
  - 0092's gate was also re-run cold on a workspace rebuilt from these .eml files alone after a second
    sandbox reset mid-round (log slice0092-gate-20260906T111233Z.log, 876 s, gate l2_disp_record_reverify51):
    57 names, CLOSED 5, OPENED 0, object 85,592 B, 6 globals, 0 collisions, both harnesses, the same DTB sha
    and payload, and no prior conclusion moved - which is the point of keeping the gate scripts and their logs
    in this repo rather than in the build workspace.
  - Image/vmlinux sha256 is still not a cross-round check: the version string embeds `git describe`,
    so the same code from a different commit differs in those bytes; sizes and the 493,517 B appended
    DTB payload are the stable observables. Both re-verifications this round moved `Image.gz` by 1-2 B
    against a published gate with `vmlinux`, `System.map` and the uncompressed `Image` identical.""")

# ---------- 5. the recovery script's stale patch count ----------
sub("tools/portwork/restore.sh",
'''say "== [5/5] series tree: git am the 82 published patches onto the base =="''',
'''say "== [5/5] series tree: git am the $(ls "$REPO"/upstream-port/patch-series/[0-9]*.eml 2>/dev/null | grep -vc cover) published patches onto the base =="''')
sub("tools/portwork/restore.sh",
'''say "== [5/5] series tree: git am the $(ls "$REPO"/upstream-port/patch-series/[0-9]*.eml 2>/dev/null | grep -vc cover) published patches onto the base =="''',
'''# counted, not named: this line read "the 82 published patches" through nine rounds of drift, because a
# hardcoded count in a recovery script is the one number nobody re-checks until a reset makes it matter
NPATCH=$(ls "$REPO"/upstream-port/patch-series/[0-9]*.eml 2>/dev/null | grep -vc cover)
say "== [5/5] series tree: git am the $NPATCH published patches onto the base =="''')

print("rec0093b.py done: MANIFEST header, MATURITY, FEATURE-PARITY, cover letter, restore.sh")
