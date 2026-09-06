#!/usr/bin/env python3
"""rec0092b.py - FEATURE-PARITY's round summary paragraph, which rec0092.py updated in its rows but not
in prose. The paragraph states the CURRENT readiness, so it has to move with the round; it also fixes one
overstatement found while re-reading it ("`mt6768.dtb` is byte-identical" -> the size and sha are what the
gates print, and the appended payload is what has been constant since 0081)."""
import os, sys
R = "/home/user/Zenium_Kernel/upstream-port"

def sub(path, old, new, count=1):
    p = os.path.join(R, path)
    s = open(p).read()
    n = s.count(old)
    if n != count:
        sys.exit("ANCHOR %s: expected %d occurrence(s), found %d in %s" % (repr(old[:52]), count, n, path))
    open(p, "w").write(s.replace(old, new, count))
    print("edited %s" % path)

sub("FEATURE-PARITY.md",
"""Readiness for this round: source yes; build yes for the default tree (0 errors, 0 undefined references,
image 12,228,264 B at the 0091 tip) and *partial* for the gated one by design (211 deferred reference lines,
62 distinct names); DT-binding verification yes in the negative sense - `mt6768.dtb` is byte-identical across
0088, 0089, 0090 and 0091 (122,474 B, sha `34a7e6b536a3…`) because no DT was edited and no binding was
invented, and the 0091 harness additionally proves the gce subsys triples this adapter reads are the vendor
board's own; runtime evidence none (host-side checks only, 55 cases / 0 mismatches on the encoding); flash
no, boot no, function no. `report/display-bringup-plan.md` 11.6-11.17 and `report/build.json`'s gates
`l2_wholetree_survey45` .. `l2_disp_record_publish49`.""",
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
`l2_disp_record_publish50`.""")
print("rec0092b done")
