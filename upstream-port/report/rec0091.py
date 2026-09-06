#!/usr/bin/env python3
"""rec0091.py - records for patch 0091 (the narrow v3 record adapter) and its host harness.

Same discipline as rec0090.py: every edit asserts its anchor, JSON round-trips byte-identically,
and nothing is claimed that the gate did not print.
"""
import json, os, sys

R = "/home/user/Zenium_Kernel/upstream-port"
def sub(path, old, new, count=1):
    p = os.path.join(R, path)
    s = open(p).read()
    n = s.count(old)
    if n != count:
        sys.exit("ANCHOR %s: expected %d occurrence(s), found %d in %s" % (repr(old[:52]), count, n, path))
    open(p, "w").write(s.replace(old, new, count))
    print("edited %s" % path)

def jsave(p, obj):
    out = json.dumps(obj, indent=1) + "\n"
    open(p, "w").write(out)
    assert open(p).read() == out, "serialization of %s is not the repo's" % p
    print("wrote %s" % p)

# ---------- design doc: section 3's claim is now a measurement ----------
sub("report/l2-record-layer-design-bprime.md",
"""one instruction each, no extra GPR, no chunk list. This is the result that makes narrow B′ cheap, and it was not
known when the option list was written.""",
"""one instruction each, no extra GPR, no chunk list. This is the result that makes narrow B′ cheap, and it was not
known when the option list was written.

**Measured at 0091, so the paragraph above no longer carries the claim alone.**
`upstream-port/tests/mtk_disp_record_host_check.c` encodes the addresses this tree can actually pass
(mmsys_config, disp_dither, and three that no row covers) under every mask `DISP_REG_SET` can spell, on both
sides, and compares the 64-bit words: 55 cases, 0 mismatches. Two header facts came out of the same run and
they are what makes the equivalence mechanical rather than arguable - the port's `CMDQ_CODE_MASK` and the
vendor's `CMDQ_CODE_MOVE` are both 0x02, and the port's `CMDQ_CODE_WRITE_S_MASK` and the vendor's
`CMDQ_CODE_WRITE_S_W_MASK` are both 0x91, so the two-instruction masked write is the same two instructions by
number as well as by layout. The harness reads those numbers out of both trees'
`include/linux/mailbox/mtk-cmdq-mailbox.h` at run time instead of restating them, and the gate log pins the
one transcription in it (the private `struct cmdq_instruction` and the two write_s helpers of
`mtk-cmdq-helper.c`) by sha256: `37d6ddcf5659`, `fb9672f3187f`, `8b965134cef7`. Where the section-4 rejection
of unresolvable addresses bites - the vendor's `CMDQ_SPR_FOR_TEMP` detour - is stated in
`KNOWN-ISSUES.md` 14, not smoothed over here.""")

