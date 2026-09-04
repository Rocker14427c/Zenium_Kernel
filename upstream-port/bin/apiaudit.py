#!/usr/bin/env python3
"""
apiaudit - two static portability audits used by the 4.19 -> 5.15 port.

1. `resolution`: every identifier that the port *inserted* into the target tree
   must resolve in that target tree.  Identifiers that exist nowhere in 5.15 are
   either (a) generic kernel APIs that changed/disappeared -> hard breakage, or
   (b) CONFIG_*/vendor symbols -> must arrive with the vendor tree/Kconfig.
   This is a compile-independent correctness gate for a mechanically ported
   tree, and it is exact about which hunks introduced the dangling reference.

2. `hazard`: count uses of APIs that are known to have been removed or changed
   between the source and target baselines, over the vendor-new file set
   (the code that must be transplanted rather than hunk-ported).

Both audits are pure `git grep` passes, so they scale to a whole kernel tree.
"""

import argparse
import collections
import json
import os
import re
import shlex
import subprocess
import sys

IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")

C_KEYWORDS = set("""
auto break case char const continue default do double else enum extern float for goto if
inline int long register restrict return short signed sizeof static struct switch typedef
union unsigned void volatile while true false NULL sizeof typeof __init __exit static inline
""".split())


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def added_identifiers(tree, base_ref):
    """identifiers -> set(files) for lines added by `git diff base_ref..HEAD`."""
    d = sh(["git", "-C", tree, "diff", "--unified=0", base_ref, "--"])
    if d.returncode:
        sys.exit("git diff failed: " + d.stderr[:400])
    ident = collections.defaultdict(set)
    cur = None
    for line in d.stdout.split("\n"):
        if line.startswith("+++ b/"):
            cur = line[6:]
            continue
        if not cur:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            if body.strip().startswith(("*", "//", "/*", "#include")):
                # comments/includes are handled by the hazard audit instead
                if not body.strip().startswith("#include"):
                    continue
            for m in IDENT_RE.findall(body):
                if m in C_KEYWORDS:
                    continue
                ident[m].add(cur)
        elif not line.startswith("-"):
            pass
    return ident


