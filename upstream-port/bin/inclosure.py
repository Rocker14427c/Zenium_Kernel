#!/usr/bin/env python3
"""inclosure.py - transplant the vendor-new *headers* that ported code demands.

A hunk-level port only rewrites files that exist on both sides.  But vendor code
routinely #includes headers that exist only in the vendor tree (Android's
<linux/android_kabi.h>, OPlus feature headers, MTK driver headers).  Without them
the ported tree cannot compile, so the honest move is to grow the tree by exactly
the closure of what is referenced - and no further.

Algorithm
  1. Collect every #include from the files the port touched.
  2. Resolve each against the ported tree (include/, arch/$(ARCH)/include/, the
     including file's own directory).
  3. Unresolved ones are looked up at the same path in the vendor tree; on a hit
     the vendor file is copied in (recorded), and its own includes are queued -
     i.e. a real closure, bounded by --rounds.
  4. Anything still unresolved is reported so it can be decided by hand, never
     silently dropped.

Every copied file is logged with its origin so the migration ledger can say
precisely what the ported tree gained.

Usage: inclosure.py --tree TREE --vendor VENDOR --files LIST --out JSON [--apply]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

INC = re.compile(r'^\s*#\s*include\s*(?:<([^>]+)>|"([^"]+)")', re.M)


def find_header(root, rel):
    """where would the compiler resolve `rel`? returns abs path or None"""
    for cand in (os.path.join(root, "include", rel),
                 os.path.join(root, "arch/arm64/include", rel),
                 os.path.join(root, "arch/arm64/include/uapi", rel),
                 os.path.join(root, "include/uapi", rel),
                 os.path.join(root, "include/asm-generic", rel)):
        if os.path.exists(cand):
            return cand
    return None


def vendor_lookup(vendor, rel):
    """absolute path of a vendor header, preferring the canonical include dirs"""
    for cand in (os.path.join(vendor, "include", rel),
                 os.path.join(vendor, "arch/arm64/include", rel),
                 os.path.join(vendor, "arch/arm64/include/uapi", rel),
                 os.path.join(vendor, "include/uapi", rel),
                 os.path.join(vendor, "drivers", rel)):
        if os.path.exists(cand):
            return cand
    # last resort: unique match by basename anywhere in the vendor tree
    base = os.path.basename(rel)
    out = subprocess.run(["git", "-C", vendor, "ls-files", f"*/{base}", base],
                         capture_output=True, text=True).stdout.split()
    hits = [h for h in out if h.endswith("/" + rel) or os.path.basename(h) == base]
    if len(set(hits)) == 1:
        return os.path.join(vendor, hits[0])
    return None


def dest_for(vendor_path, vendor):
    rel = os.path.relpath(vendor_path, vendor)
    for pre in ("include/", "arch/arm64/include/", "drivers/"):
        if rel.startswith(pre):
            return rel
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--files", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--base", default="v5.15.220")
    ap.add_argument("--all-includes", dest="only_added", action="store_false",
                    help="also consider includes already present in the base file")
    ap.set_defaults(only_added=True)
    a = ap.parse_args()

    touch = [l.strip() for l in open(a.files) if l.strip()]
    queued = [t for t in touch if t.endswith((".c", ".h", ".S"))]
    added = {}
    if a.only_added:
        keep = []
        for f in queued:
            d = subprocess.run(["git", "-C", a.tree, "diff", "--unified=0", a.base, "--", f],
                               capture_output=True, text=True).stdout
            lines = {l[1:].strip() for l in d.splitlines()
                     if l.startswith("+") and not l.startswith("+++")}
            if lines:
                added[f] = lines
                keep.append(f)
        queued = keep
        print(f"attribution: {len(queued)} files have port-added lines to scan")
    copied, unresolved, seen = [], [], set()
    for rnd in range(a.rounds):
        need = {}                      # rel include path -> set(from file)
        for f in queued:
            p = os.path.join(a.tree, f) if not f.startswith(a.tree) else f
            if not os.path.exists(p):
                continue
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            incs = INC.finditer(text) if not a.only_added else                    INC.finditer("\n".join(sorted(added[f])))
            for m in incs:
                rel = m.group(1) or m.group(2)
                if rel in seen:
                    continue
                if rel.startswith(("linux/", "asm/", "uapi/", "dt-bindings/",
                                    "media/", "soc/", "sound/", "drm/", "net/",
                                    "mtd/", "usb/", "kvm/", "xen/", "config/")):
                    if find_header(a.tree, rel):
                        continue
                    need.setdefault(rel, set()).add(f)
                else:
                    # quoted, file-relative include
                    if os.path.exists(os.path.join(a.tree, os.path.dirname(f), rel)) \
                       or find_header(a.tree, rel):
                        continue
                    need.setdefault(rel, set()).add(f)
        if not need:
            print(f"round {rnd}: nothing unresolved -> closure complete")
            break
        queued = []
        for rel, froms in sorted(need.items()):
            seen.add(rel)
            vp = vendor_lookup(a.vendor, rel)
            if not vp:
                unresolved.append({"include": rel, "needed_by": sorted(froms)[:6]})
                continue
            dst_rel = dest_for(vp, a.vendor)
            dst = os.path.join(a.tree, dst_rel)
            copied.append({"include": rel, "vendor_path": dst_rel,
                           "needed_by": sorted(froms)[:6],
                           "lines": sum(1 for _ in open(vp, encoding="utf-8", errors="replace"))})
            if a.apply and not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(vp, dst)
                queued.append(dst_rel)
        print(f"round {rnd}: {len(need)} unresolved, "
              f"{len(copied) and 'vendor hits found'} -> {len(queued)} newly copied headers to scan")
        if not queued:
            break
    rep = {"apply": a.apply, "copied_total": len(copied),
           "copied": copied, "unresolved_total": len(unresolved),
           "unresolved": unresolved}
    with open(a.out, "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    print(f"{'COPIED' if a.apply else 'DRY RUN'}: {len(copied)} vendor headers needed by ported code; "
          f"{len(unresolved)} still unresolved (see {a.out})")
    for u in unresolved[:15]:
        print(f"  unresolved <{u['include']}>  from {u['needed_by'][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
