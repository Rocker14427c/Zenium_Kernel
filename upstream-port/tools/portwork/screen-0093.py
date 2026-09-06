#!/usr/bin/env python3
"""screen-0093.py - static screen: which unlanded vendor display file could define a name that the port
still has open (env overrides: VENDOR_VIDEO, TREE, OPEN_BASE), before spending a build on it.

For every .c the vendor's mt6768 display build mentions (dispsys + videox + the common dirs it descends
into unconditionally or for this platform), minus what the port already compiles, collect the file-scope
definition names (a `^ident(` style line, plus `static ident(`), and intersect with
report/l2-open-names-at-0092.txt. Files with no intersection cannot reduce the open set this round, so
they need no probe. This is a *screen*, not a measurement: the gate numbers come from the link.
"""
import os, re

V = os.environ.get("VENDOR_VIDEO", "/home/user/Zenium_Kernel/drivers/misc/mediatek/video")
P = os.environ.get("TREE", "/home/user/portwork/series")
OPEN = os.environ.get("OPEN_BASE",
       "/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0092.txt")
open_names = set(l.strip() for l in open(OPEN) if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", l.strip()))

def objs_from_makefile(path):
    """join continuation lines, then pull every *.o named on an obj- line; keep the guard context."""
    if not os.path.isfile(path):
        return []
    raw = open(path, errors="ignore").read().split("\n")
    joined, buf, ctx = [], [], []
    for l in raw:
        ctx.append(l)
        buf.append(l)
        if l.rstrip().endswith("\\"):
            continue
        joined.append((" | ".join(x for x in ctx if re.match(r"^\s*(if|else|endif)", x)), " ".join(buf)))
        buf, ctx = [], []
    out = []
    for guard, line in joined:
        if "obj-" not in line:
            continue
        for o in re.findall(r"([a-zA-Z_0-9]+)\.o", line):
            out.append((o + ".c", guard.strip()))
    return out

landed = set()
for mk in ("mt6768/dispsys/Makefile", "mt6768/videox/Makefile"):
    for o, _ in objs_from_makefile(os.path.join(P, "drivers/misc/mediatek/video", mk)):
        landed.add(o)

cands = {}
for d, label in (("mt6768/dispsys", "dispsys"), ("mt6768/videox", "videox")):
    for o, guard in objs_from_makefile(os.path.join(V, d, "Makefile")):
        if os.path.isfile(os.path.join(V, d, o)):
            cands.setdefault(o, (label + "/" + d.split("/")[1], guard))
# common dirs the vendor descends into for this platform (video/common/Makefile:55-63)
for d in sorted(os.listdir(os.path.join(V, "common"))):
    p = os.path.join(V, "common", d)
    if not os.path.isdir(p):
        continue
    for f in sorted(os.listdir(p)):
        if f.endswith(".c"):
            cands.setdefault(f, ("common/" + d, "obj-y" if d in ("pwm10", "corr10", "color20", "aal30", "layering_rule_base") else "not built for mt6768"))

def defs(path):
    s = open(path, errors="ignore").read()
    # file-scope definition: line begins at col 0 with `type name(` or `name(`, ends with `{` on that or a later line
    out = set()
    for m in re.finditer(r"^(?:[a-zA-Z_][\w \t\*]*?\s)?\b([a-zA-Z_]\w*)\s*\([^;]*?\)\s*\{", s, re.M):
        out.add(m.group(1))
    for m in re.finditer(r"^(?:static\s+)?(?:const\s+|unsigned\s+|struct\s+\w+\s*[ \t]*|[a-zA-Z_]\w*[ \t*]+)+([a-zA-Z_]\w*)\s*\([^;)]*[^;]*$", s, re.M):
        out.add(m.group(1))
    out |= set(re.findall(r"^(?:static\s+)?(?:const\s+)?(?:struct\s+\w+|union\s+\w+)?\s*\*?\s*([a-zA-Z_]\w*)\s*\(", s, re.M))
    for m in re.finditer(r"^(?:struct|union|enum)\s+\w+\s+([a-zA-Z_]\w*)\s*(?:\[[^\]]*\])?\s*=", s, re.M):
        out.add(m.group(1))
    for m in re.finditer(r"^(?:int|void|u32|s32|unsigned\s+long|long|bool|static\s+\w+[\w \t\*]*)\s+\**([a-zA-Z_]\w*)\s*\(", s, re.M):
        out.add(m.group(1))
    return {x for x in out if x}

rows = []
for f, (src, guard) in sorted(cands.items()):
    if f in landed:
        continue
    path = None
    for base in (os.path.join(V, "mt6768", "dispsys"), os.path.join(V, "mt6768", "videox")) + tuple(os.path.join(V, "common", x) for x in os.listdir(os.path.join(V, "common")) if os.path.isdir(os.path.join(V, "common", x))):
        if os.path.isfile(os.path.join(base, f)):
            path = os.path.join(base, f)
            break
    if not path:
        continue
    d = defs(path)
    hit = sorted(open_names & d)
    rows.append((len(hit), f, src, guard[:44], hit))
rows.sort(reverse=True)
print("open names at 0092: %d ; unlanded vendor display .c files screened: %d\n" % (len(open_names), len(rows)))
print("%-4s %-28s %-22s %s" % ("n", "file", "vendor dir", "could define (of the 57)"))
for n, f, src, guard, hit in rows:
    if n:
        print("%-4d %-28s %-22s %s" % (n, f, src, " ".join(hit)[:120]))
print("\nfiles screened out (define none of the 57): %d" % sum(1 for r in rows if not r[0]))
print("  " + " ".join(r[1] for r in rows if not r[0]))
