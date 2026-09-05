#!/usr/bin/env python3
"""dupdef.py - find definitions a port duplicated into the same translation unit.

Vendor trees of 4.19 vintage are full of *backported* helpers (bpf_link_*,
vm_insert_page(), iomap bits, io_uring strum).  A hunk-level port happily
re-adds them next to the copy upstream landed in 5.15, and the build then dies
with "redefinition of 'x'".  Context matching cannot see this: the text applies
cleanly, it is simply no longer wanted.

Detection is deliberately local and exact: a function-like definition name that
appears twice as a definition in the ported file but only once in the base file
is a port-introduced duplicate.  `--strip` removes the *added* copy (the block
the port introduced, brace-matched), leaving the base definition intact.

Usage: dupdef.py TREE --base REF --files LIST [--strip] [--out JSON]
"""
import argparse
import json
import os
import re
import subprocess
import sys

# name( ... ) {  |  name( ... );  -- we only care about definitions, so `{`
DEF = re.compile(r"^[A-Za-z_][\w\s\*\t]*?([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:__[a-z_]+\s*)?\{\s*$", re.M)
DEF2 = re.compile(r"^[A-Za-z_][\w\s\*\t]*?([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{\s*$", re.M)


PP = re.compile(r"^\s*#\s*(if|ifdef|ifndef|else|elif|endif)\b(.*)$")


def guard_stacks(text):
    """line number -> tuple of active #if conditions (normalized).

    Two definitions of the same name are only a real duplicate if they are
    compiled under the *same* preprocessor guards; vendor code legitimately
    carries an #ifdef ALTERNATE next to the upstream version.
    """
    stacks = {}
    stack = []
    for i, line in enumerate(text.splitlines(), 1):
        m = PP.match(line)
        if m:
            kw, rest = m.group(1), m.group(2).strip()
            if kw in ("if", "ifdef", "ifndef"):
                stack.append(f"{kw} {rest}")
            elif kw in ("else", "elif"):
                if stack:
                    stack[-1] = stack[-1] + " / " + kw
            elif kw == "endif" and stack:
                stack.pop()
        stacks[i] = tuple(stack)
    return stacks


BADNAME = re.compile(r"^(_|sys_|SYSCALL|COMPAT_|DEFINE|TRACE|EXPORT|[A-Z0-9_]+$)")


def defs(text):
    """name -> [(line, guard_stack), ...] for real C definitions only.

    Macro invocations (SYSCALL_DEFINE*, EXPORT_SYMBOL*) look like definitions to
    a regex; they are excluded by name shape and by refusing lines that start
    with a preprocessor directive.
    """
    st = guard_stacks(text)
    lines = text.splitlines()
    out = {}
    for m in DEF2.finditer(text):
        ln = text[:m.start()].count("\n") + 1
        name = m.group(1)
        src = lines[ln - 1] if ln - 1 < len(lines) else ""
        if src.lstrip().startswith("#") or src.lstrip().startswith("}"):
            continue
        if BADNAME.match(name):
            continue
        out.setdefault(name, []).append((ln, st.get(ln, ())))
    return out


def strip_block(lines, start_idx):
    """remove the brace-matched definition starting at lines[start_idx]"""
    depth = 0
    i = start_idx
    began = False
    while i < len(lines):
        depth += lines[i].count("{") - lines[i].count("}")
        if "{" in lines[i]:
            began = True
        if began and depth <= 0:
            break
        i += 1
    # also swallow a preceding blank line and any trailing one
    a, b = start_idx, i + 1
    while a > 0 and lines[a - 1].strip() == "":
        a -= 1
    if b < len(lines) and lines[b].strip() == "":
        b += 1
    return a, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--base", required=True)
    ap.add_argument("--files", required=True)
    ap.add_argument("--strip", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    files = [l.strip() for l in open(a.files) if l.strip()
             and l.strip().endswith((".c", ".h"))]
    report = []
    for f in files:
        p = os.path.join(a.tree, f)
        if not os.path.exists(p):
            continue
        try:
            cur = open(p, encoding="utf-8", errors="replace").read()
            base = subprocess.run(["git", "-C", a.tree, "show", f"{a.base}:{f}"],
                                  capture_output=True).stdout.decode("utf-8", "replace")
        except OSError:
            continue
        cd, bd = defs(cur), defs(base)
        dups = {}
        for n, ls in cd.items():
            # a name is a port-introduced duplicate only if two copies share the
            # same guard stack (so both are compiled), or base had none of that stack
            same = {}
            for ln, g in ls:
                same.setdefault(g, []).append(ln)
            base_g = {g for _, g in bd.get(n, [])}
            for g, lns in same.items():
                if len(lns) > 1 or (g not in base_g and len(lns) >= 1 and len(ls) > len(bd.get(n, []))):
                    if len(lns) > 1:
                        dups[n] = lns
                        break
        if not dups:
            continue
        # line-number precise: a text-set would also match identical base lines,
        # and then the wrong copy could be removed.
        added = set()
        d = subprocess.run(["git", "-C", a.tree, "diff", "--unified=0", a.base, "--", f],
                           capture_output=True, text=True).stdout
        cur_new = 0
        for l in d.splitlines():
            hm = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))?", l)
            if hm:
                cur_new = int(hm.group(1)); continue
            if l.startswith("+") and not l.startswith("+++"):
                added.add(cur_new); cur_new += 1
            elif l.startswith("-") or l.startswith("\\"):
                continue
            elif l.startswith(" "):
                cur_new += 1
        entry = {"file": f,
                 "duplicated_definitions": {k: v for k, v in dups.items()},
                 "stripped": []}
        if a.strip:
            lines = cur.split("\n")
            # walk from the back so indices stay valid
            for n, ls in sorted(dups.items(), key=lambda kv: -max(kv[1])):
                # only remove copies whose header line the port added
                cands = [ln - 1 for ln in ls if ln in added]
                for idx in sorted(set(cands), reverse=True):
                    a2, b2 = strip_block(lines, idx)
                    a2 = idx if idx in added else a2
                    entry["stripped"].append({"name": n, "lines": [a2 + 1, b2],
                                              "text": lines[a2].strip()[:60]})
                    del lines[a2:b2]
            newtext = "\n".join(lines)
            # never leave a dangling body behind: if the removal changed the file's
            # brace depth, the copies were interleaved -> keep the file as is and
            # hand it to a human (recorded in the report).
            bal = lambda t: t.count("{") - t.count("}")
            if bal(newtext) != bal(cur):
                entry["skipped"] = ("interleaved with base lines: brace balance would "
                                   "change, file left for manual resolution")
                entry["stripped"] = []
                report.append(entry)
                continue
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(newtext)
        report.append(entry)
    with open(a.out, "w") as fh:
        json.dump({"files_with_port_introduced_duplicates": len(report),
                   "items": report}, fh, indent=2, sort_keys=True)
    print(f"dup-definition gate: {len(report)} file(s) carry a definition the port")
    print(f"  introduced a second copy of ({'STRIPPED' if a.strip else 'dry run'})")
    for e in report[:25]:
        names = ", ".join(sorted(e["duplicated_definitions"])[:6])
        print(f"  {e['file']}: {names}" + (f"  [{len(e['stripped'])} removed]" if e["stripped"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
