#!/usr/bin/env python3
"""bootpack.py - port the *device* image-packaging machinery from 4.19 onto 5.15.

The `even` bootloader (LK) does not load a standalone `Image`; it loads
`Image.gz-dtb` (gzip kernel + appended board DTB) and a separate `dtbo.img`
containing the /plugin/ board overlays, selected by board id. That machinery is
vendor-specific kbuild code, so it must travel with the port:

  1. scripts/mkdtboimg.py            - DTBO image packer (copied verbatim)
  2. arch/arm64/Kconfig              - BUILD_ARM64_APPENDED_DTB_IMAGE,
                                       BUILD_ARM64_DTB_OVERLAY_IMAGE, the
                                       IMG_GZ_DTB/IMG_DTB choice, the *_NAMES
                                       strings (inserted at the same structural
                                       place the vendor had them: end of the
                                       "Build options" menu, before `config COMPAT`)
  3. arch/arm64/boot/Makefile        - $(obj)/Image.gz-dtb rule
  4. arch/arm64/Makefile             - KBUILD_IMAGE override, `all:` targets,
                                       %.dtb / %.dtbo pass-through rules
  5. a kconfig fragment for the product (written to --fragment, outside the tree)

Every edit is anchored on a unique string; if an anchor is missing or ambiguous the
tool refuses to touch that file and reports it, so a re-run is safe and a silent
mis-edit is impossible. --check (default) only verifies.
"""
import argparse
import json
import os
import re
import shutil
import sys

KCONFIG_BLOCK = '''config BUILD_ARM64_APPENDED_DTB_IMAGE
	bool "Build a concatenated Image.gz/dtb by default"
	depends on OF
	help
	  Enabling this option will cause a concatenated Image.gz and list of
	  DTBs to be built by default (instead of a standalone Image.gz.)
	  The image will built in arch/arm64/boot/Image.gz-dtb

config BUILD_ARM64_DTB_OVERLAY_IMAGE
	bool "Build a device tree overlay image"
	depends on OF
	help
	  Enabling this option will casue overlay device tree
	  to be built by default.
	  Overlay DT contains device-specific configurations.
	  Please be aware that bootloader supports DT merging.

choice
	prompt "Appended DTB Kernel Image name"
	depends on BUILD_ARM64_APPENDED_DTB_IMAGE
	help
	  Enabling this option will cause a specific kernel image Image or
	  Image.gz to be used for final image creation.
	  The image will built in arch/arm64/boot/IMAGE-NAME-dtb

	config IMG_GZ_DTB
		bool "Image.gz-dtb"
	config IMG_DTB
		bool "Image-dtb"
endchoice

config BUILD_ARM64_APPENDED_KERNEL_IMAGE_NAME
	string
	depends on BUILD_ARM64_APPENDED_DTB_IMAGE
	default "Image.gz-dtb" if IMG_GZ_DTB
	default "Image-dtb" if IMG_DTB

config BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES
	string "Default dtb names"
	depends on BUILD_ARM64_APPENDED_DTB_IMAGE
	help
	  Space separated list of names of dtbs to append when
	  building a concatenated Image.gz-dtb.

config BUILD_ARM64_DTB_OVERLAY_IMAGE_NAMES
	string "Default dtb overlay names"
	depends on BUILD_ARM64_DTB_OVERLAY_IMAGE
	help
	  Space separated list of names of dtbs to append when
	  building a concatenated overlay image

'''

BOOT_RULE = '''
$(obj)/Image-dtb: $(obj)/Image $(DTB_OBJS) FORCE
	$(call if_changed,cat)
'''

ARCH_HEAD = '''# Default target when executing plain make
boot		:= arch/arm64/boot
KBUILD_IMAGE	:= $(boot)/Image.gz

all:	Image.gz
'''

ARCH_HEAD_NEW = '''# Default target when executing plain make
boot		:= arch/arm64/boot
ifeq ($(CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE),y)
KBUILD_IMAGE	:= $(boot)/$(subst $\\"$,,$(CONFIG_BUILD_ARM64_APPENDED_KERNEL_IMAGE_NAME))
else
KBUILD_IMAGE	:= $(boot)/Image.gz
endif
KBUILD_DTBS	:= dtbs

all:	Image.gz $(KBUILD_DTBS) $(subst $\\"$,,$(CONFIG_BUILD_ARM64_APPENDED_KERNEL_IMAGE_NAME))

'''

DTB_RULES = '''
%.dtb: scripts
	$(Q)$(MAKE) $(build)=$(boot)/dts $(boot)/dts/$@

%.dtbo: scripts
	$(Q)$(MAKE) $(build)=$(boot)/dts $(boot)/dts/$@
'''


