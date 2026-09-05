#!/usr/bin/env python3
"""hwenable.py - from the *built* board DTB to a device hardware-enablement fragment.

`report/dtsport.json` says how many compatibles have any driver in 5.15.  This answers the
next, practical question for each of them:

  which driver binds it -> which Kconfig builds that driver -> is that Kconfig on in this
  build -> is the node actually present in the DTB the device will boot with

It works from `dtc -I dtb -O dts` output of the built `mt6768.dtb`, i.e. from what the
kernel will really see (after all cpp guards), not from the DTS sources.  For every
compatible it greps 5.15's `of_device_id` tables, resolves the owning `obj-$(CONFIG_*)`
Makefile line, and reports the delta.  The result is a kconfig fragment for the device plus
a table of what cannot be enabled by config alone (no driver in tree = driver port work).

  python3 bin/hwenable.py --dtb <build>/arch/arm64/boot/dts/mediatek/mt6768.dtb \
          --dtc <build>/scripts/dtc/dtc --target <build> \
          --out-md report/hardware-enablement.md --out-json report/hardware-enablement.json \
          --fragment dev/even-hardware.fragment --apply-config
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

DTC_NODE = re.compile(r'^(\t+)([\w@,.\-]+) \{$')


def dtb_to_dts(dtc, dtb):
    out = subprocess.run([dtc, "-I", "dtb", "-O", dts_fmt := "dts", dtb],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("dtc failed: %s" % out.stderr[:400])
    return out.stdout


def nodes_with_compat(dts):
    """compatible -> list of node paths (best-effort path from brace depth)."""
    stack, res = [], collections.defaultdict(list)
    for line in dts.splitlines():
        m = re.match(r'^(\t+)([\w,.\-@]+) \{$', line)
        if m:
            depth = len(m.group(1))
            name = m.group(2)
            stack = stack[:depth - 1] + [name]
            continue
        if re.match(r"^\t+\};$", line):
            stack = stack[:max(0, len(stack) - 1)]
            continue
        m = re.search(r'compatible\s*=\s*((?:"[^"]+"\s*,?\s*)+);', line)
        if m:
            for c in re.findall(r'"([^"]+)"', m.group(1)):
                res[c].append("/" + "/".join(stack))
    return res


def find_binder(tree, compat):
    """Driver source + Kconfig symbol that matches this compatible in an of_match table.

    Requires `of_device_id` / `of_match_table` within the 8 lines above the string, so that
    an incidental comment or an unrelated MODULE_DEVICE alias does not look like a binding.
    """
    raw = subprocess.run(["grep", "-rn", "-B16", "--include=*.c", '"%s"' % compat,
                          os.path.join(tree, "drivers"), os.path.join(tree, "arch/arm64")],
                         capture_output=True, text=True).stdout
    hit, all_files = [], []
    for rec in raw.split("--\n"):
        lines = [l for l in rec.splitlines() if l.strip()]
        if not lines:
            continue
        m = re.match(r"^(\S+?\.c):\d+:", lines[-1])      # the matching line itself
        if not m:
            continue
        f = m.group(1)
        if "/boot/dts/" in f:
            continue
        if f not in all_files:
            all_files.append(f)
        if re.search(r"of_device_id|of_match_table", "\n".join(lines)) and f not in hit:
            hit.append(f)
    if not hit:
        return None, None, len(all_files)
    src = hit[0]
    sym = kconfig_for(src, compat, tree)
    return os.path.relpath(src, tree), sym, len(all_files)


CFG_LINE = re.compile(r'obj-\$\(CONFIG_([A-Za-z0-9_]+)\)\s*\+=\s*(\S+)')
MODULE_RULE = re.compile(r'^\s*([\w.\-]+)-objs\s*:=(\s*)(.*\S)?')


def kconfig_for(src, compat, tree):
    """Find obj-$(CONFIG_X) that pulls this object in, following -objs aggregates one level."""
    d = os.path.dirname(src)
    stem = os.path.basename(src)[:-2]
    mk = os.path.join(d, "Makefile")
    if not os.path.isfile(mk):
        return None
    txt = open(mk, errors="replace").read()
    for m in CFG_LINE.finditer(txt):
        if ("%s.o" % stem) == m.group(2) or m.group(2) == "%s.o" % stem:
            return "CONFIG_" + m.group(1)
    # aggregated module:  obj-$(CONFIG_FOO) += mt6358-core.o  with mt6358-core-y += ...
    # aggregated objects: `foo-objs := a.o b.o` with `obj-$(CONFIG_X) += foo.o`
    for m in re.finditer(r"^(\S+?)-(?:objs|y)\s*[:+]?=([^\n]*)", txt, re.M):
        mod, body = m.group(1), m.group(2)
        if ("%s.o" % stem) not in body:
            continue
        for c in CFG_LINE.finditer(txt):
            if c.group(2) in ("%s.o" % mod, mod):
                return "CONFIG_" + c.group(1)
        return "CONFIG_" + mod.upper().replace("-", "_").replace(".", "")
    # last resort: any obj-$(CONFIG_X) += <dir-stem>.o in the same Makefile
    for m in CFG_LINE.finditer(txt):
        if stem.split("-")[0] and stem.split("-")[0] in m.group(1):
            return "CONFIG_" + m.group(1)
    return None


def cfg_state(tree, sym):
    cfg = os.path.join(tree, ".config")
    if not os.path.isfile(cfg):
        return "?"
    for line in open(cfg, errors="replace"):
        if line.startswith(sym + "="):
            return line.strip().split("=", 1)[1]
        if line == "# " + sym + " is not set":
            return "n"
    return None            # symbol absent from .config entirely


def symbol_exists(tree, sym):
    out = subprocess.run(["grep", "-rhw", "--include=Kconfig*", "--include=Kconfig",
                          sym[7:] if sym.startswith("CONFIG_") else sym,
                          os.path.join(tree, "drivers"), os.path.join(tree, "arch/arm64/Kconfig"),
                          os.path.join(tree, "init/Kconfig")],
                         capture_output=True, text=True).stdout
    return bool(re.search(r"^\s*config\s+%s\s*$" % (sym[7:] if sym.startswith("CONFIG_") else sym),
                          out, re.M))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtb", required=True)
    ap.add_argument("--dtc", required=True)
    ap.add_argument("--target", required=True, help="ported 5.15 tree (for .config + drivers)")
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--fragment")
    ap.add_argument("--compat-index",
                    help="target-tree compatible index (from dtsport.py); lets the per-compatible "
                         "driver grep be skipped for strings that provably bind to nothing")
    ap.add_argument("--apply-config", action="store_true",
                    help="write the fragment's symbols into the target .config (then run olddefconfig)")
    a = ap.parse_args()

    dts = dtb_to_dts(a.dtc, a.dtb)
    nodes = nodes_with_compat(dts)
    idx = None
    if a.compat_index and os.path.isfile(a.compat_index):
        idx = set(l.strip() for l in open(a.compat_index) if l.strip())
    rows, cache = [], {}
    for compat in sorted(nodes):
        if compat not in cache:
            # membership in the pre-built index decides whether to grep for a driver file;
            # without that filter this is one recursive grep per compatible (minutes x 400)
            if idx is not None and compat not in idx:
                cache[compat] = (None, None, 0)
            else:
                cache[compat] = find_binder(a.target, compat)
        src, sym, nhit = cache[compat]
        if not src:
            rows.append({"compatible": compat, "nodes": len(nodes[compat]),
                         "driver": None, "kconfig": None, "state": None,
                         "class": "NO_DRIVER"})
            continue
        state = cfg_state(a.target, sym) if sym else None
        exists = symbol_exists(a.target, sym) if sym else False
        cls = ("ENABLED" if state in ("y", "m") else
               "DISABLED" if exists and state in ("n", None) else "UNKNOWN")
        rows.append({"compatible": compat, "nodes": len(nodes[compat]), "driver": src,
                     "kconfig": sym, "state": state, "symbol_in_tree": exists,
                     "matching_files": nhit, "class": cls})

    enable = sorted({r["kconfig"] for r in rows if r["class"] == "DISABLED" and r["kconfig"]})
    nodrv = sorted({r["compatible"] for r in rows if r["class"] == "NO_DRIVER"})
    stats = {"dtb_nodes_with_compatible": sum(len(v) for v in nodes.values()),
             "distinct_comptibles_in_built_dtb": len(nodes),
             "bound_by_5_15_driver": sum(1 for r in rows if r["driver"]),
             "enabled_in_this_build": sum(1 for r in rows if r["class"] == "ENABLED"),
             "disabled_but_enableable": len(enable),
             "no_driver_in_5_15": len(nodrv)}

    if a.fragment:
        os.makedirs(os.path.dirname(os.path.abspath(a.fragment)), exist_ok=True)
        with open(a.fragment, "w") as f:
            f.write("# even (MT6769) hardware enablement, derived by bin/hwenable.py from the\n"
                    "# built mt6768.dtb: every driver that actually matches a node in this board's\n"
                    "# device tree, that 5.15 has, and that this build left off.  Enable them and\n"
                    "# `make olddefconfig` decides which survive their dependencies.\n")
            for s in enable:
                f.write("%s=y\n" % s)
        stats["fragment"] = a.fragment
        stats["fragment_lines"] = len(enable)

    if a.apply_config and enable:
        cfg = os.path.join(a.target, ".config")
        args = []
        for s in enable:
            args += ["--enable", s[7:]]
        subprocess.run([os.path.join(a.target, "scripts/config"), "--file", cfg] + args,
                       check=True)
        subprocess.run(["make", "-C", a.target, "ARCH=arm64", "LLVM=1", "olddefconfig"],
                       check=True, capture_output=True)
        after = {s: cfg_state(a.target, s) for s in enable}
        stats["after_apply"] = {"on": sum(1 for v in after.values() if v in ("y", "m")),
                                "rejected_by_deps": sorted(k for k, v in after.items()
                                                           if v not in ("y", "m"))[:20]}

    with open(a.out_md, "w") as f:
        f.write("# Device hardware enablement, derived from the built `mt6768.dtb`\n\n")
        f.write("Source of truth: `dtc -I dtb -O dts` of the image this device would boot, then 5.15's\n"
                "`of_device_id` tables and the Makefile line that builds each matching driver. A row is\n"
                "*ENABLED* only if the Kconfig that builds that driver is `y`/`m` in the build config.\n\n")
        f.write("```\n" + "\n".join("%-34s %s" % (k, v) for k, v in stats.items()) + "\n```\n\n")
        f.write("| compatible | nodes | 5.15 driver | Kconfig | state | class |\n")
        f.write("|---|--:|---|---|---|---|\n")
        for r in sorted(rows, key=lambda r: (r["class"] != "ENABLED", r["compatible"])):
            f.write("| `%s` | %d | %s | %s | %s | %s |\n" % (
                r["compatible"], r["nodes"], r["driver"] or "-",
                r["kconfig"] or "-", r["state"] or "-", r["class"]))
        f.write("\n## What config cannot fix\n\n")
        f.write("%d compatibles in this board's DTB have **no driver in 5.15 at all** - these are the\n"
                "driver transplants, not fragment edits. First 60:\n\n" % len(nodrv))
        for c in nodrv[:60]:
            f.write("* `%s` (%d node%s)\n" % (c, len(nodes[c]), "s" if len(nodes[c]) > 1 else ""))
        if enable:
            f.write("\n## Fragment written\n\n`%s` - %d symbols:\n\n```\n%s```\n"
                    % (a.fragment, len(enable), "".join("%s=y\n" % s for s in enable)))
    json.dump({"stats": stats, "rows": rows}, open(a.out_json, "w"), indent=1)
    print("built DTB: %d nodes with compatible, %d distinct; bound %d, enabled %d, enableable %d, driverless %d"
          % (stats["dtb_nodes_with_compatible"], stats["distinct_comptibles_in_built_dtb"],
             stats["bound_by_5_15_driver"], stats["enabled_in_this_build"],
             stats["disabled_but_enableable"], stats["no_driver_in_5_15"]))
    print("wrote %s, %s%s" % (a.out_md, a.out_json, ", " + a.fragment if a.fragment else ""))


main()
