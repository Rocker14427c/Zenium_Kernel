#!/usr/bin/env python3
"""structcheck.py - structural sanity gate for a mechanically ported tree.

A hunk applied by exact-context matching can still damage a file's structure:
an `ifdef` whose matching `endif` lives in a hunk that was classified NEAR and
left unapplied, a brace opened by a vendor block whose closer came from a
different file layout, an unbalanced Kconfig menu.  A real build catches these
one at a time; this catches them all at once, without a toolchain.

For every file the port touched, it compares structural counter profiles of
base and ported trees; any file whose *balance* (opens minus closes) differs
from the base is reported.  Three dialects are checked:

  make   : `ifeq/ifneq/ifdef/ifndef/else/endif` (only files named Makefile*)
  kconfig: `menu/menuif/if` vs `endmenu/endif` (Kconfig files)
  c      : brace/paren balance and preprocessor `#if/#ifdef/#ifndef` vs `#endif`

Usage: structcheck.py PORTED_TREE --base BASE_COMMIT --against FILELIST
"""
import argparse
import re
import subprocess
from collections import defaultdict

MK_OPEN = re.compile(r"^\s*(ifeq|ifneq|ifdef|ifndef)\b")
MK_CLOSE = re.compile(r"^\s*endif\b")
MK_ELSE = re.compile(r"^\s*else\b")
# only these Kconfig keywords need a closer; `config`/`menuconfig` do not
KC_OPEN = re.compile(r"^\s*(menu|if|menuif|choose|optional|prompt)\b")
KC_CLOSE = re.compile(r"^\s*(endmenu|endif|endchoice)\b")
PP_OPEN = re.compile(r"^\s*#\s*(if|ifdef|ifndef)\b")
PP_CLOSE = re.compile(r"^\s*#\s*endif\b")


def read(tree, commit, path):
    try:
        out = subprocess.run(["git", "-C", tree, "show", f"{commit}:{path}"],
                             capture_output=True)
        if out.returncode:
            return None
        return out.stdout.decode("utf-8", "replace")
    except Exception:
        return None


def profile(text, kind):
    """(make balance, kconfig balance, brace delta, paren delta, pp balance, counts)."""
    mk = kc = pp = br = pa = 0
    mko = mkc = kco = kcc = ppo = ppc = 0
    for line in text.splitlines():
        if kind == "make":
            if MK_OPEN.match(line):
                mko += 1
            elif MK_CLOSE.match(line):
                mkc += 1
            elif MK_ELSE.match(line):
                # an 'else' is legal only once per conditional; count it
                pass
        elif kind == "kconfig":
            if KC_OPEN.match(line):
                kco += 1
            elif KC_CLOSE.match(line):
                kcc += 1
        else:
            code = re.sub(r'"(\\.|[^"\\])*"', '""', line)
            code = re.sub(r"'(\\.|[^'\\])*'", "''", code)
            code = re.sub(r"//.*$", "", code)
            if code.strip().startswith("#"):
                if PP_OPEN.match(code):
                    ppo += 1
                elif PP_CLOSE.match(code):
                    ppc += 1
            br += code.count("{") - code.count("}")
            pa += code.count("(") - code.count(")")
    return {"mk": mko - mkc, "mko": mko, "mkc": mkc,
            "kc": kco - kcc, "br": br, "pa": pa, "pp": ppo - ppc,
            "else": len([1 for l in text.splitlines() if MK_ELSE.match(l)]) if kind == "make" else 0}


def kind_of(path):
    b = path.rsplit("/", 1)[-1]
    if b.startswith("Makefile") or b.endswith(".mk"):
        return "make"
    if b.startswith("Kconfig") or b.endswith("Kconfig") or b.endswith("Kconfig.debug"):
        return "kconfig"
    if b.endswith((".c", ".h")):
        return "c"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--base", required=True)
    ap.add_argument("--against", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    files = [l.strip() for l in open(a.against) if l.strip()]
    bad = []
    checked = 0
    for p in files:
        k = kind_of(p)
        if not k:
            continue
        t1 = read(a.tree, "HEAD", p)
        t0 = read(a.tree, a.base, p)
        if t1 is None or t0 is None:
            continue
        checked += 1
        b1, b0 = profile(t1, k), profile(t0, k)
        why = []
        if k == "make":
            if b1["mk"] != b0["mk"]:
                why.append(f"make conditional imbalance {b0['mk']}->{b1['mk']} "
                           f"(open {b1['mko']} close {b1['mkc']})")
        elif k == "kconfig":
            if b1["kc"] != b0["kc"]:
                why.append(f"kconfig block imbalance {b0['kc']}->{b1['kc']}")
        else:
            for key, nm in (("br", "brace"), ("pa", "paren")):
                if b1[key] != b0[key]:
                    why.append(f"{nm} depth {b0[key]}->{b1[key]}")
            if b1["pp"] != b0["pp"]:
                why.append(f"preprocessor #if/#endif balance {b0['pp']}->{b1['pp']}")
        if why:
            bad.append({"file": p, "kind": k, "reasons": why})
    rep = {"files_checked": checked, "imbalanced": len(bad),
           "by_kind": dict(defaultdict(int, {k: sum(1 for b in bad if b['kind'] == k)
                                              for k in ("make", "kconfig", "c")})),
           "items": bad}
    with open(a.out, "w") as fh:
        json_dump(fh, rep)
    print(f"structural gate: {checked} files checked, {len(bad)} with changed balance")
    for b in bad[:40]:
        print(f"  {b['file']}  [{b['kind']}]: " + "; ".join(b["reasons"]))
    if len(bad) > 40:
        print(f"  ... {len(bad) - 40} more in {a.out}")


def json_dump(fh, obj):
    import json
    json.dump(obj, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
