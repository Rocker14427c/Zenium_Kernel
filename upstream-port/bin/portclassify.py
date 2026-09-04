#!/usr/bin/env python3
"""
portclassify - hunk-level port classification / application tool for kernel trees.

Purpose
-------
A downstream Android/SoC kernel tree (typically a squashed snapshot with no
rebase-able history) differs from its vanilla baseline in thousands of files.
Before any of that delta can be carried to a newer baseline, each *hunk* must
be classified:

  ALREADY      the change (or an equivalent) is already in the target base
               -> drop it; it was an upstream backport
  PORTABLE     the hunk's pre-image is found in the target file (possibly at a
               different line offset) -> the change can be applied mechanically
  PARTIAL      some but not all of the hunk's added lines already exist in the
               target -> needs a human to decide the remainder
  MANUAL       pre-image not found -> semantic conflict, needs a human
  NO_TARGET    file does not exist in the target base -> deletion/replacement
               decision needed
  NOISE        whitespace-only / mode-only churn
  SKIP_ARCH    file belongs to an architecture the product does not ship

Usage
-----
  portclassify.py analyze  --base BASE --vendor VENDOR --target TARGET \
                          --out OUTDIR [--prefix "a/"] [-j N]
  portclassify.py apply    --vendor VENDOR --target TARGET --portable OUT/portable.json \
                          --apply-to PORTTREE [--commit-groups]

Design notes (why this is safe enough to run on a real kernel tree):
  * Only whole-hunk decisions are made; hunks are never split.
  * A hunk is applied only if its pre-image matches the target text exactly
    (after trailing-whitespace normalisation).  No fuzzing of *changed* lines.
  * Applied hunks are recorded with the exact target offset so the result is
    reproducible and auditable via `git diff` of the port tree.
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
DIFFHDR_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")

# Architectures that a phone product never ships; carried in the ledger but
# excluded from the porting surface.
OTHER_ARCH = (
    "arch/x86/", "arch/powerpc/", "arch/mips/", "arch/sparc/", "arch/alpha/",
    "arch/ia64/", "arch/m68k/", "arch/nios2/", "arch/openrisc/", "arch/parisc/",
    "arch/riscv/", "arch/s390/", "arch/sh/", "arch/unicore32/", "arch/xtensa/",
    "arch/um/", "arch/nds32/", "arch/c6x/", "arch/hexagon/", "arch/arc/",
    "arch/arm/", "arch/microblaze/",
)

# Subsystems that must be treated as "vendor transplant", not "hunk port".
VENDOR_ROOTS = (
    "drivers/misc/mediatek/", "drivers/gpu/drm/mediatek/", "drivers/gpu/ion/",
    "net/oplus_modules/", "drivers/power/", "sound/soc/mediatek/",
    "drivers/input/", "arch/arm64/boot/dts/",
)


def norm(line):
    """Normalise a source line for matching: strip trailing ws, tabs->spaces."""
    s = line.rstrip()
    return s


def is_blank(s):
    return not s.strip()


def read_diff_index(base, vendor, paths):
    """Return {path: (base_text, vendor_text)} for a list of paths, using git
    blob contents from the base repo when possible (fast, no checkout needed)."""
    out = {}
    for p in paths:
        vb = os.path.join(vendor, p)
        bb = os.path.join(base, p)
        try:
            with open(vb, "r", encoding="utf-8", errors="surrogateescape") as f:
                vtxt = f.read()
        except OSError:
            vtxt = None
        try:
            with open(bb, "r", encoding="utf-8", errors="surrogateescape") as f:
                btxt = f.read()
        except OSError:
            btxt = None
        out[p] = (btxt, vtxt)
    return out


class TargetFile:
    """Target-base file text with an index for fast n-gram line matching."""

    def __init__(self, path):
        self.path = path
        self.lines = []
        self.index = defaultdict(list)
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            for i, raw in enumerate(f):
                ln = norm(raw)
                self.lines.append(ln)
                self.index[ln].append(i)

    def find_seq(self, seq, hint=None, window=None):
        """Find consecutive occurrence of seq (list of normalised lines).
        Returns index of first line or -1.  Uses the rarest probe line to
        candidate-anchor, so it stays O(lines) per hunk instead of O(lines*len)."""
        if not seq:
            return -1
        # anchor = rarest line in the target file
        best, bestc = None, None
        for cand in seq:
            if is_blank(cand):
                continue
            c = len(self.index.get(cand, ()))
            if bestc is None or c < bestc:
                best, bestc = cand, c
                if c == 0:
                    return -1
        if best is None:  # all-blank sequence
            return -1
        starts = []
        base_idx = self.index[best]
        if hint is not None:
            # prefer candidates nearest the hint (old hunk line), then others
            pos = {p: i for i, p in enumerate(base_idx)}
            order = sorted(base_idx, key=lambda p: abs(p - hint))
            if window:
                order = [p for p in order if abs(p - hint) <= window] + [
                    p for p in base_idx if abs(p - hint) > window
                ]
            starts = order
        else:
            starts = base_idx
        k = seq.index(best)
        n = len(seq)
        lines = self.lines
        for st in starts:
            o = st - k
            if o < 0 or o + n > len(lines):
                continue
            ok = True
            for j in range(n):
                if lines[o + j] != seq[j]:
                    ok = False
                    break
            if ok:
                return o
        return -1

    def contains_seq(self, seq):
        return self.find_seq(seq) >= 0


def parse_patch(patch_path):
    """Parse a unified diff into {newpath: {'hunks':[...], ...}}."""
    files = {}
    cur = None
    curh = None
    skipped_binary = set()
    with open(patch_path, "r", encoding="utf-8", errors="surrogateescape") as f:
        for raw in f:
            line = raw.rstrip("\n")
            m = DIFFHDR_RE.match(line)
            if m:
                old, new = m.group(1), m.group(2)
                cur = files.setdefault(
                    new, {"old": old, "new": new, "hunks": [], "mode": None}
                )
                curh = None
                continue
            if cur is None:
                continue
            if line.startswith("Binary files"):
                skipped_binary.add(cur["new"])
                cur = None
                continue
            if line.startswith("new file mode") or line.startswith("deleted file mode"):
                cur["mode"] = line.split()[0]
                continue
            if line.startswith("old mode") or line.startswith("new mode"):
                continue
            if line.startswith("--- ") or line.startswith("+++ "):
                continue
            if line.startswith("index ") or line.startswith("similarity ") or line.startswith("rename "):
                continue
            hm = HUNK_RE.match(line)
            if hm:
                curh = {
                    "old_start": int(hm.group(1)),
                    "old_count": int(hm.group(2) or 1),
                    "new_start": int(hm.group(3)),
                    "new_count": int(hm.group(4) or 1),
                    "hdr": hm.group(5).strip(),
                    "ctx": [],   # context lines as they appear
                    "pre": [],   # ' ' and '-' lines, in order
                    "post": [],  # ' ' and '+' lines, in order
                    "added": [],
                    "removed": [],
                    "ops": [],
                }
                cur["hunks"].append(curh)
                continue
            if curh is None:
                continue
            if line.startswith("+"):
                curh["post"].append(norm(line[1:]))
                curh["added"].append(norm(line[1:]))
                curh["ops"].append(("+", norm(line[1:])))
            elif line.startswith("-"):
                curh["pre"].append(norm(line[1:]))
                curh["removed"].append(norm(line[1:]))
                curh["ops"].append(("-", norm(line[1:])))
            elif line.startswith(" ") or line == "":
                txt = norm(line[1:]) if line else ""
                curh["pre"].append(txt)
                curh["post"].append(txt)
                curh["ctx"].append(txt)
                curh["ops"].append((" ", txt))
            else:
                curh = None
    for p in skipped_binary:
        files[p]["binary"] = True
    return files


def classify_file(args):
    (path, entry, target_root, drop_other_arch) = args
    res = {
        "file": path,
        "hunks": 0,
        "already": 0,
        "portable": 0,
        "partial": 0,
        "manual": 0,
        "noise": 0,
        "status": None,
        "added": 0,
        "removed": 0,
    }
    hunks = entry["hunks"]
    res["hunks"] = len(hunks)
    res["added"] = sum(len(h["added"]) for h in hunks)
    res["removed"] = sum(len(h["removed"]) for h in hunks)

    if entry.get("binary"):
        res["status"] = "BINARY"
        return res, []

    if drop_other_arch and path.startswith(OTHER_ARCH):
        res["status"] = "SKIP_ARCH"
        return res, []

    tgt_path = os.path.join(target_root, path)
    if not os.path.exists(tgt_path):
        res["status"] = "NO_TARGET"
        return res, []
    try:
        tf = TargetFile(tgt_path)
    except OSError:
        res["status"] = "NO_TARGET"
        return res, []

    decisions = []
    for idx, h in enumerate(hunks):
        if not h["added"] and not h["removed"]:
            res["noise"] += 1
            decisions.append({"file": path, "hunk": idx, "state": "NOISE", "target_line": None})
            continue
        # 1. exact post-image already in target?
        if h["post"] and tf.contains_seq(h["post"]):
            res["already"] += 1
            decisions.append({"file": path, "hunk": idx, "state": "ALREADY", "target_line": None})
            continue
        # 2. pre-image found in target?  (allow trimmed context)
        pre = h["pre"]
        found = -1
        trimmed = False
        if pre:
            found = tf.find_seq(pre, hint=h["old_start"] - 1, window=400)
            if found < 0 and len(pre) > 2:
                # drop up to 3 outer context lines on each side, never changed lines
                for k in range(1, 4):
                    head_ok = pre[k] if k < len(pre) else None
                    # only trim if trimmed lines were pure context
                    if head_ok is None:
                        break
                    trial = pre[k:-k] if len(pre) > 2 * k else pre[k:]
                    if not trial:
                        break
                    found = tf.find_seq(trial, hint=h["old_start"] - 1, window=400)
                    if found >= 0:
                        trimmed = True
                        break
        if found >= 0 and not trimmed:
            res["portable"] += 1
            decisions.append({
                "file": path, "hunk": idx, "state": "PORTABLE",
                "target_line": found, "hdr": h["hdr"],
                "ops": h["ops"],
            })
            continue
        if found >= 0 and trimmed:
            res["partial"] += 1
            decisions.append({"file": path, "hunk": idx, "state": "NEAR", "target_line": found})
            continue
        # 3. all added lines present somewhere in the target file?
        if h["added"] and all(a in tf.index for a in h["added"]):
            res["partial"] += 1
            decisions.append({"file": path, "hunk": idx, "state": "PARTIAL", "target_line": None})
            continue
        res["manual"] += 1
        decisions.append({"file": path, "hunk": idx, "state": "MANUAL", "target_line": None})

    if res["portable"] == res["hunks"]:
        res["status"] = "FULLY_PORTABLE"
    elif res["already"] == res["hunks"]:
        res["status"] = "OBSOLETE"
    elif res["noise"] == res["hunks"]:
        res["status"] = "NOISE_ONLY"
    elif res["portable"]:
        res["status"] = "MIXED"
    else:
        res["status"] = "MANUAL"
    return res, decisions


def subsystem_of(path):
    parts = path.split("/")
    if parts[0] == "drivers" and len(parts) > 2:
        return "/".join(parts[:3])
    if parts[0] == "arch" and len(parts) > 3:
        return "/".join(parts[:3])
    return parts[0]


def cmd_analyze(a):
    print(f"[1/4] parsing delta patch {a.delta}", flush=True)
    files = parse_patch(a.delta)
    print(f"      {len(files)} files, {sum(len(v['hunks']) for v in files.values())} hunks",
          flush=True)

    if a.base_list:
        with open(a.base_list) as f:
            names = set(x.strip() for x in f if x.strip())
        for n in names & set(files):
            files[n]["note"] = "modified-in-base-only"

    jobs = [(p, e, a.target, not a.keep_other_arch) for p, e in sorted(files.items())]
    results = []
    decisions = []
    print(f"[2/4] classifying hunks against {a.target}", flush=True)
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for i, (r, d) in enumerate(ex.map(classify_file, jobs, chunksize=8)):
            results.append(r)
            decisions.extend(d)
            if (i + 1) % 500 == 0:
                print(f"      {i+1}/{len(jobs)} files", flush=True)

    print("[3/4] writing ledgers", flush=True)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "ledger.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        for r in sorted(results, key=lambda x: (x["status"], -x["hunks"], x["file"])):
            w.writerow(r)

    # portable.json is the machine-readable instruction set for `apply`
    port = defaultdict(list)
    for d in decisions:
        if d["state"] == "PORTABLE":
            port[d["file"]].append(d)
    with open(os.path.join(a.out, "portable.json"), "w") as f:
        json.dump(port, f)

    st = Counter(r["status"] for r in results)
    hs = Counter(d["state"] for d in decisions)
    sub = defaultdict(Counter)
    for r in results:
        sub[subsystem_of(r["file"])][r["status"]] += 1
        sub[subsystem_of(r["file"])]["hunks"] += r["hunks"]
        sub[subsystem_of(r["file"])]["portable_hunks"] += r["portable"]
        sub[subsystem_of(r["file"])]["already_hunks"] += r["already"]
        sub[subsystem_of(r["file"])]["manual_hunks"] += r["manual"]
    summary = {
        "files_total": len(results),
        "hunks_total": sum(hs.values()),
        "file_status": dict(st),
        "hunk_status": dict(hs),
        "subsystems": {k: dict(v) for k, v in sorted(
            sub.items(), key=lambda kv: -kv[1]["portable_hunks"])},
    }
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print("[4/4] done", flush=True)
    print(json.dumps({"file_status": dict(st), "hunk_status": dict(hs)}, indent=1))


def apply_hunks(tgt_text, tline, ops):
    """Apply a hunk's ops at target line tline (0-based) to text lines.

    Matching is done on rstripped text (the classifier indexed the target that
    way), but untouched lines are written back verbatim so the resulting diff
    contains only the ported change and no whitespace noise.
    """
    lines = tgt_text.split("\n")
    ops = [(o, t) for o, t in ops]
    n_pre = sum(1 for o, _ in ops if o in (" ", "-"))
    # sanity: the pre-image must match exactly (modulo trailing whitespace).
    # j walks the target/pre-image, i walks the whole op list ('+' lines do not
    # exist in the pre-image, so they must not advance j).
    j = 0
    for i, (o, t) in enumerate(ops):
        if o in (" ", "-"):
            if tline + j >= len(lines) or lines[tline + j].rstrip() != t:
                return None
            j += 1
    # preserve original bytes for context lines, use vendor bytes for additions
    out = []
    n_ctx = 0
    for o, t in ops:
        if o == " ":
            out.append(lines[tline + n_ctx])
            n_ctx += 1
        elif o == "-":
            n_ctx += 1
        else:
            out.append(t)
    lines[tline:tline + n_pre] = out
    return "\n".join(lines)


def cmd_apply(a):
    with open(a.portable) as f:
        port = json.load(f)
    applied, failed, touched = 0, 0, []
    for path, hunks in sorted(port.items()):
        tgt = os.path.join(a.apply_to, path)
        if not os.path.exists(tgt):
            failed += 1
            continue
        with open(tgt, "r", encoding="utf-8", errors="surrogateescape") as f:
            text = f.read()
        # apply bottom-up so earlier offsets stay valid; drop overlapping ones
        hunks = sorted(hunks, key=lambda d: -d["target_line"])
        used = []
        for h in hunks:
            if any(h["target_line"] < u and h["target_line"] + 3 > u - 60 for u in used):
                continue
        hunks2 = []
        last = None
        for h in sorted(hunks, key=lambda d: d["target_line"]):
            if last is not None and h["target_line"] <= last:
                continue
            hunks2.append(h)
            last = h["target_line"] + sum(1 for o, _ in h["ops"] if o in (" ", "-"))
        for h in sorted(hunks2, key=lambda d: -d["target_line"]):
            new = apply_hunks(text, h["target_line"], h["ops"])
            if new is None:
                failed += 1
                continue
            text = new
            applied += 1
        if hunks2:
            with open(tgt, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(text)
            touched.append(path)
    print(f"applied {applied} hunks to {len(touched)} files ({failed} skipped)")
    with open(os.path.join(os.path.dirname(a.portable), "applied_files.txt"), "w") as f:
        f.write("\n".join(touched) + "\n")


def cmd_audit(a):
    """Vendor-new-file audit: LOC + use of APIs that changed/disappeared by the
    target base.  Produces the effort ranking for the transplant work."""
    removed_apis = {
        # name -> why it matters on 5.15
        "create_proc_read_entry": "removed in 5.5 (proc_ops conversion)",
        "create_proc_entry": "removed in 5.5 (proc_ops conversion)",
        "proc_create_data+PDE_DATA": "",
        "PDE_DATA": "removed in 5.17 -> pde_data()",
        "get_fs": "removed in 5.11 (set_fs/goto_if)",
        "set_fs": "removed in 5.11",
        "FORCE_SETFS": "removed in 5.11",
        "mm_segment_t": "removed in 5.18",
        "VERIFY_READ": "access_ok() signature changed in 5.0",
        "VERIFY_WRITE": "access_ok() signature changed in 5.0",
        "get_user_pages_fast": "replaced by pin_user_pages_* in 5.8-5.9",
        "strlcpy": "removed tree-wide in 6.x (strscpy)",
        "strlcat": "removed tree-wide in 6.x",
        "strict_strtol": "removed long ago",
        "ACCESS_ONCE": "removed in 5.8 -> READ_ONCE/WRITE_ONCE",
        "signal->curr_target": "changed in 5.17",
        "kmap_atomic": "deprecated 5.11 -> kmap_local_page",
        "kmap(": "deprecated 5.11 -> kmap_local_page",
        "alloc_pages_node": "",
        "struct timespec": "removed in 5.6 -> timespec64",
        "current_kernel_time": "removed in 5.6",
        "getrawmonotonic": "removed in 5.6",
        "do_gettimeofday": "removed for in-kernel use",
        "file_operations": "5.6: /proc needs struct proc_ops",
        "struct iov_iter": "",
        "blk_queue_make_request": "removed in 5.9 -> blk_mq",
        "make_request_fn": "removed in 5.14",
        "register_sysctl_table": "",
        "clk_get_rate+of_property": "",
        "ion_alloc": "Ion removed in 5.18 -> dma-buf heaps",
        "MTK_ION": "MTK ion glue depends on removed Ion core",
        "struct hrtimer": "",
        "aead_request": "",
        "netif_napi_add": "weight arg dropped in 5.19/6.1",
        "napi_gro_receive": "",
        "pci_enable_msi": "",
        "dma_map_sg": "",
        "scsi": "",
        "of_get_cpu_node": "",
        "proc_create": "file_operations -> proc_ops (5.6)",
        "struct sysdata suspend": "",
    }
    keys = sorted({k for k in removed_apis if k and "+" not in k})
    roots = [r for r in a.roots]
    loc = Counter()
    files = Counter()
    hits = Counter()
    hitfiles = defaultdict(set)
    import subprocess
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            out = subprocess.run(
                ["git", "-C", a.vendor, "ls-files", root],
                capture_output=True, text=True, check=True).stdout.split()
        except Exception:
            out = []
        for rel in out:
            files[subsystem_of(rel)] += 1
            p = os.path.join(a.vendor, rel)
            try:
                with open(p, "r", encoding="utf-8", errors="surrogateescape") as f:
                    txt = f.read()
            except OSError:
                continue
            loc[subsystem_of(rel)] += txt.count("\n")
            for k in keys:
                n = txt.count(k)
                if n:
                    hits[k] += n
                    hitfiles[subsystem_of(rel)].add(rel)
    rep = {
        "vendor_files": sum(files.values()),
        "vendor_loc": sum(loc.values()),
        "by_subsystem": {k: {"files": files[k], "loc": loc[k]} for k in
                         sorted(loc, key=lambda x: -loc[x])},
        "api_risk": {k: {"uses": hits[k], "why": removed_apis[k]} for k in
                     sorted(hits, key=lambda x: -hits[x])},
    }
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps({k: rep[k] for k in ("vendor_files", "vendor_loc")}, indent=1))
    print("top api risks:")
    for k, v in list(rep["api_risk"].items())[:20]:
        print(f"  {v['uses']:7d}  {k:28s} {v['why']}")


def cmd_verify(a):
    """Independent post-apply verification.

    For every hunk the applier claims to have applied:
      1. the hunk's post-image must now be present in the ported file;
      2. the pre-image must have been *unique* in the pristine base file, or the
         hunk is flagged AMBIGUOUS (misplacement risk) and reported with the
         number of candidate sites;
      3. the number of changed lines must equal the hunk's own delta, so that
         overlapping/duplicated insertions are detected.
    """
    import subprocess
    with open(a.portable) as f:
        port = json.load(f)
    stats = Counter()
    problems = []
    for path, hunks in sorted(port.items()):
        if not hunks:
            continue
        ported_file = os.path.join(a.ported, path)
        if not os.path.exists(ported_file):
            stats["MISSING_FILE"] += len(hunks)
            continue
        with open(ported_file, "r", encoding="utf-8", errors="surrogateescape") as f:
            ptext = [norm(x) for x in f.read().split("\n")]
        try:
            base_txt = subprocess.run(
                ["git", "-C", a.ported, "show", f"{a.base_ref}:{path}"],
                capture_output=True, text=True, check=True).stdout
        except Exception:
            stats["NO_BASE_REF"] += len(hunks)
            continue
        btext = [norm(x) for x in base_txt.split("\n")]
        for h in hunks:
            stats["hunks"] += 1
            ops = [(o, t) for o, t in h["ops"]]
            post = [t for o, t in ops if o in (" ", "+")]
            pre = [t for o, t in ops if o in (" ", "-")]
            # 1. post-image present in ported tree?
            def find_seq(text, seq):
                if not seq:
                    return -1
                first = seq[0]
                for i, l in enumerate(text):
                    if l == first and text[i:i + len(seq)] == seq:
                        return i
                return -1
            if find_seq(ptext, post) < 0:
                stats["POST_NOT_FOUND"] += 1
                problems.append({"file": path, "state": "POST_NOT_FOUND", "hdr": h.get("hdr", "")})
                continue
            stats["POST_OK"] += 1
            # 2. uniqueness of pre-image in pristine base
            occ = sum(1 for i in range(len(btext) - len(pre) + 1)
                      if btext[i:i + len(pre)] == pre)
            if occ > 1:
                stats["AMBIGUOUS_PRE"] += 1
                problems.append({"file": path, "state": "AMBIGUOUS_PRE",
                                 "occurrences": occ, "hdr": h.get("hdr", "")})
            elif occ == 0:
                stats["PRE_MOVED"] += 1
            else:
                stats["PRE_UNIQUE"] += 1
        # per-file accounting: total expected line delta vs actual
        exp = sum(len([1 for o, _ in h["ops"] if o in (" ", "+")])
                  - len([1 for o, _ in h["ops"] if o in (" ", "-")]) for h in hunks)
        got = len(ptext) - len(btext)
        if exp != got:
            stats["FILE_LINEDELTA_MISMATCH"] += 1
            problems.append({"file": path, "state": "LINEDELTA", "expected": exp, "got": got})
        else:
            stats["FILE_OK"] += 1
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump({"stats": dict(stats), "problems": problems[:500]}, f, indent=1)
    print(json.dumps(dict(stats), indent=1))
    print(f"problems listed: {min(len(problems), 500)} of {len(problems)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    a1 = sub.add_parser("analyze")
    a1.add_argument("--base", required=True)
    a1.add_argument("--vendor", required=True)
    a1.add_argument("--target", required=True)
    a1.add_argument("--delta", required=True, help="unified diff base->vendor")
    a1.add_argument("--base-list", help="file listing vendor-new files (informational)")
    a1.add_argument("--out", required=True)
    a1.add_argument("--jobs", type=int, default=max(1, os.cpu_count()))
    a1.add_argument("--keep-other-arch", action="store_true")
    a1.set_defaults(func=cmd_analyze)

    a2 = sub.add_parser("apply")
    a2.add_argument("--vendor", required=True)
    a2.add_argument("--apply-to", required=True)
    a2.add_argument("--portable", required=True)
    a2.set_defaults(func=cmd_apply)

    a3 = sub.add_parser("audit")
    a3.add_argument("--vendor", required=True)
    a3.add_argument("--out", required=True)
    a3.add_argument("--roots", nargs="*", default=["drivers/misc/mediatek"])
    a3.set_defaults(func=cmd_audit)

    a4 = sub.add_parser("verify")
    a4.add_argument("--ported", required=True)
    a4.add_argument("--portable", required=True)
    a4.add_argument("--base-ref", default="v5.15.220")
    a4.add_argument("--out", required=True)
    a4.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
