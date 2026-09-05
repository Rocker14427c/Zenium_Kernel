#!/usr/bin/env python3
"""
portedcheck - does the mechanically ported tree actually hold up?

Two bounded checks, both computed from `git diff <base>..HEAD` of the port tree:

1. API-regression scan.  Every line the port inserted is matched against APIs
   that are known to have changed or disappeared between the source baseline
   (4.19) and the target baseline (5.15).  A hit means "this hunk applied
   textually but will not compile / is semantically wrong until reworked", and
   it is attributed to the exact file.

2. Header-resolution proxy.  A hunk that calls a cross-subsystem helper must
   find that symbol declared in the target tree's include/ set.  Identifiers
   introduced by the port that exist neither locally nor in the target headers
   can only come from vendor code that has not been transplanted yet, so they
   measure how coupled the ported subset is to the vendor tree.
"""

import argparse
import collections
import json
import re
import subprocess
import sys

IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
C_KEYWORDS = set("""auto break case char const continue default do double else enum extern
float for goto if inline int long register restrict return short signed sizeof static struct
switch typedef union unsigned void volatile while NULL true false inline __init __exit
__user __iomem __maybe_unused __always_inline""".split())

# APIs whose semantics differ between the 4.19 source base and the 5.15 target base.
REGRESSIONS = [
    ("set_fs/get_fs removed in 5.11", r"\b(set_fs|get_fs|FORCE_SETFS|KERNEL_DS)\b"),
    ("access_ok() 2-arg since 5.0", r"access_ok\s*\(\s*VERIFY_"),
    ("proc_ops required since 5.6", r"\bcreate_proc_(read_)?entry\b|\bPDE_DATA\b|proc_create\w*\([^)]*file_operations"),
    ("timespec removed in 5.6", r"\bstruct timespec\b|\bcurrent_kernel_time\b|\bgetrawmonotonic64?\b|\bset_fs_time\b"),
    ("Ion removed in 5.18 / changed before", r"\bion_[a-z_]+\s*\(|<linux/ion.h>|ion_handle"),
    ("GUP -> pin_user_pages (5.8+)", r"\bget_user_pages(_fast|_remote)?\s*\("),
    ("kmap -> kmap_local (5.11+)", r"\bkmap_atomic\s*\("),
    ("timer_setup required (4.15+)", r"\b(init_timer|setup_timer|setup_pinned_timer)\s*\("),
    ("block: make_request_fn gone (5.14)", r"\b(make_request_fn|blk_queue_make_request)\b"),
    ("strlcpy -> strscpy (6.x, deprecated 5.10+)", r"\bstrlcpy\s*\(|\bstrlcat\s*\("),
    ("ACCESS_ONCE removed (5.8)", r"\bACCESS_ONCE\s*\("),
    ("of_gpio/nodes api churn", r"\bof_get_gpio\b|\bogpio_get\b"),
    ("debugfs/attribute churn", r"\bDEBUGFS_REGEX"),
    ("signal send_sig_info semantics", r"\bsend_sig_info\s*\("),
    ("netif_napi_add lost weight arg (5.19/6.1)", r"netif_napi_add\s*\([^;]*,[^;]*,[^;]*,[^;]*\)"),
    ("mm: mmap_sem renamed (5.8)", r"\bmmap_sem\b"),
    ("vm_insert_pfn/pfnmap changes", r"\bvm_insert_pfn\b"),
    ("file_operations->llseek etc (misc)", r"\bgeneric_file_aio_read\b"),
    ("sched: autogroup/scheduler feature removals", r"CONFIG_SCHED_AUTOGROUP"),
    ("RCU/barrier API churn", r"\bsynchronize_kernel\s*\("),
]


