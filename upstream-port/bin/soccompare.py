#!/usr/bin/env python3
"""
soccompare - evidence for the question "can an MT8365 (Genio 510) base serve an
MT6769 (Helio G85) phone?", measured instead of asserted.

Method (every number below is reproducible with the two commands printed by
--verbose):
  A. IP inventory of the phone: every `compatible` string instantiated by the
     downstream 4.19 SoC/board DTS.
  B. bindability in the target base: one git-grep pass that collects *all*
     of-lookup compatible strings the target tree's drivers claim, then set
     intersection with (A).
  C. overlap with MT8365: same intersection against the compatible strings of
     mainline's arch/arm64/boot/dts/mediatek/mt8365.dtsi, plus the mt8365<->
     mt6765/68/69 name-rewrite test (do the *same* IP bindings exist?).
  D. residue = hardware that needs vendor/BSP code no matter which 5.x base is
     picked, grouped by IP class.
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys

# "vendor,soc-block" strings as used by of_match_id / DT_SCHEMA
ANY_COMPAT_RE = re.compile(r'"([a-z0-9][a-z0-9_.+-]*,[a-z0-9][a-z0-9_.+-]*)"')
DTS_LINE_RE = re.compile(r"compatible\s*=\s*([^;]+);")
PHONE_MTK = re.compile(r"mt(6761|6763|6765|6768|6769|8321)\b")
GENIO = "mt8365"


def sh(args, cwd=None):
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    if r.returncode not in (0, 1):
        raise RuntimeError("cmd failed: " + " ".join(args) + "\n" + r.stderr[:400])
    return r.stdout


def dts_compatibles(paths, verbose=False):
    """compatibles actually instantiated by the given dts/dtsi files."""
    out = sh(["bash", "-c",
              "grep -rhoE 'compatible[[:space:]]*=[[:space:]]*[^;]+;' " +
              " ".join(paths)])
    comps = set()
    for line in out.split("\n"):
        for m in ANY_COMPAT_RE.finditer(line):
            comps.add(m.group(1))
    if verbose:
        print("  [A] " + "grep -rhoE 'compatible = [^;]+' " + " ".join(paths))
    return comps


def tree_claimed_compatibles(tree, ref, verbose=False):
    """Every compatible string any driver/binding in the tree claims (1 pass)."""
    out = sh(["bash", "-c",
              f"git -C {tree} grep -h -o -E '\"[a-z0-9][a-z0-9_.+-]*,[a-z0-9][a-z0-9_.+-]*\"' "
              f"{ref} -- drivers arch/arm64 arch/arm/boot/dts sound net include/linux "
              f"Documentation/ABI Documentation/devicetree | tr -d '\"' | sort -u"])
    if verbose:
        print("  [B] " + f"git -C {tree} grep -h -o -E '\"vend,block\"' {ref} -- drivers ... | sort -u")
    return set(x for x in out.split("\n") if x)


def classify(comp):
    head, _, tail = comp.partition(",")
    t = tail.lower()
    for k, pats in (
        ("clock/PLL/CGU", ("clk", "topckgen", "infracfg", "pericfg", "mmpll")),
        ("power/PMIC/pwrap", ("pwrap", "mt6323", "mt6357", "mt6366", "regulator", "charger", "gauge", "pmic", "mt6370")),
        ("display (DSI/DPI/OVL/MDP)", ("dsi", "dpi", "disp", "ovl", "rdma", "mmsys", "color", "gamma", "aal", "ccorr", "vpp", "frame", "hdmi", "dp")),
        ("GPU (Mali)", ("mali", "g52", "g76", "g77")),
        ("IOMMU/SMI/CMDQ/GCE", ("smi", "iommu", "m4u", "cmdq", "gce", "larb", "mutex", "mutex")),
        ("camera/ISP", ("cam", "isp", "imgsys", "vpu", "raw", "sensor", "srccam", "imx", "s5k")),
        ("video codec", ("vcodec", "vdec", "venc")),
        ("audio (AFE/codec)", ("afe", "audsys", "audio", "mt6660", "da7", "rt5", "da7219")),
        ("modem/CCCI/connectivity", ("ccci", "md", "wcn", "connac", "wifi", "bt", "gps", "nfc", "extcon")),
        ("input/touch/fp", ("touch", "tp_", "fingerprint", "keypad", "mtk-kpd", "huion", "gt1x", "syna", "goodix", "hilocker")),
        ("memory/storage", ("msdc", "ufs", "ufshci", "mmc", "nand", "blk", "pmem", "mmlp", "bpq", "mcps")),
        ("DVFS/thermal/cpufreq", ("dvfs", "dvfsrc", "thermal", "cpufreq", "cpuopp", "bandwidth", "bwhist", "scp")),
        ("security/TEE", ("tee", "sec", "sbi", "rpmb", "keymaster", "trustzone", "tz")),
        ("pin/pinctrl/EINT", ("pinctrl", "eint", "gpio")),
        ("serial/spi/i2c/uart", ("uart", "16550", "spi", "i2c", "hsipi", "mt6765-i2c")),
        ("USB/PHY/typec", ("usb", "typec", "phy", "xhci", "dwc3", "mtu3")),
        ("network", ("eth", "gmac", "mdio")),
        ("misc/sensor", ("sensor", "iio", "rtc", "watchdog", "auxadc", "efuse", "dump", "aee", "panic")),
    ):
        if any(p in t for p in pats):
            return k
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor-dts", required=True, nargs="+")
    ap.add_argument("--target-tree", required=True)
    ap.add_argument("--target-ref", required=True)
    ap.add_argument("--mt8365-dtsi", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    print("[1/4] phone IP inventory", flush=True)
    phone = dts_compatibles(a.vendor_dts, a.verbose)
    phone_mtk = sorted(c for c in phone if c.startswith("mediatek,"))
    print(f"      {len(phone)} unique compatibles; {len(phone_mtk)} mediatek,*", flush=True)

    print(f"[2/4] what the target base ({a.target_ref}) can bind", flush=True)
    claimed = tree_claimed_compatibles(a.target_tree, a.target_ref, a.verbose)
    print(f"      target tree claims {len(claimed)} distinct compatibles", flush=True)

    bound = sorted(c for c in phone if c in claimed)
    mtk_bound = sorted(c for c in phone_mtk if c in claimed)

    # name-rewrite test: does the target bind the *mt8365* spelling of the same IP?
    rewritten = {c: PHONE_MTK.sub(GENIO, c) for c in phone_mtk}
    sib_bound = sorted({c for c, s in rewritten.items() if s in claimed and s != c})

    m365 = set()
    if a.mt8365_dtsi and os.path.exists(a.mt8365_dtsi):
        m365 = dts_compatibles([a.mt8365_dtsi], a.verbose)

    by_class = collections.Counter()
    bound_class = collections.Counter()
    for c in phone:
        k = classify(c)
        by_class[k] += 1
        if c in claimed:
            bound_class[k] += 1
    table = []
    for k in sorted(by_class, key=lambda x: -by_class[x]):
        table.append({"ip_class": k, "device_nodes": by_class[k],
                      "bindable_in_target": bound_class[k],
                      "needs_vendor_or_backport": by_class[k] - bound_class[k]})

    rep = {
        "target": f"{a.target_ref}",
        "device_compatibles": len(phone),
        "device_mediatek_compatibles": len(phone_mtk),
        "target_claims_total": len(claimed),
        "device_bound_in_target": len(bound),
        "device_mediatek_bound_in_target": len(mtk_bound),
        "mt8365_spelling_bound_in_target": len(sib_bound),
        "mt8365_dtsi_compatibles": len(m365),
        "mt8365_shared_with_device": len(sorted(m365 & phone)),
        "shared_with_device": len(sorted(m365 & phone)),
        "sibling_only_bound": len(sib_bound),
        "mt8365_spelling_bound_in_target": len(sib_bound),
        "device_bound_in_target": len(bound),
        "shared_examples": sorted(m365 & phone)[:60],
        "unbound_examples": sorted(set(phone_mtk) - claimed)[:80],
        "by_ip_class": table,
    }
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)

    pct = 100 * len(bound) // max(1, len(phone))
    print(f"\n=== {a.target_ref} vs this phone's MT6765/MT6769 IP ===", flush=True)
    print(f"device compatibles instantiated      : {len(phone)}")
    print(f"  of them mediatek,*                 : {len(phone_mtk)}")
    print(f"bindable by a driver in {a.target_ref:12s}: {len(bound)}  ({pct}%)")
    print(f"only the mt8365-spelling is bound    : {len(sib_bound)}")
    print(f"mt8365 dtsi compatibles (mainline)   : {len(m365)}")
    print(f"shared mt8365 <-> phone compatibles  : {rep['mt8365_shared_with_device']}")
    print("\n| IP class | device nodes | bindable in target | needs vendor/backport |")
    print("|---|---|---|---|")
    for r in table:
        print(f"| {r['ip_class']} | {r['device_nodes']} | {r['bindable_in_target']} | "
              f"{r['needs_vendor_or_backport']} |")


if __name__ == "__main__":
    main()
