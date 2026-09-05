#!/usr/bin/env python3
"""Audit a MediaTek CCF clock provider against the *device's* DT cell indices.

Why this exists: a ported clock driver can compile cleanly and still not be a clock
provider for the SoC. MTK BSPs carry per-domain gate tables, and some domains are
stubs (the legacy clkmgr provided those bits in 4.19). If the driver registers a
provider for `mediatek,pericfg` with 1 gate while the device tree references dozens
of indices in that same space, then every consumer either defers forever (index not
registered) or - worse - gets a *different* clock whose index happens to collide.
Silently-wrong clocks are the failure mode that looks like success in a build log.

So this script answers three questions with the built DTB as input:

  1. per provider domain: how many ids does the driver actually register?
  2. per provider domain: how many DT clock references does the device make, and
     which indices?
  3. hazard: does any DT-referenced index fall inside the set the driver registers?
     (overlap => a consumer could bind to an unrelated clock, no error anywhere)

Outputs JSON + a markdown table. Read-only; no config is touched.
"""
import argparse, collections, json, re, os, subprocess, sys

PROVIDER_DOMAIN = {  # DT compatible -> header prefix family used by mt6768-clk.h
    "mediatek,topckgen": "CLK_TOP",
    "mediatek,topckgen_ao": "CLK_TOP",
    "mediatek,apmixed": "CLK_APMIXED",
    "mediatek,pericfg": "CLK_PERI",
    "mediatek,infracfg_ao": "CLK_INFRA",
    "mediatek,infracfg": "CLK_INFRA",
    "mediatek,audio": "CLK_AUD",
    "mediatek,mt6768-camsys": "CLK_CAM",
    "mediatek,mt6768-imgsys": "CLK_IMG",
    "mediatek,gce": "CLK_GCE",
    "mediatek,mmsys_config": "CLK_MM",
    "mediatek,mfgcfg": "CLK_MFG",
    "mediatek,venc_gcon": "CLK_VENC",
    "mediatek,vdec_gcon": "CLK_VDEC",
}
# which <name>_clks[] array feeds which provider, from the driver's probe switch
# Every mtk_* table in the driver, attributed to the domain whose probe registers it.
# Getting this right matters: a topckgen probe registers gates *and* muxes *and* dividers
# into one clk_data, so counting only *_clks[] would report dozens of DT references as
# "unregistered" when the driver does provide them.
ARRAY_FOR_DOMAIN = {
    "CLK_TOP": ("top_clks", "top_muxes", "top_divs", "top_factors", "top_audmuxes",
                "top_child_clks", "top_child_factors", "top_pwrsel_muxes"),
    "CLK_APMIXED": ("apmixed_clks", "plls"),
    "CLK_PERI": ("peri_clks", "peri1_clks"),
    "CLK_INFRA": ("ifr_clks", "ifr2_clks"),
    "CLK_AUD": ("audio_clks",),
    "CLK_CAM": ("cam_clks",),
    "CLK_IMG": ("img_clks",),
    "CLK_GCE": ("gce_clks",),
    "CLK_MM": ("mm_clks",),
    "CLK_MFG": ("mfgcfg_clks",),
    "CLK_VENC": ("venc_clks",),
    "CLK_VDEC": ("vdec_clks",),
    None: ("mipi0a_clks", "mipi0b_clks", "mipi1a_clks", "mipi1b_clks",
           "mipi2a_clks", "mipi2b_clks"),
}


