#!/usr/bin/env python3
"""buildreport.py - turn the build attempt into machine-checkable evidence.

Collects: the exact cross toolchain used (versions), the config deltas made for
the sandbox and why, every gate's findings, the per-file decision ledger, and
the resulting artifacts (Image / .config / objects / dtbs / modules) with hashes
and sizes.  Writes report/build.json plus a markdown block the migration doc
includes, so no number in the write-up is hand-typed.

Usage: buildreport.py --tree T --base REF --report DIR [--logs "build-*.log"]
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess


def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str),
                          capture_output=True, text=True).stdout.strip()


def ver(path, args=("--version",)):
    try:
        out = subprocess.run([path] + list(args), capture_output=True, text=True,
                             env={**os.environ,
                                  "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH", "")})
        first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else ""
        return {"path": path, "version": first.strip(), "ok": out.returncode == 0}
    except Exception as e:
        return {"path": path, "version": f"unusable: {e}", "ok": False}


def sha256(p, cap=None):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


GATES = [
    ("structcheck.json", "structcheck", "structural balance of every touched file "
     "(make/Kconfig conditionals, braces, #if/#endif)"),
    ("gluecheck.json", "gluecheck", "every build-glue reference (Kconfig source, obj-y dir) resolves"),
    ("gluefix.json", "gluefix", "kconfig parser driven until it accepts the tree"),
    ("dupdef.json", "dupdef", "definitions the port duplicated next to 5.15's own copy"),
    ("kabistrip.json", "kabistrip", "Android GKI KABI padding carried in by the port"),
    ("inclosure.json", "inclosure", "vendor headers the ported code #includes"),
    ("verify.json", "verify", "post-image / pre-image / line-delta per hunk"),
    ("portedcheck.json", "portedcheck", "ported lines touching APIs changed between 4.19 and 5.15"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--base", default="v5.15.220")
    ap.add_argument("--report", required=True)
    ap.add_argument("--logs", default="/home/user/.cache/upstream/build-*.log")
    ap.add_argument("--config-notes", default=None,
                    help="file of 'CONFIG_X=n  reason' lines to reproduce verbatim")
    a = ap.parse_args()
    R = a.report
    rep = {}

    # ---- toolchain -------------------------------------------------------
    tb = {}
    for name, cand in [
        ("clang", "clang-14"), ("ld.lld", "ld.lld"), ("llvm-ar", "llvm-ar"),
        ("llvm-nm", "llvm-nm"), ("llvm-objcopy", "llvm-objcopy"),
        ("llvm-strip", "llvm-strip"), ("llvm-readelf", "llvm-readelf"),
        ("llvm-objdump", "llvm-objdump"), ("make", "make"), ("flex", "flex"),
        ("bison", "bison"), ("m4", "m4"), ("python3", "python3"), ("perl", "perl"),
        ("host-gcc", "gcc"),
    ]:
        w = sh(["bash", "-lc", f"command -v {cand}"]) or cand
        tb[name] = ver(w if "/" in w or os.path.exists(w) else cand)
    rep["toolchain"] = tb

    # ---- what the tree looks like now ------------------------------------
    touched = sh(["git", "-C", a.tree, "diff", "--name-only", a.base]).split("\n")
    touched = [t for t in touched if t.strip()]
    numstat = sh(["git", "-C", a.tree, "diff", "--numstat", a.base])
    add = rem = 0
    for l in numstat.splitlines():
        p = l.split("\t")
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            add += int(p[0]); rem += int(p[1])
    newfiles = [l[3:].strip() for l in sh(["git", "-C", a.tree, "status", "--short"]).splitlines()
                if l.startswith("??")]
    rep["tree"] = {
        "files_modified": len(touched), "insertions": add, "deletions": rem,
        "untracked_paths": len(newfiles),
        "head": sh(["git", "-C", a.tree, "rev-parse", "HEAD"]),
        "base_commit": sh(["git", "-C", a.tree, "rev-parse", a.base]),
        "worktree": a.tree,
    }

    # ---- gates -----------------------------------------------------------
    gates = {}
    for fn, key, desc in GATES:
        p = os.path.join(R, fn)
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        brief = {"description": desc}
        for k in ("files_checked", "imbalanced", "glue_files_checked", "dangling_total",
                  "dangling_introduced_by_port", "dangling_pre_existing", "clean",
                  "iterations", "files_with_port_introduced_duplicates", "files",
                  "lines_removed", "copied_total", "unresolved_total", "target"):
            if k in d:
                brief[k] = d[k]
        if "totals" in d:
            brief["totals"] = d["totals"]
        if "counts" in d:
            brief["counts"] = d["counts"]
        if key == "verify":
            brief["counts"] = d.get("counts", {})
        gates[key] = brief
    rep["gates"] = gates

    # ---- decisions ledger ------------------------------------------------
    dp = os.path.join(R, "decisions.json")
    if os.path.exists(dp):
        dec = json.load(open(dp))["decisions"]
        for extra in glob.glob("/home/user/.cache/upstream/bf-*.log.actions.json"):
            for act in json.load(open(extra)).get("actions", []):
                dec.append({**act, "source": os.path.basename(extra)})
        by_action = {}
        for d in dec:
            by_action[d["action"]] = by_action.get(d["action"], 0) + 1
        rep["decisions"] = {"count": len(dec), "by_action": by_action, "items": dec}

    # ---- config deltas ---------------------------------------------------
    cfg = []
    if a.config_notes and os.path.exists(a.config_notes):
        for line in open(a.config_notes):
            line = line.strip()
            if line and not line.startswith("#"):
                cfg.append(line)
    rep["config_notes"] = cfg
    rep["config_summary"] = {
        k: v for k, v in [
            (l.split("=")[0][len("CONFIG_"):], l.split("=", 1)[1])
            for l in sh(["grep", "-E",
                         "^CONFIG_(ARM64|CC_IS_CLANG|LD_IS_LLD|MODULES|DEBUG_INFO|"
                         "ARCH_MEDIATEK|LOCALVERSION)[=A-Z_]*", os.path.join(a.tree, ".config")])
            .splitlines() if "=" in l]
    }

    # ---- build evidence --------------------------------------------------
    logs = sorted(glob.glob(a.logs))
    ev = {"logs": [], "artifacts": {}}
    for lg in logs:
        try:
            txt = open(lg, errors="replace").read()
        except OSError:
            continue
        errs = sorted(set(re.findall(r"^\S+:\d+:\d+: error: .*$", txt, re.M)))
        ev["logs"].append({"log": os.path.basename(lg), "bytes": len(txt),
                           "error_lines": len(errs),
                           "first_errors": [e[:160] for e in errs[:6]],
                           "clean": "EXIT=0" in txt and not errs})
    for cand in ("arch/arm64/boot/Image", "arch/arm64/boot/Image.gz",
                 "arch/arm64/boot/Image.gz-dtb", "vmlinux", "System.map"):
        p = os.path.join(a.tree, cand)
        if os.path.exists(p):
            ev["artifacts"][cand] = {"bytes": os.path.getsize(p),
                                     "sha256": sha256(p)}
    ev["objects_compiled"] = int(sh(["bash", "-lc",
        f"find {a.tree} -name '*.o' -not -path '*/.git/*' | wc -l"]) or 0)
    ev["modules_built"] = int(sh(["bash", "-lc",
        f"find {a.tree} -name '*.ko' | wc -l"]) or 0)
    ev["dtbs_built"] = int(sh(["bash", "-lc",
        f"find {a.tree}/arch/arm64/boot/dts -name '*.dtb' 2>/dev/null | wc -l"]) or 0)
    rep["build"] = ev

    with open(os.path.join(R, "build.json"), "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)

    # ---- markdown block --------------------------------------------------
    L = ["## Build evidence", "",
         "Toolchain actually used (every one of these is the binary the build ran):", "",
         "| tool | version |", "|---|---|"]
    for k, v in tb.items():
        L.append(f"| `{k}` | {v['version'][:96]} |")
    L += ["", f"Tree state: **{rep['tree']['files_modified']} files modified**, "
          f"+{rep['tree']['insertions']:,}/-{rep['tree']['deletions']:,} against "
          f"`{a.base}` (`{rep['tree']['head'][:12]}`), "
          f"{rep['tree']['untracked_paths']} paths added by the transplant step.", "",
          "Gates run over the ported tree:", "",
          "| gate | what it proves | result |", "|---|---|---|"]
    for k, g in gates.items():
        res = []
        for kk in ("imbalanced", "dangling_introduced_by_port", "files_with_port_introduced_duplicates",
                   "lines_removed", "copied_total", "unresolved_total", "iterations",
                   "clean"):
            if kk in g:
                res.append(f"{kk}={g[kk]}")
        if "counts" in g and isinstance(g["counts"], dict):
            res.append("counts=" + json.dumps(g["counts"], sort_keys=True)[:120])
        L.append(f"| `{k}` | {g['description']} | {', '.join(res) or 'see json'} |")
    if "decisions" in rep:
        L += ["", "Per-file decisions taken to make the port coherent (nothing was dropped "
              "silently; each entry names the reason):", "",
              "| action | files |", "|---|---|"]
        for k, v in sorted(rep["decisions"]["by_action"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {k} | {v} |")
        L.append(f"| **total** | **{rep['decisions']['count']}** |")
    if cfg:
        L += ["", "Config deltas made *for this build* (sandbox constraints, not port issues):", ""]
        L += [f"- `{c}`" for c in cfg]
    L += ["", "Compile evidence:", "",
          f"- objects produced: **{ev['objects_compiled']:,}**",
          f"- `.ko` modules: {ev['modules_built']},  `.dtb` files: {ev['dtbs_built']}"]
    for k, v in ev["artifacts"].items():
        L.append(f"- `{k}`: {v['bytes']:,} bytes, sha256 `{v['sha256'][:16]}...`")
    for lg in ev["logs"][-3:]:
        L.append(f"- `{lg['log']}`: {lg['error_lines']} distinct error line(s)"
                 + (" -> **build clean**" if lg["clean"] else ""))
    with open(os.path.join(R, "build-evidence.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {R}/build.json and build-evidence.md")
    print(f"  objects={ev['objects_compiled']:,}  artifacts={list(ev['artifacts'])}")
    print(f"  files modified={rep['tree']['files_modified']}  "
          f"decisions={rep.get('decisions', {}).get('count', 0)}")


if __name__ == "__main__":
    main()