# ---------- KNOWN-ISSUES: a new numbered entry ----------
sub("KNOWN-ISSUES.md",
"""those cells become unbound platform devices - which is what the vendor code does for any absent
sub-driver, and which is why they were left rather than trimmed.""",
"""those cells become unbound platform devices - which is what the vendor code does for any absent
sub-driver, and which is why they were left rather than trimmed.

## 14. The CMDQ record adapter (0091) links, encodes like the vendor, and cannot be exercised

`drivers/soc/mediatek/mtk-cmdq-disp-record.c` answers `cmdqRecWrite`, `cmdqRecWaitNoClear` and
`cmdqRecSetEventToken`, the three names 0090's `ddp_path.c` opened, and the whole-tree open-name count moves
65 -> 62 with each of the three defined exactly once tree-wide. It is *not* the vendor's record engine, and
three differences are deliberate, each one measured before it was accepted:

1. **No prefetch traffic.** Stock's `cmdq_append_command()` (v3/cmdq_record.c:970) consults
   `cmdq_get_func()->shouldEnablePrefetch()` and, when enabled, brackets writes with a prefetch-disable and a
   mark instruction. That policy lives in v3/cmdq_virtual.c, which this series does not build. A record built
   here therefore matches a stock record whose prefetch policy was *off*, word for word, and differs from one
   where it was on by those two instructions per write. No landed code can observe this today, and no
   hardware behaviour is inferred from it.
2. **Unresolvable addresses are refused, not detoured.** Stock takes an address no subsys row covers and
   loads it into `CMDQ_SPR_FOR_TEMP` with a `CMDQ_CODE_LOGIC`/`CMDQ_LOGIC_ASSIGN` instruction, then writes
   through that register. This tree has no SPR allocator and `mtk-cmdq-helper.c` exposes no primitive for it,
   so the adapter returns `-EINVAL` and logs once. It cannot pack 99 into the field instead: the 5-bit
   `sop` would turn `CMDQ_SPECIAL_SUBSYS_ADDR` into subsys 3 and write somewhere else silently - which the
   harness carries as its own case. Measured, the only landed addresses needing a detour
   (`0x1100e000`, `0x1100d000`) are unreachable through this entry point, and `video/mt6768` plus
   `video/common` contain zero references to `CMDQ_REG_VALUE`, `CMDQ_REG_EXT_VALUE` or
   `cmdq_reg_val_to_reg_str()`.
3. **Register-typed operands are refused.** `cmdqRecWrite()` takes `u32 value` in this tree's header
   (v3/cmdq_record.h:167), so the vendor's `CMDQ_DATA_BIT` tag is 0 by construction and `value_type == 1` is
   unreachable; the branch is kept as a rejection so that anyone landing `cmdqRecWriteFromDataRegister()`
   later meets a documented hole rather than a plausible-looking wrong encoding.

The larger honesty point: **nothing in this tree can build a record.** `cmdqRecCreate()` is referenced only by
the `DISP_REG_VAL_SET()` macro at `ddp_reg.h:272`, which no landed object expands, so there is no handle to
pass and the layer is required at link time and unreachable at run time. That is why landing it did not and
does not move the maturity level past "compiles and links", why the display path still cannot be called
functional, and why the first live callsite will need a `cmdq_pkt_create()`-owning caller and a mailbox
channel - at which point the prefetch question and the `#if !defined(CONFIG_MTK_CMDQ_MBOX_DRV)` binding of
the header (the eight header warnings this file inherits, including `mtk-cmdq-mailbox.h:91`'s
`struct mbox_chan` scope wart, which pre-dates 0091 and affects every includer) become live engineering
questions rather than documented omissions.""")

# ---------- MANIFEST header ----------
sub("patch-series/MANIFEST.txt",
    "# Zenium 4.19.325 -> v5.15.220 port series (90 commits + cover letter)",
    "# Zenium 4.19.325 -> v5.15.220 port series (91 commits + cover letter)")
sub("patch-series/MANIFEST.txt",
    "`ls patch-series/*.eml | grep -v cover | wc -l` must be 90 -",
    "`ls patch-series/*.eml | grep -v cover | wc -l` must be 91 -")
sub("patch-series/MANIFEST.txt",
    """# verify:   git rev-parse HEAD^{tree}  ==  7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed  (0090 tip)
#           published prefixes, re-derived by the same command in the 0090 round, both exact
#           (the older ones below are the rounds' own measurements named beside them, carried
#           forward and not re-run, because 0090 touches no file that any of them contains):
#             0001-0089 -> 7320325c38fdc188de726f3ba658d0f6b80e7eb6   (0090 round)""",
    """# verify:   git rev-parse HEAD^{tree}  ==  3483759c24eb022373a5290523933b61bbd7ac62  (0091 tip)
#           published prefixes, re-derived by the same command in the 0091 round, both exact
#           (the older ones below are the rounds' own measurements named beside them, carried
#           forward and not re-run, because 0091 touches no file that any of them contains):
#             0001-0090 -> 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed   (0091 round)
#             0001-0089 -> 7320325c38fdc188de726f3ba658d0f6b80e7eb6   (0090 round)""")
sub("patch-series/MANIFEST.txt",
    """#            l2_path_layer_publish48, i.e. the 0090 tip; 0089's is l2_pmic_dsv_publish47,
#            0088's l2_slot_pool_publish46) and report/display-bringup-plan.md 11.16 (11.11 is the
#            0089 round, 11.8 the 0088 round);""",
    """#            l2_disp_record_publish49, i.e. the 0091 tip; 0090's is l2_path_layer_publish48,
#            0089's l2_pmic_dsv_publish47, 0088's l2_slot_pool_publish46) and
#            report/display-bringup-plan.md 11.17 (11.16 is the 0090 round, 11.11 the 0089 round);""")

