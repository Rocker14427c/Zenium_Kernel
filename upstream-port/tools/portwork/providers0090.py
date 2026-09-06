#!/usr/bin/env python3
#
# Two things this script settled, recorded because a conclusion is only as good as its method:
#   * Provider attribution must come from definition-shaped lines. A first-mention grep reports call
#     sites inside already-landed files (ddp_clkmgr.c:320 for _get_dst_module_by_lcm, ddp_irq.c:243
#     for ovl_to_index) and so invents work that belongs to a file nobody landed yet.
#   * grep -E is POSIX ERE: (?:...) is Python-only and matches nothing there. That turned a whole
#     scan into "0 definitions" and briefly looked like a property of the tree instead of the tool.
"""Definition-based provider table for the 78 open names (fixes the earlier first-mention table,
which often reported a *call site* as the provider).

For each name: every vendor .c whose definition-shaped line matches, restricted to this SoC's
provider dirs; plus whether that file is landed in the tree of record.
"""
import json, os, re, subprocess
from collections import defaultdict

REPO = "/home/user/Zenium_Kernel"
SERIES = "/home/user/portwork/series"
OPEN = REPO + "/upstream-port/report/l2-open-names-at-0089.txt"
DIRS = ["drivers/misc/mediatek/video/mt6768", "drivers/misc/mediatek/video/common",
        "drivers/misc/mediatek/video/include", "drivers/misc/mediatek/cmdq",
        "drivers/misc/mediatek/smi", "drivers/misc/mediatek/i2c", "drivers/misc/mediatek/pmic"]
names = [l.strip() for l in open(OPEN) if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", l.strip())][:80]

_cache = {}
def def_re(name):
    if name not in _cache:
        _cache[name] = re.compile(
            r"^(?:static\s+|inline\s+|__init\s+|__maybe_unused\s+|asmlinkage\s+)*"
            r"[A-Za-z_][A-Za-z0-9_\*\s\t]*?[ \t\*]+%s[ \t]*\(" % re.escape(name))
    return _cache[name]

# Which .c files exist in the landed tree, so we can say LANDED vs not
landed = set()
for d, _, fs in os.walk(SERIES + "/drivers/misc/mediatek"):
    for f in fs:
        if f.endswith(".c"):
            landed.add(os.path.relpath(os.path.join(d, f), SERIES))

rows = {}
for n in names:
    p = subprocess.run(["grep", "-rnE", r"\b%s\s*\(" % n] +
                       [os.path.join(REPO, d) for d in DIRS] + ["--include=*.c"],
                       capture_output=True, text=True)
    R = def_re(n)
    hits = []
    for line in p.stdout.splitlines():
        try:
            f, ln, txt = line.split(":", 2)
        except ValueError:
            continue
        t = txt.strip()
        if not R.match(t) or t.endswith(";"):
            continue
        rel = f.replace(REPO + "/", "")
        hits.append((rel, int(ln)))
    rows[n] = hits

by_file = defaultdict(list)
for n in names:
    hits = rows[n]
    if not hits:
        by_file["(no definition in this SoC's provider dirs)"].append(n)
    for rel, ln in hits[:1]:          # primary provider = first definition found
        tag = "LANDED" if rel in landed else "not landed"
        by_file["%s [%s]" % (rel, tag)].append(n)

print("names: %d   with a definition in a provider .c: %d\n" %
      (len(names), sum(len(v) for v in rows.values())))
print("%-78s %-11s %s" % ("PROVIDER (.c holding the definition)", "IN OURS?", "NAMES"))
for f in sorted(by_file, key=lambda x: (-len(by_file[x]), x)):
    ns = by_file[f]
    loc = f.rsplit(" [", 1)[0]
    landed_p = "yes" if "LANDED]" in f else "no"
    print("%-78s %-11s %2d  %s" % (f, landed_p, len(ns), ", ".join(sorted(ns)[:6]) + (" ..." if len(ns) > 6 else "")))
json.dump({n: [list(h) for h in rows[n]] for n in names}, open("/home/user/portwork/providers0090.json", "w"), indent=1)

# line counts per provider file, from the vendor tree
print("\n%-78s %6s" % ("FILE", "LINES"))
seen = {}
for f in by_file:
    if "no definition" in f:
        continue
    rel = f.rsplit(" [", 1)[0]
    if rel in seen:
        continue
    try:
        seen[rel] = sum(1 for _ in open(REPO + "/" + rel, errors="replace"))
    except OSError:
        seen[rel] = -1
for rel, ln in sorted(seen.items(), key=lambda kv: -kv[1]):
    print("%-78s %6d" % (rel, ln))