def read(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def header_ids(hdr):
    """name -> id, and id -> names, for one header."""
    name2id, id2names = {}, collections.defaultdict(list)
    for m in re.finditer(r"^#define\s+(CLK_\w+)\s+(\d+)", read(hdr), re.M):
        name2id[m.group(1)] = int(m.group(2))
        id2names[int(m.group(2))].append(m.group(1))
    return name2id, id2names


def driver_tables(src):
    """array name -> set of id macros used, for every *_clks[] / _muxes[] table."""
    out = {}
    for m in re.finditer(r"(?:static\s+)?(?:const\s+)?struct\s+mtk_\w+\s+(\w+)\s*(?:__initconst\s*)?\[\]\s*=\s*\{(.*?)^\};",
                         src, re.S | re.M):
        name, body = m.group(1), m.group(2)
        ids = re.findall(r"\b(CLK_[A-Z0-9_]+)\b", body)
        out[name] = ids
    return out


def dtc_nodes(dtb, dtc):
    r = subprocess.run([dtc, "-I", "dtb", "-O", "dts", "-q", dtb],
                       capture_output=True, text=True)
    if r.returncode and not r.stdout:
        sys.exit("dtc failed: " + r.stderr[:300])
    nodes, stack = [], []
    for line in r.stdout.split("\n"):
        # Two shapes matter here: the unit address is optional (MTK board dts use plain
        # node names), and dtc -O dts prefixes a node with its *label* ("pericfg:
        # pericfg@10003000 {"). Matching only "name@addr {" silently drops every labeled
        # node, and since those are exactly the clock/reset providers, each phandle they
        # carry disappears and all consumers look dangling. Both are allowed for here.
        m = re.match(r"^(\t+)(?:[\w,.\-]+:\s+)?([\w,.\-]+(?:@[\w,.\-]+)?) \{$", line)
        if m:
            n = {"name": m.group(2), "props": {}, "comp": [], "phandle": None,
                 "parent": stack[-1]["name"] if stack else "/"}
            stack.append(n)
            nodes.append(n)
            continue
        if re.match(r"^\t+\};", line) and stack:
            stack.pop()
            continue
        if not stack:
            continue
        m = re.match(r"^\t+([\w,\-.#]+) = (.*);$", line)
        if not m:
            continue
        k, v = m.groups()
        stack[-1]["props"].setdefault(k, []).append(v)
        if k == "compatible":
            # dtc prints a multi-string property as one quoted string with \0 between
            # entries: "mediatek,topckgen\0syscon". Split it, or every provider's
            # compatible fails to match the domain table and the audit sees nothing.
            stack[-1]["comp"] = [s for raw in re.findall(r'"([^"]*)"', v)
                                 for s in raw.split("\\0") if s]
        elif k == "phandle":
            stack[-1]["phandle"] = int(v.strip("&<> "), 0) if v.strip("&<> ").startswith("0x") else int(v.strip("&<> "))
    return nodes


SUFFIXES = (".dts", ".dtsi", ".h")


def dtb_provenance(dtb):
    """Identify the exact bytes being audited, and refuse to be quietly stale.

    This audit's conclusions are only as good as the .dtb fed to it: a file kbuild
    considers up to date is not recompiled, so an audit can silently describe an
    older DTB than the tree builds today (that happened twice on this port, and both
    times produced a published DTB-size claim that had no cause).  So: hash the input,
    and compare its mtime against everything kbuild feeds into the dtc rule - the
    board Makefile (its DTS_CPPFLAGS -D list), every .dts/.dtsi in the dts tree, the
    dt-binding headers, and include/generated/autoconf.h (the DTS #includes it, so a
    .config change that turns a #if defined(CONFIG_MTK_*) block on or off changes the
    DTB without touching a single source file).
    """
    import hashlib
    st = os.stat(dtb)
    sha = hashlib.sha256(open(dtb, "rb").read()).hexdigest()
    tree = dtb[:dtb.find("/arch/")] or os.path.dirname(dtb)
    roots = [os.path.join(tree, "arch/arm64/boot/dts"),
             os.path.join(tree, "include/dt-bindings"),
             os.path.join(tree, "include/generated/autoconf.h"),
             os.path.join(tree, "scripts/Makefile.lib")]
    newer = []
    for r in roots:
        if os.path.isfile(r):
            if os.stat(r).st_mtime > st.st_mtime:
                newer.append(os.path.relpath(r, tree))
            continue
        for dirpath, _dirs, files in os.walk(r):
            for f in files:
                if f.endswith(SUFFIXES) or f == "Makefile":
                    q = os.path.join(dirpath, f)
                    try:
                        if os.stat(q).st_mtime > st.st_mtime:
                            newer.append(os.path.relpath(q, tree))
                    except OSError:
                        pass
    return {"path": dtb, "bytes": st.st_size, "sha256_16": sha[:16],
            "newer_than_dtb": sorted(newer)[:40], "newer_count": len(newer)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtb", required=True)
    ap.add_argument("--driver", required=True, help="the ported CCF driver .c")
    ap.add_argument("--header", required=True, help="the dt-bindings clock header used by both")
    ap.add_argument("--dtc", default="dtc")
    ap.add_argument("--out-json")
    ap.add_argument("--require-fresh", action="store_true",
                    help="exit 2 if the .dtb is older than any input kbuild would feed dtc")
    ap.add_argument("--out-md")
    a = ap.parse_args()

    name2id, id2names = header_ids(a.header)
    src = read(a.driver)
    tables = driver_tables(src)
    reg = {}   # array -> set(int ids)
    for arr, ids in tables.items():
        reg[arr] = {name2id[i] for i in ids if i in name2id}
    registered = {}   # domain -> {id: (array, macro name)}
    for dom, arrays in ARRAY_FOR_DOMAIN.items():
        s = {}
        for arr in arrays:
            for macro in tables.get(arr, []):
                if macro in name2id:
                    s.setdefault(name2id[macro], (arr, macro))
        registered[dom] = s

    prov = dtb_provenance(a.dtb)
    if prov["newer_count"]:
        msg = ("STALE INPUT: %d file(s) newer than %s (e.g. %s) - rebuild the dtbs "
               "target before trusting this audit" % (prov["newer_count"],
               os.path.basename(a.dtb), prov["newer_than_dtb"][0]))
        print(msg, file=sys.stderr)
        if a.require_fresh:
            sys.exit(2)
    nodes = dtc_nodes(a.dtb, a.dtc)
    byph = {n["phandle"]: n for n in nodes if n["phandle"] is not None}

    def dom_of(node):
        for c in node["comp"]:
            if c in PROVIDER_DOMAIN:
                return PROVIDER_DOMAIN[c]
        return None

    refs = collections.Counter()          # domain -> count of DT clock refs
    bucket = collections.defaultdict(collections.Counter)   # domain -> class -> count
    ok, unresolved, unregistered, foreign, collisions = [], [], [], [], []
    for n in nodes:
        for prop in ("clocks", "assigned-clocks"):
            for v in n["props"].get(prop, []):
                # clocks/assigned-clocks are FLAT cell lists: <phandle id...> repeated,
                # where the id cell count is that provider's #clock-cells (0 = fixed-clock).
                cells = [int(c, 0) for c in re.findall(r"0x[0-9a-fA-F]+|\d+", v)]
                i = 0
                while i < len(cells):
                    prov = byph.get(cells[i])
                    if prov is None:
                        break              # dangling or label-only reference
                    nc = 0
                    cc = prov["props"].get("#clock-cells")
                    if cc:
                        mm = re.search(r"0x[0-9a-fA-F]+|\d+", cc[0])
                        nc = int(mm.group(0), 0) if mm else 0
                    i += 1 + nc
                    idx = cells[i - nc] if nc else None
                    dom = dom_of(prov)
                    if nc == 0:
                        bucket[dom]["registered"] += 1   # zero-cell provider: resolves by construction
                        continue
                    refs[dom] += 1
                    cls = "unresolved_provider"
                    got = registered.get(dom, {})
                    names = id2names.get(idx, [])
                    if idx in got:
                        cls = "registered"
                        ok.append({"consumer": n["name"], "provider": prov["name"],
                                   "index": idx, "clock": got[idx][1]})
                    elif names and any(x.startswith((dom or "") + "_") for x in names):
                        cls = "header_id_not_registered"
                        unregistered.append((n["name"], prov["name"], dom, idx, ",".join(names)))
                    elif dom is None:
                        cls = "unresolved_provider"
                        unresolved.append((n["name"], prov["name"], idx))
                    else:
                        cls = "foreign_numbering"
                        foreign.append({"consumer": n["name"], "provider": prov["name"],
                                        "domain": dom, "index": idx,
                                        "header_names_with_value": names[:4]})
                        if names:
                            collisions.append((n["name"], idx, names[0]))
                    bucket[dom][cls] += 1
    res = {
        "inputs": {"dtb": os.path.basename(a.dtb), "dtb_provenance": prov, "driver": os.path.basename(a.driver),
                   "header": os.path.basename(a.header)},
        "header_defines": len(name2id),
        "driver_tables": {k: len(set(v)) for k, v in sorted(tables.items()) if v},
        "registered_ids_per_domain": {str(d): len(v) for d, v in registered.items()},
        "dt_refs_per_domain": {"domain=%s" % d: {"refs": c,
                                                  "classified": dict(bucket.get(d, {}))}
                               for d, c in refs.most_common()},
        "totals": {"refs": sum(refs.values()), "registered": len(ok),
                   "header_id_not_registered": len(unregistered),
                   "foreign_numbering": len(foreign), "unresolved_provider": len(unresolved),
                   "cross_domain_name_collisions": len(collisions)},
        "examples_not_registered": [list(u) for u in unregistered[:10]],
        "examples_foreign": foreign[:10],
        "examples_registered": ok[:10],
    }
    if a.out_json:
        json.dump(res, open(a.out_json, "w"), indent=1)
    if a.out_md:
        with open(a.out_md, "w") as fh:
            fh.write("# Clock provider audit - %s vs %s\n\n" %
                     (os.path.basename(a.dtb), os.path.basename(a.driver)))
            fh.write("Per provider domain: ids the ported driver registers, and how the device's\n"
                     "own clock references classify against the header + driver.\n\n")
            fh.write("| domain | ids registered by driver | refs | registered | header id, not registered | foreign numbering | unresolved provider |\n")
            fh.write("|---|---|---|---|---|---|---|\n")
            for d in sorted(set(list(registered) + list(refs)), key=lambda x: str(x)):
                b = bucket.get(d, {})
                fh.write("| %s | %d | %d | %d | %d | %d | %d |\n" % (
                    d, len(registered.get(d, {})), refs.get(d, 0), b.get("registered", 0),
                    b.get("header_id_not_registered", 0), b.get("foreign_numbering", 0),
                    b.get("unresolved_provider", 0)))
            fh.write("\nTotals: %s\n" % json.dumps(res["totals"]))
    print(json.dumps(res, indent=1)[:2000])



if __name__ == "__main__":
    main()
