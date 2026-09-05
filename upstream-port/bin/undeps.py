#!/usr/bin/env python3
"""undeps.py - classify the unresolved externals of a built directory, without pretending it is a link.

A per-directory build here has ~80 objects out of ~7,400, so a naive `nm -u` diff makes almost every
symbol look "missing". That already produced one wrong sentence in a report (it listed `snprintf`,
`vunmap` and `simple_read_from_buffer` as needing a provider, when the provider is simply vmlinux,
which a per-directory pass never builds). The question the next slice actually needs answered is
narrower: which names still have no provider ANYWHERE in this tree.

Classes, in decision order:
  satisfied                      defined by an object that exists in this tree (nm type T D B R W V,
                                 and file-local t d b are not counted as providers of other objects
                                 - except that nm -u of one object is satisfied by another's T only)
  core (vmlinux)                 declared as a function-like name in a mainline header
                                 (include/linux, include/uapi/linux, include/asm-generic,
                                  arch/arm64/include) or one of the mem/str helpers the compiler
                                 itself emits calls to. The provider exists; this pass just does not
                                 build it. NOT a blocker.
  provider landed, not built     a .c in this tree defines the name but its .o is absent (CONFIG off,
                                 or the file is in a directory the gate did not build)
  PROVIDER NOT LANDED            nothing in this tree defines it. Attributed to the vendor file that
                                 does, preferring the mt6768 copy over the mt6765 one. This is the
                                 dependency-order list the next slice is made of.

Usage: undeps.py --tree TREE --objs DIR [--vendor REPO] [--nm PREFIXnm] [--json]
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter

# Names the compiler emits calls to that no header declares in the form we grep for.
COMPILER_BUILTINS = {
    "memcpy", "memmove", "memset", "memcmp", "__memcpy", "__memmove", "__memset",
    "strlen", "strnlen", "strcmp", "strncmp", "strcpy", "strncpy", "strcat", "strncat",
    "snprintf", "vsnprintf", "sprintf", "vsprintf", "scnprintf", "vscnprintf", "sscanf",
    "__cmpdi2", "__aeabi_uidiv", "__aeabi_idiv", "__aeabi_uldivmod", "__udivdi3", "__divdi3",
    "__ffs", "__fls", "__ashldi3", "__ashrdi3", "__lshrdi3", "ftrace_likely_update",
}
# A C function definition: return type + name + params + '{' at column 0, no ';' before the brace.
DEF_RE = re.compile(r"^[a-zA-Z_][\w \t\*]*?\b([a-zA-Z_]\w*)\s*\([^;{}]*?\)\s*(?:__[a-z_]+\s*)?\{", re.M)
DECL_CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]{2,})\s*\(")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def nm_chunked(nmtool, args, files):
    out = []
    for i in range(0, len(files), 200):
        out.append(run([nmtool] + args + files[i:i + 200]))
    return "\n".join(out)


def walk_o(root):
    for r, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in fs:
            if f.endswith(".o"):
                yield os.path.join(r, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--objs", required=True, nargs="+",
                    help="director(y/ies) relative to --tree whose .o are checked; a slice that spans "
                         "two directories (dispsys + videox) has to be checked as one set, because a "
                         "symbol satisfied by the sibling is not a blocker")
    ap.add_argument("--vendor", default="/home/user/Zenium_Kernel", help="4.19 tree, for attribution")
    ap.add_argument("--nm", default=None, help="default: $CROSS_COMPILE nm, else plain nm")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    objdirs = [os.path.join(tree, d) for d in a.objs]
    for dd in objdirs:
        if not os.path.isdir(dd):
            sys.exit("not a directory: %s" % dd)
    objs = sorted(f for dd in objdirs for f in (os.path.join(dd, x) for x in os.listdir(dd))
                  if f.endswith(".o"))
    if not objs:
        sys.exit("no .o files in %s - build the directory first" % ", ".join(a.objs))
    nmtool = a.nm or (os.environ.get("CROSS_COMPILE", "") + "nm")
    if not (os.path.exists(nmtool) or run(["sh", "-c", "command -v %s" % nmtool]).strip()):
        sys.exit("nm not usable: %s (source tools/env.sh first)" % nmtool)

    # 1. every name the slice leaves undefined, and which object needs it
    per = {}
    t = nm_chunked(nmtool, ["-u"], objs)
    for ln in t.split("\n"):
        p = ln.split()
        if len(p) == 2 and p[0] == "U":
            cur = os.path.basename(objs[0])
            per.setdefault(p[1], set()).add(cur)
    # nm prints a "file:" header per member when given >1 file, so re-run per file for attribution
    if len(objs) > 1:
        per = {}
        for o in objs:
            for ln in run([nmtool, "-u", o]).split("\n"):
                p = ln.split()
                if len(p) == 2 and p[0] == "U":
                    per.setdefault(p[1], set()).add(os.path.basename(o))
    names = sorted(per)

    # 2. everything this tree defines (built objects only)
    all_o = list(walk_o(tree))
    sat = set()
    for ln in nm_chunked(nmtool, ["--defined-only"], all_o).split("\n"):
        p = ln.split()
        if len(p) >= 3 and re.match(r"^[TDBRWV]$", p[1]):
            sat.add(p[2])

    # 3. mainline header surface = vmlinux API
    core = set()
    for d in ("include/linux", "include/uapi/linux", "include/asm-generic", "arch/arm64/include"):
        root = os.path.join(tree, d)
        for r, _, fs in os.walk(root):
            for f in fs:
                if f.endswith(".h"):
                    try:
                        src = open(os.path.join(r, f), errors="replace").read()
                    except OSError:
                        continue
                    core.update(DECL_CALL_RE.findall(src))
    core.update(COMPILER_BUILTINS)

    # 4. definitions in sources this pass did not build
    # Scoped to the mediatek/mailbox/smi subtrees: scanning all of drivers/ for unbuilt definitions
    # means ~10k regex passes for names that can only come from there anyway, and a full-tree scan in
    # a 2 CPU sandbox costs more than the classification is worth.
    srcdef = {}
    unbuilt = []
    roots = [os.path.join(tree, d) for d in
             ("drivers/misc/mediatek", "drivers/soc/mediatek", "drivers/mailbox",
              "drivers/iommu/mediatek", "drivers/gpu/drm/mediatek")
             if os.path.isdir(os.path.join(tree, d))]
    for root in roots:
        for r, dirs, fs in os.walk(root):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in fs:
                if not f.endswith(".c"):
                    continue
                path = os.path.join(r, f)
                if not os.path.exists(path[:-2] + ".o"):
                    unbuilt.append(path)
    for path in unbuilt:
        try:
            src = open(path, errors="replace").read()
        except OSError:
            continue
        if "{" not in src:
            continue
        for m in DEF_RE.finditer(src):
            srcdef.setdefault(m.group(1), os.path.relpath(path, tree))

    # 5. vendor attribution for the rest
    vroot = os.path.join(a.vendor, "drivers/misc/mediatek")
    cache = {}
    if os.path.isdir(vroot):
        for r, dirs, fs in os.walk(vroot):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in fs:
                if f.endswith(".c"):
                    cache.setdefault(f[:-2], os.path.join(r, f))
    leftover = [n for n in names if n not in sat and n not in core and n not in srcdef]
    prov_src = {}
    # GNU grep's ERE accepts neither \b nor \t in a bracket expression the way PCRE does: this exact
    # pattern with [\w \t\*] and \b silently matched NOTHING, which made every name report
    # "unattributed" - a clean-looking report that said the opposite of the truth. This form is the one
    # measured to match (it finds cmdqRecWrite in cmdq/v2, cmdq/v3 and mdp/cmdq_record.c).
    def grep_def(sym):
        return run(["grep", "-rlE",
                    "^[a-zA-Z_][a-zA-Z0-9_ *]*%s *" % sym.replace("(", "\\(") + r"\(",
                    "--include=*.c", vroot]).strip().split("\n")
    if leftover and not [x for x in grep_def("cmdqRecWrite") if x]:
        print("WARNING: attribution grep matched nothing even for a symbol known to exist in the "
              "vendor tree - the grep engine is broken, so 'unattributed' below means nothing.",
              file=sys.stderr)
    for n in leftover:
        p = grep_def(n)
        p = [x for x in p if x]
        if not p:
            continue
        pref = [x for x in p if "/mt6768/" in x]
        prov_src[n] = os.path.relpath((pref or p)[0], a.vendor)

    rows = []
    for n in names:
        if n in sat:
            cls, prov = "satisfied", ""
        elif n in core:
            cls, prov = "core (vmlinux)", ""
        elif n in srcdef:
            cls, prov = "provider landed, not built here", srcdef[n]
        else:
            cls = "PROVIDER NOT LANDED" if n in prov_src else "unattributed"
            prov = prov_src.get(n, "")
        rows.append((n, cls, prov, sorted(per[n])))

    order = {"PROVIDER NOT LANDED": 0, "unattributed": 1, "provider landed, not built here": 2,
             "core (vmlinux)": 3, "satisfied": 4}
    if a.json:
        import json
        print(json.dumps([{"symbol": n, "class": c, "provider": p, "needed_by": w}
                          for n, c, p, w in sorted(rows, key=lambda r: (order.get(r[1], 0), r[0]))],
                         indent=1))
        return
    print("nm=%s  %d objects in %s  %d distinct unresolved names  (%d .o built in tree)"
          % (nmtool, len(objs), "+".join(a.objs), len(names), len(all_o)))
    print()
    for n, c, p, w in sorted(rows, key=lambda r: (order.get(r[1], 0), r[0])):
        if c in ("PROVIDER NOT LANDED", "unattributed", "provider landed, not built here"):
            print("%-34s %-31s %-46s %s" % (n, c, p, ",".join(w)))
    cnt = Counter(c for _, c, _, _ in rows)
    print("\nsummary: " + ", ".join("%s=%d" % (k, v) for k, v in
                                    sorted(cnt.items(), key=lambda x: -x[1])))
    hard = [r for r in rows if r[1] in ("PROVIDER NOT LANDED", "unattributed")]
    print("%d names have no provider in this tree at all - that set, grouped by its vendor file, IS "
          "the next slice's scope:" % len(hard))
    byfile = Counter(r[2] or "?" for r in hard)
    for f, k in byfile.most_common():
        print("   %3d  %s" % (k, f))


if __name__ == "__main__":
    main()