def sh(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    diff = sh(["git", "-C", a.tree, "diff", "--unified=0", a.base, "--"])
    if not diff.strip():
        sys.exit("empty diff - nothing ported?")

    cur = None
    reg = collections.defaultdict(lambda: collections.Counter())
    ident = collections.defaultdict(set)
    per_file_added = collections.Counter()
    hunks = 0
    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            cur = line[6:].strip()
            continue
        if line.startswith("@@"):
            hunks += 1
            continue
        if not cur or not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:]
        per_file_added[cur] += 1
        for name, pat in REGRESSIONS:
            n = len(re.findall(pat, body))
            if n:
                reg[name][cur] += n
        for m in IDENT_RE.findall(body):
            if m in C_KEYWORDS or m.startswith(("*", "&")):
                continue
            ident[m].add(cur)

    print(f"[1/3] {hunks} hunks, {sum(per_file_added.values())} inserted lines, "
          f"{len(ident)} inserted identifiers", flush=True)

    # identifiers that resolve nowhere: not local, not in target headers
    hdr = sh(["bash", "-c",
              f"git -C {a.tree} grep -h -o -E '[A-Za-z_][A-Za-z0-9_]{{2,}}' "
              f"{a.base} -- include | sort -u"])
    known = set(hdr.split("\n"))
    print(f"[2/3] target include/ vocabulary: {len(known)} identifiers", flush=True)

    unresolved = {}
    for name, files in ident.items():
        if name in known:
            continue
        unresolved[name] = files

    # A symbol only counts as "external" if the port's own files define none of
    # it.  A cheap positional regex over the touched files removes most of the
    # local-variable / static-helper noise from the raw set difference.
    import os
    local_defs = set()
    defpat = re.compile(r"^[A-Za-z_][\w \t*]*?\b([A-Za-z_][A-Za-z0-9_]{2,})\s*(\(|\[|=|;|,)")
    structpat = re.compile(r"\b(?:struct|enum|union|typedef)\s+([A-Za-z_][A-Za-z0-9_]{2,})")
    for rel in sorted(per_file_added):
        try:
            txt = open(os.path.join(a.tree, rel), encoding="utf-8",
                       errors="surrogateescape").read()
        except OSError:
            continue
        for line in txt.split("\n"):
            for m in structpat.findall(line):
                local_defs.add(m)
            if line.startswith(("#define", "static", "int ", "void ", "unsigned ",
                                "long ", "bool ", "char ", "struct ")):
                for m in defpat.findall(line):
                    local_defs.add(m)
    external = {k: v for k, v in unresolved.items() if k not in local_defs}
    vendorish = {k: v for k, v in external.items()
                 if k.startswith(("MTK_", "mtk_", "oplus_", "OPLUS_", "CONFIG_"))}
    generic = {k: v for k, v in external.items() if k not in vendorish}

    rep = {
        "hunks": hunks,
        "inserted_lines": sum(per_file_added.values()),
        "inserted_identifiers": len(ident),
        "unresolved_in_target_headers": len(external),
        "unresolved_vendorish": len(vendorish),
        "unresolved_generic": len(generic),
        "regression_hits": {
            name: {"uses": sum(c.values()), "files": len(c),
                   "top_files": [f for f, _ in c.most_common(5)]}
            for name, c in sorted(reg.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "top_unresolved_generic": [
            {"symbol": k, "files": len(v)} for k, v in
            sorted(generic.items(), key=lambda kv: -len(kv[1]))[:50]
        ],
    }
    print("[3/3] writing report", flush=True)
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)

    print(f"\ninserted identifiers unresolved in target headers: {len(external)}")
    print(f"  vendor-namespaced (arrive with the vendor tree): {len(vendorish)}")
    print(f"  generic-looking (need compat work)             : {len(generic)}")
    if rep["regression_hits"]:
        print("\nported lines referencing APIs that changed/disappeared before 5.15:")
        for n, v in rep["regression_hits"].items():
            print(f"  {v['uses']:6d} uses / {v['files']:4d} files  {n}"
                  f"   e.g. {v['top_files'][0]}")


if __name__ == "__main__":
    main()