# ---------- MATURITY ----------
sub("MATURITY.md",
    "**90 patches** (`patch-series/0000-cover-letter.eml` + `0001..0090`), base `v5.15.220`, tree **`7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed`**.",
    "**91 patches** (`patch-series/0000-cover-letter.eml` + `0001..0091`), base `v5.15.220`, tree **`3483759c24eb022373a5290523933b61bbd7ac62`**.")
sub("MATURITY.md",
    "`patch-series/` (90 `.eml`), `report/ledger.csv`",
    "`patch-series/` (91 `.eml`), `report/ledger.csv`")
sub("MATURITY.md",
    "- at the 0090 tip, config of record:",
    "- at the 0091 tip, config of record:")
sub("MATURITY.md",
    "deliberately do **not** link (281 deferred reference lines / 65 distinct names, \u00a7Round 0083-0090)",
    "deliberately do **not** link (211 deferred reference lines / 62 distinct names, \u00a7Round 0083-0091)")
sub("MATURITY.md",
    "`report/build.json` (gate `l2_path_layer_publish48`), `report/subsystem-audit.md`",
    "`report/build.json` (gate `l2_disp_record_publish49`), `report/subsystem-audit.md`")

# ---------- FEATURE-PARITY ----------
sub("FEATURE-PARITY.md",
    "## Round 0082-0090: display core, gate, slot pool, panel bias, path layer (supersedes the rows above where they conflict)",
    "## Round 0082-0091: display core, gate, slot pool, panel bias, path layer, record adapter (supersedes the rows above where they conflict)")
sub("FEATURE-PARITY.md",
    """Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,265 B at the 0090 tip) and *partial* for the gated one by design (281 deferred reference lines,
65 distinct names); DT-binding verification yes in the negative sense - `mt6768.dtb` is byte-identical across
0088, 0089 and 0090 (122,474 B, sha `34a7e6b536a3\u2026`) because no DT was edited; runtime evidence none
(host-side checks only); flash no, boot no, function no. `report/display-bringup-plan.md` 11.6-11.16 and
`report/build.json`'s gates `l2_wholetree_survey45` .. `l2_path_layer_publish48`.""",
    """Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,264 B at the 0091 tip) and *partial* for the gated one by design (211 deferred reference lines,
62 distinct names); DT-binding verification yes in the negative sense - `mt6768.dtb` is byte-identical across
0088, 0089, 0090 and 0091 (122,474 B, sha `34a7e6b536a3\u2026`) because no DT was edited and no binding was
invented, and the 0091 harness additionally proves the gce subsys triples this adapter reads are the vendor
board's own; runtime evidence none (host-side checks only, 55 cases / 0 mismatches on the encoding); flash
no, boot no, function no. `report/display-bringup-plan.md` 11.6-11.17 and `report/build.json`'s gates
`l2_wholetree_survey45` .. `l2_disp_record_publish49`.""")

