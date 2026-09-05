#!/usr/bin/env python3
"""buildfix.py - drive the build until it compiles, fixing what is mechanical.

A hunk-level port produces three failure shapes that need no judgement, only
consistency:

  1. a missing header - the ported file #includes a vendor-new header nobody
     copied yet;  resolve it in the vendor tree and transplant that one file;
  2. a dangling vendor hook - the ported hunk calls a function / touches a struct
     member whose *definition* lives in vendor code that phase 1 does not carry;
     the hunk is therefore not portable as-is, so the file returns to base;
  3. a duplicate export - dupdef removed a duplicated definition but left its
     EXPORT_SYMBOL, so the assembler reports the __ksymtab symbol twice; drop the
     export the port added.

Anything else (type drift, semantics, a hook whose removal changes behaviour the
device needs) is left for a human and reported.  Every action is appended to a
JSONL ledger so the migration report can state exactly what was given up and why.

Usage: buildfix.py TREE --log OUT.log [--max-passes N] [--dry-run] [--make-only]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ERR_LINE = re.compile(r"^(?P<f>[^\s:]+):(?P<l>\d+):(?P<c>\d+): error: (?P<m>.*)$")
MISSING_INC = re.compile(r"fatal error: '(?P<h>[^']+)' file not found")
MISSING_SYM = re.compile(r"(?:use of undeclared identifier|implicit declaration of function|"
                         r"no member named|no member called|unknown type name|has no member named|"
                         r"unknown field name) '(?P<s>[^']+)'")
DUP_EXPORT = re.compile(r"symbol '(?P<s>__kstrtab[a-z_]*(?P<name>\w+))' is already defined")
VENDOR_DIRS = ("include", "arch/arm64/include", "drivers", "sound", "fs", "net", "kernel", "mm", "lib")


def sh(cmd, cwd=None, text=True):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=text)


def vendor_find(vendor, header):
    for d in VENDOR_DIRS:
        cand = os.path.join(vendor, d, header)
        if os.path.exists(cand):
            return cand
    # canonical location for <linux/...> style
    cand = os.path.join(vendor, "include", header)
    if os.path.exists(cand):
        return cand
    hits = sh(["git", "-C", vendor, "ls-files", "--", f"*/{os.path.basename(header)}"]).stdout.split()
    hits = [h for h in hits if h.endswith(header) or os.path.basename(h) == os.path.basename(header)]
    if len(set(hits)) == 1:
        return os.path.join(vendor, hits[0])
    return None


def copy_header(tree, vendor, header, log):
    vp = vendor_find(vendor, header)
    if not vp:
        return None
    rel = os.path.relpath(vp, vendor)
    dst = os.path.join(tree, rel)
    if os.path.exists(dst):
        return None
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(vp, dst)
    log.append({"action": "transplant-header", "path": rel, "from": rel})
    print(f"    + transplanted {rel}")
    return rel


def added_lines(tree, base, path):
    """new-file line numbers the port added"""
    d = sh(["git", "-C", tree, "diff", "--unified=0", base, "--", path]).stdout
    out, cur = set(), 0
    for l in d.splitlines():
        hm = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)?", l)
        if hm:
            cur = int(hm.group(1)); continue
        if l.startswith("+") and not l.startswith("+++"):
            out.add(cur); cur += 1
        elif not l.startswith("-"):
            cur += 1
    return out


def drop_dangling_exports(tree, base, files, log):
    """EXPORT_SYMBOL(x) whose x is not defined in that file, and which the port added"""
    n = 0
    for f in files:
        p = os.path.join(tree, f)
        if not os.path.exists(p) or not f.endswith(".c"):
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        add = added_lines(tree, base, f)
        lines = text.split("\n")
        keep, removed = [], []
        for i, line in enumerate(lines, 1):
            m = re.match(r"\s*EXPORT_SYMBOL(?:_GPL|_NS)?\((\w+)\)\s*;", line)
            if m and i in add:
                name = m.group(1)
                defined = re.search(r"^\w[\w \t\*]*\b%s\s*\(" % re.escape(name), text, re.M)
                if not defined:
                    removed.append(line.strip()); n += 1
                    continue
            keep.append(line)
        if removed:
            open(p, "w", encoding="utf-8").write("\n".join(keep))
            log.append({"action": "drop-dangling-export", "file": f, "symbols": removed})
            print(f"    - {f}: dropped {len(removed)} dangling EXPORT_SYMBOL line(s)")
    return n


def hunk_prepost(text_diff):
    """yield (pre_block, post_block) line-lists for each @@ hunk of a git diff"""
    hunks, pre, post = [], None, None
    for l in text_diff.split("\n"):
        if l.startswith("@@"):
            if pre is not None:
                hunks.append((pre, post))
            pre, post = [], []
            continue
        if pre is None:
            continue
        if l.startswith("+"):
            post.append(l[1:])
        elif l.startswith("-"):
            pre.append(l[1:])
        else:
            c = l[1:] if l[:1] in (" ", "\\") else l
            pre.append(c); post.append(c)
    if pre is not None:
        hunks.append((pre, post))
    return hunks


def repair_deletions(tree, base, need, log, dry=False):
    """`need` maps a broken file -> missing symbols.  If a *ported* file deleted a
    line mentioning that symbol, undo just that hunk (post-image back to
    pre-image) instead of reverting the whole header."""
    fixed = 0
    ported = [f for f in sh(["git", "-C", tree, "diff", "--name-only", base]).stdout.splitlines()
              if f.strip()]
    for f, syms in sorted(need.items()):
        ff = f[2:] if f.startswith("./") else f
        if sh(["git", "-C", tree, "diff", "--quiet", base, "--", ff]).returncode == 0:
            pass  # at base: the culprit is elsewhere, look for a deletion that hurt it
        else:
            continue
        for s2 in sorted(syms):
            for h in ported:
                if not h.endswith((".h", ".c", ".S")) or h == ff:
                    continue
                d = sh(["git", "-C", tree, "diff", "--unified=3", base, "--", h]).stdout
                if not d:
                    continue
                text = open(os.path.join(tree, h), encoding="utf-8", errors="replace").read()
                changed = False
                for pre, post in hunk_prepost(d):
                    if not any(s2 in l for l in pre):
                        continue
                    if not any(l.startswith("-") for l in
                               [x for x in sh(["git", "-C", tree, "diff", "--unified=0", base, "--", h]).stdout.split("\n")
                                if x.startswith("-") and s2 in x]):
                        continue
                    post_t = "\n".join(post)
                    pre_t = "\n".join(pre)
                    if post_t and text.count(post_t) == 1:
                        text = text.replace(post_t, pre_t, 1)
                        changed = True
                        log.append({"action": "undo-hunk-with-deletion", "file": h,
                                    "symbol": s2, "reason":
                                    "the ported hunk deleted 5.15 code that unmodified base "
                                    "files still use; the hunk was undone so the base "
                                    "definition survives",
                                    "restored": pre_t.strip()[:90]})
                        print(f"    ~ undid a deleting hunk in {h} (restores `{s2}` for {ff})")
                if changed:
                    if not dry:
                        open(os.path.join(tree, h), "w", encoding="utf-8").write(text)
                    fixed += 1
                    break
    return fixed


SIG_ERR = re.compile(r"(?:conflicting types for|redefinition of|too many arguments to function call|"
                    r"too few arguments to function call|incompatible function pointer types|"
                    r"is already defined)\s*'?([A-Za-z_]\w*)'?"
                    r"|no previous (?:prototype|global declaration) for '([A-Za-z_]\w*)'")


def repair_signature_conflicts(tree, base, errs, ledger, dry, cap=40):
    """The vendor changed a symbol's signature; 5.15's own definition must win.

    For every conflicting symbol, revert the *ported* files whose delta touches
    that symbol - preferring files next to the failing one, since kbuild keeps
    private headers beside the sources that use them.
    """
    syms = {}
    for f, ln, mtxt in errs:
        m = SIG_ERR.search(mtxt)
        if not m:
            continue
        name = m.group(1) or m.group(2)
        if not name:
            continue
        syms.setdefault(name, set()).add(f[2:] if f.startswith("./") else f)
    if not syms:
        return 0
    ported = [x.strip() for x in
              sh(["git", "-C", tree, "diff", "--name-only", base]).stdout.splitlines() if x.strip()]
    reverted = 0
    for name, where in sorted(syms.items()):
        dirs = {os.path.dirname(w) for w in where}
        cands = [p2 for p2 in ported
                 if p2.endswith((".c", ".h")) and os.path.dirname(p2) in dirs
                 and sh(["git", "-C", tree, "diff", base, "--", p2]).stdout.count(name)]
        cands.sort(key=lambda p2: (0 if p2.endswith(".h") else 1, p2))
        for p2 in cands[:max(1, len(cands))]:
            if reverted >= cap:
                break
            d = sh(["git", "-C", tree, "diff", "--numstat", base, "--", p2]).stdout.strip()
            adds = d.split("\t")[0] if d else "0"
            dels = d.split("\t")[1] if d and len(d.split("\t")) > 1 else "0"
            if adds == "-":
                adds = "0"
            if not dry:
                sh(["git", "-C", tree, "checkout", base, "--", p2])
            ledger.append({"action": "reverted-signature-conflict", "file": p2,
                           "symbol": name,
                           "reported_in": sorted(where)[:4],
                           "reason": "the vendor delta re-typed this symbol, which conflicts "
                                     "with 5.15's own definition/prototype; 5.15's form wins so "
                                     "the tree stays coherent, and the vendor variant is left to "
                                     "the manual pass",
                           "ported_lines_given_up": {"+": adds, "-": dels}})
            print(f"    = held at base ({name}): {p2}")
            reverted += 1
    return reverted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--vendor", default="/home/user/Zenium_Kernel")
    ap.add_argument("--base", default="v5.15.220")
    ap.add_argument("--build", default="/home/user/.cache/upstream/build.sh")
    ap.add_argument("--target", default="Image")
    ap.add_argument("--from-log", default=None,
                    help="analyse an existing build log instead of rebuilding first")
    ap.add_argument("--log", required=True)
    ap.add_argument("--max-passes", type=int, default=14)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--aggressive", action="store_true",
                    help="also hold at base any *ported* file that fails to compile "
                         "(4.19-shaped code that cannot adapt without its vendor subsystem)")
    a = ap.parse_args()
    ledger = []
    touched_cache = None

    for p in range(a.max_passes):
        if a.from_log:
            blob = open(a.from_log, errors="replace").read()
            rc = 1
            a.from_log = None            # analyse once, then rebuild normally
        else:
            r = sh([a.build, a.target])
            blob = r.stdout + "\n" + r.stderr
            open(a.log, "w").write(blob)
            rc = r.returncode
        if rc == 0:
            print(f"pass {p}: BUILD CLEAN")
            json.dump({"pass": p, "clean": True, "actions": ledger},
                      open(a.log + ".actions.json", "w"), indent=2, sort_keys=True)
            return 0

        errs = []
        for line in blob.splitlines():
            m = ERR_LINE.match(line.strip())
            if m:
                errs.append((m.group("f"), int(m.group("l")), m.group("m")))
        if not errs:
            print(f"pass {p}: no parseable compiler error (build glue or link error); "
                  f"see {a.log}")
            print("\n".join(l for l in blob.splitlines() if "Error " in l)[-1500:])
            break

        # --- 1: missing headers -> transplant the vendor file -----------------
        hdrs = sorted({m.group("h") for _, _, mtxt in errs
                       for m in [MISSING_INC.search(mtxt)] if m})
        # also the plain "fatal error: 'x' file not found" lines that ERR_LINE missed
        hdrs = sorted(set(hdrs) | {m.group("h") for l in blob.splitlines()
                                   for m in [MISSING_INC.search(l)] if m})
        done = 0
        if hdrs and not a.dry_run:
            print(f"pass {p}: {len(hdrs)} missing header(s)")
            for h in hdrs:
                if copy_header(a.tree, a.vendor, h, ledger):
                    done += 1
        elif hdrs:
            print(f"pass {p}: (dry run) would transplant {hdrs[:8]}")

        # --- 3: dangling exports -------------------------------------------
        dupnames = sorted({m.group("name") for l in blob.splitlines()
                           for m in [DUP_EXPORT.search(l)] if m})
        if dupnames and not a.dry_run:
            cfiles = sorted({f for f, _, mtxt in errs if "ksymtab" in mtxt})
            cfiles = [f for f in blob.splitlines() if False] or []
            # the assembler error has no usable filename; scan all touched .c files
            if touched_cache is None:
                touched_cache = [x.strip() for x in
                                 sh(["git", "-C", a.tree, "diff", "--name-only", a.base]).stdout.splitlines()
                                 if x.strip().endswith(".c")]
            n = drop_dangling_exports(a.tree, a.base, touched_cache, ledger)
            print(f"pass {p}: dropped {n} dangling EXPORT_SYMBOL line(s) "
                  f"for {', '.join(dupnames[:6])}")
            done += n

        # --- 2: files whose only problem is a missing vendor symbol ----------
        byfile = {}
        for f, ln, mtxt in errs:
            if "file not found" in mtxt or "already defined" in mtxt:
                continue
            syms = set()
            for m in MISSING_SYM.finditer(mtxt):
                syms.add(m.group("s"))
            if not syms:
                continue
            if f.startswith("./"):
                f = f[2:]
            byfile.setdefault(f, set()).update(syms)
        # only act on files where *every* error is of the missing-symbol kind
        todo = []
        for f, syms in byfile.items():
            ferr = [mtxt for ff, _, mtxt in errs if (ff[2:] if ff.startswith("./") else ff) == f]
            if all(("undeclared identifier" in x or "implicit declaration" in x
                    or "no member named" in x or "has no member named" in x
                    or "unknown type name" in x or "unknown field name" in x) for x in ferr):
                todo.append((f, sorted(syms)))
        at_base, still_broken = set(), {}
        for f, syms in byfile.items():
            ff = f[2:] if f.startswith("./") else f
            if sh(["git", "-C", a.tree, "diff", "--quiet", a.base, "--", ff]).returncode == 0:
                still_broken[ff] = syms
        if still_broken and not a.dry_run:
            print(f"pass {p}: {len(still_broken)} file(s) are already at base but still "
                  f"fail -> a ported deletion broke them; repairing")
            repair_deletions(a.tree, a.base, still_broken, ledger, a.dry_run)
        todo = [(f, syms) for f, syms in todo
                if sh(["git", "-C", a.tree, "diff", "--quiet", a.base, "--", f]).returncode != 0]
        if todo and not a.dry_run:
            print(f"pass {p}: {len(todo)} file(s) reference only untransplanted vendor symbols")
            for f, syms in todo:
                p2 = os.path.join(a.tree, f)
                if not os.path.exists(p2):
                    continue
                d = sh(["git", "-C", a.tree, "diff", "--numstat", a.base, "--", f]).stdout.strip()
                adds = d.split("\t")[0] if d else "0"
                dels = d.split("\t")[1] if d and len(d.split("\t")) > 1 else "0"
                sh(["git", "-C", a.tree, "checkout", a.base, "--", f])
                # a header the port *created* (vendor-new) must be dropped, not checked out
                if sh(["git", "-C", a.tree, "ls-files", "--error-unmatch", f]).returncode != 0:
                    os.remove(p2)
                ledger.append({"action": "reverted-file", "file": f,
                               "missing_symbols": syms[:12],
                               "reason": "port-added code references vendor infrastructure "
                                         "that phase 1 does not transplant; file held at base",
                               "ported_lines_given_up": {"+": adds, "-": dels}})
                print(f"    = held at base: {f}  (missing: {', '.join(syms[:4])})")
                done += 1

        n_sig = repair_signature_conflicts(a.tree, a.base, errs, ledger, a.dry_run)
        done += n_sig

        if a.aggressive:
            # every ported file that still fails is 4.19-shaped: hold it at base and
            # record why, so the ledger says exactly which vendor change is deferred.
            agg = {}
            for f, ln, mtxt in errs:
                ff = f[2:] if f.startswith("./") else f
                if ff.endswith((".o", ".s")) or "already defined" in mtxt:
                    continue
                agg.setdefault(ff, []).append(mtxt[:100])
            n2 = 0
            for ff in sorted(agg):
                if sh(["git", "-C", a.tree, "diff", "--quiet", a.base, "--", ff]).returncode == 0:
                    continue
                if a.dry_run:
                    print(f"    ! (dry) would hold at base: {ff}")
                    n2 += 1; continue
                d = sh(["git", "-C", a.tree, "diff", "--numstat", a.base, "--", ff]).stdout.strip()
                adds = d.split("\t")[0] if d else "0"
                dels = d.split("\t")[1] if d and len(d.split("\t")) > 1 else "0"
                sh(["git", "-C", a.tree, "checkout", a.base, "--", ff])
                ledger.append({"action": "reverted-file-api-drift", "file": ff,
                               "errors": sorted(set(agg[ff]))[:6],
                               "reason": "the ported 4.19 form does not type-check against "
                                         "5.15 APIs; deferred to the manual pass, which must "
                                         "re-adapt it to 5.15 (or drop the feature)",
                               "ported_lines_given_up": {"+": adds, "-": dels}})
                print(f"    ! held at base (API drift): {ff}")
                n2 += 1
            if n2:
                done += n2

        if not done:
            print(f"pass {p}: nothing mechanical left to fix; {len(set(f for f,_,_ in errs))} "
                  f"file(s) need judgement -> see {a.log}")
            byfile2 = {}
            for f, ln, mtxt in errs:
                byfile2.setdefault(f, []).append(mtxt[:110])
            with open(a.log + ".remaining.json", "w") as fh:
                json.dump({"files": len(byfile2), "total_errors": len(errs),
                           "by_file": {k: sorted(set(v))[:4] for k, v in sorted(byfile2.items())},
                           "actions_so_far": ledger}, fh, indent=2, sort_keys=True)
            print(f"    wrote {a.log}.remaining.json with the per-file breakdown")
            break
    json.dump({"clean": False, "actions": ledger},
              open(a.log + ".actions.json", "w"), indent=2, sort_keys=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
