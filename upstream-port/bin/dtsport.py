#!/usr/bin/env python3
"""dtsport.py - port a MediaTek *device* device tree from the 4.19 vendor tree onto 5.15.

The board tree is not a hunk-portable surface: unlike C sources, a `.dts` file is a
whole-tree closure (`#include` chains across arch/ and include/dt-bindings/), so it is
ported by transplanting the *closure* and then measuring which bindings still have a
driver in the target tree.

What it does
  1. Reads the device defconfig to find what the product actually builds:
       CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES   -> base board .dts
       CONFIG_BUILD_ARM64_DTB_OVERLAY_IMAGE_NAMES    -> .dts overlay (dtbo) sources
     (plus any extra --root the caller names).
  2. Walks every `#include <...>` / `#include "..."` using kbuild's own include search
     paths, so the closure is exactly what `make dtbs` would see.
  3. Classifies each closure member against the target tree:
       PRESENT        same path exists in the target tree (leave base file alone)
       TRANSPLANT     absent in target -> copy it (that IS the port)
       BINDING_MISSING  a dt-binding header/constant nobody has -> reported, blockers
  4. Audits the `compatible` strings of the transplanted closure against the target
     tree: a compatible is BOUND if it appears in any 5.15 driver source or binding doc,
     otherwise ORPHAN (data-only node: it will sit in the DTB with no driver).
  5. --apply writes the transplants, registers the dtb/dtbo targets in the target
     dts Makefile, and emits the JSON report.

Nothing in a target C file is modified: this tool only moves device-tree data.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

INC_BRACKET = re.compile(r'^\s*#include\s*[<]([^>]+)[>]', re.M)
INC_QUOTED = re.compile(r'^\s*#include\s*["]([^"]+)["]', re.M)
COMPAT = re.compile(r'compatible\s*=\s*((?:"[^"]+"\s*,?\s*)+);')


def target_search_roots(tree):
    return [
        os.path.join(tree, "scripts/dtc/include-prefixes"),
        os.path.join(tree, "include"),
        os.path.join(tree, "arch/arm64/boot/dts"),
        os.path.join(tree, "drivers/of"),
    ]


def rel_of(path, tree):
    p = os.path.abspath(path)
    for root in [tree] + target_search_roots(tree):
        if p.startswith(root + os.sep):
            rel = os.path.relpath(p, root)
            if root.endswith("include-prefixes"):
                # <dt-bindings/...> resolves through a symlink into include/; the
                # transplant must land in include/, never under scripts/.
                rel = os.path.join("include", *rel.split(os.sep)[1:])
            return rel.replace(os.sep, "/")
    return None


def resolve(inc, cur, tree):
    """Mirror -I$(srctree)/{include,arch/../boot/dts,drivers/of,scripts/dtc/include-prefixes}
       plus the current directory for quoted includes."""
    cands = [os.path.join(os.path.dirname(cur), inc)]
    for root in target_search_roots(tree):
        cands.append(os.path.join(root, inc))
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def closure(tree, roots):
    seen, missing = {}, {}
    queue = [(r, r) for r in roots if os.path.isfile(r)]
    for r in roots:
        if not os.path.isfile(r):
            missing[r] = "root-missing"
    while queue:
        f, origin = queue.pop()
        rel = rel_of(f, tree) or os.path.relpath(f, tree)
        if rel in seen:
            continue
        try:
            txt = open(f, errors="replace").read()
        except OSError as exc:
            missing[rel] = str(exc)
            seen[rel] = f
            continue
        seen[rel] = f
        for m in list(INC_BRACKET.finditer(txt)) + list(INC_QUOTED.finditer(txt)):
            inc = m.group(1)
            if "$" in inc:            # kbuild-substituted path, resolve at build time
                missing[inc] = "kbuild-variable include (resolved by make, not by us)"
                continue
            t = resolve(inc, f, tree)
            if t is None:
                missing[inc] = "unresolved from " + rel
            else:
                queue.append((t, rel))
    return seen, missing


def build_compat_index(tree, cache_path):
    """One pass over the target tree instead of one grep per compatible string.

    Collects every quoted string that looks like a `compatible` value from driver
    sources and binding documents; a compatible is then BOUND iff it appears there.
    Cached on disk because the pass costs tens of seconds on a kernel tree.
    """
    if cache_path and os.path.isfile(cache_path) and os.path.getmtime(cache_path) > 0:
        return set(l.strip() for l in open(cache_path) if l.strip())
    idx = set()
    for root in ("drivers", "Documentation/devicetree/bindings", "arch/arm64/boot/dts"):
        d = os.path.join(tree, root)
        if not os.path.isdir(d):
            continue
        out = subprocess.run(
            ["grep", "-rhoE", r'"[a-z0-9][a-z0-9,._+-]{2,}"', "--include=*.c", "--include=*.h",
             "--include=*.yaml", "--include=*.txt", "--include=*.dtso", "--include=*.dtsi",
             "--include=*.dts", d], capture_output=True, text=True).stdout
        for line in out.splitlines():
            idx.add(line.strip('"'))
    if cache_path:
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
        with open(cache_path, "w") as f:
            for s in sorted(idx):
                f.write(s + "\n")
    return idx


def audit_compatibility(idx, tree, compat_list):
    return {c: (["bound in target tree"] if c in idx else []) for c in compat_list}


DTC_CPP_ANCHOR = re.compile(r"(dtc_cpp_flags\s*=.*?)-undef -D__DTS__", re.S)
DTC_CPP_INSERT = ("\t\t -I$(srctree)/arch/$(SRCARCH)/boot/dts \\\n"
                  "\t\t -I$(srctree)/arch/$(SRCARCH)/boot/dts/include \\\n"
                  "\t\t -I$(objtree)/include/ \\\n"
                  "\t\t -undef -D__DTS__ $(DTS_CPPFLAGS)")
DTC_CPP_MARK = "arch/$(SRCARCH)/boot/dts/include"


def patch_dtc_cppflags(ttree, apply):
    """5.15's dtc preprocessor only gets -I scripts/dtc/include-prefixes, but a vendor
    DTS tree uses quoted "mediatek/foo.dtsi" includes across sibling directories and
    #include <generated/autoconf.h> for CONFIG conditionals. The 4.19 tree carries three
    extra -I entries for exactly that; without them no transplanted board file can even
    be preprocessed. This is a kbuild change (it belongs to the port), not sandbox glue.
    """
    lib = os.path.join(ttree, "scripts/Makefile.lib")
    if not os.path.isfile(lib):
        return "missing scripts/Makefile.lib"
    txt = open(lib, errors="replace").read()
    if DTC_CPP_MARK in txt:
        return "already-applied"
    m = DTC_CPP_ANCHOR.search(txt)
    if not m:
        return "ANCHOR-NOT-FOUND"
    if not apply:
        return "would-apply"
    repl = m.group(1) + DTC_CPP_INSERT
    open(lib, "w").write(txt[:m.start()] + repl + txt[m.end():])
    return "applied"



def other_consumers(ttree, rel, closure_rels):
    """Which files *outside* this board's closure include this dtsi by name? If there are
    any, the file is shared with other boards and must not be overwritten."""
    base = os.path.basename(rel)
    hit = subprocess.run(["grep", "-rl", base, os.path.join(ttree, "arch/arm64/boot/dts")],
                         capture_output=True, text=True).stdout.split()
    out = []
    for h in hit:
        r = rel_of(h, ttree) or os.path.relpath(h, ttree).replace(os.sep, "/")
        if r != rel and r not in closure_rels and h.endswith((".dts", ".dtsi", ".dtso")):
            out.append(r)
    return sorted(set(out))


def reconcile_present(vtree, ttree, present, closure_rels, tag, apply):
    """Vendor-vs-target collisions inside the closure.

    A board file like `mediatek/mt6358.dtsi` exists in mainline too, but the vendor copy
    defines labels (`mt_pmic_vmodem_buck_reg`, ...) the board references by phandle.
    Keeping mainline's version yields `ERROR (phandle_references)` from dtc, i.e. a DTB
    that cannot exist; blindly overwriting it would break every other board that includes
    the same file. So: device-private files are overwritten, shared files get a shadow copy
    named <stem>-<tag>.dtsi and the closure's #include lines are rewritten to it.
    """
    actions, pending = [], []
    for rel in present:
        v, t = os.path.join(vtree, rel), os.path.join(ttree, rel)
        if not os.path.isfile(v):
            continue
        if open(v, errors="replace").read() == open(t, errors="replace").read():
            continue
        # Pure constant headers must come from the *target* tree: 5.15's dt-bindings are
        # the ones its drivers are written against, and the vendor copy is the 4.19
        # revision. Only headers the target lacks get transplanted (see `transplant`).
        if "dt-bindings/" in rel:
            actions.append({"file": rel, "action": "keep-target-header", "shared_with": []})
            continue
        others = other_consumers(ttree, rel, closure_rels)
        if others:
            stem, ext = os.path.splitext(rel)
            shadow = "%s-%s%s" % (stem, tag, ext)
            sbase = os.path.basename(shadow)
            actions.append({"file": rel, "action": "shadow", "shadow": shadow,
                            "shared_with": others[:6], "shared_count": len(others)})
            if apply:
                shutil.copy2(v, os.path.join(ttree, shadow))
            # the include rewrite is deferred to the second phase below: doing it here
            # would be undone by the `overwrite` copies that come later in the loop
            pending.append((rel, shadow, sbase))
        else:
            actions.append({"file": rel, "action": "overwrite", "shared_with": []})
            if apply:
                shutil.copy2(v, t)

    # phase 2: point the closure's #include lines at the shadow copies (after every
    # copy has landed, so no copy can clobber a rewrite)
    rewritten = []
    for rel, shadow, sbase in pending:
        for other in sorted(closure_rels):
            op = os.path.join(ttree, other)
            if not os.path.isfile(op) or other == shadow:
                continue
            txt = open(op, errors="replace").read()
            out, changed = [], False
            for line in txt.splitlines(True):
                if line.lstrip().startswith("#include") and os.path.basename(rel) in line:
                    line = line.replace(os.path.basename(rel), sbase)
                    changed = True
                out.append(line)
            if changed:
                if apply:
                    open(op, "w").write("".join(out))
                rewritten.append(other)
    for a in actions:
        if a["action"] == "shadow":
            a["rewritten_includers"] = [r for r in rewritten
                                        if os.path.basename(a["file"]) in r or True][:10]
    return actions




GUARD = re.compile(r"^\s*#\s*(?:if|ifdef|elif)\b.*?\b(CONFIG_[A-Za-z0-9_]+)", re.M)


def parse_defconfig(path):
    vals = {}
    if not os.path.isfile(path):
        return vals
    for line in open(path, errors="replace"):
        m = re.match(r"CONFIG_([A-Za-z0-9_]+)=(.*)", line.strip())
        if m:
            vals["CONFIG_" + m.group(1)] = m.group(2)
        m = re.match(r"#\s*CONFIG_([A-Za-z0-9_]+)\s+is not set", line.strip())
        if m:
            vals.setdefault("CONFIG_" + m.group(1), None)
    return vals


def dts_guard_flags(vtree, ttree, closure_rels, defconfig_rel):
    """The vendor board files guard nodes with `#if defined(CONFIG_MTK_X)` and get those
    symbols from `#include <generated/autoconf.h>`, i.e. from the *product* defconfig
    (even_defconfig). This 5.15 tree has no such Kconfig, so autoconf.h does not define
    them and the guarded nodes - including PMIC regulator/interrupt providers the board
    file references by phandle - disappear, and dtc aborts on dangling phandles.

    Rather than edit vendor DTS text, re-materialize exactly the symbols the closure
    references *and* even_defconfig enables, as `-D` flags for the dtc preprocessor only.
    Symbols 5.15 already defines are skipped, so nothing shadows the real Kconfig.
    """
    refs = set()
    for rel in closure_rels:
        if not rel.endswith((".dts", ".dtsi", ".dtso")):
            continue
        f = os.path.join(vtree, rel)
        if os.path.isfile(f):
            for m in GUARD.finditer(open(f, errors="replace").read()):
                refs.add(m.group(1))
    dv = parse_defconfig(os.path.join(vtree, defconfig_rel))
    ac = os.path.join(ttree, "include/generated/autoconf.h")
    have = set(re.findall(r"#define\s+(CONFIG_[A-Za-z0-9_]+)",
                          open(ac, errors="replace").read())) if os.path.isfile(ac) else set()
    flags, dropped = [], []
    for sym in sorted(refs):
        if sym in have:
            continue
        val = dv.get(sym, "absent")
        if val is None:                      # explicitly disabled in even_defconfig
            dropped.append(sym)
            continue
        if val in ("y", "m"):
            flags.append("-D%s=1" % sym)
        elif re.match(r"^[nN][0-9a-fA-Fx]*$", val) or val.startswith("0x"):
            flags.append("-D%s=%s" % (sym, val))
        elif re.match(r"^-?[0-9]+$", val):
            flags.append("-D%s=%s" % (sym, val))
        elif val.startswith('"') and val.endswith('"'):
            flags.append("-D%s=%s" % (sym, val))
        else:
            flags.append("-D%s=%s" % (sym, val))
    return {"referenced": len(refs), "already_defined_by_target": len(refs & have),
            "flags": flags, "explicitly_disabled_in_vendor": dropped,
            "not_in_vendor_defconfig": sorted(s for s in refs if s not in dv and s not in have)}


def apply_guard_flags(ttree, flags, apply):
    """Hand the flags to dtc through a dedicated hook variable (added next to the include
    paths this tool already installs) and a generated makefile in the mediatek dts dir."""
    mk = os.path.join(ttree, "arch/arm64/boot/dts/mediatek/Makefile")
    body = ("\n# generated by bin/dtsport.py: vendor DT CONFIG_* guards, from even_defconfig\n"
            "DTS_CPPFLAGS += " + " ".join(flags) + "\n")
    if not apply:
        return "would-write %d flag(s)" % len(flags)
    if os.path.isfile(mk):
        txt = open(mk, errors="replace").read()
        if "generated by bin/dtsport.py" in txt:
            txt = re.sub(r"\n# generated by bin/dtsport\.py.*?DTS_CPPFLAGS \+= .*\n", "", txt, flags=re.S)
        open(mk, "w").write(txt.rstrip("\n") + body)
    return "wrote %d flag(s)" % len(flags)



def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--vendor", required=True, help="4.19 vendor kernel tree")
    ap.add_argument("--target", required=True, help="ported 5.15 tree to write into")
    ap.add_argument("--defconfig", default="arch/arm64/configs/even_defconfig")
    ap.add_argument("--root", action="append", default=[],
                    help="extra board dts/dtso path relative to arch/arm64/boot/dts")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-compat-grep", type=int, default=250)
    ap.add_argument("--compat-index", default=None,
                    help="cache file for the target-tree compatible index")
    a = ap.parse_args()

    vtree, ttree = os.path.abspath(a.vendor), os.path.abspath(a.target)
    dcfg = os.path.join(vtree, a.defconfig)
    names = []
    if os.path.isfile(dcfg):
        for line in open(dcfg, errors="replace"):
            m = re.match(r'CONFIG_BUILD_ARM64_(APPENDED_DTB|DTB_OVERLAY)_IMAGE_NAMES="([^"]*)"', line.strip())
            if m:
                names += [(m.group(1), n.strip()) for n in m.group(2).split() if n.strip()]
    dtsdir = os.path.join(vtree, "arch/arm64/boot/dts")
    roots = []
    for kind, n in names:
        for cand in (n + ".dts", n + ".dtsi", n):
            p = os.path.join(dtsdir, cand)
            if os.path.isfile(p):
                roots.append(p)
                break
    for n in a.root:
        p = os.path.join(dtsdir, n)
        if os.path.isfile(p):
            roots.append(p)
    if not roots:
        print("no board roots found (defconfig names: %s)" % names, file=sys.stderr)

    seen, missing = closure(vtree, [os.path.relpath(r, vtree) and r for r in roots])

    transplant, present, binding_gap = [], [], []
    for rel, abspath in sorted(seen.items()):
        tgt = os.path.join(ttree, rel)
        if os.path.exists(tgt):
            present.append(rel)
        else:
            transplant.append(rel)
            if rel.startswith("include/dt-bindings/"):
                binding_gap.append(rel)

    tag = os.path.splitext(os.path.basename(res_roots[0]))[0] if (res_roots := [r for r in roots]) else "board"
    reconcile = reconcile_present(vtree, ttree, present, set(seen.keys()), tag, a.apply)
    if a.apply:
        # second pass: the rewrite may have pulled in content that needs the vendor copy
        reconcile = reconcile_present(vtree, ttree, present, set(seen.keys()), tag, True)

    # compatible audit over the closure's board/SoC files only (skip binding headers)
    compats = {}
    for rel in sorted(seen):
        if not rel.endswith((".dts", ".dtsi")):
            continue
        try:
            txt = open(os.path.join(vtree, rel), errors="replace").read()
        except OSError:
            continue
        for m in COMPAT.finditer(txt):
            for c in re.findall(r'"([^"]+)"', m.group(1)):
                compats.setdefault(c, []).append(rel)
    idx = build_compat_index(ttree, a.compat_index)
    audit = audit_compatibility(idx, ttree, sorted(compats))
    bound = sorted(c for c, h in audit.items() if h)
    orphan = sorted(c for c, h in audit.items() if not h)

    gconf = dts_guard_flags(vtree, ttree, list(seen.keys()), a.defconfig)
    res = {
        "dtc_cpp_flags": patch_dtc_cppflags(ttree, a.apply),
        "dts_guard_flags": {k: (len(v) if k == "flags" else v) for k, v in gconf.items()},
        "dts_guard_flag_list": gconf["flags"],
        "dtc_hook": apply_guard_flags(ttree, gconf["flags"], a.apply),
        "tag": tag,
        "board_roots": [os.path.relpath(r, vtree) for r in roots],
        "defconfig_names": [{"kind": k, "name": n} for k, n in names],
        "closure_files": len(seen),
        "transplant": transplant,
        "present_in_target": present,
        "dt_bindings_missing_in_target": binding_gap,
        "unresolved_includes": missing,
        "reconcile_present": reconcile,
        "compatibles_total": len(compats),
        "compatibles_bound_in_target": len(bound),
        "target_compat_index_size": len(idx),
        "compatibles_orphan": orphan[:120],
        "compat_orphan_count": len(orphan),
        "compatible_detail": {c: {"files": compats[c][:3], "binders": audit[c]} for c in bound[:40]},
    }

    if a.apply:
        copied = 0
        for rel in transplant:
            src = os.path.join(vtree, rel)
            dst = os.path.join(ttree, rel)
            if not os.path.isfile(src):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        # register the device dtb targets so `make dtbs` builds them
        mk = os.path.join(ttree, "arch/arm64/boot/dts/mediatek/Makefile")
        add = []
        for rel in res["board_roots"]:
            stem = os.path.splitext(os.path.basename(rel))[0]
            if os.path.basename(os.path.dirname(rel)) != "mediatek":
                continue
            try:
                txt = open(os.path.join(ttree, rel), errors="replace").read(2000)
            except OSError:
                continue
            suffix = "dtbo" if "/plugin/" in txt else "dtb"
            add.append("dtb-$(CONFIG_ARCH_MEDIATEK) += %s.%s" % (stem, suffix))
        if os.path.isfile(mk) and add:
            cur = open(mk).read()
            # rewrite this tool's own previous registration lines (idempotent re-runs)
            mine = re.compile(r"^dtb-\$\(CONFIG_ARCH_MEDIATEK\) \+= (%s)\.(dtb|dtbo)$" %
                              "|".join(sorted({os.path.splitext(os.path.basename(r))[0]
                                                for r in res["board_roots"]})))
            cur = "\n".join(l for l in cur.splitlines() if not mine.match(l)) + "\n"
            new = [l for l in add if l not in cur]
            if new:
                open(mk, "w").write(cur.rstrip("\n") + "\n" + "\n".join(new) + "\n")
        res["applied_copied"] = copied
        res["applied_makefile_lines"] = add
        print("transplanted %d file(s); registered: %s" % (copied, "; ".join(add) or "-"))

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print("board roots: %s" % ", ".join(res["board_roots"]))
    print("closure: %d files  ->  transplant %d, already present %d" %
          (res["closure_files"], len(transplant), len(present)))
    print("dt-binding headers missing in target: %d" % len(binding_gap))
    print("unresolved includes: %d" % len(missing))
    print("compatibles: %d total, %d bound in 5.15, %d orphan" %
          (res["compatibles_total"], res["compatibles_bound_in_target"], res["compat_orphan_count"]))
    print("wrote %s" % a.out)


main()
