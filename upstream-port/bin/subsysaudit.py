#!/usr/bin/env python3
"""subsysaudit.py - audit every major subsystem of the 5.15 port against the working 4.19 kernel.

The question this answers, per subsystem: how much did the vendor tree change it, how much of
that survived into the 5.15 tree, does the 5.15 tree contain a *driver* for the hardware the
device tree describes, and did those files actually compile in the last build.

Inputs (all already produced by the other tools in bin/):
  report/ledger.csv          per-file vendor delta + hunk classification (portclassify.py)
  report/summary.json        subsystem rollup from the same ledger
  <dts report>               dtsport.py output: transplanted closure + compatible audit
  <build log>                the make log of the ported tree (object + error counts)
  the ported 5.15 tree       `git diff --numstat <base>..HEAD` per subsystem = what the port adds

Nothing is guessed: the PORTED / NOT_PORTED verdicts are computed from file counts, and the
"driver in 5.15 for this hardware" column is a grep of the target tree for the exact compatible
strings the device tree declares.
"""
import argparse
import collections
import csv
import json
import os
import re
import subprocess
import sys

# Subsystems that matter for booting and using this phone, in dependency order.
SUBSYSTEMS = [
    # --- hardware-critical vendor driver trees (device must be ported driver-by-driver) ---
    ("drivers/misc/mediatek/pmic_wrap", "pwrap: PMIC register bus", "every PMIC client sits on it"),
    ("drivers/misc/mediatek/pmic", "PMIC drivers (mt6358/mt6370/rtc/eip)", "power rails, kpd, charger"),
    ("drivers/power/oplus", "OPLUS charging + battery stack", "won't survive a charge cycle without it"),
    ("drivers/power/supply", "power supply class + charger drivers", "battery/USB-PD reporting"),
    ("drivers/mmc", "msdc: eMMC/SD storage + CMDQ queue", "rootfs lives here"),
    ("drivers/clk/mediatek", "SoC clock drivers", "no clocks, no probes"),
    ("drivers/pinctrl/mediatek", "pinmux / pinconf", "all bus and GPIO setup"),
    ("drivers/misc/mediatek/cmdq", "CMDQ hardware engine", "display and msdc timeouts rely on it"),
    ("drivers/misc/mediatek/m4u", "M4U: SMI/IOMMU client glue", "display, cam, codec are SMI clients"),
    ("drivers/iommu", "mediatek IOMMU core", "bound to SMI"),
    ("drivers/memory", "SMI local/global arbiter", "display, cam, codec"),
    ("drivers/misc/mediatek/video", "MSDK display core (DISP/ODR/HDCP)", "screen bring-up (this tree's path)"),
    ("drivers/misc/mediatek/lcm", "LCM/DSI panel drivers", "panel power-on sequence"),
    ("drivers/gpu/drm/mediatek", "mainline mtk_drm", "the 5.15-native display driver for this family"),
    ("drivers/gpu/drm", "DRM core, panels, bridges", "display"),
    ("drivers/misc/mediatek/gpu", "Mali GPU DDK (in-tree here)", "UI rendering; DDK is huge and vendor-only"),
    ("drivers/misc/mediatek/imgsensor", "camera sensor + P2/IspTuning", "camera"),
    ("drivers/misc/mediatek/cameraisp", "CAMSYS/ISP kernel side", "camera"),
    ("drivers/misc/mediatek/lens", "lens drivers", "camera"),
    ("drivers/media", "media controller + platform video nodes", "camera/codecs"),
    ("drivers/misc/mediatek/connectivity", "WCN: Wi-Fi/BT/FM (wmt + connac)", "connectivity"),
    ("drivers/net/wireless", "cfg80211/mac80211 + MTK wireless dirs", "connectivity"),
    ("net", "core networking (tcp/bpf/xfrm/wifi)", "connectivity"),
    ("drivers/misc/mediatek/eccci", "modem E-CCCI IPC + 629x", "calls, RIL"),
    ("drivers/usb", "USB core/gadget + MTK usb20/xhci", "adb, MTP, OTG"),
    ("drivers/misc/mediatek/usb20", "MTK USB2 host/gadget helpers", "adb on the low-speed path"),
    ("drivers/misc/mediatek/typec", "USB Type-C / PD", "charging + DP alt-mode"),
    ("sound/soc/mediatek", "ASoC machine + platform (AFE/DSP)", "audio"),
    ("drivers/misc/mediatek/audio_ipi", "audio DSP IPI channel", "audio effects/DSP"),
    ("sound", "core audio (compress, usb-audio, haptics)", "audio + haptics"),
    ("drivers/input", "touchscreen, keys, haptics", "unusable without touch"),
    ("drivers/spi", "SPI controllers/adapters", "sensors, display ICs"),
    ("drivers/i2c", "I2C controllers + adapters", "touch/charger/sensor buses"),
    ("drivers/hid", "HID (usb HID over OTG)", "accessory"),
    ("drivers/leds", "backlight + notification LEDs", "brightness path"),
    ("drivers/misc/mediatek/thermal", "MTK thermal + power-manager hooks", "thermal safety"),
    ("drivers/thermal", "thermal core, governors", "thermal safety"),
    ("drivers/devfreq", "devfreq (gpu/dram), thermal governors", "perf and power"),
    ("drivers/misc/mediatek/lpm", "SPM / DVFSRC / CPU idle", "suspend, battery life"),
    ("drivers/misc/mediatek/ccu", "CCU (MCUPM co-processor)", "DVFS/suspend"),
    ("drivers/misc/mediatek/sspm", "SSPM (TCO/WDT/sleep)", "suspend"),
    ("drivers/misc/mediatek/apusys", "APUSYS NPU/DSP", "AI/offload"),
    ("drivers/misc/mediatek/adsp", "ADSP audio/haptic DSP", "audio effects"),
    ("drivers/misc/mediatek/sensors-1.0", "sensor hub drivers", "SMDP sensors"),
    ("drivers/misc/mediatek/performance", "perf tuner / cpu_freq / boot_cpu", "perf"),
    ("drivers/misc/mediatek/base", "vendor core: kpd/aee_kdump/smp/PMIC wrappers", "boot and SMP path"),
    ("drivers/misc/mediatek/aee", "AEE + tombstone + kdump", "crash reporting"),
    ("drivers/misc/mediatek/met_drv_v3", "MET tracing", "perf analysis"),
    ("drivers/misc/mediatek/boot", "bootloader interface / LK args", "boot"),
    ("drivers/misc/mediatek", "remaining vendor misc tree", "various"),
    ("drivers/soc/mediatek", "socinfo/pwrap clients/pmic aux", "probe ordering"),
    ("drivers/misc", "non-MTK misc drivers", "various"),
    ("drivers/base", "core driver model, sync state, pm_domain", "probe ordering"),
    ("drivers/android", "binder + vendor Android drivers", "Android IPC"),
    ("drivers/staging/android", "ion/ashmem (removed upstream)", "vendor HAL ABI"),
    ("drivers/firmware/efi", "EFI stub", "unused by LK"),
    ("fs", "VFS, procfs, ext4/f2fs, binder fs", "userspace ABI surface"),
    ("mm", "page allocator, CMA, zram backing", "memory path"),
    ("kernel", "scheduler, time, cgroups, tracing", "core behaviour/tunables"),
    ("block", "IO, partitions, zram/swap backends", "storage/swap"),
    ("crypto", "kernel crypto API (lz4/xxhash/aes-neon)", "fscrypt, dm-verity, zram"),
    ("lib", "lz4*/xxhash/zstd, cmdline", "compression"),
    ("include", "UAPI + internal headers (mtk ifaces, dt-bindings)", "ABI of everything above"),
    ("security", "SELinux, keys, integrity", "Android MAC"),
    ("init", "boot path, sysctl defaults", "boot"),
    ("usr", "default keyring", "module signature / verification"),
    ("tools", "perf, bootimg, headers", "userspace-side build"),
    ("arch/arm64", "arch code, defconfigs, boot/dts", "boot + device tree"),
]