# ---------- decisions.json ----------
p = os.path.join(R, "report/decisions.json")
d = json.load(open(p))
assert len(d["decisions"]) == 156 and d["decisions"][-1]["id"] == 156
d["decisions"].append({
 "id": 157,
 "date": "2026-09-06",
 "title": "0091 lands the record adapter as vendor-shaped delegation - no mailbox ABI change, no new binding - and the encoding equivalence is measured by a host harness instead of argued",
 "context": "156 published 0090 and left three open names. The standing instruction for 0091 was explicit: narrow MT6768/v3 shape, no change to the mainline mailbox ABI, no invented DT bindings, verify command encoding and buffer/address handling against the vendor implementation, then build/link and reproduce the series before 0092. Reading the vendor path end to end (v3/cmdq_record.c:196/:706/:847/:970/:1368/:1481/:1510/:1532, v3/cmdq_helper_ext.c:2265/:2515, v3/cmdq_device.c:264/:336, v3/cmdq_virtual.c:170, v3/cmdq_subsys_common.c, v3/cmdq_event_common.c) settled three things the design doc had only argued: the two event entry points are pure delegations in stock as well, so delegating is not a compromise; the vendor's chunked command buffer (pkt->buf/avail_buf_size/cmdq_pkt_add_cmd_buffer) has no counterpart in this tree's struct cmdq_pkt, so re-implementing the engine is impossible without an ABI change; and stock's masked write uses CMDQ_CODE_MOVE while mainline's helper uses CMDQ_CODE_MASK - which could either be an equivalence or a real divergence depending on the numbers.",
 "decision": "Land one file, drivers/soc/mediatek/mtk-cmdq-disp-record.c, plus one pure-rule header, and pin the equivalence by measurement. The numbers turned out to be the interesting part: the port's CMDQ_CODE_MASK and the vendor's CMDQ_CODE_MOVE are both 0x02, and the port's CMDQ_CODE_WRITE_S_MASK and the vendor's CMDQ_CODE_WRITE_S_W_MASK are both 0x91, so the delegated pair produces the same two instructions stock produces - and tests/mtk_disp_record_host_check.c proves it word by word for the addresses this tree can pass and every mask DISP_REG_SET can spell: 55 cases, 0 mismatches, with the harness parsing the opcode numbers out of both trees' headers at run time so the claim cannot rot into a comment. The same file compares the 44-row subsys name table against the vendor's cmdq_subsys_common.c row by row in both directions and checks that the 31 triples this board's gce node carries equal the vendor board's, and it reproduces cmdq_core_init_dts_data()'s event rule for all 1023 indices. Three vendor behaviours are rejected rather than approximated, each with a measured reason and a loud error: the SPR/CMDQ_CODE_LOGIC detour for unresolvable addresses (no allocator, no primitive, and packing 99 into a 5-bit field would retarget the write to subsys 3 silently), register-typed operands (unreachable through a u32 parameter by construction), and the prefetch insert pairs (a v3/cmdq_virtual.c policy this series does not build). The table is read from a postcore_initcall rather than lazily at the callsite, because stock reads it at its own driver's probe and a lazy of_mutex path in front of code the vendor reaches from atomic context would be a new sleeping bug.",
 "still_open_on_purpose": [
  "no landed code can create a record (cmdqRecCreate() appears only in the unused DISP_REG_VAL_SET() macro at ddp_reg.h:272), so the layer is link-required and runtime-unreachable; the maturity language stops at compiles-and-links and KNOWN-ISSUES 14 says why",
  "the first live callsite reopens the prefetch question and the WFE/SPR design of the vendor's record engine; both are documented as omissions, not as solved",
  "the 62 remaining open names are unchanged in kind: the panel handover (set_lcm/read_lcm/primary_display_*, DSI_send_cmdq_to_bdg), the per-module dump/rdma/wdma set that 0092 takes, and ddp_mmp_* (declined, DEFAULT_MMP_ENABLE is defined nowhere)",
  "whether a real device tree needs to grow a property for any HW event beyond stream_done_0 = <130>, which the board already supplies - measured for the events landed code passes, and no binding was added on speculation"
 ],
 "consequences": [
  "the tree at 42960308a / 3483759c24eb022373a5290523933b61bbd7ac62 is published as the 91st patch, and 0001-0090 still reproduces 7fbaf8257bfa..., so the base did not move",
  "gate l2_disp_record_publish49 is 66 s rather than 15 min because the tree was warm; it still deletes the objects whose existence is the claim ($D/*.o and the record .o) and asserts the LD vmlinux marker, so the measurement is of the link, not of a cache",
  "Image.gz moved by 1 B between the 0090 and 0091 gates (11,734,748 -> 11,734,747) with vmlinux and the DTB payload identical; the record states that as gzip plus the build path in the version string, not as a change this patch made",
  "the eight warnings the new object inherits are header warts (cmdq_record.h:804/833/845/889, cmdq_helper_ext.h:880/881/988, mtk-cmdq-mailbox.h:91's struct mbox_chan in a parameter list) that pre-date 0091 and affect every includer of that header; 0 diagnostics are attributed to either new file",
  "0092 (ddp_matrix_para.h with ddp_rdma_ex.c + ddp_wdma_ex.c) is next, and it inherits the record layer as already-available: the rdma/wdma writes go through DISP_REG_SET into cmdqRecWrite, whose encoding is now measured"
 ],
 "artifacts": [
  "series commit 42960308a, tree 3483759c24eb022373a5290523933b61bbd7ac62",
  "drivers/soc/mediatek/mtk-cmdq-disp-record.c (440 ln, sha256 d09f5a729d99), include/linux/soc/mediatek/mtk-cmdq-disp-record.h (229 ln, 2db3ccded27d), one line + a per-object CFLAGS pair in drivers/soc/mediatek/Makefile",
  "upstream-port/tests/mtk_disp_record_host_check.c (61d6d16cda98) and upstream-port/tests/stub/linux/{types,errno}.h",
  "portwork/slice0091-gate.sh -> upstream-port/tools/portwork/slice0091-gate.sh; log portwork/logs/slice0091-gate-20260906T070201Z.log, name set portwork/logs/names-0091.txt",
  "report/build.json gates.l2_disp_record_publish49, report/l2-record-layer-design-bprime.md section 3 (now carrying the measurement), KNOWN-ISSUES.md 14",
  "patch-series/0091-soc-mediatek-answer-the-three-record-mode-symbols-the-.eml (34,184 B) and its 74-line MANIFEST block"
 ]})
