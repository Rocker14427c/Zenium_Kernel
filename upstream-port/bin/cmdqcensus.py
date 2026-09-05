#!/usr/bin/env python3
"""cmdqcensus.py - measure which CMDQ client entry points the MT6768/even display path actually
needs, the only way that question can be answered: strip C comments and string literals, then walk
the preprocessor stack so every callsite is reported together with the #if/#ifdef guards that decide
whether it is compiled for this board's config.

Why this exists: grep-counting symbol names over-counts. It counts commented-out calls (ddp_dsi.c
carries one such cmdq_pkt_sleep call inside /* */) and calls guarded by CONFIG_MTK_MT6382_BDG, which
even_defconfig does not set - and which also guards the vendor definition of cmdq_pkt_sleep_by_poll,
so that function is not compiled for this board at all.

Usage:
  cmdqcensus.py [--root REPO] [--config arch/arm64/configs/even_defconfig] SYM [SYM...]
Output: JSON on stdout: per symbol, per callsite {file, line, code, guards, guards_active_for_this_board}
"""
import argparse
import json
import os
import re
import sys

# Config symbols whose value decides reachability, read from the board defconfig once.
def parse_defconfig(path):
    """Return {CONFIG_NAME: 'y'|'m'|'n'} for every symbol mentioned as set or 'is not set'."""
    state = {}
    if not os.path.exists(path):
        return state
    for line in open(path, errors="replace"):
        line = line.strip()
        m = re.match(r"CONFIG_(\w+)=([ym]|n|0|1)", line)
        if m:
            state[m.group(1)] = m.group(2) if m.group(2) in "ym" else "n"
            continue
        m = re.match(r"#\s*CONFIG_(\w+)\s+is not set", line)
        if m:
            state[m.group(1)] = "n"
    return state


def strip_comments_and_strings(src):
    """Blank out C comments and string/char literal contents, preserving line and column layout.
    Returns text where every comment/string byte is a space, so regexes cannot match them."""
    out = []
    i, n = 0, len(src)
    mode = "code"  # code | line_comment | block_comment | string | char
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if mode == "code":
            if c == "/" and nxt == "/":
                mode = "line_comment"; out.append("  "); i += 2; continue
            if c == "/" and nxt == "*":
                mode = "block_comment"; out.append("  "); i += 2; continue
            if c == '"':
                mode = "string"; out.append(c); i += 1; continue
            if c == "'":
                mode = "char"; out.append(c); i += 1; continue
            out.append(c); i += 1; continue
        if mode == "line_comment":
            if c == "\n":
                mode = "code"; out.append("\n")
            else:
                out.append(" ")
            i += 1; continue
        if mode == "block_comment":
            if c == "*" and nxt == "/":
                mode = "code"; out.append("  "); i += 2; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        if mode in ("string", "char"):
            quote = '"' if mode == "string" else "'"
            if c == "\\":
                out.append("  "); i += 2; continue
            if c == quote:
                mode = "code"; out.append(c); i += 1; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
    return "".join(out)


DIRECTIVE = re.compile(r"^\s*#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)$")
IDENT_COND = re.compile(r"^(?:defined\s*\(\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\)?$")


def evaluate(cond, cfg, assume_true=set()):
    """Evaluate a #if expression over CONFIG_* symbols using the defconfig map.
    Unknown symbols -> None (undecidable), so the caller reports 'unknown' instead of guessing."""
    def repl(m):
        name = m.group(1)
        if name.startswith("CONFIG_"):
            name = name[len("CONFIG_"):]
        v = cfg.get(name)
        if v is None and name in assume_true:
            v = "y"
        if v is None:
            return "UNDECIDABLE"
        return "1" if v in ("y", "m", "1") else "0"

    expr = re.sub(r"defined\s+\(\s*([A-Za-z_][\w.]*)\s*\)", r"\1", cond)
    expr = re.sub(r"defined\s+([A-Za-z_][\w.]*)", r"\1", expr)
    expr = re.sub(r"CONFIG_([A-Za-z0-9_]*)", r"CONFIG_\1", expr)
    expr = re.sub(r"\b([A-Za-z_][A-Za-z0-9_.]*)\b", repl, expr)
    if "UNDECIDABLE" in expr:
        return None
    expr = expr.replace("||", " or ").replace("&&", " and ").replace("!", " not ")
    expr = re.sub(r"==\s*1", "== 1", expr)
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return None


def guard_stack(lines, cfg):
    """For every line index, the list of active guard expressions (outermost first)."""
    stack, out = [], []
    for line in lines:
        m = DIRECTIVE.match(line)
        if m:
            kw, rest = m.group(1), m.group(2).strip()
            if kw in ("ifdef", "ifndef"):
                sym = rest.split()[0] if rest.split() else "?"
                expr = ("CONFIG_" + sym.replace("CONFIG_", "")) if kw == "ifdef" \
                    else "!defined(CONFIG_" + sym.replace("CONFIG_", "") + ")"
                stack.append((line.strip(), expr))
            elif kw == "if":
                stack.append((line.strip(), rest))
            elif kw == "elif" and stack:
                stack[-1] = (stack[-1][0], "elif " + rest)
            elif kw == "else" and stack:
                stack[-1] = (stack[-1][0], "else")
            elif kw == "endif" and stack:
                stack.pop()
        out.append(list(stack))
    return out


def reach(guards, cfg):
    """'live' if every guard evaluates true for this config, 'dead' if any evaluates false,
    'unknown' if any is undecidable."""
    if not guards:
        return "live"
    verdict = "live"
    for _, expr in guards:
        if expr.startswith("elif") or expr == "else":
            val = None
        else:
            val = evaluate(expr, cfg)
        if val is None:
            verdict = "unknown" if verdict != "dead" else "dead"
        elif val is False:
            return "dead"
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--config", default="arch/arm64/configs/even_defconfig")
    ap.add_argument("--scan", default="drivers/misc/mediatek/video/mt6768")
    ap.add_argument("syms", nargs="+")
    a = ap.parse_args()

    cfg = parse_defconfig(os.path.join(a.root, a.config))
    files = []
    for rel in a.scan.split(","):
        base = os.path.join(a.root, rel)
        for root, _, fs in os.walk(base):
            for fn in fs:
                if fn.endswith((".c", ".h")):
                    files.append(os.path.join(root, fn))
    files.sort()

    result = {s: [] for s in a.syms}
    for path in files:
        try:
            raw = open(path, errors="replace").read()
        except OSError:
            continue
        clean = strip_comments_and_strings(raw)
        lines = clean.split("\n")
        stacks = guard_stack(lines, cfg)
        for i, line in enumerate(lines):
            for sym in a.syms:
                if re.search(r"\b" + re.escape(sym) + r"\s*\(", line):
                    guards = stacks[i]
                    result[sym].append({
                        "file": os.path.relpath(path, a.root),
                        "line": i + 1,
                        "code": line.strip()[:110],
                        "guards": [g[0][:70] for g in guards],
                        "reach": reach(guards, cfg),
                    })
    print(json.dumps({
        "config": a.config,
        "config_relevant": {k: v for k, v in sorted(cfg.items())
                            if any(t in k for t in ("MT6382_BDG", "MTK_CMDQ", "MACH_MT6768", "DRM"))},
        "symbols": result,
        "summary": {s: {"hits": len(v),
                        "live": sum(1 for x in v if x["reach"] == "live"),
                        "dead": sum(1 for x in v if x["reach"] == "dead"),
                        "unknown": sum(1 for x in v if x["reach"] == "unknown")}
                    for s, v in result.items()},
    }, indent=1))


if __name__ == "__main__":
    sys.exit(main())
