#!/usr/bin/env python3
"""l2slice.py - land one L2 dispsys slice: copy the requested vendor files verbatim, then close the
include gap by asking the compiler what it cannot find, up to --max-headers times.

Nothing here edits vendor code: files are copied byte-for-byte from the 4.19.325 tree into the same
relative path of the target tree, exactly as the earlier layers did. The Makefile include list starts
from the stock rule, restricted to directories that actually exist in the target tree - an -I path
that does not exist is a silent lie about what the port carries.

  python3 upstream-port/bin/l2slice.py --objs ddp_info.c ddp_mutex.c ... [--dry-run]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

VENDOR_REL = "drivers/misc/mediatek"
# The stock dispsys ccflags list, in vendor order. Kept verbatim so a reviewer can diff it against
# drivers/misc/mediatek/video/mt6768/dispsys/Makefile in the vendor tree.
STOCK_INCLUDE_DIRS = [
    "drivers/misc/mediatek/video/include",
    "drivers/misc/mediatek/video/common",
    "drivers/misc/mediatek/video/common/rdma20",
    "drivers/misc/mediatek/video/common/wdma20",
    "drivers/misc/mediatek/video/common/layering_rule_base/v1.1",
    "drivers/misc/mediatek/video/mt6768/videox",
    # From the stock videox/Makefile, not the dispsys one: dispsys objects include videox headers
    # (disp_drv_log.h) which in turn include dispsys headers (display_recorder.h), so the platform
    # dispsys directory has to be on the path for either directory to build. Without it the vendor
    # tree compiles and the port does not.
    "drivers/misc/mediatek/video/mt6768/dispsys",
    "drivers/misc/mediatek/base/power/include",
    "drivers/misc/mediatek/smi",
    "drivers/misc/mediatek/gpu/ged/include",
    "drivers/iommu",
    "drivers/misc/mediatek/smi/variant",
    "drivers/staging/android/mtk_ion",
    "drivers/staging/android/mtk_ion/mtk",
    "drivers/misc/mediatek/dramc/mt6768",
    "drivers/misc/mediatek/cmdq/v3",
    "drivers/misc/mediatek/include",
    "drivers/misc/mediatek/m4u/2.0",
    "drivers/misc/mediatek/m4u/mt6768",
    "drivers/misc/mediatek/mmp",
    "drivers/misc/mediatek/lcm/inc",
    # The remaining stock videox/Makefile lines (52-88), added so a header included from videox
    # resolves exactly as it does in the vendor build. The generator keeps only those that exist in
    # the target tree, so paths whose files are not ported are not advertised.
    "drivers/misc/mediatek/sync",
    "drivers/misc/mediatek/mach/mt6768/include/mach",
    "drivers/misc/mediatek/base/power/mt6768",
    "drivers/misc/mediatek/base/power/include/spm_v2",
    "drivers/misc/mediatek/mmdvfs",
    "drivers/devfreq",
    "include/linux/soc/mediatek",
    "drivers/misc/mediatek/include/mt-plat",
    "drivers/misc/mediatek/cmdq/v3/mt6768",
]


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def copy_verbatim(vendor, target, rel):
    src = os.path.join(vendor, rel)
    dst = os.path.join(target, rel)
    if not os.path.exists(src):
        return "missing-vendor"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        a = open(src, "rb").read()
        b = open(dst, "rb").read()
        if a == b:
            return "already-identical"
        return "DIFFERS-REFUSING"
    shutil.copyfile(src, dst)
    return "copied"


def find_header(vendor, name, search_dirs):
    """Locate a #include "name" the way the compiler would: first the directories on the include
    path, then a tree-wide basename search so the copy lands at the path the include resolves to."""
    for d in search_dirs:
        cand = os.path.join(vendor, d, name)
        if os.path.exists(cand):
            return os.path.relpath(cand, vendor)
    out = subprocess.run(["find", os.path.join(vendor, VENDOR_REL), "-name", os.path.basename(name),
                          "-type", "f"], capture_output=True, text=True).stdout.split()
    if not out:
        out = subprocess.run(["find", os.path.join(vendor, "include"), "-name", os.path.basename(name),
                              "-type", "f"], capture_output=True, text=True).stdout.split()
    if not out:
        return None
    pref = [p for p in out if "/mt6768/" in p or "/v3/" in p] or out
    return os.path.relpath(pref[0], vendor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", default="/home/user/Zenium_Kernel")
    ap.add_argument("--target", default="/home/user/portwork/series")
    ap.add_argument("--objs", nargs="+", required=True)
    ap.add_argument("--max-headers", type=int, default=45)
    ap.add_argument("--srcdir", default="video/mt6768/dispsys",
                    help="vendor dir relative to drivers/misc/mediatek; the .c files named in --objs "
                         "are read from here and the generated Makefile is written there too. Use "
                         "cmdq/v3 to probe the record layer the same way the dispsys slices were sized.")
    ap.add_argument("--extra-inc", nargs="*", default=[],
                    help="extra -I dirs (tree-relative) for probes that need a ccflags list beyond "
                         "the dispsys stock set, e.g. drivers/misc/mediatek/mdp. Never used for the "
                         "published dispsys slice, whose Makefile must stay byte-identical.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    disp = os.path.join(VENDOR_REL, a.srcdir)
    search_dirs = [d for d in STOCK_INCLUDE_DIRS] + list(a.extra_inc) + [disp, os.path.join(VENDOR_REL, "include/mt-plat"),
                 os.path.join(VENDOR_REL, "include"), os.path.join(VENDOR_REL, "video/mt6768/videox")]

    plan = []
    for o in a.objs:
        plan.append(os.path.join(disp, o))
    copied, refused = [], []
    for rel in plan:
        st = copy_verbatim(a.vendor, a.target, rel) if not a.dry_run else "dry"
        (copied if st in ("copied", "dry", "already-identical") else refused).append((rel, st))

    # makefile: obj list + include dirs that exist in the target tree
    def write_makefile():
        # Recomputed every iteration: the closure loop creates directories by copying into them,
        # and a -I path that existed only after a copy is still a -I path the compiler must be told.
        inc = [d for d in STOCK_INCLUDE_DIRS + list(a.extra_inc)
               if os.path.isdir(os.path.join(a.target, d))]
        objlines = "\n".join("obj-y += %s" % os.path.basename(o)[:-2] + ".o" for o in a.objs)
        body = ("#\n# MT6768 display core (ported subset of the vendor dispsys).\n#\n"
                "# Generated by upstream-port/bin/l2slice.py. The ccflags list below is the stock\n"
                "# drivers/misc/mediatek/video/mt6768/dispsys/Makefile include set, filtered to the\n"
                "# directories that exist in this tree; every object listed is copied verbatim from the\n"
                "# 4.19.325 vendor source and is built by the device config gate.\n#\n\n"
                "ccflags-y += " + " \\\n             ".join("-I$(srctree)/" + d for d in inc) + "\n\n"
                + objlines + "\n")
        open(os.path.join(a.target, mk_rel), "w").write(body)
        return inc

    mk_rel = os.path.join(disp, "Makefile")
    tgt_mk = os.path.join(a.target, mk_rel)
    inc = [d for d in STOCK_INCLUDE_DIRS + list(a.extra_inc)
           if os.path.isdir(os.path.join(a.target, d))]
    skipped = [d for d in STOCK_INCLUDE_DIRS + list(a.extra_inc) if d not in inc]
    print("include dirs present in target tree: %d, absent (so not advertised): %d" % (len(inc), len(skipped)))
    for s in skipped:
        print("   -I skipped: %s" % s)
    if not a.dry_run:
        write_makefile()
        print("wrote %s (%d objs)" % (mk_rel, len(a.objs)))

    # closure loop driven by the compiler
    env = dict(os.environ)
    envfile = os.path.join(a.target, ".env_source")
    hdr_added = []
    for it in range(a.max_headers):
        rc, out = run(["bash", "-lc",
                       ". /home/user/portwork/tools/env.sh; make ARCH=arm64 CROSS_COMPILE=\"$CROSS_COMPILE\" "
                       "-k -j2 %s/" % disp], a.target)
        if rc == 0:
            want = [os.path.join(a.target, disp, os.path.basename(o)[:-2] + ".o") for o in a.objs]
            missing_o = [w for w in want if not os.path.exists(w) or os.path.getsize(w) == 0]
            if missing_o:
                print("iteration %d: rc=0 but %d expected objects absent - the Makefile is not"
                      " building them (obj-y takes .o names): %s"
                      % (it, len(missing_o), [os.path.basename(m) for m in missing_o]))
                for m in missing_o:
                    print("   obj-y += %s" % os.path.basename(m))
                out2 = open(os.path.join(a.target, mk_rel)).read()
                if any(os.path.basename(m)[:-2] + ".c" in ln for ln in out2.split("\n")
                       if ln.startswith("obj-y")):
                    print("  -> rewriting the obj list from .c to .o and retrying")
                    open(os.path.join(a.target, mk_rel), "w").write(
                        out2.replace(".c\n", ".o\n"))
                    continue
                break
            print("iteration %d: build rc=0 and all %d objects present" % (it, len(want)))
            for w in want:
                print("   %-22s %8d B" % (os.path.basename(w), os.path.getsize(w)))
            break
        missing = sorted(set(re.findall(r"([\w./+-]+\.h): No such file or directory", out)))
        if not missing and "Nothing to be done for '%s/'" % disp in out:
            print("iteration %d: kbuild never entered %s/ - no Makefile on the descent path lists it. "
                  "The published slices are reached by an obj-y line in an already-descended Makefile "
                  "(e.g. drivers/misc/mediatek/video/Makefile: obj-$(CONFIG_MTK_DISP_M4U) += "
                  "mt6768/dispsys/); a probe dir needs the same, or nothing is compiled and every "
                  "later count is a fiction." % (it, disp))
            break
        if not missing:
            print("iteration %d: build rc=%d, no missing headers -> real compile errors remain" % (it, rc))
            open("/tmp/l2_last_build.log", "w").write(out)
            print("  log kept at /tmp/l2_last_build.log (%d lines)" % len(out.split("\n")))
            break
        progressed = False
        for m in missing:
            rel = find_header(a.vendor, m, search_dirs)
            if not rel:
                print("  UNRESOLVED include: %s" % m)
                continue
            st = copy_verbatim(a.vendor, a.target, rel) if not a.dry_run else "dry"
            if st in ("copied", "dry"):
                hdr_added.append(rel)
                progressed = True
                print("  + %-58s (%s)" % (rel, st))
            elif st == "already-identical":
                print("  = %-58s already present, but the include path does not reach it" % rel)
        if progressed and not a.dry_run:
            inc = write_makefile()
            print("  rewrote Makefile ccflags: %d include dirs now advertised" % len(inc))
        if not progressed:
            print("no progress this iteration; stopping. Log:")
            print("\n".join(l for l in out.split("\n") if "fatal error" in l)[:4000])
            break
    print("\ncopied this run: %d files (%d headers added by the closure loop)"
          % (len(copied) + len(hdr_added), len(hdr_added)))
    if refused:
        print("REFUSED (target differs from vendor, refusing to overwrite): %s" % refused)
    return 0


if __name__ == "__main__":
    sys.exit(main())