jsave(p, d)

# ---------- build.json ----------
p = os.path.join(R, "report/build.json")
b = json.load(open(p))
g = b["gates"]
assert "l2_disp_record_publish49" not in g
g["l2_disp_record_publish49"] = {
 "when": "2026-09-06, on the tree that became patch 0091 (the CMDQ record adapter for the display path), immediately followed by the publish of both 0090 and 0091",
 "command": "bash /home/user/portwork/slice0091-gate.sh; log portwork/logs/slice0091-gate-20260906T070201Z.log; then bin/publish.py (count 1) for the .eml and MANIFEST",
 "tree": "series commit 42960308a, HEAD^{tree} 3483759c24eb022373a5290523933b61bbd7ac62, landing tree clean. git am of 0001-0091 reproduces that tree and 0001-0090 reproduces 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed, so publishing the adapter did not move the 0090 base",
 "numbers": {
  "elapsed_s": 66,
  "why_so_fast": "the tree was warm from 0090's gate, and the gate still deletes what its claim is about: all 15 display objects and the record object are removed and rebuilt, and the OFF link asserts 'LD vmlinux' twice rather than trusting a zero error count",
  "off_link": "make ARCH=arm64 -j2 vmlinux Image.gz-dtb rc=0, 0 error:, 0 undefined reference, vmlinux 168,340,520 B (identical to 0090's), System.map 6,911,826 B, Image 34,165,248 B, Image.gz 11,734,747 B, Image.gz-dtb 12,228,264 B, appended DTB payload 493,517 B, mt6768.dtb sha256 prefix 34a7e6b536a3 - the last two unchanged since 0081 because no DT file is touched. The 1 B movement in Image.gz with vmlinux and the DTB byte-identical is gzip and the embedded git-describe path, not this patch.",
  "off_exclusion": "mtk-cmdq-disp-record.o absent with CONFIG_MTK_DISP_BRINGUP off, 0 gated display objects, and nm finds no cmdqRecWrite / ddp_path_init / module_list_scenario / display_bias_regulator_init in that vmlinux",
  "on_object": "single-object make rc=0, mtk-cmdq-disp-record.o 101,464 B, 0 error: lines, 0 diagnostics attributed to mtk-cmdq-disp-record.c or its header; the 8 warnings are header-scope warts (cmdq_record.h:804/833/845/889, cmdq_helper_ext.h:880/881/988, mtk-cmdq-mailbox.h:91 'struct mbox_chan' declared inside parameter list) that pre-date this patch",
  "on_symbols": "exactly three T symbols (cmdqRecWrite, cmdqRecWaitNoClear, cmdqRecSetEventToken); its undefined set is cmdq_pkt_write_s_value, cmdq_pkt_write_s_mask_value, cmdq_pkt_wait_no_clear, cmdq_pkt_set_event (all four exported by drivers/soc/mediatek/mtk-cmdq-helper.c, which is built here: CONFIG_MTK_CMDQ_MBOX=y is now visible in the config of record), of_find_node_by_name, of_node_put, of_property_read_variable_u32_array, mutex_lock/unlock, _printk, __stack_chk_fail",
  "on_link": "make -k vmlinux rc=2 (the known deferred gaps), 0 error:, 211 'undefined reference to' lines (281 at 0090) and 62 distinct open names (65 at 0090, 78 at 0089) - the predicted 62, met",
  "closed": "cmdqRecWrite, cmdqRecWaitNoClear, cmdqRecSetEventToken: each open:0 in the link, defined-tree-wide:1 (nm over every .o under drivers/kernel/lib/mm/fs/net), in-object:1 - the every-symbol-defined-exactly-once rule holds; 0090's 15 path names and 0089's 2 bias names stay closed; cmdqRecCreate and cmdqRecFinalize stay at open:0 because nothing references them, which is the documented runtime-unreachable state",
  "census": "3 new global text symbols, 0 collisions with the rest of the tree",
  "harness": "gcc -std=gnu11 -Wall -Wextra build rc=0 with 0 warnings; run against $TREE and the vendor tree: 55 cases, 0 mismatches, rc=0. It proves: port MASK 0x02 == vendor MOVE 0x02 and port WRITE_S_MASK 0x91 == vendor WRITE_S_W_MASK 0x91; identical 64-bit words for 7 addresses x 5 masks; 44/44 subsys name rows equal to the vendor's cmdq_subsys_common.c both directions; 31 gce triples equal to the vendor dts byte for byte; mmsys_config -> 1, disp_dither -> 2, 0x14120100/0x1100e000/0x1100d000 -> 99 (rejected); the event default rule equal to cmdq_core_init_dts_data() for all 1023 indices; tokens 640/641 self-numbering and stream_done_0 = <130> present in the gce node of both trees",
  "transcription_pins": "sha256 prefixes of the only transcribed code in the harness, taken from drivers/soc/mediatek/mtk-cmdq-helper.c: cmdq_pkt_write_s_value 295 B fb9672f3187f, cmdq_pkt_write_s_mask_value 442 B 8b965134cef7, struct cmdq_instruction 857 B 37d6ddcf5659; and of the files under test: mtk-cmdq-disp-record.c d09f5a729d99, mtk-cmdq-disp-record.h 2db3ccded27d, the harness 61d6d16cda98",
  "config": "sha256 prefix 099cdd6421b6 at gate start and gate end (apply.sh restores it after the ON experiment)"
 },
 "verdict": "0091 is compile-, link- and encoding-verified against the vendor source, and nothing more. The record layer is required at link time and unreachable at runtime (no landed code creates a record), the three vendor behaviours this adapter does not carry are rejected loudly and listed in KNOWN-ISSUES 14, and the display path still has 62 names open before it links. No device is flashed and no frame is drawn."
}
jsave(p, b)

