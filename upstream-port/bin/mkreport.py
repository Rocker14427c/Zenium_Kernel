#!/usr/bin/env python3
"""
mkreport - render the migration tables (markdown) from the audit artifacts
produced by portclassify.py / apiaudit.py / portedcheck.py / soccompare.py.

    mkreport.py --in <artifact dir> --out tables.md
"""
import argparse
import collections
import csv
import json
import os

IRRELEVANT = (
    "arch/x86/", "arch/powerpc/", "arch/mips/", "arch/sparc/", "arch/alpha/",
    "arch/ia64/", "arch/m68k/", "arch/nios2/", "arch/openrisc/", "arch/parisc/",
    "arch/riscv/", "arch/s390/", "arch/sh/", "arch/unicore32/", "arch/xtensa/",
    "arch/um/", "arch/nds32/", "arch/c6x/", "arch/hexagon/", "arch/arc/",
    "arch/arm/", "arch/microblaze/",
    "drivers/pinctrl/sh-pfc", "drivers/pinctrl/samsung", "drivers/pinctrl/sunxi",
    "drivers/pinctrl/bcm", "drivers/pinctrl/freescale", "drivers/pinctrl/nuvoton",
    "drivers/pinctrl/pinctrl-s*", "drivers/gpu/drm/i915", "drivers/gpu/drm/amd",
    "drivers/gpu/drm/nouveau", "drivers/gpu/drm/tilcdc", "drivers/gpu/drm/lima",
    "drivers/gpu/drm/vc4", "drivers/gpu/drm/imx", "drivers/gpu/drm/exynos",
    "drivers/net/ethernet", "drivers/net/wireless/broadcom", "drivers/usb/host",
    "drivers/scsi/lsi", "drivers/scsi/lpfc", "drivers/media/pci",
    "drivers/media/usb", "drivers/staging/mt7621", "drivers/staging/android",
    "drivers/infiniband", "drivers/rtc/rtc-s5m", "sound/soc/qcom",
    "sound/soc/intel", "sound/soc/amd", "sound/soc/rockchip", "sound/soc/tegra",
    "sound/soc/unisoc", "sound/soc/sprd", "sound/sparc", "drivers/video/fbdev",
    "drivers/gpu/drm/radeon", "drivers/gpu/drm/bridge/samsung",
)


