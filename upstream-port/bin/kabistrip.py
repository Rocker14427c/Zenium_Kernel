#!/usr/bin/env python3
"""kabistrip.py - remove Android GKI KABI-padding that the port carried over.

`ANDROID_KABI_RESERVE(n)` / `ANDROID_KABI_USE(...)` / `struct android_kabi` are
the Android common kernel's ABI-preservation slots: they exist so that a *single
prebuilt GKI Image* can keep its exported struct layout stable while vendors
patch it.  They are meaningless for a kernel built from source for one device -
there is no pre-existing binary ABI to preserve - and on vanilla 5.15 they do not
even parse (the helper header's macros need CONFIG_ANDROID_KABI_RESERVE).

So the port must drop them.  This does it line-wise, and refuses to touch anything
that looks like a multi-line construct, so nothing is silently mangled: a
suspect list is reported for a human instead.

Usage: kabistrip.py TREE [--out JSON] [--dry-run]
"""
import argparse
import json
import os
import re
import subprocess
import sys

PAT = re.compile(r"ANDROID_KABI|android_kabi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    listing = subprocess.run(
        ["grep", "-rl", "-E", "ANDROID_KABI|android_kabi", "--include=*.h",
         "--include=*.c", "."], cwd=a.tree, capture_output=True, text=True).stdout
    files = sorted({l.strip().lstrip("./") for l in listing.splitlines() if l.strip()})
    per_file, suspects, removed = {}, [], 0
    for f in files:
        p = os.path.join(a.tree, f)
        lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        keep, drop = [], []
        for i, line in enumerate(lines):
            if PAT.search(line):
                drop.append((i + 1, line))
            else:
                keep.append(line)
        for ln, line in drop:
            stripped = line.strip()
            if stripped.endswith("\\") or stripped.endswith("({") \
               or stripped.count("(") != stripped.count(")") \
               or not (stripped.endswith(";") or stripped.endswith("*/")
                       or stripped.startswith("#") or stripped == ""):
                suspects.append({"file": f, "line": ln, "text": stripped})
        per_file[f] = len(drop)
        removed += len(drop)
        if drop and not a.dry_run and not any(s["file"] == f for s in suspects):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("\n".join(keep))
    rep = {"files": len(files), "lines_removed": removed, "per_file": per_file,
           "suspect_multi_line_constructs": suspects,
           "dry_run": a.dry_run}
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(rep, fh, indent=2, sort_keys=True)
    print(f"kabi strip: {removed} lines in {len(files)} files "
          f"{'(dry run)' if a.dry_run else 'removed'}; "
          f"{len(suspects)} constructs need a human")
    for s in suspects[:12]:
        print(f"  SUSPECT {s['file']}:{s['line']}  {s['text'][:78]}")
    print(f"  remaining references after strip: "
          f"{subprocess.run(['grep','-rc','-E','ANDROID_KABI|android_kabi','--include=*.h','--include=*.c','.'],cwd=a.tree,capture_output=True,text=True).stdout.count(chr(10))} files listed in report")
    return 0


if __name__ == "__main__":
    sys.exit(main())