# ---------- plan ----------
plan = os.path.join(R, "report/display-bringup-plan.md")
s = open(plan).read()
assert "### 11.17" not in s
open(plan, "w").write(s.rstrip("\n") + """

### 11.17 - Round 0091: the record adapter, landed as vendor-shaped delegation with the encoding measured

The queue's gate node is passed: `cmdqRecWrite`, `cmdqRecWaitNoClear` and `cmdqRecSetEventToken` now have a
provider, the whole-tree open-name count is 62, and no file under `drivers/mailbox/` or
`include/linux/mailbox/` was edited, no compatible or `#cells` was added, and no property was invented. The
shape is what 11.13-\u003e11.15 argued for and what the user fixed as the instruction: the narrow MT6768/v3
adapter, not the engine.

Three things the reading settled that the design doc had only inferred, now in the records because each one
changes what the code does:

  * the two event entry points are delegations in the vendor itself (`:1510` and `:1532` call
    `cmdq_pkt_wait_no_clear()` / `cmdq_pkt_set_event()`), so this port delegating is not a weakening;
  * the vendor's masked write starts with `CMDQ_CODE_MOVE` and mainline's with `CMDQ_CODE_MASK`, and the two
    headers give those names the *same number* (0x02), as they do for `WRITE_S_W_MASK` / `WRITE_S_MASK`
    (0x91) - so the delegated write is the same instruction stream, which is a claim the harness now checks
    instead of a claim this document makes;
  * SW sync tokens need no device tree at all (their default id is their own index, per
    `cmdq_core_init_dts_data()`), while `CMDQ_EVENT_MUTEX0_STREAM_EOF` takes `stream_done_0 = <130>` from the
    board's `gce` node - present, so `ddp_path.c:908` resolves exactly as stock's does on this board.

Gate `l2_disp_record_publish49` (62 distinct names, 3 symbols defined once tree-wide, 0 collisions, 0
diagnostics in either new file) and harness 55/0; published as the 91st patch with `0001-0090` still
reproducing the 0090 tip. KNOWN-ISSUES 14 records the three vendor behaviours deliberately not carried
(prefetch insert pairs, the SPR/`CMDQ_CODE_LOGIC` detour, register-typed operands) and why each fails loudly
rather than quietly.

Queue now: **0092** `ddp_matrix_para.h` with `ddp_rdma_ex.c` + `ddp_wdma_ex.c` (each blocked by that one
header alone, per the header probe), then the DSI/panel handover names, which are a device question and not a
code question.
""")
print("appended plan 11.17")