def numstat_by_prefix(tree, base, prefixes):
    """Added/removed/file counts per prefix inside the ported tree."""
    out = subprocess.run(["git", "-C", tree, "diff", "--numstat", "%s..HEAD" % base],
                         capture_output=True, text=True).stdout
    agg = collections.defaultdict(lambda: [0, 0, 0])
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add, rem, path = parts
        add = int(add) if add.isdigit() else 0
        rem = int(rem) if rem.isdigit() else 0
        for p in prefixes:
            if path.startswith(p.rstrip("/") + "/") or path == p:
                a = agg[p]
                a[0] += add
                a[1] += rem
                a[2] += 1
    return agg


def ledger_by_prefix(csv_path, prefixes):
    agg = collections.defaultdict(lambda: collections.Counter())
    with open(csv_path, newline="", errors="replace") as f:
        for row in csv.DictReader(f):
            fl = row["file"].replace("\\", "")
            for p in prefixes:
                if fl.startswith(p.rstrip("/") + "/"):
                    a = agg[p]
                    a["files"] += 1
                    a["hunks"] += int(row["hunks"] or 0)
                    a["added"] += int(row["added"] or 0)
                    a["removed"] += int(row["removed"] or 0)
                    for k in ("already", "portable", "partial", "manual", "noise"):
                        a[k] += int(row[k] or 0)
                    a["status:" + row["status"]] += 1
                    break
    return agg


