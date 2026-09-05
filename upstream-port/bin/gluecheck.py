#!/usr/bin/env python3
"""gluecheck.py - verify that every build-glue reference resolves in the tree.

Hunk-level porting is content-exact but not *whole-tree* coherent: a ported
`source "drivers/foo/Kconfig"` or `obj-y += bar/` line is only meaningful if the
directory it points at also exists.  Vendor trees are full of such glue for code
that lives in the 29k vendor-new files, so the portable subset must either drag
those directories in or leave the glue alone.  This script finds the difference.

Two reference dialects are checked, both of which stop the build immediately:

  Kconfig   `source|rsource|osource "path"`  -> path must exist
  Makefile  `obj-*(...) += dir/`              -> dir must exist

Each offender is attributed: `introduced-by-port` when the line was added by the
ported delta, `pre-existing` when base already had it (so it is not our bug).

Usage: gluecheck.py TREE --base REF [--files LIST] --out JSON
"""
import argparse
import json
import os
import re
import subprocess
import sys

# vendor Kconfig sometimes omits the quotes, which kconfig rejects outright;
# accept both spellings so the gate sees every reference.
SRC_RE = re.compile(r'^\s*(rsource|osource|source)\s+"?([^"\s]+)"?')
OBJ_RE = re.compile(r'^\s*(?:obj-[yM]\s*\+?=|obj-\$[^+]*\+?=)\s*(.+)$')
SUBDIR_RE = re.compile(r'([A-Za-z0-9._\-/]+/)')


def added_lines(tree, base, path):
    """lines the port added (the '+' side), as a set of stripped texts"""
    try:
        out = subprocess.run(["git", "-C", tree, "diff", "--unified=0", base, "--", path],
                             capture_output=True)
    except Exception:
        return set()
    return {l[1:].strip() for l in out.stdout.decode("utf-8", "replace").splitlines()
            if l.startswith("+") and not l.startswith("+++")}


def glue_files(tree):
    files = subprocess.run(["git", "-C", tree, "ls-files"],
                           capture_output=True).stdout.decode().splitlines()
    return [f for f in files
            if os.path.basename(f).startswith(("Kconfig", "Makefile"))
            or f.endswith((".mk",))
            or "/Kconfig." in f]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--base", required=True)
    ap.add_argument("--files", help="restrict to this list of paths")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--strip-dangling", action="store_true",
                    help="remove port-added fatal dangling references (records them)")
    a = ap.parse_args()

    if a.files:
        wanted = {l.strip() for l in open(a.files) if l.strip()}
        files = [f for f in glue_files(a.tree) if f in wanted]
    else:
        files = glue_files(a.tree)

    bad, checked = [], 0
    for f in files:
        p = os.path.join(a.tree, f)
        if not os.path.exists(p):
            continue
        checked += 1
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        added = added_lines(a.tree, a.base, f)
        d = os.path.dirname(f)
        for i, line in enumerate(text.splitlines(), 1):
            refs = []
            m = SRC_RE.match(line)
            if m:
                refs.append(m.group(2))
                base_dir = d  # `source` is relative to srctree in practice; try both
            if "source" in line and not SRC_RE.match(line):
                pass
            sev = "fatal"
            if OBJ_RE.match(line):
                # obj-$(CONFIG_FOO) is only descended when FOO is on; obj-y is not
                seg = line.split("=", 1)[0]
                if "$(CONFIG_" in seg or "$(CONFIG_" in line.split("+=")[0]:
                    sev = "conditional"
            if OBJ_RE.match(line):
                for sub in SUBDIR_RE.findall(OBJ_RE.match(line).group(1)):
                    if sub.startswith(("$(", "$(", "./")):
                        continue
                    refs.append(os.path.normpath(os.path.join(d, sub)))
            for r in refs:
                # Kconfig `source` is srctree-relative, `rsource` file-relative;
                # Makefile dirs are file-relative.  Trying all of them avoids
                # false alarms, but never the glue file itself.
                cands = [c for c in (os.path.join(a.tree, r),
                                     os.path.join(a.tree, d, r)) if c]
                if any(os.path.exists(c) for c in cands):
                    continue
                bad.append({"file": f, "line": i, "text": line.strip(),
                            "missing": r, "severity": sev,
                            "origin": "introduced-by-port"
                            if line.strip() in added else "pre-existing"})
    intro = [b for b in bad if b["origin"] == "introduced-by-port"]
    if a.strip_dangling:
        byfile = {}
        for b in intro:
            if b["severity"] == "fatal":
                byfile.setdefault(b["file"], set()).add(b["line"])
        n = 0
        for f, lines in sorted(byfile.items()):
            p2 = os.path.join(a.tree, f)
            keep, removed = [], []
            drop_at = {}
            for i, line in enumerate(open(p2, encoding="utf-8", errors="replace").read().splitlines(), 1):
                if i in lines:
                    # A vendor line often lists several entries
                    # (`obj-y += drm/ vga/ mediatek/`); deleting the whole line
                    # would silently unbuild drm/ and vga/ too.  Remove only the
                    # missing token, and drop the line only if nothing is left.
                    missing = [b["missing"] for b in intro
                               if b["file"] == f and b["line"] == i and b["severity"] == "fatal"]
                    tok = {os.path.basename(m.rstrip("/")) + "/" for m in missing}
                    head, _, tail = line.partition("+=")
                    if not tok or "/*" in line or not tail.strip():
                        removed.append(line); n += 1
                        continue
                    entries = tail.split()
                    left = [e for e in entries if e not in tok and
                           not any(e == t or e.endswith("/" + t) for t in tok)]
                    if len(left) == len(entries):
                        left = [e for e in entries if os.path.basename(e.rstrip("/")) + "/" not in tok]
                    if not left:
                        removed.append(line); n += 1
                        continue
                    newl = (head + "+= " + " ".join(left)).rstrip()
                    removed.append(line)
                    drop_at[i] = newl
                    n += 1
                    print(f"    rewrote {f}:{i} to keep the surviving entries: {newl.strip()}")
                    keep.append(newl)
                    continue
                else:
                    keep.append(line)
            with open(p2, "w", encoding="utf-8") as fh:
                fh.write("\n".join(keep) + "\n")
            print(f"  stripped {len(removed)} dangling glue line(s) from {f}")
        print(f"glue gate: stripped {n} fatal dangling reference(s); "
              f"they return with their driver directories in the transplant phase")
        with open(a.out + ".stripped", "w") as fh:
            json.dump({"stripped_lines": n,
                       "detail": {f: sorted(v) for f, v in byfile.items()}}, fh, indent=2)
        bad = [b for b in bad if b["severity"] != "fatal"
               or b["origin"] != "introduced-by-port"]
        intro = [b for b in bad if b["origin"] == "introduced-by-port"]
    rep = {"glue_files_checked": checked, "dangling_total": len(bad),
           "dangling_introduced_by_port": len(intro),
           "dangling_pre_existing": len(bad) - len(intro),
           "files_introduced": sorted({b["file"] for b in intro}),
           "items": bad[:4000]}
    with open(a.out, "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    print(f"glue gate: {checked} build-glue files scanned; "
          f"{len(intro)} dangling references introduced by the port "
          f"(+{len(bad)-len(intro)} already dangling in base)")
    for b in intro[:a.limit]:
        print(f"  {b['file']}:{b['line']}  {b['text'][:70]}  -> MISSING {b['missing']}")
    if len(intro) > a.limit:
        print(f"  ... {len(intro)-a.limit} more in {a.out}")
    return 1 if intro else 0


if __name__ == "__main__":
    sys.exit(main())