# ---------- cover letter ----------
sub("patch-series/0000-cover-letter.eml",
"""backup-slot pool (0088) that the landed display core calls on directly, and the MT6370 sub-PMIC
DSV regulator cells (0089), which are the provider behind the two panel-bias calls that core already
makes.""",
"""backup-slot pool (0088) that the landed display core calls on directly, the MT6370 sub-PMIC
DSV regulator cells (0089), which are the provider behind the two panel-bias calls that core already
makes, the display path/scenario layer `ddp_path.c` landed verbatim (0090), and the CMDQ record adapter
that answers the three names it opens (0091) - a narrow vendor-shaped delegation with its instruction
encoding compared word by word against the 4.19 source in `tests/mtk_disp_record_host_check.c`.""")
sub("patch-series/0000-cover-letter.eml",
"""Gates run on exactly this tree:
  - `git am` of all 89 onto pristine v5.15.220 -> rc=0, applied=89, dirty=0, tree
    7320325c38fdc188de726f3ba658d0f6b80e7eb6 - the tree that was built, linked and gated, so the .eml set
    IS the build.""",
"""Gates run on exactly this tree:
  - `git am` of all 91 onto pristine v5.15.220 -> rc=0, applied=91, dirty=0, tree
    3483759c24eb022373a5290523933b61bbd7ac62 - the tree that was built, linked and gated, so the .eml set
    IS the build.""")
sub("patch-series/0000-cover-letter.eml",
"""    Published prefix trees are re-derived every round, because adding a patch must not move them: this
    round measured 0001-0088 -> 1a7cf42b066c5379a93cea37fa22a41a4bd9d4c3 and 0001-0087 ->
    deba5bd29ec656ecb9b542837198cccc76cc5a09, both exact. The 0088 round's figures for 0001-0085""",
"""    Published prefix trees are re-derived every round, because adding a patch must not move them: the 0091
    round measured 0001-0090 -> 7fbaf8257bfa9a33b6909c6ea4cfc1f2b17269ed and 0001-0089 ->
    7320325c38fdc188de726f3ba658d0f6b80e7eb6, both exact, and the 0090 round measured 0001-0088 ->
    1a7cf42b066c5379a93cea37fa22a41a4bd9d4c3. The 0088 round's figures for 0001-0085""")
sub("patch-series/0000-cover-letter.eml",
"""  - Image/vmlinux sha256 is still not a cross-round check:""",
"""  - gates for 0090 and 0091, same tree, same two directions, scripts kept in the repo:
    `upstream-port/tools/portwork/slice0090-gate.sh` (log slice0090-gate-20260906T063720Z.log, 861 s - a
    cold tree) and `slice0091-gate.sh` (log slice0091-gate-20260906T070201Z.log, 66 s on a warm tree, which
    is why it still deletes the objects its claims are about before measuring). 0090: switch OFF links clean
    (rc=0, two `LD vmlinux` steps, 0 `error:`, 0 undefined, vmlinux 168,340,520 B, payload 493,517 B), switch
    ON builds 15 objects with 0 diagnostics in `ddp_path.c` and moves the open-name set 78 -> 65 while
    closing exactly the 15 names it claims. 0091: switch OFF unchanged, switch ON compiles the adapter with 0
    errors and 62 distinct open names (211 reference lines), the three record names defined exactly once
    tree-wide, 3 new globals, 0 collisions - and `tests/mtk_disp_record_host_check.c` prints 55 cases / 0
    mismatches with both trees as arguments, including the opcode numbers it parsed out of each tree's
    mailbox header and the sha256 pins of the one transcription it relies on.
  - Image/vmlinux sha256 is still not a cross-round check:""", 1)
print("done")