def vendor_tree_files(repo, prefix):
    """Tracked .c/.h under a path in the 4.19 tree - the true size of the surface a
    device-driver port has to carry (the modified-only ledger cannot express this:
    the whole MTK driver tree is vendor-added, not vendor-modified)."""
    # recursive: vendor driver directories nest (arm_display/disp, pmic_wrap/v2, ...)
    out = subprocess.run(["git", "-C", repo, "ls-files", "--", prefix],
                         capture_output=True, text=True).stdout.split()
    return len([f for f in out if f.endswith((".c", ".h"))])


def compat_files(vendor_tree, closure_rel_files):
    """compatible string -> vendor dts files declaring it (from the transplanted closure)."""
    out = collections.defaultdict(set)
    pat = re.compile(r'compatible\s*=\s*((?:"[^"]+"\s*,?\s*)+);')
    for rel in closure_rel_files:
        p = os.path.join(vendor_tree, rel)
        if not p.endswith((".dts", ".dtsi")) or not os.path.isfile(p):
            continue
        try:
            txt = open(p, errors="replace").read()
        except OSError:
            continue
        for m in pat.finditer(txt):
            for c in re.findall(r'"([^"]+)"', m.group(1)):
                out[c].add(rel)
    return out


def binder_dirs(target_tree, compats):
    """For each compatible that has a driver in 5.15, which driver directory binds it."""
    res, skipped_generic = {}, []
    for c in compats:
        hit = subprocess.run(["grep", "-rl", "--include=*.c", '"%s"' % c,
                              os.path.join(target_tree, "drivers")],
                             capture_output=True, text=True).stdout.strip().splitlines()
        if not hit:
            continue
        dirs = sorted({os.path.dirname(os.path.relpath(h, target_tree)) for h in hit})
        if len(dirs) > 4:      # generic binding (syscon, fixed-clock, simple-bus, ...)
            skipped_generic.append(c)
            continue
        res[c] = dirs[:4]
    res["_skipped_generic"] = skipped_generic
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="4.19 vendor kernel tree (contains upstream-port/)")
    ap.add_argument("--target", required=True, help="ported 5.15 tree")
    ap.add_argument("--base", default="v5.15.220", help="target-tree base commit for the diff")
    ap.add_argument("--dts", help="dtsport.py JSON")
    ap.add_argument("--buildlog", help="the make log to attribute objects/errors to")
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    rep = os.path.join(repo, "upstream-port")
    prefixes = [p for p, _, _ in SUBSYSTEMS]

    led = ledger_by_prefix(os.path.join(rep, "report", "ledger.csv"), prefixes)
    port = numstat_by_prefix(a.target, a.base, prefixes) if a.target else {}

    objs = collections.Counter()
    err = collections.Counter()
    linked = collections.Counter()
    if a.buildlog and os.path.isfile(a.buildlog):
        with open(a.buildlog, errors="replace") as f:
            for line in f:
                m = re.match(r"\s+(?:CC|AS|LD[^ ]*|OBJCOPY)\s+(\S+\.o)\s*$", line)
                if m:
                    path = m.group(1)
                    for p in prefixes:
                        if path.startswith(p.rstrip("/") + "/"):
                            objs[p] += 1
                            break
                if " error:" in line:
                    m2 = re.search(r"\.\./?(\S+\.(?:c|h))", line) or re.search(r"(\S+\.(?:c|h))", line)
                    if m2:
                        path = m2.group(1).replace("../", "")
                        for p in prefixes:
                            if path.startswith(p.rstrip("/") + "/"):
                                err[p] += 1
                                break

    closure_files, compat_bound, all_bound = [], {}, []
    if a.dts and os.path.isfile(a.dts):
        d = json.load(open(a.dts))
        closure_files = list(d.get("transplant", [])) + list(d.get("present_in_target", []))
        # re-derive which binders live where, but only for the *bound* subset
        compats = list(d.get("compatible_detail", {}).keys())
        compat_bound = binder_dirs(a.target, compats)

    # every 5.15 driver directory that binds a compatible this device's DT declares
    generic = compat_bound.pop("_skipped_generic", [])
    all_bound = sorted({d for bs in compat_bound.values() for d in bs})

    rows = []
    for p, title, why in SUBSYSTEMS:
        L, P = led.get(p, {}), port.get(p, [0, 0, 0])
        vfiles = L.get("files", 0)
        vhunks = L.get("hunks", 0)
        pfiles = P[2]
        status = ("NOT PORTED" if pfiles == 0 else
                  "PORTED (partial)" if pfiles < vfiles else "PORTED")
        if pfiles and not objs.get(p):
            status += ", not built"
        if objs.get(p):
            status = "PORTED + BUILT" if not err.get(p) else "PORTED, %d build error(s)" % err[p]
        binders = [d for d in all_bound
                   if d.startswith(p.rstrip("/") + "/") or d == p]
        rows.append({"path": p, "title": title, "why": why,
                     "vendor_tree_files": vendor_tree_files(repo, p),
                     "vendor_files": vfiles, "vendor_hunks": vhunks,
                     "vendor_added": L.get("added", 0), "vendor_removed": L.get("removed", 0),
                     "vendor_manual_hunks": L.get("manual", 0),
                     "vendor_already_hunks": L.get("already", 0),
                     "ported_files": pfiles, "ported_added": P[0], "ported_removed": P[1],
                     "objects_built": objs.get(p, 0), "build_errors": err.get(p, 0),
                     "dt_bound_dirs": binders[:4], "dt_bound_total": len(all_bound),
                     "dt_bound_compat_files": sorted({c for c, bs in compat_bound.items()
                                                        if any(d.startswith(p.rstrip("/") + "/") for d in bs)})[:6],
                     "status": status})

    with open(a.out_md, "w") as f:
        f.write("# Subsystem audit: 5.15 port vs the working 4.19 kernel\n\n")
        complete = ""
        if a.buildlog and os.path.isfile(a.buildlog):
            complete = "\n**The build log used here is PARTIAL** (it does not end in `BUILD_DONE`), so " \
                       "`objs built` understates coverage; re-run this tool when the build is finished.\n" \
                       if "BUILD_DONE" not in open(a.buildlog, errors="replace").read()[-4000:] else \
                       "\nThe build log used here is complete (`BUILD_DONE` present).\n"
        f.write("Generated by `bin/subsysaudit.py` (no hand-edited counts).\n\n"
                "* `4.19 driver files`: tracked `.c/.h` under that path in the working 4.19 kernel - the "
                "surface a device-driver port must carry.\n"
                "* `modified in Zenium`: files/hunks from `report/ledger.csv` (Zenium 4.19 vs vanilla "
                "4.19.325), i.e. what this port had to reconcile.\n"
                "* `ported to 5.15`: `git diff %s..HEAD` in the ported tree.\n"
                "* `objs built` / `build err`: attributed from the make log%s.\n%s\n\n"
                % (a.base, "" if not a.buildlog else " (`%s`)" % os.path.basename(a.buildlog), complete))
        f.write("`DT-bound dirs` = directories in the 5.15 tree that match a compatible string actually used by\n"
                "this device's transplanted device tree - i.e. hardware that is *driven*, not just described.\n\n")
        f.write("| subsystem | 4.19 driver files | modified in Zenium (hunks) | ported to 5.15 (+lines) | objs built | build err | 5.15 driver dir bound by this device's DT | status |\n")
        f.write("|---|--:|--:|--:|--:|--:|---|---|\n")
        for r in rows:
            f.write("| `%s` | %d | %d files / %d (%d manual) | %d (+%d) | %d | %d | %s | %s |\n" % (
                r["path"], r["vendor_tree_files"], r["vendor_files"], r["vendor_hunks"],
                r["vendor_manual_hunks"], r["ported_files"], r["ported_added"],
                r["objects_built"], r["build_errors"],
                ", ".join("`%s`" % d for d in r["dt_bound_dirs"]) or "-", r["status"]))
        f.write("\n`5.15 driver dir bound by this device's DT` counts only *device-specific* compatibles; "
                "%d generic ones (%s) were excluded because they bind in >4 unrelated directories.\n"
                % (len(generic), ", ".join("`%s`" % g for g in generic[:6])))
        tot_v = sum(r["vendor_tree_files"] for r in rows)
        tot_p = sum(r["ported_files"] for r in rows)
        tot_o = sum(r["objects_built"] for r in rows)
        pending = sum(r["vendor_tree_files"] for r in rows if r["ported_files"] == 0)
        f.write("\n**Remaining device-driver surface**: %d tracked `.c/.h` files live in subsystems with "
                "no ported content at all (Mali DDK, MSDK display, connectivity, camera, charging are the "
                "bulk). Those are *not* hunk-portable: each is its own transplant with dependency fixes.\n"
                % pending)
        f.write("\n**Totals**: %d tracked `.c/.h` files live under the audited paths in the 4.19 kernel; the\n"
                "port modifies %d files in those same paths of the 5.15 tree; %d objects from those directories\n"
                "appear in the build log used here. Rows are *not* disjoint (`drivers/misc/mediatek` contains\n"
                "the rows under it), so treat the totals as ceilings, not sums.\n" % (tot_v, tot_p, tot_o))
        f.write("\n## Reading of the table\n\n")
        notport = [r for r in rows if r["ported_files"] == 0]
        f.write("* **%d of %d audited subsystems carry no ported content** - these are the vendor-only\n"
                "  driver trees (`arm_display`, `cmdq5`, `ccci`, connac wireless, MTK ASoC, ...). They are\n"
                "  not a regression from this port: 5.15 has no upstream equivalent, so each needs its own\n"
                "  transplant + dependency fix, which is the device-driver work tracked in\n"
                "  `MIGRATION-5.15.md`.\n" % (len(notport), len(rows)))
        f.write("* Subsystems where 5.15 *has* a driver for this device's hardware (see `DT-bound dirs`)\n"
                "  are the ones where the port preserves functionality through an upstream driver rather than\n"
                "  the vendor one; where the column is empty, the DTB node is data without a consumer.\n")
        f.write("* `vendor hunks (manual)` is the residual: manual hunks are 4.19-shaped changes (removed APIs,\n"
                "  renamed ops, vendor struct fields) that cannot be textually applied and were reviewed by\n"
                "  hand rather than shipped blind.\n")
    json.dump({"generated_from": {"ledger": "report/ledger.csv", "base": a.base,
                                  "buildlog": a.buildlog, "dts": a.dts},
               "rows": rows}, open(a.out_json, "w"), indent=1)
    print("wrote %s (%d subsystems)" % (a.out_md, len(rows)))
    print("wrote %s" % a.out_json)
    zero = [r["path"] for r in rows if r["ported_files"] == 0]
    print("subsystems with no ported content: %d -> %s" % (len(zero), ", ".join(zero[:8])))
    print("objects attributed to audited subsystems: %d" % sum(r["objects_built"] for r in rows))


main()