def tree_identifiers(tree, ref, ident, patterns=None):
    """Which of `ident` actually exist in `ref`?  One Aho-Corasick pass with a
    fixed-pattern file, so cost is independent of the number of candidates."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(sorted(ident)) + "\n")
        pat = f.name
    ps = list(patterns) if patterns else ["*.c", "*.h", "*.S", "*.inc",
                                          "Kconfig", "Makefile"]
    r = subprocess.run(
        ["bash", "-c",
         f"git -C {tree!r} grep -h -o -w -F -f {pat} {ref} -- {' '.join(ps)}"
         f" | sort -u"],
        capture_output=True, text=True)
    os.unlink(pat)
    if r.returncode not in (0, 1):
        sys.exit("git grep failed: " + r.stderr[:400])
    return set(x for x in r.stdout.split("\n") if x)


def cmd_resolution(a):
    print(f"[1/3] extracting identifiers added by {a.base}..HEAD in {a.tree}", flush=True)
    ident = added_identifiers(a.tree, a.base)
    print(f"      {len(ident)} distinct identifiers", flush=True)
    print("[2/3] building identifier index of the target tree (single git-grep pass)",
          flush=True)
    present = tree_identifiers(a.tree, a.base, ident.keys())
    print(f"      {len(present)} identifiers exist in target base", flush=True)

    missing = {k: v for k, v in ident.items() if k not in present}
    buckets = collections.defaultdict(list)
    for name, files in missing.items():
        if name.startswith(("CONFIG_", "MTK_", "OPLUS_", "DTYPE_")):
            buckets["config_or_vendor_symbol"].append((name, sorted(files)[:6]))
        elif name.startswith(("__", "mtk_", "oplus_", "pmic_", "cpu_")):
            buckets["vendor_or_arch_helper"].append((name, sorted(files)[:6]))
        else:
            buckets["generic_kernel_api"].append((name, sorted(files)[:6]))
    for k in buckets:
        buckets[k].sort(key=lambda x: len(x[1]), reverse=True)
    rep = {
        "inserted_identifiers": len(ident),
        "unresolved_total": len(missing),
        "by_class": {k: len(v) for k, v in buckets.items()},
        "generic_kernel_api": [
            {"symbol": n, "files": f, "n_files": len(fs)} for n, fs in
            buckets["generic_kernel_api"][:200]
            for fs in [missing[n]]
        ],
    }
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)
    print("[3/3] summary")
    print(f"inserted identifiers:   {len(ident)}")
    print(f"unresolved in 5.15:     {len(missing)}")
    for k, v in buckets.items():
        print(f"  {k:26s} {len(v)}")
    print("\nhard breakage (generic kernel APIs the port calls but 5.15 lacks):")
    for it in rep["generic_kernel_api"][:25]:
        print(f"  {it['symbol']:34s} in {it['n_files']:4d} file(s)  e.g. {it['files'][0]}")


HAZARDS = [
    ("set_fs/goto_if", r"\b(set_fs|get_fs|FORCE_SETFS|mm_segment_t|KERNEL_DS|USER_DS)\b"),
    ("old access_ok", r"access_ok\s*\(\s*VERIFY_"),
    ("proc_fops (needs proc_ops)", r"\bcreate_proc_(read_)?entry\b|\bPDE_DATA\b"),
    ("ion (removed 5.18)", r"\bion_(alloc|map_kernel|fd_get|import|heap)|<linux/ion.h>"),
    ("get_user_pages (5.8+ -> pin_*)", r"\bget_user_pages(_fast|_remote)?\s*\("),
    ("timespec (removed 5.6)", r"\bstruct timespec\b|\bcurrent_kernel_time\b|\bgetrawmonotonic\b"),
    ("kmap (5.11+ -> kmap_local)", r"\bkmap_atomic\s*\(|\bkmap\s*\("),
    ("blk: make_request_fn (5.14)", r"\bmake_request_fn\b|\bblk_queue_make_request\b"),
    ("dma_map_sg attrs/dma_attrs", r"\bdma_alloc_attrs\b|\bdma_declare_coherent_memory\b"),
    ("strlcpy/strlcat", r"\bstrlcpy\s*\(|\bstrlcat\s*\("),
    ("netif_napi_add weight arg", r"netif_napi_add\s*\([^)]*,[^,)]*,[^,)]*,[^)]*\)"),
    ("timer_setup gap", r"init_timer|setup_timer|mod_timer\s*\([^)]*>\s*\)"),
    ("pci/pci_ops changed", r"struct pci_ops\s*\*\s*\w+\s*=\s*\{[^}]*read\s*="),
    ("ll_rw_block (removed 5.18)", r"\bll_rw_block\b"),
    ("init_MUTEX (removed)", r"\binit_MUTEX\b"),
    ("signal: send_sig_info sigqueue", r"__send_sig_info|send_sig_info"),
    ("net: skb_frag page_link", r"skb_frag_page\s*\("),
]


def cmd_hazard(a):
    """Count uses of APIs whose semantics changed between the source and target
    baseline, over the *vendor-new* file set (the transplant surface)."""
    roots = a.roots or ["drivers/misc/mediatek"]
    files = sh(["git", "-C", a.tree, "ls-files", "--"] + roots).stdout.split("\n")
    src = [f for f in files if f.endswith((".c", ".h"))]
    if a.only_new:
        with open(a.only_new) as fh:
            newset = {x.strip() for x in fh if x.strip()}
        src = [f for f in src if f in newset]
    print(f"auditing {len(src)} vendor-new files under: {', '.join(roots)}", flush=True)
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".lst", delete=False) as tf:
        tf.write("\0".join(src) + "\0")
        lst = tf.name
    loc = 0
    for f in src:
        try:
            with open(os.path.join(a.tree, f), "rb") as fh:
                loc += fh.read().count(b"\n")
        except OSError:
            pass
    counts = {}
    for name, pat in HAZARDS:
        uses = sh(["bash", "-c",
                   f"xargs -0 -a {lst} grep -ohE {shlex.quote(pat)} 2>/dev/null | wc -l"]).stdout
        ffiles = sh(["bash", "-c",
                     f"xargs -0 -a {lst} grep -lE {shlex.quote(pat)} 2>/dev/null | wc -l"]).stdout
        u = int(uses.strip() or 0)
        if u:
            counts[name] = {"uses": u, "files": int(ffiles.strip() or 0)}
    os.unlink(lst)
    out = {
        "audited_roots": roots,
        "scope": "vendor-new files only (not present in vanilla base)" if a.only_new
                 else "all files under roots",
        "files": len(src),
        "loc": loc,
        "hazards": dict(sorted(counts.items(), key=lambda kv: -kv[1]["uses"])),
    }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"files audited: {len(src)}  ({loc} lines of C in scope)")
    for k, v in out["hazards"].items():
        print(f"  {v['uses']:8d} uses in {v['files']:5d} files  {k}")


def main():
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="cmd", required=True)
    r = s.add_parser("resolution")
    r.add_argument("--tree", required=True, help="ported tree (git repo)")
    r.add_argument("--base", required=True, help="base ref inside that tree")
    r.add_argument("--out", required=True)
    r.set_defaults(func=cmd_resolution)
    h = s.add_parser("hazard")
    h.add_argument("--tree", required=True)
    h.add_argument("--roots", nargs="*")
    h.add_argument("--out", required=True)
    h.add_argument("--only-new", help="file listing (only audit paths in this list)")
    h.set_defaults(func=cmd_hazard)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