def patch(path, anchor, replacement, must_contain=None, required=True):
    """Replace a unique anchor (or add text when anchor is None => append)."""
    if not os.path.isfile(path):
        return {"file": path, "status": "missing-file", "ok": not required}
    txt = open(path, errors="replace").read()
    if must_contain and must_contain in txt:
        return {"file": path, "status": "already-applied", "ok": True}
    n = txt.count(anchor)
    if n != 1:
        return {"file": path, "status": "anchor-ambiguous(%d)" % n, "ok": False}
    return {"file": path, "status": "ok", "ok": True,
            "new": txt.replace(anchor, replacement, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--fragment", help="write the product kconfig fragment here")
    ap.add_argument("--dtb-name", default="mediatek/mt6768")
    ap.add_argument("--dtbo-names",
                    default="mediatek/oplus6768_20761 mediatek/oplus6769_2167A "
                            "mediatek/oplus6769_216AF mediatek/oplus6769_226AF "
                            "mediatek/oplus6769_226BE")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    v, t = os.path.abspath(a.vendor), os.path.abspath(a.target)
    steps = []

    # 1. packer script
    src = os.path.join(v, "scripts/mkdtboimg.py")
    dst = os.path.join(t, "scripts/mkdtboimg.py")
    steps.append({"step": "copy scripts/mkdtboimg.py", "ok": os.path.isfile(src),
                  "identical": os.path.exists(dst) and
                  open(src, errors="replace").read() == open(dst, errors="replace").read()})
    if a.apply and os.path.isfile(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)

    # 2. Kconfig symbols
    kconf = os.path.join(t, "arch/arm64/Kconfig")
    txt = open(kconf, errors="replace").read()
    # The vendor had this block at the end of its "Build options" menu, immediately
    # before `config COMPAT`. 5.15 has no such menu (arch/arm64/Kconfig is flat) and
    # COMPAT is a `menuconfig`, so the block is inserted at that same neighbour: the
    # first `config COMPAT` / `menuconfig COMPAT` line. Same position in the file,
    # same surrounding symbols, therefore same Kconfig semantics.
    txt = open(kconf, errors="replace").read()
    m = list(re.finditer(r"^(?:menu)?config COMPAT\b.*", txt, re.M))
    has = "BUILD_ARM64_APPENDED_DTB_IMAGE" in txt
    steps.append({"step": "arch/arm64/Kconfig block (before COMPAT)",
                  "anchor_candidates": len(m), "ok": has or len(m) == 1, "already": has})
    if a.apply and len(m) == 1 and not has:
        open(kconf, "w").write(txt[:m[0].start()] + KCONFIG_BLOCK + txt[m[0].start():])

    # 3. Image.gz-dtb rule
    r = patch(os.path.join(t, "arch/arm64/boot/Makefile"),
              "\n$(obj)/Image.gz: $(obj)/Image FORCE\n\t$(call if_changed,gzip)\n",
              "\n$(obj)/Image.gz: $(obj)/Image FORCE\n\t$(call if_changed,gzip)\n"
              "\n$(obj)/Image.gz-dtb: $(obj)/Image.gz $(DTB_OBJS) FORCE\n"
              "\t$(call if_changed,cat)\n",
              must_contain="Image.gz-dtb: $(obj)/Image.gz")
    steps.append({"step": "arch/arm64/boot/Makefile Image.gz-dtb", **{k: v2 for k, v2 in r.items() if k != "new"}})
    if a.apply and r.get("new"):
        open(r["file"], "w").write(r["new"])

    # 4. arch/arm64/Makefile: KBUILD_IMAGE override + dtb/dtbo pass-through
    r = patch(os.path.join(t, "arch/arm64/Makefile"), ARCH_HEAD, ARCH_HEAD_NEW,
              must_contain="CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE")
    steps.append({"step": "arch/arm64/Makefile KBUILD_IMAGE", **{k: v2 for k, v2 in r.items() if k != "new"}})
    newtxt = r.get("new")
    if newtxt and a.apply:
        if "\n%.dtb: scripts\n" not in newtxt:
            newtxt = newtxt.replace("install: install-image := Image",
                                    DTB_RULES + "\ninstall: install-image := Image", 1)
        open(r["file"], "w").write(newtxt)

    # 5. product fragment (outside the tree: it is build configuration, not port content)
    if a.fragment:
        os.makedirs(os.path.dirname(a.fragment) or ".", exist_ok=True)
        with open(a.fragment, "w") as f:
            f.write("# even (Realme 9i / MT6769) - device image packaging, from the "
                    "4.19 vendor defconfig\n"
                    "CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE=y\n"
                    "CONFIG_IMG_GZ_DTB=y\n"
                    'CONFIG_BUILD_ARM64_APPENDED_KERNEL_IMAGE_NAME="Image.gz-dtb"\n'
                    'CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES="%s"\n'
                    "CONFIG_BUILD_ARM64_DTB_OVERLAY_IMAGE=y\n"
                    'CONFIG_BUILD_ARM64_DTB_OVERLAY_IMAGE_NAMES="%s"\n'
                    % (a.dtb_name, a.dtbo_names))
        steps.append({"step": "kconfig fragment", "path": a.fragment, "ok": True})

    res = {"steps": steps, "applied": bool(a.apply),
           "all_ok": all(s.get("ok", True) for s in steps)}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    for s in steps:
        print("%-42s %s" % (s["step"], "OK" if s.get("ok", True) and not s.get("status", "").startswith("anchor") else s.get("status", "FAIL")))
    print("wrote %s" % a.out)
    return 0 if res["all_ok"] else 1


sys.exit(main())