def relevant(p):
    return not p.startswith(IRRELEVANT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(os.path.join(a.indir, "ledger.csv"))))
    for r in rows:
        for k in ("hunks", "portable", "already", "manual", "partial",
                  "noise", "added", "removed"):
            r[k] = int(r[k])
    summ = json.load(open(os.path.join(a.indir, "summary.json")))
    ver = json.load(open(os.path.join(a.indir, "verify.json")))
    hz = json.load(open(os.path.join(a.indir, "hazard.json")))
    pc = json.load(open(os.path.join(a.indir, "portedcheck.json")))
    soc = json.load(open(os.path.join(a.indir, "soccompare.json")))

    tot = {k: sum(r[k] for r in rows) for k in
           ("hunks", "portable", "already", "manual", "partial", "added", "removed")}
    rel = [r for r in rows if relevant(r["file"]) and r["status"] not in ("SKIP_ARCH",)]
    rel_tot = {k: sum(r[k] for r in rel) for k in
               ("hunks", "portable", "already", "manual", "partial")}

    out = []
    w = out.append
    w("## 1. Delta ledger (downstream 4.19.325 vs vanilla 4.19.325, mapped onto v5.15.220)\n")
    w("Hunks classified by `portclassify.py analyze`; every number is reproducible\n"
      "from `ledger.csv`.\n")
    w("| metric | value |")
    w("|---|---|")
    w(f"| modified files in delta | {len(rows)} |")
    w(f"| hunks in delta | {tot['hunks']} |")
    w(f"| +lines / -lines of vendor delta | {tot['added']} / {tot['removed']} |")
    w(f"| ALREADY in 5.15 (drop, was an upstream backport) | {tot['already']} hunks "
      f"({100*tot['already']//max(1,tot['hunks'])}%) |")
    w(f"| PORTABLE (pre-image matched, mechanically applied) | {tot['portable']} hunks |")
    w(f"| NEAR / PARTIAL (context moved, needs a human) | {tot['partial']} hunks |")
    w(f"| MANUAL (semantic conflict) | {tot['manual']} hunks |")
    w(f"| file-level: fully portable | {sum(1 for r in rows if r['status']=='FULLY_PORTABLE')} |")
    w(f"| file-level: obsolete (all hunks already upstream) | "
      f"{sum(1 for r in rows if r['status']=='OBSOLETE')} |")
    w(f"| file-level: mixed | {sum(1 for r in rows if r['status']=='MIXED')} |")
    w(f"| file-level: manual | {sum(1 for r in rows if r['status']=='MANUAL')} |")
    w(f"| file-level: no such file in 5.15 | {sum(1 for r in rows if r['status']=='NO_TARGET')} |")
    w(f"| file-level: other arch, irrelevant to this product | "
      f"{sum(1 for r in rows if r['status']=='SKIP_ARCH')} |")
    w("")
    w(f"Device-relevant subset (MTK/arm64-relevant paths, non-arm arches and "
      f"foreign-SoC\ndrivers filtered out): **{len(rel)} files, {rel_tot['hunks']} hunks, "
      f"{rel_tot['manual']} manual**.\n")

    w("## 2. Subsystem breakdown\n")
    w("| subsystem | hunks | portable | already | manual+partial | applied now |")
    w("|---|---|---|---|---|---|")
    sub = summ["subsystems"]
    for k, v in sorted(sub.items(), key=lambda kv: -kv[1].get("portable_hunks", 0))[:26]:
        left = v.get("hunks", 0) - v.get("portable_hunks", 0) - v.get("already_hunks", 0)
        w(f"| `{k}` | {v.get('hunks',0)} | {v.get('portable_hunks',0)} | "
          f"{v.get('already_hunks',0)} | {left} | "
          f"{100*v.get('portable_hunks',0)//max(1,v.get('hunks',1))}% |")
    w("")

    w("## 3. Verification of the applied subset\n")
    st = ver["stats"]
    w("`portclassify.py verify` re-reads the ported tree and the pristine base.\n")
    w("| check | result |")
    w("|---|---|")
    w(f"| applied hunks whose post-image is present in the ported tree | "
      f"{st['POST_OK']}/{st['hunks']} |")
    w(f"| hunks whose pre-image was **unique** in the base (zero misplacement risk) | "
      f"{st['PRE_UNIQUE']} |")
    w(f"| hunks whose pre-image matched multiple sites (nearest-to-origin chosen, flagged) | "
      f"{st.get('AMBIGUOUS_PRE',0)} |")
    w(f"| hunks dropped by the applier (overlapping regions) | {st['POST_NOT_FOUND']} |")
    w(f"| files whose line delta equals the sum of their hunks exactly | "
      f"{st['FILE_OK']}/{st['FILE_OK']+st['FILE_LINEDELTA_MISMATCH']} |")
    w("")
    pcr = pc["regression_hits"]
    w(f"`portedcheck.py`: {pc['inserted_lines']} inserted lines scanned for APIs that "
      f"changed\nor vanished between 4.19 and 5.15 -> "
      f"**{sum(v['uses'] for v in pcr.values())} hits**.\n")
    if pcr:
        w("| changed/removed API | uses | files | worst file |")
        w("|---|---|---|---|")
        for n, v in pcr.items():
            w(f"| {n} | {v['uses']} | {v['files']} | `{v['top_files'][0]}` |")
        w("")
    w(f"Header-resolution proxy: {pc['unresolved_in_target_headers']} of "
      f"{pc['inserted_identifiers']} inserted identifiers do not resolve in the "
      f"target's `include/` set; {pc['unresolved_vendorish']} are "
      f"`MTK_*/oplus_*` (they arrive with the vendor tree) and the rest are "
      "mostly Android/vendor-local symbols, locals and Makefile variables - this "
      "screen is deliberately conservative (see README).")
    w("")

    w("## 4. Vendor-new code that cannot be hunk-ported (transplant surface)\n")
    w(f"{hz['files']} vendor-new C files / {hz['loc']:,} lines in scope "
      f"(roots: {', '.join(hz['audited_roots'])}).\n")
    w("| API hazard | uses | files | why it hurts on 5.15 |")
    w("|---|---|---|---|")
    why = {
        "set_fs/goto_if": "removed in 5.11; every userspace-copy path in MTK/OPLUS drivers uses it",
        "ion (removed 5.18)": "Ion core gone; MTK's mtk_memalloc/ion glue must move to dma-buf heaps",
        "proc_fops (needs proc_ops)": "/proc drivers must convert to proc_ops (5.6)",
        "timespec (removed 5.6)": "struct timespec/y2038 rework",
        "kmap (5.11+ -> kmap_local)": "kmap_atomic semantics + HIGHMEM helpers deprecated",
        "strlcpy/strlcat": "deprecated in favour of strscpy",
        "timer_setup gap": "old timer init API must become timer_setup()/from_timer()",
        "old access_ok": "access_ok() lost the VERIFY_* argument in 5.0",
        "get_user_pages (5.8+ -> pin_*)": "long-term pins must use pin_user_pages",
        "signal: send_sig_info sigqueue": "sigqueue allocation semantics changed",
        "netif_napi_add weight arg": "weight argument removed (5.19/6.1)",
        "net: skb_frag page_link": "skb_frag API/memdesc rework",
        "init_MUTEX (removed)": "long-removed mutex API",
        "ll_rw_block (removed 5.18)": "fs submit API removed",
        "dma_map_sg attrs/dma_attrs": "dma-mapping attribute API rework",
        "phy/mii changed": "PHY state machine rework",
        "sysfs bin_attr compat": "attribute macro rework",
        "blk: make_request_fn (5.14)": "must move to blk-mq",
        "read_write_semaphore": "semaphore API removals",
    }
    for n, v in hz["hazards"].items():
        w(f"| `{n}` | {v['uses']} | {v['files']} | {why.get(n,'-')} |")
    w("")

    w("## 5. MT6769 (phone) vs MT8365 (Genio 510) - measured\n")
    w("| measurement | value |")
    w("|---|---|")
    w(f"| compatibles instantiated by the phone's MT6765/MT6768 DTS | "
      f"{soc['device_compatibles']} ({soc['device_mediatek_compatibles']} `mediatek,*`) |")
    w(f"| of those, bindable by a driver in **v5.15.220** | "
      f"{soc['device_bound_in_target']} "
      f"({100*soc['device_bound_in_target']//max(1,soc['device_compatibles'])}%) |")
    w(f"| only the mt8365 spelling is bound in 5.15 (rename test) | "
      f"{soc['mt8365_spelling_bound_in_target']} |")
    w(f"| mainline `mt8365.dtsi` compatible set | {soc['mt8365_dtsi_compatibles']} |")
    w(f"| shared with the phone's IP | {soc['mt8365_shared_with_device']} |")
    w(f"| first release with clk-mt8365.c / mt8365.dtsi | 6.1 / 6.4 (absent from 5.15) |")
    w("")
    w("Per-IP-block view for the chosen target (v5.15.220):\n")
    w("| IP class | device nodes | bindable in target | needs vendor/backport |")
    w("|---|---|---|---|")
    for r in soc["by_ip_class"]:
        w(f"| {r['ip_class']} | {r['device_nodes']} | {r['bindable_in_target']} | "
          f"{r['needs_vendor_or_backport']} |")
    w("")

    with open(a.out, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {a.out} ({len(out)} lines)")
    print(f"device-relevant remaining manual work: {rel_tot['manual']} hunks "
          f"in {sum(1 for r in rel if r['manual'])} files")


if __name__ == "__main__":
    main()
