#!/usr/bin/env python3
"""gluefix.py - drive kconfig/make until build glue parses, reverting offenders.

A hunk matched by context alone can land in the wrong region of a Kconfig file
(an ambiguous pre-image), producing syntax that no longer parses, or a stray C
statement spliced into a menu.  Rather than guessing, run the real parser and
let it point at the file: revert just that file to the base kernel and record the
decision, so nothing is silently dropped and the whole pass is reproducible.

Only *build glue* is handled here (Kconfig/Makefile).  C sources are fixed by the
compiler in the build phase, which is a stricter judge than any script.

Usage: gluefix.py TREE --base REF --out JSON [--target defconfig]
"""
import argparse
import json
import os
import re
import subprocess
import sys

ERR = re.compile(r"^([A-Za-z0-9_./-]+):(\d+):\s*(.+)$")
GLUE_HINT = re.compile(r"(unknown statement|invalid statement|can't open file|"
                       r"syntax error|unexpected|no rule to make target|"
                       r"only one 'else'|unterminated)")


def run_make(tree, target, extra):
    return subprocess.run(["make", "-C", tree, f"--output-sync=recurse", target] + extra,
                          capture_output=True, text=True, cwd=tree)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", default="defconfig")
    ap.add_argument("--max-iters", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    decisions, seen, ok = [], set(), False
    for it in range(a.max_iters):
        p = run_make(a.tree, a.target, ["ARCH=arm64", "LLVM=1", "HOSTCC=gcc"])
        blob = (p.stdout or "") + "\n" + (p.stderr or "")
        if p.returncode == 0:
            ok = True
            print(f"[{it}] {a.target}: clean")
            break
        hit = None
        for line in blob.splitlines():
            m = ERR.match(line.strip())
            if m and GLUE_HINT.search(m.group(3)):
                cand = m.group(1)
                if os.path.basename(cand).startswith(("Kconfig", "Makefile")) \
                        or cand.endswith((".mk", "Makefile")):
                    hit = (cand, int(m.group(2)), m.group(3))
                    break
        if not hit:
            print(f"[{it}] remaining failure is not build glue; handing off to the compiler")
            print("\n".join(l for l in blob.splitlines() if "Error" in l or "error" in l)[:2000])
            break
        f, ln, msg = hit
        print(f"[{it}] {f}:{ln}: {msg}")
        if f in seen:
            print(f"  {f} already reverted once but still failing -> stop, needs a human")
            decisions.append({"file": f, "line": ln, "error": msg,
                              "action": "STILL_BROKEN_AFTER_REVERT"})
            break
        seen.add(f)
        if not a.dry_run:
            # how much ported content does the revert give up?
            diff = subprocess.run(["git", "-C", a.tree, "diff", "--numstat", a.base, "--", f],
                                  capture_output=True, text=True).stdout.strip()
            adds = dels = 0
            if diff:
                parts = diff.split("\t")
                adds, dels = int(parts[0] or 0), int(parts[1] or 0)
            subprocess.run(["git", "-C", a.tree, "checkout", a.base, "--", f],
                           capture_output=True)
            decisions.append({"file": f, "line": ln, "error": msg,
                              "action": "reverted-to-base",
                              "hunks_lost_lines": {"+": adds, "-": dels}})
            print(f"  reverted {f} to base (giving up +{adds}/-{dels} ported lines)")
    rep = {"target": a.target, "clean": ok, "iterations": it + 1,
           "files_reverted": sorted(d["file"] for d in decisions if d["action"] == "reverted-to-base"),
           "decisions": decisions}
    with open(a.out, "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    print(f"wrote {a.out}: clean={ok}, {len(rep['files_reverted'])} glue files reverted")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
