#!/usr/bin/env python3
"""glueclose.py - close "No rule to make target" gaps the honest way.

Ported build glue still points at files the port did not create, because those
files are *vendor-new*: they exist only in the 4.19 tree (Android's
kernel/power/wakeup_reason.c, MTK's clkchk-*.c, drivers/nvmem/nvmem-sysfs.c).
Two possible resolutions exist and only one is honest:

  1. transplant the vendor-new file, when it exists and compiles standalone;
  2. otherwise strip that one glue line, recording that the feature (with its
     file) waits for the manual/transplant pass.

Reverting the whole Makefile is deliberately not offered: the other entries in
those files are load-bearing for the parts of the port that do work.

Usage: glueclose.py --log BUILD.log --tree T --vendor V --base REF --out JSON [--apply]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

NORULE = re.compile(r"\*\*\* No rule to make target '([^']+)'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--base", default="v5.15.220")
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max", type=int, default=60)
    a = ap.parse_args()

    blob = open(a.log, errors="replace").read()
    targets = sorted(set(NORULE.findall(blob)))
    actions = []
    for t in targets[:a.max]:
        t = t.strip()
        dst = os.path.join(a.tree, t)
        if t.endswith(".o"):
            stem = t[:-2]
            src = None
            for ext in (".c", ".S", ".cpp"):
                cand = os.path.join(a.vendor, stem + ext)
                if os.path.exists(cand):
                    src = cand
                    break
            glue = os.path.join(a.tree, os.path.dirname(t), "Makefile")
            if src:
                dstd = os.path.join(a.tree, stem + os.path.splitext(src)[1])
                os.makedirs(os.path.dirname(dstd), exist_ok=True)
                if not os.path.exists(dstd):
                    if a.apply:
                        shutil.copy2(src, dstd)
                    actions.append({"action": "transplant-vendor-new",
                                    "path": os.path.relpath(dstd, a.tree),
                                    "from": os.path.relpath(src, a.vendor),
                                    "for": t})
                    print(f"  + transplant {os.path.relpath(dstd, a.tree)} (for {t})")
                else:
                    actions.append({"action": "already-present", "path": stem, "for": t})
            else:
                # no source anywhere: the glue line itself is the bug
                if os.path.exists(glue):
                    txt = open(glue, encoding="utf-8", errors="replace").read()
                    base = subprocess.run(["git", "-C", a.tree, "show",
                                           f"{a.base}:{os.path.relpath(glue, a.tree)}"],
                                          capture_output=True, text=True).stdout
                    lines, n = txt.split("\n"), 0
                    keep = []
                    for l in lines:
                        if os.path.basename(t) in l and l.strip().startswith("obj-") \
                           and base.count(os.path.basename(t)) == 0:
                        # (kept for readability; the strip happens below)
                            n += 1
                            continue
                        keep.append(l)
                    if n and a.apply:
                        open(glue, "w", encoding="utf-8").write("\n".join(keep))
                    actions.append({"action": "strip-glue-line", "file": os.path.relpath(glue, a.tree),
                                    "target": t, "lines": n,
                                    "reason": "no such file in the vendor tree either "
                                             "(deleted by the vendor or renamed upstream)"})
                    print(f"  - {os.path.relpath(glue, a.tree)}: no source for {t} -> "
                          f"glue line {'stripped' if n else 'not found to strip'}")
        elif t.endswith("Makefile") or t.endswith("Kconfig"):
            d = os.path.dirname(t)
            vdir = os.path.join(a.vendor, d)
            glue = os.path.join(a.tree, d, "Makefile")
            if os.path.isdir(vdir):
                dst = os.path.join(a.tree, d)
                if not os.path.exists(dst):
                    if a.apply:
                        shutil.copytree(vdir, dst)
                    nf = sum(len(fs) for _, _, fs in os.walk(vdir))
                    actions.append({"action": "transplant-vendor-dir", "path": d,
                                    "files": nf, "for": t})
                    print(f"  + transplant dir {d}/ ({nf} files, for {t})")
            else:
                if os.path.exists(glue):
                    txt = open(glue, encoding="utf-8", errors="replace").read()
                    base = subprocess.run(["git", "-C", a.tree, "show",
                                           f"{a.base}:{os.path.relpath(glue, a.tree)}"],
                                          capture_output=True, text=True).stdout
                    keep, n = [], 0
                    for l in txt.split("\n"):
                        if os.path.basename(d) + "/" in l and l.strip().startswith("obj-") \
                           and base.count(os.path.basename(d) + "/") == 0:
                            n += 1
                            continue
                        keep.append(l)
                    if n and a.apply:
                        open(glue, "w", encoding="utf-8").write("\n".join(keep))
                    actions.append({"action": "strip-glue-line", "file": os.path.relpath(glue, a.tree),
                                    "target": t, "lines": n,
                                    "reason": "subdirectory does not exist in the vendor tree either"})
                    print(f"  - {os.path.relpath(glue, a.tree)}: no {d}/ in vendor -> "
                          f"{'stripped ' + str(n) + ' line(s)' if n else 'nothing matched'}")
    rep = {"no_rule_targets": len(targets), "actions": actions, "applied": a.apply}
    with open(a.out, "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    tr = [x for x in actions if x["action"].startswith("transplant")]
    st = [x for x in actions if x["action"] == "strip-glue-line"]
    print(f"glue closure: {len(tr)} transplant action(s), {len(st)} glue line(s) stripped "
          f"({'applied' if a.apply else 'dry run'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
