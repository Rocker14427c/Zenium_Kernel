#!/usr/bin/env python3
#
# Two things this script settled, recorded because a conclusion is only as good as its method:
#   * Provider attribution must come from definition-shaped lines. A first-mention grep reports call
#     sites inside already-landed files (ddp_clkmgr.c:320 for _get_dst_module_by_lcm, ddp_irq.c:243
#     for ovl_to_index) and so invents work that belongs to a file nobody landed yet.
#   * grep -E is POSIX ERE: (?:...) is Python-only and matches nothing there. That turned a whole
#     scan into "0 definitions" and briefly looked like a property of the tree instead of the tool.
"""Per-name classification of the 78 open names at 0089, against the *landed* tree.

For each name: find a definition in the landed tree; if found, report the file:line and the
guard stack that encloses it (so we can tell "not ported" from "ported but compiled out"), and
the stock value of each guard symbol (even_defconfig) vs our config of record.
"""
import json, os, re, subprocess, sys

SERIES = "/home/user/portwork/series"
REPO = "/home/user/Zenium_Kernel"
NAMES = [l.strip() for l in open(REPO + "/upstream-port/report/l2-open-names-at-0089.txt")
         if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", l.strip())]
NAMES = NAMES[:80]
SUB = "drivers/misc/mediatek"

_DEF_CACHE = {}
def def_re(name):
    if name not in _DEF_CACHE:
        _DEF_CACHE[name] = re.compile(
            r"^(?:static\s+|inline\s+|__init\s+|__maybe_unused\s+)*"
            r"[A-Za-z_][A-Za-z0-9_\*\s\t]*?[ \t\*]+%s[ \t]*\(" % re.escape(name))
    return _DEF_CACHE[name]
def defs_in(root, name):
    """Definition-like lines for `name` in root/SUB: at line start, return type present, no ';'.
    grep does the scanning with an ERE-safe pattern; Python does the real filtering."""
    DEF_RE = def_re(name)
    out = []
    p = subprocess.run(["grep", "-rnE", "\\b%s\\s*\\(" % name,
                        os.path.join(root, SUB), "--include=*.c", "--include=*.h"],
                       capture_output=True, text=True)
    for line in p.stdout.splitlines():
        try:
            f, ln, txt = line.split(":", 2)
        except ValueError:
            continue
        t = txt.strip()
        if not DEF_RE.match(t):
            continue
        if t.endswith(";"):
            continue                                  # prototype / decl
        if "&&" in t or "||" in t or t.startswith("return"):
            continue
        out.append((f.replace(root + "/", ""), int(ln), t))
    return out

def guard_stack(path, upto):
    """#if/#ifdef directives still open at line `upto` (1-based)."""
    stack, depth = [], []
    try:
        lines = open(path, errors="replace").read().split("\n")
    except OSError:
        return []
    for i, l in enumerate(lines[:upto], 1):
        s = l.strip()
        if re.match(r"#\s*(if|ifdef|ifndef)\b", s):
            depth.append((i, s))
        elif re.match(r"#\s*endif\b", s):
            if depth:
                depth.pop()
    return depth

stock = {}
cfg = {}
def load_kv(path, d):
    for l in open(path, errors="replace"):
        m = re.match(r"\s*CONFIG_([A-Za-z0-9_]+)\s*=\s*(\S+)", l)
        if m:
            d[m.group(1)] = m.group(2)
        m = re.match(r"\s*CONFIG_([A-Za-z0-9_]+)\s+([ymn])\b", l)
        if m:
            d.setdefault(m.group(1), m.group(2))
load_kv(os.path.join(REPO, "arch/arm64/configs/even_defconfig"), stock)
load_kv(SERIES + "/.config", cfg)

_mc = {}
def macro_state(sym):
    if sym not in _mc:
        r = subprocess.run("grep -rlE 'define[[:space:]]+%s\b' %s/drivers/misc/mediatek 2>/dev/null | head -2; "
                           "grep -rlE '\\-D%s\\b' %s/drivers/misc/mediatek --include=Makefile --include=Kbuild 2>/dev/null | head -2"
                           % (sym, REPO, sym, REPO), shell=True, capture_output=True, text=True)
        hits = [h for h in r.stdout.split() if h]
        _mc[sym] = ("defined in " + ",".join(os.path.basename(h) for h in hits)) if hits else "not defined anywhere in drivers/misc/mediatek"
    return _mc[sym]

def state(sym):
    s = stock.get(sym, "ABSENT")
    o = cfg.get(sym, "ABSENT")
    return "%s/%s" % (s, o)

rows, landed_def, vendor_only = [], [], []
for n in NAMES:
    d = defs_in(SERIES, n)
    if d:
        f, ln, txt = d[0]
        gs = guard_stack(os.path.join(SERIES, f), ln)
        parts = []
        for i, m in gs:
            syms = re.findall(r"C?ONFIG_([A-Za-z0-9_]+)", m)
            plain = [s for s in re.findall(r"defined\s*\(\s*([A-Za-z0-9_]+)", m)]
            vals = "; ".join("%s %s" % (s, state(s)) for s in syms)
            vals += "".join(", %s %s" % (s, macro_state(s)) for s in plain)
            parts.append("@%d [%s] %s" % (i, m, vals or "(macro/no CONFIG)"))
        gtxt = " || ".join(parts) or "(unguarded)"
        rows.append((n, "IN-LANDED-TREE", "%s:%d" % (f, ln), gtxt))
        landed_def.append(n)
    else:
        v = defs_in(REPO, n)
        rows.append((n, "vendor-only", v[0][0] + ":" + str(v[0][1]) if v else "no definition found in vendor video/", ""))
        vendor_only.append(n)

print("open names examined: %d   defined in the landed tree: %d   not in the tree: %d"
      % (len(NAMES), len(landed_def), len(vendor_only)))
print("\n### A. name is IN A FILE WE ALREADY LANDED but its guard arm excludes it ###")
for n, k, loc, g in rows:
    if k == "IN-LANDED-TREE":
        print("  %-38s %s\n        guards: %s" % (n, loc, g))
print("\n### B. name's provider is NOT in the tree ###")
from collections import defaultdict
by = defaultdict(list)
for n, k, loc, g in rows:
    if k != "IN-LANDED-TREE":
        by[loc.split(":")[0]].append(n)
for f in sorted(by, key=lambda x: -len(by[x])):
    print("  %-72s %2d names" % (f, len(by[f])))
json.dump([{"name": n, "kind": k, "loc": loc, "guards": g} for n, k, loc, g in rows],
          open("/home/user/portwork/namecensus0090.json", "w"), indent=1)
print("\nwrote /home/user/portwork/namecensus0090.json  (stock/ours config pairs are 'stock/ours')")
